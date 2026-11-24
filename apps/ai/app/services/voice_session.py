"""
WS /voice — push-to-talk voice sessions (messages: app/schemas/voice.py).

One turn:
    audio_start … binary frames … audio_end   (or a typed `text` message)
      → STT, live: each frame goes to the provider as it arrives (services/utterance.py);
        "transcript" final:false while the caller speaks, then "transcript" final:true soon after audio_end
      → agent (voice mode) streaming "agent_text" / "agent_tool"
      → each finished sentence goes to TTS right away (sentence by sentence = first audio sooner)
      → "agent_audio_start" {mime}, binary audio chunks…, "agent_audio_end"   (one audio segment per turn)
      → "agent_done" {text, timings}

Barge-in: a new audio_start / text while the agent is still busy cancels the running turn (asyncio
cancellation); what was heard and said so far stays in the history.
"""

import asyncio
import json
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import aclosing, suppress
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from app.agent import run_agent, sanitize_history
from app.agent.loop import ms_since
from app.clients import STTUpdate, TTSClient, get_llm_client, get_stt_client, get_tts_client
from app.config import settings
from app.schemas import (
    AgentAudioEndMessage,
    AgentAudioStartMessage,
    AgentDoneMessage,
    AgentTextMessage,
    AgentToolMessage,
    AudioEndMessage,
    AudioStartMessage,
    ChatMessage,
    ErrorEvent,
    ReadyMessage,
    ResetMessage,
    StartMessage,
    TextEvent,
    TextMessage,
    ToolCallEvent,
    ToolResultEvent,
    TranscriptMessage,
    TurnTimings,
    VoiceClientMessage,
    VoiceErrorMessage,
)
from app.schemas.base import WireModel
from app.tools import ErpClient, all_tools

from app.clients.mock_speech import silent_wav
from app.schemas import MOCK_TTS_MIME

from . import truck_calls
from .call_prep import ack_note, choose_ack, is_aside, is_waiting_phrase, said_goodbye
from .call_report import write_report
from .warmup import WARM_EVERY_S, Warmer, warm_prompt_cache
from .utterance import Utterance
from .vocabulary import stt_hint

client_message = TypeAdapter(VoiceClientMessage)

# Messages kept per call. A call is one conversation: with 40 (about ten turns) the client's card, fetched on the first
# turn, fell out of the history mid-call and the agent lost the ids it needs to edit the order.
CALL_MEMORY = 200
# Longest text spoken before a tool call ("Je regarde ça tout de suite.").
MAX_WAIT_WORDS = 5
REPORTS: set[asyncio.Task] = set()  # call reports being written (they outlive the turn that started them)
# After a TTS failure the provider is left alone for this long and the browser's voice speaks instead.
TTS_RETRY_AFTER_S = 60
TTS_HEALTH = {"down_until": 0.0}  # time.monotonic() until which the provider is considered down
# A live transcript shorter than this is not trusted to choose the instant words (see run_turn).
MIN_PARTIAL_WORDS = 4
# A typed turn « /appel ord_020798 » (the page's "Appeler" button sends exactly that): the agent calls that client
# about his delivery of this morning and speaks first (services/truck_calls.py).
OUTGOING = re.compile(r"^\s*/appel\s+(ord_\w+)\s*$", re.I)


@dataclass
class Conversation:
    id: str
    actor_name: str | None = None
    history: list[ChatMessage] = field(default_factory=list)
    acks: list[str] = field(default_factory=list)  # the opening word of each turn so far ("" = none), oldest first
    reported: int = 0  # length of `history` when the last call report was written (services/call_report.py)


# In memory: a reconnect with the same sessionId continues the conversation.
conversations: dict[str, Conversation] = {}


class VoiceConnection:
    """One WebSocket connection. Reads client messages; runs each turn as a background task."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.conversation: Conversation | None = None
        self.recording: Utterance | None = None  # while the key is down
        self.last_partial = ""  # live transcript of the recording in progress (for the instant acknowledgement)
        self.turn: asyncio.Task | None = None
        self.warmer = Warmer()
        self.warming: asyncio.Task | None = None  # keeps the model's prompt cache warm while the page is connected
        self.warm_up: asyncio.Task | None = None
        self._send_lock = asyncio.Lock()

    # ── sending ──

    async def send(self, msg: WireModel) -> None:
        await self._send(text=msg.to_json())

    async def send_bytes(self, data: bytes) -> None:
        await self._send(bytes=data)

    async def _send(self, **message) -> None:
        async with self._send_lock:
            with suppress(WebSocketDisconnect, RuntimeError):  # the client is gone: nothing to do
                if message.get("text") is not None:
                    await self.ws.send_text(message["text"])
                else:
                    await self.ws.send_bytes(message["bytes"])

    # ── receiving ──

    async def keep_warm(self) -> None:
        """While this page is connected: touch the model's prompt cache now, then after every 4 minutes without a
        turn, so the first answer of a call never pays for a cold cache (services/warmup.py)."""
        for _ in range(30):  # the page sends "start" right after connecting: wait for it (who is calling shapes the prompt)
            if self.conversation:
                break
            await asyncio.sleep(0.1)
        while not self.warmer.idle():
            if self.warmer.due():
                await warm_prompt_cache(self.conversation.actor_name if self.conversation else None)
                self.warmer.model_used_at = time.monotonic()
            await asyncio.sleep(WARM_EVERY_S / 8)

    def start_warming(self) -> None:
        if self.warming is None or self.warming.done():
            self.warming = asyncio.create_task(self.keep_warm())

    async def serve(self) -> None:
        await self.ws.accept()
        self.start_warming()
        try:
            while True:
                frame = await self.ws.receive()
                if frame["type"] == "websocket.disconnect":
                    break
                if frame.get("bytes") is not None:
                    if self.recording:
                        self.recording.feed(frame["bytes"])
                    continue
                await self.handle_text(frame.get("text") or "")
        except WebSocketDisconnect:
            pass
        finally:
            if self.warming:
                self.warming.cancel()
            await self.interrupt()
            await self.report_call()  # the caller hung up

    async def report_call(self) -> None:
        """Write the call report to the client's history (once per call; again only if the call went on after it).
        Best effort: a report that cannot be written must never break a call.

        The write runs as its own task: the goodbye turn that starts it can be cancelled a moment later (the caller
        hangs up, "Nouvelle session"), and a report cancelled halfway was simply lost, because the hang-up then
        found it already marked as written. Now the write goes on by itself, and if it fails the mark is taken back
        so the next end-of-call tries again."""
        conv = self.conversation
        if not conv or len(conv.history) <= conv.reported:
            return
        start, conv.reported = conv.reported, len(conv.history)  # claimed now: a hang-up right behind us must not write it twice
        history, actor = list(conv.history), conv.actor_name

        async def write() -> None:
            try:
                await asyncio.wait_for(write_report(ErpClient("voice_agent", actor), history, start), 6)
            except Exception:
                conv.reported = min(conv.reported, start)  # not written: try again at the next end-of-call

        task = asyncio.create_task(write())
        REPORTS.add(task)  # keep a reference until it is done
        task.add_done_callback(REPORTS.discard)
        with suppress(Exception):
            await asyncio.shield(task)  # if we are cancelled here, the write itself carries on

    async def handle_text(self, raw: str) -> None:
        try:
            msg = client_message.validate_python(json.loads(raw))
        except (json.JSONDecodeError, ValidationError):
            await self.send(VoiceErrorMessage(message="invalid JSON message"))
            return
        if not self.conversation and not isinstance(msg, StartMessage):
            await self.open()  # no "start" yet: open a fresh conversation

        match msg:
            case StartMessage(session_id=session_id, actor_name=actor_name):
                await self.interrupt()
                if self.conversation and session_id != self.conversation.id:
                    await self.report_call()  # a new call starts: close the previous one
                await self.open(session_id, actor_name)
            case AudioStartMessage(mime=mime, hint=hint):
                await self.interrupt()  # barge-in
                self.last_partial = ""
                self.recording = Utterance(get_stt_client(), mime, hint, on_partial=self.send_partial)
            case AudioEndMessage():
                if self.recording:
                    utterance, self.recording = self.recording, None
                    utterance.end()  # the STT finalizes from this instant, not after the turn has been set up
                    self.start_turn(utterance=utterance, partial=self.last_partial)
            case TextMessage(text=text):
                await self.interrupt()
                if order := OUTGOING.match(text or ""):
                    await self.call_out(order.group(1))
                else:
                    self.start_turn(text=text)
            case ResetMessage():
                await self.interrupt()
                await self.report_call()  # "Nouvelle session": the call is over
                self.conversation.history = []
                self.conversation.acks = []
                self.conversation.reported = 0
                await self.open(self.conversation.id)

    async def call_out(self, order_id: str) -> None:
        """Outgoing call before the truck leaves: a new call starts (the previous one is reported and closed), the
        client's file and the facts of the call are fetched in code, and the agent speaks first."""
        conv = self.conversation
        await self.report_call()
        conv.history, conv.acks, conv.reported = [], [], 0
        try:
            opening = await truck_calls.opening(ErpClient("voice_agent", conv.actor_name), order_id)
        except Exception as e:  # unknown order, nothing missing on it, ERP down: say why, start nothing
            await self.send(VoiceErrorMessage(message=str(e) or type(e).__name__))
            return
        self.start_turn(text=opening.label, opening=opening)

    async def send_partial(self, update: STTUpdate) -> None:
        self.last_partial = update.text
        await self.send(TranscriptMessage(text=update.text, final=False, stable=update.stable))

    async def open(self, session_id: str | None = None, actor_name: str | None = None) -> None:
        conv = conversations.get(session_id or "") or Conversation(id=session_id or str(uuid.uuid4()))
        if actor_name:
            conv.actor_name = actor_name
        conversations[conv.id] = self.conversation = conv
        llm = get_llm_client()
        await self.send(
            ReadyMessage(session_id=conv.id, stt=get_stt_client().name, tts=get_tts_client().name, llm=f"{llm.provider}:{llm.model}")
        )
        # Fetch the company vocabulary for the STT now, not when the caller first speaks.
        self.warm_up = self.warm_up or asyncio.create_task(stt_hint(get_stt_client().name, None))

    def start_turn(self, **turn_input) -> None:
        self.warmer.used()
        self.start_warming()  # (it stops by itself after a long silence: a new turn starts it again)
        self.turn = asyncio.create_task(self.run_turn(self.conversation, **turn_input))

    async def interrupt(self) -> None:
        """Barge-in: drop a recording in progress, stop the running turn and wait until it has cleaned up."""
        if self.recording:
            self.recording.cancel()
            self.recording = None
        if self.turn and not self.turn.done():
            self.turn.cancel()
            with suppress(asyncio.CancelledError):
                await self.turn
        self.turn = None

    # ── one turn ──

    async def run_turn(
        self,
        conv: Conversation,
        text: str | None = None,
        utterance: Utterance | None = None,  # spoken: already being transcribed since audio_start
        partial: str = "",  # spoken: the live transcript at the moment the key was released
        opening: "truck_calls.Opening | None" = None,  # outgoing call: nobody spoke yet, the agent opens (see call_out)
    ) -> None:
        t0 = time.perf_counter()  # end of caller speech
        timings = TurnTimings()
        heard, spoken = "", ""
        step_text = ""  # what the model said since the last tool result (not yet in `working`)
        working: list[ChatMessage] | None = None
        committed = False
        speaker: Speaker | None = None
        try:
            # 0. Instant acknowledgement ("Bonjour Christian.", "D'accord.") from the live transcript: spoken while
            #    the STT finalizes and the model thinks. Chosen in code (services/call_prep.py), never a fact.
            heard = (text or "").strip()  # a typed turn is known at once (kept if the turn is interrupted early)
            # The page shows exactly what goes to the voice, sentence by sentence: a remark the model makes before
            # calling a tool, which we do not speak, is not displayed either.
            to_show: list[str] = []
            speaker = Speaker(get_tts_client(), self.send, self.send_bytes, on_sentence=to_show.append)

            async def show() -> None:
                nonlocal spoken
                while to_show:
                    sentence = to_show.pop(0).strip()
                    spoken += f"{sentence} "
                    await self.send(AgentTextMessage(delta=f"{sentence} "))

            erp = ErpClient("voice_agent", conv.actor_name)
            blocked = any(m.role == "tool" and m.name == "identify_caller" and '"BLOCKED"' in (m.content or "") for m in conv.history)
            # The live transcript often lags a few words behind the voice. On a short one ("Ou", "Attends, attends")
            # the words were chosen for the wrong kind of turn ("Je vérifie." after a yes) or not at all, and the
            # caller then waited the whole STT + model time in silence. So: a typed turn or a live transcript of a
            # few words is trusted at once; otherwise we choose again below, on the final transcript.
            early = text or (partial if len(partial.split()) >= MIN_PARTIAL_WORDS else "")
            ack = ""
            if early and not opening:  # (an outgoing call opens with the agent's own first sentence, no instant word)
                with suppress(Exception):
                    ack = await choose_ack(early, not conv.history, erp, conv.acks, blocked)
            if ack:
                speaker.speak(ack)
                await show()

            # 1. Speech → text: with a streaming STT only the last words are left to finalize
            if utterance is not None:
                text = await utterance.text()
                timings.stt_ms = ms_since(t0)  # end of speech → final transcript
                with suppress(Exception):
                    print(utterance.timing(partial, text or ""), flush=True)
            heard = (text or "").strip()
            if not heard:
                await speaker.finish()
                await self.send(VoiceErrorMessage(message="Rien entendu — réessayez."))
                return
            await self.send(TranscriptMessage(text=heard, final=True))
            if opening:  # the client's card and the facts of the call go to the page like any tool result
                for name, args, result in opening.tools:
                    await self.send(AgentToolMessage(name=name, args=args))
                    await self.send(AgentToolMessage(name=name, ok=True, ms=0, result=result))
            if not ack and utterance is not None:  # second chance, on the full sentence, while the model starts
                with suppress(Exception):
                    ack = await choose_ack(heard, not conv.history, erp, conv.acks, blocked)
                if ack:
                    speaker.speak(ack)
                    await show()
            conv.acks.append(ack)

            # 2. Agent, on a working copy of the history (committed at the end). The model is told what was already
            #    said aloud. (The agent loop identifies the caller in code before the first model step.)
            working = [*conv.history, ChatMessage(role="user", content=f"{heard}\n\n{ack_note(ack)}" if ack else heard)]
            if opening:
                working = list(opening.messages)
            llm_start = time.perf_counter()
            async for ev in run_agent(working, llm=get_llm_client(), tools=all_tools(), mode="voice", actor_name=conv.actor_name):
                match ev:
                    case TextEvent(delta=delta):
                        if timings.llm_first_token_ms is None:
                            timings.llm_first_token_ms = ms_since(llm_start)
                        step_text += delta
                        speaker.push(delta)
                        await show()
                    case ToolCallEvent(call=call):
                        # Speak what was said before the tool ("Je regarde.") now, not when the tool comes back:
                        # the sentence splitter waits for a space after the full stop, which only arrives with
                        # the text of the next step, i.e. after the whole tool round-trip.
                        # Only a short waiting phrase is worth saying there. A longer text before a tool is the
                        # model thinking aloud ("pas de commande existante, je la crée") : not for the caller.
                        if ack or len(step_text.split()) > MAX_WAIT_WORDS or not is_waiting_phrase(step_text):
                            speaker.drop()  # (after an ack we already said something: the step comment stays unspoken)
                        else:
                            speaker.flush()
                        await show()
                        await self.send(AgentToolMessage(name=call.name, args=call.arguments))
                    case ToolResultEvent(name=name, ok=ok, ms=ms, result=result):
                        step_text = ""
                        # the result goes to the page too: the Voix page draws the client and order cards from it
                        await self.send(AgentToolMessage(name=name, ok=ok, ms=ms, result=result))
                    case ErrorEvent(message=message):
                        await self.send(VoiceErrorMessage(message=message))
                        sorry = "Excusez-moi, j'ai un souci technique. Vous pouvez répéter ?"
                        speaker.speak(sorry)
                        await show()
            timings.llm_total_ms = ms_since(llm_start)
            conv.history = trim(working, CALL_MEMORY)
            committed = True

            # 3. Speak the last sentence and wait until all the audio is sent
            speaker.flush()
            await show()
            await speaker.finish()
            timings.tts_first_byte_ms = speaker.tts_first_byte_ms
            if speaker.first_byte_at:
                timings.total_ms = int((speaker.first_byte_at - t0) * 1000 + 0.5)
            await self.send(AgentDoneMessage(text=spoken.strip(), timings=timings))
            if said_goodbye(heard):  # "merci, au revoir": the report is in the ERP before he has hung up
                await self.report_call()

        except asyncio.CancelledError:
            # Interrupted: keep what was heard, the tool rounds already done (an order the agent created must stay
            # known) and what the agent had started to say. Not when the turn was already committed (barge-in during
            # the last sentence's audio): that would duplicate it. trim() closes a tool call cut mid-run.
            if heard and not committed:
                kept = working if working is not None else [*conv.history, ChatMessage(role="user", content=heard)]
                last = kept[-1]
                if step_text.strip() and not (last.role == "assistant" and last.tool_calls):
                    kept = [*kept, ChatMessage(role="assistant", content=f"{step_text.strip()} …")]
                conv.history = trim(kept, CALL_MEMORY)
            if speaker:
                await speaker.stop()
            raise
        except Exception as e:
            await self.send(VoiceErrorMessage(message=str(e) or type(e).__name__))
            if speaker:
                await speaker.stop()  # close the audio segment: the page must not wait for sound that will not come
        finally:
            if utterance:
                utterance.cancel()  # interrupted while transcribing: close the provider stream


class Speaker:
    """Buffers the streamed text, cuts it into sentences and speaks them in order, as one audio segment."""

    # a sentence ends with . ! ? … followed by a space ("18.50" is not a boundary)
    SENTENCE = re.compile(r"^([\s\S]*?[.!?…])\s+")

    def __init__(
        self,
        tts: TTSClient,
        send: Callable[[WireModel], Awaitable],
        send_bytes: Callable[[bytes], Awaitable],
        on_sentence: Callable[[str], None] | None = None,  # called with each sentence as it goes to the TTS
    ):
        self.tts, self.send, self.send_bytes, self.on_sentence = tts, send, send_bytes, on_sentence
        self.buffer = ""
        self.sentences: asyncio.Queue[str | None] = asyncio.Queue()
        self.worker: asyncio.Task | None = None  # speaks the queued sentences one after the other
        self.started = False
        self.fallback = False  # this turn is spoken by the browser's voice (the provider failed)
        self.first_byte_at: float | None = None
        self.tts_first_byte_ms: int | None = None

    def push(self, delta: str) -> None:
        self.buffer += delta
        while m := self.SENTENCE.match(self.buffer):
            self.speak(m[1])
            self.buffer = self.buffer[m.end() :]

    def speak(self, sentence: str) -> None:
        if not sentence.strip():
            return
        if is_aside(sentence):  # the model talking about the caller or its rules, not to him: never spoken or shown
            print(f"[ai] aside not spoken: {sentence.strip()[:160]}", flush=True)
            return
        if self.worker is None:
            self.worker = asyncio.create_task(self._speak_queued())
        if self.on_sentence:
            self.on_sentence(sentence)
        self.sentences.put_nowait(sentence)

    def flush(self) -> None:
        """Speak whatever is buffered right away (used when the model pauses to call a tool)."""
        if self.buffer.strip():
            self.speak(self.buffer)
        self.buffer = ""

    def drop(self) -> None:
        """Forget what is buffered and not yet sent to the TTS (a remark the model made before calling a tool)."""
        self.buffer = ""

    async def finish(self) -> None:
        """Speak what is left in the buffer, wait for all the audio, close the segment."""
        self.speak(self.buffer)
        self.buffer = ""
        if self.worker:
            self.sentences.put_nowait(None)
            await self.worker
        if self.started:
            await self.send(AgentAudioEndMessage())

    async def stop(self) -> None:
        """Interrupted: drop the queued sentences, close the segment if audio was sent."""
        if self.worker:
            self.worker.cancel()
            with suppress(asyncio.CancelledError):
                await self.worker
        if self.started:
            await self.send(AgentAudioEndMessage())

    async def _browser_voice(self) -> None:
        """Hand this turn to the browser's own French voice: the page speaks the whole answer when the turn ends
        (the path the mock TTS already uses). Slower to start than the real voice, but never silent."""
        if not self.started:
            self.started = True
            await self.send(AgentAudioStartMessage(mime=MOCK_TTS_MIME))
            self.first_byte_at = time.perf_counter()
            await self.send_bytes(silent_wav(0.1))

    async def _speak_queued(self) -> None:
        while (sentence := await self.sentences.get()) is not None:
            if time.monotonic() < TTS_HEALTH["down_until"]:
                if self.started and not self.fallback:
                    continue  # real audio already went out this turn: the rest of it stays text only
                self.fallback = True
                await self._browser_voice()
                continue
            tts_start = time.perf_counter()
            try:
                result = await self.tts.synthesize(sentence, settings.tts.voice or None)
                # aclosing: on barge-in (cancellation) the provider's HTTP stream is closed right away
                async with aclosing(result.chunks) as chunks:  # type: ignore[type-var]
                    async for chunk in chunks:
                        if not self.started:
                            self.started = True
                            await self.send(AgentAudioStartMessage(mime=result.mime))
                            self.first_byte_at = time.perf_counter()
                            self.tts_first_byte_ms = ms_since(tts_start)
                        await self.send_bytes(chunk)
            except Exception as e:
                # The voice provider is down (key refused, quota used up, network). Do not try it again for a
                # minute, say so once, and let the browser speak instead: a demo must never go silent.
                TTS_HEALTH["down_until"] = time.monotonic() + TTS_RETRY_AFTER_S
                await self.send(VoiceErrorMessage(message=f"TTS indisponible, voix de secours du navigateur. ({str(e)[:160]})"))
                if not self.started:
                    self.fallback = True
                    await self._browser_voice()


def trim(history: list[ChatMessage], max_messages: int = 40) -> list[ChatMessage]:
    """Keep the last ~40 messages, starting on a user message (never split a tool call from its result)."""
    history = sanitize_history(history)  # no dangling tool call (cancelled mid-tool), no orphan result
    if len(history) <= max_messages:
        return history
    start = next((i for i, m in enumerate(history) if i >= len(history) - max_messages and m.role == "user"), -1)
    return history[start:] if start > 0 else history

