"""Default in-memory Session backend.

Single-process, dict-backed. Pickleable (`state_dict()` / `load_state_dict()`) so it can be
passed across `asyncio` boundaries or checkpointed alongside `RunState`.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .session import SessionABC
from .session_settings import SessionSettings, resolve_session_limit

if TYPE_CHECKING:
    from ..items import TResponseInputItem


class InMemorySession(SessionABC):
    """Thread-safe in-memory Session for tests and single-process apps."""

    session_id: str
    session_settings: SessionSettings | None

    def __init__(
        self,
        session_id: str,
        *,
        session_settings: SessionSettings | None = None,
    ) -> None:
        self.session_id = session_id
        self.session_settings = session_settings
        self._items: list[TResponseInputItem] = []
        self._lock = asyncio.Lock()

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        async with self._lock:
            effective = resolve_session_limit(limit, self.session_settings)
            if effective is None:
                return list(self._items)
            return list(self._items[-effective:])

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        async with self._lock:
            self._items.extend(items)

    async def pop_item(self) -> TResponseInputItem | None:
        async with self._lock:
            if not self._items:
                return None
            return self._items.pop()

    async def clear_session(self) -> None:
        async with self._lock:
            self._items.clear()

    # ---- checkpointable helpers ----

    def state_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "items": list(self._items)}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.session_id = state.get("session_id", self.session_id)
        self._items = list(state.get("items") or [])


__all__ = ["InMemorySession"]