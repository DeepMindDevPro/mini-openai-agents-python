"""User-configurable error handlers that degrade exceptions into final outputs.

`RunErrorHandlers` is a `TypedDict` keyed by error kind. Each handler receives a snapshot of
what the run did so far (`RunErrorData`) and returns either:
- A `RunErrorHandlerResult` with a degraded `final_output` (the run succeeds with that output).
- A dict shaped `{"final_output": ...}`.
- A raw value treated as `final_output`.
- `None` to re-raise.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic

from typing_extensions import TypedDict, TypeVar

from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent
    from .exceptions import MaxTurnsExceeded, ModelRefusalError
    from .items import ModelResponse, RunItem, TResponseInputItem
    from .run_context import RunContextWrapper

TContext = TypeVar("TContext", default=Any)


@dataclass
class RunErrorData:
    input: str | list[TResponseInputItem]
    new_items: list[RunItem] = field(default_factory=list)
    history: list[TResponseInputItem] = field(default_factory=list)
    output: list[TResponseInputItem] = field(default_factory=list)
    raw_responses: list[ModelResponse] = field(default_factory=list)
    last_agent: Agent[Any] | None = None


@dataclass
class RunErrorHandlerInput(Generic[TContext]):
    error: MaxTurnsExceeded | ModelRefusalError
    context: RunContextWrapper[TContext]
    run_data: RunErrorData


@dataclass
class RunErrorHandlerResult:
    final_output: Any
    include_in_history: bool = True


RunErrorHandler = Callable[
    [RunErrorHandlerInput[TContext]],
    MaybeAwaitable[RunErrorHandlerResult | dict[str, Any] | Any | None],
]


class RunErrorHandlers(TypedDict, Generic[TContext], total=False):
    """Error handlers keyed by error kind."""

    max_turns: RunErrorHandler[TContext]
    model_refusal: RunErrorHandler[TContext]


__all__ = [
    "RunErrorData",
    "RunErrorHandler",
    "RunErrorHandlerInput",
    "RunErrorHandlerResult",
    "RunErrorHandlers",
]