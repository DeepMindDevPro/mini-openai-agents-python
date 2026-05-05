"""Session helper types."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..util._types import MaybeAwaitable

if TYPE_CHECKING:
    from ..items import TResponseInputItem

SessionInputCallback = Callable[
    [list["TResponseInputItem"], list["TResponseInputItem"]],
    MaybeAwaitable[list["TResponseInputItem"]],
]
"""Merge history + new input. Given `(history_items, new_items)`, returns the combined list."""

__all__ = ["SessionInputCallback"]