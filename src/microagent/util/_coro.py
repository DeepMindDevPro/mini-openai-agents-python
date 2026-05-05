"""Coroutine helpers."""
from __future__ import annotations

import inspect
from typing import Any

from ._types import MaybeAwaitable, T


async def resolve(value: MaybeAwaitable[T]) -> T:
    """Await `value` if it is awaitable, otherwise return it."""
    if inspect.isawaitable(value):
        return await value  # type: ignore[no-any-return]
    return value  # type: ignore[return-value]


noop: Any = None