"""
One push-to-talk utterance, transcribed WHILE it is recorded (used by WS /voice and WS /voice/command).

    audio_start  → Utterance(stt, mime, hint, on_partial)   opens the provider stream (if stt.streams)
    binary frame → feed(frame)                              forwarded to the provider at once
                     … on_partial(STTUpdate)                partial transcripts, to show while the caller speaks
    audio_end    → await text()                             end of audio: only the last words are left to finalize

With a streaming STT (Soniox, Deepgram, mock) the transcript is ready a few hundred ms after the release, instead
of transcribing the whole recording then. Every frame is also kept: if the live stream breaks (network, provider
error, no final words in time), text() transcribes the whole recording the classic way, so the utterance is never
lost. cancel() (barge-in, client gone) closes the provider stream.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing

from app.clients import STTClient
from app.clients.base import STTUpdate

from .vocabulary import stt_hint

FINAL_TIMEOUT_S = 5.0  # after audio_end, how long to wait for the live stream's final words before the fallback


class Utterance:
    def __init__(self, stt: STTClient, mime: str, hint: str | None, on_partial: Callable[[STTUpdate], Awaitable[None]]):
        self.stt, self.mime, self.hint, self.on_partial = stt, mime, hint, on_partial
        self.frames: list[bytes] = []
        self.ended = False
        # timing, for the "where does the STT second go" log line (see voice_session.run_turn)
        self.started_at = time.perf_counter()
        self.ended_at: float | None = None
        self.frame_at: list[float] = []  # arrival time of each audio frame
        self.partial_at: float | None = None  # when the last live transcript arrived
        self.queue: asyncio.Queue[bytes | None] = asyncio.Queue()  # frames for the live stream, None = end of audio
        self.live = asyncio.create_task(self._listen()) if stt.streams else None

    def feed(self, frame: bytes) -> None:
        self.frames.append(frame)
        self.frame_at.append(time.perf_counter())
        self.queue.put_nowait(frame)

    def end(self) -> None:
        """End of audio: tell the live stream now, so the provider starts finalizing at once (idempotent).
        Call it the moment audio_end arrives, before anything else is awaited."""
        if not self.ended:
            self.ended = True
            self.ended_at = time.perf_counter()
            self.queue.put_nowait(None)

    async def text(self) -> str:
        """Call at audio_end: the final transcript."""
        self.end()
        if self.live:
            try:
                return await asyncio.wait_for(self.live, FINAL_TIMEOUT_S)  # on timeout the stream is cancelled
            except Exception as e:
                print(f"[ai] live STT failed ({type(e).__name__}: {e}): transcribing the whole recording", flush=True)
        hint = await stt_hint(self.stt.name, self.hint)
        return await self.stt.transcribe(b"".join(self.frames), self.mime, hint)

    def timing(self, partial: str, final: str) -> str:
        """One log line that says where the time between the key release and the final transcript went:
        was audio still arriving in a burst at the end (browser buffering), had the live transcript fallen behind,
        or did the provider take long after the end-of-audio signal?"""
        end = self.ended_at or time.perf_counter()
        ms = lambda t: int((t) * 1000 + 0.5)  # noqa: E731
        n = len(self.frame_at)
        late = sum(1 for t in self.frame_at if end - t <= 0.3)
        gaps = [b - a for a, b in zip(self.frame_at, self.frame_at[1:])]
        return (
            f"[ai] stt timing: audio {ms(end - self.started_at)} ms in {n} frames ({sum(map(len, self.frames))} bytes), "
            f"first frame after {ms(self.frame_at[0] - self.started_at) if n else -1} ms, longest gap {ms(max(gaps)) if gaps else 0} ms, "
            f"{late} frame(s) in the last 300 ms, last frame {ms(end - self.frame_at[-1]) if n else -1} ms before the end; "
            f"live transcript {len(partial.split())} word(s), last update {ms(end - self.partial_at) if self.partial_at else -1} ms before the end; "
            f"final {len(final.split())} word(s) {ms(time.perf_counter() - end)} ms after the end"
        )

    def cancel(self) -> None:
        if not self.live:
            return
        if not self.live.done():
            self.live.cancel()
        elif not self.live.cancelled():
            self.live.exception()  # a stream that already failed: nobody will read it, that's fine

    async def _audio(self) -> AsyncIterator[bytes]:
        while (frame := await self.queue.get()) is not None:
            yield frame

    async def _listen(self) -> str:
        hint = await stt_hint(self.stt.name, self.hint)  # cached; frames wait in the queue meanwhile
        shown = None
        # aclosing: leaving early (final words, cancellation) closes the provider's socket right away
        async with aclosing(self.stt.transcribe_stream(self._audio(), self.mime, hint)) as updates:  # type: ignore[type-var]
            async for update in updates:
                if update.final:
                    return update.text
                if update.text != shown:
                    shown = update.text
                    self.partial_at = time.perf_counter()
                    await self.on_partial(update)
        return shown or ""
