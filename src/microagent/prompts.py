"""Prompt shapes.

Two kinds:

- **DynamicPromptFunction** — a callable that returns instructions at runtime. Provider-neutral.
- **Prompt (TypedDict)**    — a reference to a provider-stored prompt (OpenAI-Responses style).
  Present in core so `Agent.prompt` can type-check, but only OpenAI addons actually dereference it.

Core `Agent` uses `instructions` for inline system prompts; `prompt` is optional / addon-only.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from typing_extensions import NotRequired, TypedDict

from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent
    from .run_context import RunContextWrapper


class Prompt(TypedDict):
    """Provider-stored prompt reference (OpenAI-compatible shape)."""

    id: str
    version: NotRequired[str]
    variables: NotRequired[dict[str, Any]]


@dataclass
class GenerateDynamicPromptData:
    context: RunContextWrapper[Any]
    agent: Agent[Any]


DynamicPromptFunction = Callable[[GenerateDynamicPromptData], MaybeAwaitable[Prompt]]


__all__ = ["DynamicPromptFunction", "GenerateDynamicPromptData", "Prompt"]