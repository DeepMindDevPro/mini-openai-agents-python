"""Best-effort progress inspection for tool-call coroutines that have been cancelled.

When a tool task is cancelled (e.g. timeout or upstream guardrail trip), the runner
sometimes wants to surface "the tool was waiting on `asyncio.sleep(30)`" so user-facing
errors are intelligible. We probe via the public coroutine-introspection API only, and
fail-safe (return ``None``) on anything we don't recognize.
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any


def get_awaitable_chain_tail(awaitable: Any, *, max_depth: int = 16) -> Any | None:
    """Walk `cr_await` / `gi_yieldfrom` / `ag_await` chains to the leaf awaitable."""
    current = awaitable
    for _ in range(max_depth):
        nxt = _next_in_chain(current)
        if nxt is None:
            return current
        current = nxt
    return current


def get_pending_sleep_deadline(
    awaitable: Any, *, loop: asyncio.AbstractEventLoop | None = None
) -> float | None:
    """If the awaitable is parked inside `asyncio.sleep`, return its wake-up timestamp."""
    target = get_awaitable_chain_tail(awaitable)
    if target is None:
        return None
    loop = loop or asyncio.get_event_loop()

    if inspect.isgenerator(target):
        code = getattr(target, "gi_code", None)
        if code is not None and code.co_name == "__sleep0":
            return loop.time()
        return None

    if not inspect.iscoroutine(target):
        return None

    frame = target.cr_frame
    if frame is None or frame.f_code.co_name != "sleep":
        return None
    delay = frame.f_locals.get("delay")
    if isinstance(delay, (int, float)):
        return loop.time() if delay <= 0 else loop.time() + float(delay)
    return None


def _next_in_chain(awaitable: Any) -> Any | None:
    if inspect.iscoroutine(awaitable):
        return awaitable.cr_await
    if inspect.isgenerator(awaitable):
        return awaitable.gi_yieldfrom
    if inspect.isasyncgen(awaitable):
        return awaitable.ag_await
    return None


__all__ = ["get_awaitable_chain_tail", "get_pending_sleep_deadline"]