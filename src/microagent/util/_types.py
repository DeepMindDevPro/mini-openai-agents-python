"""Shared type aliases."""
from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar, Union

T = TypeVar("T")
MaybeAwaitable = Union[T, Awaitable[T]]