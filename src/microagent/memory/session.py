"""Session Protocol & ABC.

Protocol-first design: any object with the 4 async methods is a valid Session.
`SessionABC` exists for internal base-class reuse inside this repo only.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, TypeGuard, runtime_checkable

if TYPE_CHECKING:
    from ..items import TResponseInputItem
    from .session_settings import SessionSettings


@runtime_checkable
class Session(Protocol):
    """Protocol every Session implementation must satisfy."""

    session_id: str
    session_settings: SessionSettings | None = None

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Retrieve conversation history (most-recent-first when `limit` is set, else all asc)."""
        ...

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        """Append new items to history."""
        ...

    async def pop_item(self) -> TResponseInputItem | None:
        """Pop the most-recent item (used for rewind on conversation-lock retries)."""
        ...

    async def clear_session(self) -> None:
        """Delete all stored items for this session."""
        ...


class SessionABC(ABC):
    """Abstract base class for Session implementations (internal use only).

    Third-party libraries should implement the `Session` Protocol directly;
    this ABC is a convenience base for first-party implementations.
    """

    session_id: str
    session_settings: SessionSettings | None = None

    @abstractmethod
    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        raise NotImplementedError

    @abstractmethod
    async def add_items(self, items: list[TResponseInputItem]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def pop_item(self) -> TResponseInputItem | None:
        raise NotImplementedError

    @abstractmethod
    async def clear_session(self) -> None:
        raise NotImplementedError


def is_runtime_session(value: object) -> TypeGuard[Session]:
    """Duck-typing check used where an `isinstance(value, Session)` call isn't ergonomic."""
    return (
        hasattr(value, "get_items")
        and hasattr(value, "add_items")
        and hasattr(value, "pop_item")
        and hasattr(value, "clear_session")
    )


__all__ = ["Session", "SessionABC", "is_runtime_session"]