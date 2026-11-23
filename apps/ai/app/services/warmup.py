"""
Keeps the model's prompt cache warm while a Voix page is connected.

Our voice prompt (rules + company context + tools) is about 28 000 tokens and identical on every call. Anthropic
caches it for 5 minutes after its last use; a call that starts after a longer pause pays for reading it all again,
in time and in price. So while a page is open we touch the cache at connection and then every 4 minutes of silence,
with the documented warm-up request: the real tools and system prompt, `max_tokens: 0`, no output at all
(https://platform.claude.com/docs/en/build-with-claude/prompt-caching). A cache read is billed at a small fraction
of the input price and no output token is produced. It changes nothing in what the agent says.

    VOICE_WARM=off in .env switches it off.

Only for the Anthropic provider (the others have no explicit cache); every failure is swallowed: warming is a
comfort, never a reason for a call to fail.
"""

import os
import time

from app.agent.prompts import build_system_prompt
from app.clients import LLMRequest, get_llm_client
from app.clients.http import http_client
from app.schemas import ChatMessage
from app.tools import all_tools

ENABLED = (os.environ.get("VOICE_WARM") or "on").strip().lower() not in ("off", "0", "false", "no")
WARM_EVERY_S = 240  # under the 5-minute cache lifetime, with a margin
STOP_AFTER_IDLE_S = 45 * 60  # a page left open with nobody calling stops costing anything after this long


async def warm_prompt_cache(actor_name: str | None = None) -> dict | None:
    """One warm-up request. → the provider's usage block ({cache_read_input_tokens, cache_creation_input_tokens, …}),
    or None when it does not apply or failed."""
    if not ENABLED or os.environ.get("PYTEST_CURRENT_TEST"):  # never from the test suite: it would call the real provider
        return None
    try:
        llm = get_llm_client()
        if getattr(llm, "provider", "") != "anthropic" or not hasattr(llm, "build_body"):
            return None
        system = await build_system_prompt("voice", actor_name)
        # exactly what a real voice turn sends first: same tools, same order, same system prompt, same effort
        body = llm.build_body(LLMRequest(system=system, messages=[ChatMessage(role="user", content="warmup")], tools=[t.info for t in all_tools()]))
        body["stream"] = False
        body["messages"] = [{"role": "user", "content": "warmup"}]  # no cache breakpoint on the placeholder message
        headers = {"x-api-key": llm.api_key, "anthropic-version": "2023-06-01"}
        http = llm.http or http_client()
        for max_tokens in (0, 1):  # 0 is the documented warm-up; 1 is the older way, if this account refuses 0
            res = await http.post(f"{llm.base_url}/v1/messages", json={**body, "max_tokens": max_tokens}, headers=headers, timeout=20)
            if res.status_code == 200:
                return res.json().get("usage") or {}
        print(f"[ai] prompt cache warm-up refused ({res.status_code}): {res.text[:200]}", flush=True)
    except Exception as e:
        print(f"[ai] prompt cache warm-up failed ({type(e).__name__}: {e})", flush=True)
    return None


class Warmer:
    """Decides when a connected page should touch the cache. The voice session tells it when the model was used."""

    def __init__(self) -> None:
        now = time.monotonic()
        self.model_used_at = float("-inf")  # never: warm at once (the clock starts near zero in a fresh container)
        self.caller_active_at = now

    def used(self) -> None:
        """A real turn just went to the model: the cache is fresh, the caller is there."""
        self.model_used_at = self.caller_active_at = time.monotonic()

    def due(self) -> bool:
        return time.monotonic() - self.model_used_at >= WARM_EVERY_S - 10

    def idle(self) -> bool:
        return time.monotonic() - self.caller_active_at > STOP_AFTER_IDLE_S
