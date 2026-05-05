"""Complete exception hierarchy for microagent.

All exceptions carry an optional `run_data: RunErrorDetails` snapshot so callers can rebuild the
full context (input / generated items / raw responses / last agent / guardrail results).
This is the same contract as the upstream `openai-agents` SDK.

Guardrail tripwires raise dedicated exception subclasses so user code can `except` on behavior,
not string matching.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .util._pretty_print import pretty_print_run_error_details

if TYPE_CHECKING:
    from .agent import Agent
    from .guardrail import InputGuardrailResult, OutputGuardrailResult
    from .items import ModelResponse, RunItem, TResponseInputItem
    from .run_context import RunContextWrapper
    from .tool_guardrails import (
        ToolGuardrailFunctionOutput,
        ToolInputGuardrail,
        ToolOutputGuardrail,
    )


@dataclass
class RunErrorDetails:
    """Snapshot of a run when an exception is raised."""

    input: Any = None
    new_items: list[RunItem] = field(default_factory=list)
    raw_responses: list[ModelResponse] = field(default_factory=list)
    last_agent: Agent[Any] | None = None
    context_wrapper: RunContextWrapper[Any] | None = None
    input_guardrail_results: list[InputGuardrailResult] = field(default_factory=list)
    output_guardrail_results: list[OutputGuardrailResult] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - user-facing repr
        return pretty_print_run_error_details(self)


class AgentsException(Exception):
    """Base class for microagent exceptions."""

    run_data: RunErrorDetails | None

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.run_data = None


class MaxTurnsExceeded(AgentsException):
    """Raised when the Runner exceeds its `max_turns` budget."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ModelBehaviorError(AgentsException):
    """Raised when the model returns malformed data (bad JSON, unknown tool, etc)."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ModelRefusalError(AgentsException):
    """Raised when the model explicitly refuses to generate output."""

    refusal: str

    def __init__(self, refusal: str) -> None:
        self.refusal = refusal
        super().__init__(f"Model refused to produce output: {refusal}")


class UserError(AgentsException):
    """Raised when the SDK is misused by the caller."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class MCPToolCancellationError(AgentsException):
    """Raised when an MCP tool call is cancelled externally."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ToolTimeoutError(AgentsException):
    """Raised when a tool invocation exceeds its configured timeout."""

    tool_name: str
    timeout_seconds: float

    def __init__(self, tool_name: str, timeout_seconds: float) -> None:
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Tool {tool_name!r} timed out after {timeout_seconds:g}s")


class InputGuardrailTripwireTriggered(AgentsException):
    """Raised when an input guardrail tripwire fires."""

    guardrail_result: InputGuardrailResult

    def __init__(self, guardrail_result: InputGuardrailResult) -> None:
        self.guardrail_result = guardrail_result
        super().__init__(
            f"Input guardrail {guardrail_result.guardrail.__class__.__name__} triggered tripwire"
        )


class OutputGuardrailTripwireTriggered(AgentsException):
    """Raised when an output guardrail tripwire fires."""

    guardrail_result: OutputGuardrailResult

    def __init__(self, guardrail_result: OutputGuardrailResult) -> None:
        self.guardrail_result = guardrail_result
        super().__init__(
            f"Output guardrail {guardrail_result.guardrail.__class__.__name__} triggered tripwire"
        )


class ToolInputGuardrailTripwireTriggered(AgentsException):
    """Raised when a tool-input guardrail tripwire fires."""

    guardrail: ToolInputGuardrail[Any]
    output: ToolGuardrailFunctionOutput

    def __init__(
        self,
        guardrail: ToolInputGuardrail[Any],
        output: ToolGuardrailFunctionOutput,
    ) -> None:
        self.guardrail = guardrail
        self.output = output
        super().__init__(
            f"Tool input guardrail {guardrail.__class__.__name__} triggered tripwire"
        )


class ToolOutputGuardrailTripwireTriggered(AgentsException):
    """Raised when a tool-output guardrail tripwire fires."""

    guardrail: ToolOutputGuardrail[Any]
    output: ToolGuardrailFunctionOutput

    def __init__(
        self,
        guardrail: ToolOutputGuardrail[Any],
        output: ToolGuardrailFunctionOutput,
    ) -> None:
        self.guardrail = guardrail
        self.output = output
        super().__init__(
            f"Tool output guardrail {guardrail.__class__.__name__} triggered tripwire"
        )


__all__ = [
    "AgentsException",
    "InputGuardrailTripwireTriggered",
    "MCPToolCancellationError",
    "MaxTurnsExceeded",
    "ModelBehaviorError",
    "ModelRefusalError",
    "OutputGuardrailTripwireTriggered",
    "RunErrorDetails",
    "ToolInputGuardrailTripwireTriggered",
    "ToolOutputGuardrailTripwireTriggered",
    "ToolTimeoutError",
    "UserError",
]