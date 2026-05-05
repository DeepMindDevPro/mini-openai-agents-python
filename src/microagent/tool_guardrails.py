"""Tool-level guardrails with 3-way behaviors.

Unlike `InputGuardrail` / `OutputGuardrail` which carry a boolean `tripwire_triggered` flag,
tool guardrails return a richer `behavior`:

- `allow`           — continue normally.
- `reject_content`  — skip tool execution, inject a model-visible message instead.
- `raise_exception` — halt the run with `ToolInputGuardrailTripwireTriggered` /
  `ToolOutputGuardrailTripwireTriggered`.

This lets tools be gated without either fully blocking the run or silently passing.
"""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

from typing_extensions import TypedDict, TypeVar

from .exceptions import UserError
from .tool_context import ToolContext
from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent


class RejectContentBehavior(TypedDict):
    type: Literal["reject_content"]
    message: str


class RaiseExceptionBehavior(TypedDict):
    type: Literal["raise_exception"]


class AllowBehavior(TypedDict):
    type: Literal["allow"]


ToolGuardrailBehavior = RejectContentBehavior | RaiseExceptionBehavior | AllowBehavior


@dataclass
class ToolGuardrailFunctionOutput:
    """Return value of tool guardrails."""

    output_info: Any
    behavior: ToolGuardrailBehavior = field(
        default_factory=lambda: AllowBehavior(type="allow")
    )

    @classmethod
    def allow(cls, output_info: Any = None) -> ToolGuardrailFunctionOutput:
        return cls(output_info=output_info, behavior=AllowBehavior(type="allow"))

    @classmethod
    def reject(cls, message: str, output_info: Any = None) -> ToolGuardrailFunctionOutput:
        return cls(
            output_info=output_info,
            behavior=RejectContentBehavior(type="reject_content", message=message),
        )

    @classmethod
    def raise_exception(cls, output_info: Any = None) -> ToolGuardrailFunctionOutput:
        return cls(
            output_info=output_info,
            behavior=RaiseExceptionBehavior(type="raise_exception"),
        )


TContext = TypeVar("TContext", bound=Any, default=Any)


@dataclass
class ToolInputGuardrailData(Generic[TContext]):
    context: ToolContext[TContext]
    agent: Agent[Any]
    input_args: dict[str, Any]


@dataclass
class ToolOutputGuardrailData(Generic[TContext]):
    context: ToolContext[TContext]
    agent: Agent[Any]
    input_args: dict[str, Any]
    output: Any


@dataclass
class ToolInputGuardrailResult(Generic[TContext]):
    guardrail: ToolInputGuardrail[TContext]
    output: ToolGuardrailFunctionOutput


@dataclass
class ToolOutputGuardrailResult(Generic[TContext]):
    guardrail: ToolOutputGuardrail[TContext]
    output: ToolGuardrailFunctionOutput


@dataclass
class ToolInputGuardrail(Generic[TContext]):
    guardrail_function: Callable[
        [ToolInputGuardrailData[TContext]], MaybeAwaitable[ToolGuardrailFunctionOutput]
    ]
    name: str | None = None

    def get_name(self) -> str:
        return self.name or self.guardrail_function.__name__

    async def run(
        self, data: ToolInputGuardrailData[TContext]
    ) -> ToolInputGuardrailResult[TContext]:
        if not callable(self.guardrail_function):
            raise UserError(f"Guardrail must be callable, got {self.guardrail_function!r}")
        output = self.guardrail_function(data)
        if inspect.isawaitable(output):
            output = await output
        return ToolInputGuardrailResult(guardrail=self, output=output)


@dataclass
class ToolOutputGuardrail(Generic[TContext]):
    guardrail_function: Callable[
        [ToolOutputGuardrailData[TContext]], MaybeAwaitable[ToolGuardrailFunctionOutput]
    ]
    name: str | None = None

    def get_name(self) -> str:
        return self.name or self.guardrail_function.__name__

    async def run(
        self, data: ToolOutputGuardrailData[TContext]
    ) -> ToolOutputGuardrailResult[TContext]:
        if not callable(self.guardrail_function):
            raise UserError(f"Guardrail must be callable, got {self.guardrail_function!r}")
        output = self.guardrail_function(data)
        if inspect.isawaitable(output):
            output = await output
        return ToolOutputGuardrailResult(guardrail=self, output=output)


# --------------------------------------------------------------------------- decorators


def tool_input_guardrail(
    func: Any = None, *, name: str | None = None
) -> Any:
    def _wrap(f: Any) -> ToolInputGuardrail[Any]:
        return ToolInputGuardrail(guardrail_function=f, name=name)

    if func is not None:
        return _wrap(func)
    return _wrap


def tool_output_guardrail(
    func: Any = None, *, name: str | None = None
) -> Any:
    def _wrap(f: Any) -> ToolOutputGuardrail[Any]:
        return ToolOutputGuardrail(guardrail_function=f, name=name)

    if func is not None:
        return _wrap(func)
    return _wrap


__all__ = [
    "AllowBehavior",
    "RaiseExceptionBehavior",
    "RejectContentBehavior",
    "ToolGuardrailBehavior",
    "ToolGuardrailFunctionOutput",
    "ToolInputGuardrail",
    "ToolInputGuardrailData",
    "ToolInputGuardrailResult",
    "ToolOutputGuardrail",
    "ToolOutputGuardrailData",
    "ToolOutputGuardrailResult",
    "tool_input_guardrail",
    "tool_output_guardrail",
]