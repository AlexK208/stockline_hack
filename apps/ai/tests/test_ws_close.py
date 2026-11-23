"""open_ws must hand back the provider's result without waiting for the close handshake.

Soniox answers `finalize` in 0,1–0,35 s but takes 1,1–1,3 s to acknowledge a close; awaiting that close held every
final transcript back by over a second (measured 2026-11-24, lane B)."""

import asyncio
import time

from app.clients import ws as ws_module


class SlowCloseSocket:
    def __init__(self, close_s: float):
        self.close_s, self.closed = close_s, False

    async def close(self) -> None:
        await asyncio.sleep(self.close_s)
        self.closed = True


async def test_leaving_open_ws_does_not_wait_for_a_slow_close(monkeypatch):
    sock = SlowCloseSocket(close_s=0.5)

    async def fake_connect(*_args, **_kwargs):
        return sock

    monkeypatch.setattr(ws_module, "connect", fake_connect)

    t0 = time.perf_counter()
    async with ws_module.open_ws("wss://example.invalid", {}, "test"):
        pass
    assert time.perf_counter() - t0 < 0.1  # the result is free at once, not after the 0,5 s close
    assert not sock.closed

    await asyncio.sleep(0.6)
    assert sock.closed  # the close still happens, in the background


async def test_a_failing_close_is_swallowed(monkeypatch):
    class BrokenClose:
        async def close(self) -> None:
            raise OSError("socket already gone")

    async def fake_connect(*_args, **_kwargs):
        return BrokenClose()

    monkeypatch.setattr(ws_module, "connect", fake_connect)
    async with ws_module.open_ws("wss://example.invalid", {}, "test"):
        pass
    await asyncio.sleep(0.05)
    assert not ws_module._closing  # the task is done and forgotten, its error retrieved (no "never retrieved" warning)
