"""Input & output guardrails.

Two kinds of guardrails run around the agent turn:

- `InputGuardrail`  — runs only on the **first turn** for the **starting agent**.
  Can run in parallel with the model call (`run_in_parallel=True`) and cancel the model task
  if tripped, or as a **blocking pre-check** (`run_in_parallel=False`).
- `OutputGuardrail` — runs once the agent has produced a final output.

Each returns a `GuardrailFunctionOutput` whose `tripwire_triggered` flag raises a dedicated
exception (`InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered`).

Tool-level guardrails live in `tool_guardrails.py` because they carry a 3-way `behavior` instead
of a simple boolean.
"""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, overload

from typing_extensions import TypeVar

from .exceptions import UserError
from .items import TResponseInputItem
from .run_context import RunContextWrapper, TContext
from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent


@dataclass
class GuardrailFunctionOutput:
    """The return value of a guardrail function."""

    output_info: Any
    tripwire_triggered: bool


@dataclass
class InputGuardrailResult:
    guardrail: InputGuardrail[Any]
    output: GuardrailFunctionOutput


@dataclass
class OutputGuardrailResult:
    guardrail: OutputGuardrail[Any]
    agent: Agent[Any]
    agent_output: Any
    output: GuardrailFunctionOutput


# --------------------------------------------------------------------------- InputGuardrail


@dataclass
class InputGuardrail(Generic[TContext]):
    """Checks run before / alongside the first model call."""

    guardrail_function: Callable[
        [RunContextWrapper[TContext], Agent[Any], str | list[TResponseInputItem]],
        MaybeAwaitable[GuardrailFunctionOutput],
    ]
    name: str | None = None
    run_in_parallel: bool = True
    """When True (default), runs concurrently with the model call and can cancel it on trip.
    When False, blocks the model call until the guardrail completes.
    """

    def get_name(self) -> str:
        return self.name or self.guardrail_function.__name__

    async def run(
        self,
        agent: Agent[Any],
        input: str | list[TResponseInputItem],
        context: RunContextWrapper[TContext],
    ) -> InputGuardrailResult:
        if not callable(self.guardrail_function):
            raise UserError(
                f"Guardrail function must be callable, got {self.guardrail_function!r}"
            )
        output = self.guardrail_function(context, agent, input)
        if inspect.isawaitable(output):
            output = await output
        return InputGuardrailResult(guardrail=self, output=output)


# --------------------------------------------------------------------------- OutputGuardrail


@dataclass
class OutputGuardrail(Generic[TContext]):
    """Checks that run after the agent produces a final output."""

    guardrail_function: Callable[
        [RunContextWrapper[TContext], Agent[Any], Any],
        MaybeAwaitable[GuardrailFunctionOutput],
    ]
    name: str | None = None

    def get_name(self) -> str:
        return self.name or self.guardrail_function.__name__

    async def run(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[Any],
        agent_output: Any,
    ) -> OutputGuardrailResult:
        if not callable(self.guardrail_function):
            raise UserError(
                f"Guardrail function must be callable, got {self.guardrail_function!r}"
            )
        output = self.guardrail_function(context, agent, agent_output)
        if inspect.isawaitable(output):
            output = await output
        return OutputGuardrailResult(
            guardrail=self,
            agent=agent,
            agent_output=agent_output,
            output=output,
        )


# --------------------------------------------------------------------------- decorators

TContext_co = TypeVar("TContext_co", bound=Any, covariant=True)

_InputGuardrailFunc = Callable[
    [RunContextWrapper[TContext_co], "Agent[Any]", str | list[TResponseInputItem]],
    MaybeAwaitable[GuardrailFunctionOutput],
]
_OutputGuardrailFunc = Callable[
    [RunContextWrapper[TContext_co], "Agent[Any]", Any],
    MaybeAwaitable[GuardrailFunctionOutput],
]


@overload
def input_guardrail(func: _InputGuardrailFunc[TContext_co]) -> InputGuardrail[TContext_co]: ...


@overload
def input_guardrail(
    *,
    name: str | None = None,
    run_in_parallel: bool = True,
) -> Callable[[_InputGuardrailFunc[TContext_co]], InputGuardrail[TContext_co]]: ...


def input_guardrail(
    func: Any = None,
    *,
    name: str | None = None,
    run_in_parallel: bool = True,
) -> Any:
    """Decorator turning a function into an `InputGuardrail`."""

    def _wrap(f: _InputGuardrailFunc[TContext_co]) -> InputGuardrail[TContext_co]:
        return InputGuardrail(
            guardrail_function=f,
            name=name,
            run_in_parallel=run_in_parallel,
        )

    if func is not None:
        return _wrap(func)
    return _wrap


@overload
def output_guardrail(func: _OutputGuardrailFunc[TContext_co]) -> OutputGuardrail[TContext_co]: ...


@overload
def output_guardrail(
    *,
    name: str | None = None,
) -> Callable[[_OutputGuardrailFunc[TContext_co]], OutputGuardrail[TContext_co]]: ...


def output_guardrail(
    func: Any = None,
    *,
    name: str | None = None,
) -> Any:
    """Decorator turning a function into an `OutputGuardrail`."""

    def _wrap(f: _OutputGuardrailFunc[TContext_co]) -> OutputGuardrail[TContext_co]:
        return OutputGuardrail(guardrail_function=f, name=name)

    if func is not None:
        return _wrap(func)
    return _wrap


__all__ = [
    "GuardrailFunctionOutput",
    "InputGuardrail",
    "InputGuardrailResult",
    "OutputGuardrail",
    "OutputGuardrailResult",
    "input_guardrail",
    "output_guardrail",
]