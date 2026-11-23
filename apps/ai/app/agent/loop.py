"""
The agent loop — the heart of the service.

    system prompt + conversation ──► model ──► text? ──────────────► stream it ──► done
                                       │
                                       └► tool calls ─► run them (ERP API) ─► append results ─► model again …

`run_agent` is an async generator of ChatStreamEvent: exactly the events POST /chat streams.
It APPENDS the new assistant / tool messages to `messages`, so a caller that keeps that list
(voice session, CLI) keeps the full history, including the ids returned by tools.

Interrupting: cancel the task that iterates it (asyncio). Nothing is yielded after a cancellation.
"""

import asyncio
import json
import time
import traceback
import uuid
from collections.abc import AsyncIterator

from app.clients import LLMClient, LLMRequest, LLMText, LLMToolCall, LLMUsage
from app.config import settings
from app.schemas import (
    ChatMessage,
    ChatMode,
    ChatStreamEvent,
    DoneEvent,
    ErrorEvent,
    TextEvent,
    ToolCall,
    ToolCallEvent,
    ToolResultEvent,
    Usage,
)
from app.tools import ErpClient, Tool, ToolContext
from app.tools.desk import prefetch_identify

from .prompts import build_system_prompt

GIVE_UP = "Désolé, je n'ai pas réussi à aller au bout. Pouvez-vous reformuler ?"


async def run_agent(
    messages: list[ChatMessage],  # conversation so far, ending with the user's message (no system message)
    *,
    llm: LLMClient,
    tools: list[Tool],
    mode: ChatMode = "chat",  # command = single turn, act-first
    actor_name: str | None = None,
    max_steps: int | None = None,
) -> AsyncIterator[ChatStreamEvent]:
    started = time.perf_counter()
    actor = "ai_chat" if mode == "chat" else "voice_agent"
    ctx = ToolContext(erp=ErpClient(actor, actor_name), actor=actor)
    usage = Usage(input_tokens=0, output_tokens=0)

    try:
        system = await build_system_prompt(mode, actor_name)
        # Start of a call: when what the caller said matches exactly ONE client, run identify_caller here, in code,
        # and hand its result to the model as if it had called the tool: one model round-trip less before the answer.
        # Only before identify_caller has run at all: once the agent has asked "lequel ?", the answer ("celui de la
        # place", "c'est Julien") is for the model to resolve with the candidates, not for a fresh match.
        asked_before = any(m.role == "tool" and m.name == "identify_caller" for m in messages)
        if mode == "voice" and messages and messages[-1].role == "user" and not asked_before and any(t.name == "identify_caller" for t in tools):
            pre_started = time.perf_counter()
            said = messages[-1].content.split("\n\n[Système", 1)[0]
            found = await prefetch_identify(said, ctx.erp)
            if found:
                call = ToolCall(id=f"pre_{uuid.uuid4().hex[:16]}", name="identify_caller", arguments={"said": found[0]})
                yield ToolCallEvent(call=call)
                messages.append(ChatMessage(role="assistant", content="", tool_calls=[call]))
                messages.append(ChatMessage(role="tool", tool_call_id=call.id, name=call.name, content=to_json(found[1])))
                yield ToolResultEvent(call_id=call.id, name=call.name, ok=True, result=found[1], ms=ms_since(pre_started))

        request = LLMRequest(system=system, messages=messages, tools=[t.info for t in tools])
        said_something = False

        for _step in range(max_steps or settings.max_steps):
            # 1. Ask the model. Stream the text as it comes; collect the tool calls.
            text = ""
            calls: list[ToolCall] = []
            async for ev in llm.stream(request):
                match ev:
                    case LLMText(delta=delta):
                        # keep words apart when the model speaks again after a tool call
                        shown = f" {delta}" if said_something and not text and not delta[:1].isspace() else delta
                        text += delta
                        yield TextEvent(delta=shown)
                    case LLMToolCall(call=call):
                        calls.append(call)
                        yield ToolCallEvent(call=call)
                    case LLMUsage(input_tokens=i, output_tokens=o, cache_creation_input_tokens=cw, cache_read_input_tokens=cr):
                        usage.input_tokens += i or 0
                        usage.output_tokens += o or 0
                        if cw is not None:
                            usage.cache_creation_input_tokens = (usage.cache_creation_input_tokens or 0) + cw
                        if cr is not None:
                            usage.cache_read_input_tokens = (usage.cache_read_input_tokens or 0) + cr
            said_something = said_something or bool(text)

            # 2. No tool call → that was the final answer.
            if not calls:
                message = ChatMessage(role="assistant", content=text)
                messages.append(message)
                yield DoneEvent(message=message, usage=usage, ms=ms_since(started))
                return

            # 3. Run the tools (in parallel), append the results, loop.
            messages.append(ChatMessage(role="assistant", content=text, tool_calls=calls))
            if mode == "voice":  # a client is on the phone: the tools only work on that client (see call_guard)
                ctx.on_call, ctx.caller, ctx.heard = True, known_caller(messages), last_heard(messages)
            results = await execute_all(calls, tools, ctx)
            # All results go into the history BEFORE the first yield: if the caller interrupts while we stream them,
            # an order that was written stays known and is not created a second time.
            messages.extend(ChatMessage(role="tool", tool_call_id=r.call_id, name=r.name, content=to_json(r.result)) for r in results)
            for r in results:
                yield r

        # Safety net: the model kept calling tools.
        message = ChatMessage(role="assistant", content=GIVE_UP)
        messages.append(message)
        yield TextEvent(delta=GIVE_UP)
        yield DoneEvent(message=message, usage=usage, ms=ms_since(started))
    except Exception as e:  # provider down, bad key… (a cancellation is not an Exception: it just stops us)
        print("[agent] erreur pendant le tour :", flush=True)
        traceback.print_exc()
        yield ErrorEvent(message=str(e) or type(e).__name__)


async def execute_all(calls: list[ToolCall], tools: list[Tool], ctx: ToolContext) -> list[ToolResultEvent]:
    """Run the tool calls of one step in parallel, except the calls on the same order: those run one after the
    other, in the order the model wrote them. Two edits of one order then never cross, and the last result is the
    order as it ends up (no get_order needed to read it back). Results come back in call order."""
    results: list[ToolResultEvent | None] = [None] * len(calls)
    chains: dict[str, list[int]] = {}
    for i, call in enumerate(calls):
        order_id = (call.arguments or {}).get("orderId")
        chains.setdefault(order_id if isinstance(order_id, str) and order_id else f"#{i}", []).append(i)

    async def run_chain(indexes: list[int]) -> None:
        for i in indexes:
            results[i] = await execute_tool(calls[i], tools, ctx)

    await asyncio.gather(*(run_chain(indexes) for indexes in chains.values()))
    return [r for r in results if r is not None]


async def execute_tool(call: ToolCall, tools: list[Tool], ctx: ToolContext) -> ToolResultEvent:
    """Run one tool call. Never raises: errors become `{"error": ...}` so the model can explain or retry."""
    started = time.perf_counter()
    tool = next((t for t in tools if t.name == call.name), None)
    try:
        if not tool:
            raise LookupError(f"Outil inconnu : {call.name}")
        await call_guard(call, ctx)
        result = await tool.run(call.arguments, ctx)
        try:  # a value the model can't read back (datetime, set, object…) is the tool's error, not the turn's
            to_json(result)
        except (TypeError, ValueError) as e:
            raise TypeError(f"résultat de {call.name} non sérialisable en JSON : {e}") from e
        ok = True
    except Exception as e:
        print(f"[tool {call.name}] erreur :", flush=True)
        traceback.print_exc()
        ok, result = False, {"error": str(e) or type(e).__name__}
    return ToolResultEvent(call_id=call.id, name=call.name, ok=ok, result=result, ms=ms_since(started))


def caller_known(messages: list[ChatMessage]) -> bool:
    """True once identify_caller has returned a client card in this conversation."""
    return known_caller(messages) is not None


def known_caller(messages: list[ChatMessage]) -> str | None:
    """Id of the client on the phone: the last card identify_caller returned in this conversation.
    (Parsed, not searched as text: a history sent back by a client of POST /chat is not always compact JSON.)"""
    for m in reversed(messages):
        if m.role == "tool" and m.name == "identify_caller":
            try:
                result = json.loads(m.content or "")
                if result.get("status") == "found":
                    return result["client"]["id"]
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
    return None


def last_heard(messages: list[ChatMessage]) -> str:
    """The caller's last sentence as transcribed, without the notes the voice session adds for the model."""
    said = next((m.content or "" for m in reversed(messages) if m.role == "user"), "")
    return said.split("\n\n[Système", 1)[0]


OTHER_CLIENT = (
    "Refusé : pendant un appel, les outils ne servent que le client qui appelle. Les commandes, prix et informations "
    "d'un autre client sont confidentiels : dis-le simplement, sans rien citer de l'autre client."
)
NOT_IDENTIFIED = "Refusé : identifie d'abord l'appelant avec identify_caller (nom du commerce, ville). Rien ne s'écrit ni ne se lit avant."


async def call_guard(call: ToolCall, ctx: ToolContext) -> None:
    """One call = one client. On the phone, a tool that names a client or an order only runs for the caller's own.
    The prompt says so too, but a rule the model can forget is not a guarantee: this one is in code. Raises to refuse."""
    if not ctx.on_call or call.name == "identify_caller":
        return
    args = call.arguments or {}
    client_ids = {v for v in args.values() if isinstance(v, str) and v.startswith("cli_")}
    order_id = args.get("orderId") or args.get("order_id")
    if not client_ids and not order_id:
        return
    if not ctx.caller:
        raise PermissionError(NOT_IDENTIFIED)
    if client_ids - {ctx.caller}:
        raise PermissionError(OTHER_CLIENT)
    if order_id:
        try:
            order = await ctx.erp.get(f"/api/orders/{order_id}")
        except Exception:
            return  # unknown order: the tool reports it itself
        owner = order.get("clientId") or (order.get("client") or {}).get("id")
        if owner and owner != ctx.caller:
            raise PermissionError(OTHER_CLIENT)


def ms_since(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000 + 0.5)


def to_json(value) -> str:
    """Compact JSON, accents kept (what the model reads back)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
