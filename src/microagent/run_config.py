"""RunConfig — global settings that override per-agent defaults for a single run.

Positional field order is a public contract. New optional fields **must** be appended.

Fields grouped:

- **Model overrides**: `model` / `model_provider` / `model_settings`
- **Handoff shaping**:  `handoff_input_filter` / `nest_handoff_history` / `handoff_history_mapper`
- **Guardrail overrides**: `input_guardrails` / `output_guardrails`
- **Session**:     `session_settings` / `session_input_callback`
- **Model input**: `call_model_input_filter`
- **Tool errors**: `tool_error_formatter`
- **Tracing**:     `workflow_name` / `trace_id` / `group_id` / `trace_metadata` /
                   `trace_include_sensitive_data` / `tracing_disabled` / `tracing`
- **Reasoning items**: `reasoning_item_id_policy`

The optional `microagent-sandbox` addon registers a `sandbox` field at import-time via the
entry-point hook; core does not declare it to keep the dependency optional.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal

from typing_extensions import NotRequired, TypedDict

from .guardrail import InputGuardrail, OutputGuardrail
from .handoffs import HandoffHistoryMapper, HandoffInputFilter
from .items import TResponseInputItem
from .memory.session import Session
from .memory.session_settings import SessionSettings
from .memory.util import SessionInputCallback
from .model_settings import ModelSettings
from .models.interface import Model, ModelProvider
from .run_context import TContext
from .run_error_handlers import RunErrorHandlers
from .tracing.config import TracingConfig
from .util._types import MaybeAwaitable

if TYPE_CHECKING:
    from .agent import Agent
    from .run_context import RunContextWrapper


DEFAULT_MAX_TURNS = 10
ReasoningItemIdPolicy = Literal["preserve", "omit"]


def _default_trace_include_sensitive_data() -> bool:
    v = os.getenv("MICROAGENT_TRACE_INCLUDE_SENSITIVE_DATA", "true").strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass
class ModelInputData:
    """Payload passed to the model just before the call."""

    input: list[TResponseInputItem]
    instructions: str | None


@dataclass
class CallModelData(Generic[TContext]):
    """Argument envelope for `RunConfig.call_model_input_filter`."""

    model_data: ModelInputData
    agent: Agent[TContext]
    context: TContext | None


CallModelInputFilter = Callable[[CallModelData[Any]], MaybeAwaitable[ModelInputData]]


@dataclass
class ToolErrorFormatterArgs(Generic[TContext]):
    kind: Literal["approval_rejected", "tool_timeout", "tool_exception"]
    tool_type: Literal["function", "custom", "computer", "shell", "apply_patch"]
    tool_name: str
    call_id: str
    error: Exception | None = None
    context: RunContextWrapper[TContext] | None = None


ToolErrorFormatter = Callable[[ToolErrorFormatterArgs[Any]], MaybeAwaitable[str | None]]


@dataclass
class RunConfig:
    """Global settings for an entire `Runner.run(...)` invocation."""

    # --- Model overrides ---
    model: str | Model | None = None
    model_provider: ModelProvider | None = None
    model_settings: ModelSettings | None = None

    # --- Handoff shaping ---
    handoff_input_filter: HandoffInputFilter | None = None
    nest_handoff_history: bool = False
    handoff_history_mapper: HandoffHistoryMapper | None = None

    # --- Guardrail overrides ---
    input_guardrails: list[InputGuardrail[Any]] | None = None
    output_guardrails: list[OutputGuardrail[Any]] | None = None

    # --- Tracing ---
    tracing_disabled: bool = False
    tracing: TracingConfig | None = None
    trace_include_sensitive_data: bool = field(
        default_factory=_default_trace_include_sensitive_data
    )
    workflow_name: str = "Agent workflow"
    trace_id: str | None = None
    group_id: str | None = None
    trace_metadata: dict[str, Any] | None = None

    # --- Session ---
    session_input_callback: SessionInputCallback | None = None
    session_settings: SessionSettings | None = None

    # --- Hooks into the model call ---
    call_model_input_filter: CallModelInputFilter | None = None

    # --- Tool errors ---
    tool_error_formatter: ToolErrorFormatter | None = None

    # --- Reasoning ---
    reasoning_item_id_policy: ReasoningItemIdPolicy | None = None


class RunOptions(TypedDict, Generic[TContext], total=False):
    """Kwargs accepted by `AgentRunner.run(...)` (used for internal plumbing)."""

    context: NotRequired[TContext | None]
    max_turns: NotRequired[int]
    hooks: NotRequired[Any]
    run_config: NotRequired[RunConfig | None]
    error_handlers: NotRequired[RunErrorHandlers[TContext] | None]
    previous_response_id: NotRequired[str | None]
    auto_previous_response_id: NotRequired[bool]
    conversation_id: NotRequired[str | None]
    session: NotRequired[Session | None]


__all__ = [
    "CallModelData",
    "CallModelInputFilter",
    "DEFAULT_MAX_TURNS",
    "ModelInputData",
    "ReasoningItemIdPolicy",
    "RunConfig",
    "RunOptions",
    "ToolErrorFormatter",
    "ToolErrorFormatterArgs",
]