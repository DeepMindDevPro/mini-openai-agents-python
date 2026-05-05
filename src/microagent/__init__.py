"""microagent — provider-neutral, lightweight Python Agent framework."""

from __future__ import annotations

from . import _config, extensions, sandbox
from .agent import Agent
from .agent_runner import AgentRunner
from .exceptions import (
    AgentsException,
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    ModelBehaviorError,
    ModelRefusalError,
    OutputGuardrailTripwireTriggered,
    RunErrorDetails,
    ToolInputGuardrailTripwireTriggered,
    ToolOutputGuardrailTripwireTriggered,
    ToolTimeoutError,
    UserError,
)
from .extensions.handoff_prompt import (
    RECOMMENDED_PROMPT_PREFIX,
    prompt_with_handoff_instructions,
)
from .guardrail import (
    GuardrailFunctionOutput,
    InputGuardrail,
    InputGuardrailResult,
    OutputGuardrail,
    OutputGuardrailResult,
    input_guardrail,
    output_guardrail,
)
from .handoffs import (
    Handoff,
    HandoffInputData,
    default_handoff_history_mapper,
    handoff,
    nest_handoff_history,
)
from .items import (
    CompactionItem,
    HandoffCallItem,
    HandoffOutputItem,
    ItemHelpers,
    MCPApprovalRequestItem,
    MCPApprovalResponseItem,
    MessageOutputItem,
    ModelResponse,
    ReasoningItem,
    RunItem,
    ToolApprovalItem,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
)
from .lifecycle import AgentHooks, RunHooks
from .memory import (
    InMemorySession,
    Session,
    SessionABC,
    SessionSettings,
    is_openai_responses_compaction_aware_session,
)
from .model_settings import ModelSettings
from .models import FakeModel, FakeModelTurn, Model, ModelProvider, ModelTracing
from .models.multi_provider import MultiProvider
from .result import AgentToolInvocation, RunResult, RunResultStreaming
from .retry import (
    ModelRetryAdvice,
    ModelRetryAdviceRequest,
    ModelRetryBackoffSettings,
    ModelRetryNormalizedError,
    ModelRetrySettings,
    RetryDecision,
    RetryPolicy,
    RetryPolicyContext,
    retry_policies,
)
from .run import Runner
from .run_config import RunConfig
from .run_context import AgentHookContext, RunContextWrapper, TContext
from .run_error_handlers import (
    RunErrorData,
    RunErrorHandler,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    RunErrorHandlers,
)
from .run_state import CURRENT_SCHEMA_VERSION, RunState, SCHEMA_VERSION_SUMMARIES
from .run_state_resume import (
    async_resume_run_state,
    create_run_state_from_result,
    resume_run_state,
)
from .stream_events import (
    AgentUpdatedStreamEvent,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    StreamEvent,
)
from .streaming import run_streamed
from .tool import FunctionTool, FunctionToolResult, Tool, function_tool
from .tool_context import ToolContext
from .tool_guardrails import (
    ToolGuardrailFunctionOutput,
    ToolInputGuardrail,
    ToolInputGuardrailData,
    ToolInputGuardrailResult,
    ToolOutputGuardrail,
    ToolOutputGuardrailData,
    ToolOutputGuardrailResult,
    tool_input_guardrail,
    tool_output_guardrail,
)
from .usage import RequestUsage, TokenDetails, Usage
from .version import __version__

# Re-export config setters so `microagent.set_default_openai_key(...)` works.
set_default_openai_key = _config.set_default_openai_key
set_default_openai_client = _config.set_default_openai_client
set_default_openai_api = _config.set_default_openai_api
set_default_openai_responses_transport = _config.set_default_openai_responses_transport
set_default_openai_harness = _config.set_default_openai_harness
set_default_openai_agent_registration = _config.set_default_openai_agent_registration

# Optional: re-export `AsyncOpenAI` if the `openai` addon dependency is installed.
try:  # pragma: no cover - optional dependency
    from openai import AsyncOpenAI  # type: ignore[assignment]
except Exception:  # pragma: no cover - optional dependency
    AsyncOpenAI = None  # type: ignore[assignment]


__all__ = [
    "Agent",
    "AgentHookContext",
    "AgentHooks",
    "AgentRunner",
    "AgentToolInvocation",
    "AgentUpdatedStreamEvent",
    "AgentsException",
    "AsyncOpenAI",
    "CURRENT_SCHEMA_VERSION",
    "CompactionItem",
    "FakeModel",
    "FakeModelTurn",
    "FunctionTool",
    "FunctionToolResult",
    "GuardrailFunctionOutput",
    "Handoff",
    "HandoffCallItem",
    "HandoffInputData",
    "HandoffOutputItem",
    "InMemorySession",
    "InputGuardrail",
    "InputGuardrailResult",
    "InputGuardrailTripwireTriggered",
    "ItemHelpers",
    "MCPApprovalRequestItem",
    "MCPApprovalResponseItem",
    "MaxTurnsExceeded",
    "MessageOutputItem",
    "Model",
    "ModelBehaviorError",
    "ModelProvider",
    "ModelRefusalError",
    "ModelResponse",
    "ModelRetryAdvice",
    "ModelRetryAdviceRequest",
    "ModelRetryBackoffSettings",
    "ModelRetryNormalizedError",
    "ModelRetrySettings",
    "ModelSettings",
    "ModelTracing",
    "MultiProvider",
    "OutputGuardrail",
    "OutputGuardrailResult",
    "OutputGuardrailTripwireTriggered",
    "RawResponsesStreamEvent",
    "RECOMMENDED_PROMPT_PREFIX",
    "ReasoningItem",
    "RequestUsage",
    "RetryDecision",
    "RetryPolicy",
    "RetryPolicyContext",
    "RunConfig",
    "RunContextWrapper",
    "RunErrorData",
    "RunErrorDetails",
    "RunErrorHandler",
    "RunErrorHandlerInput",
    "RunErrorHandlerResult",
    "RunErrorHandlers",
    "RunHooks",
    "RunItem",
    "RunItemStreamEvent",
    "RunResult",
    "RunResultStreaming",
    "RunState",
    "Runner",
    "SCHEMA_VERSION_SUMMARIES",
    "Session",
    "SessionABC",
    "SessionSettings",
    "StreamEvent",
    "TContext",
    "TResponseInputItem",
    "TokenDetails",
    "Tool",
    "ToolApprovalItem",
    "ToolCallItem",
    "ToolCallOutputItem",
    "ToolContext",
    "ToolGuardrailFunctionOutput",
    "ToolInputGuardrail",
    "ToolInputGuardrailData",
    "ToolInputGuardrailResult",
    "ToolInputGuardrailTripwireTriggered",
    "ToolOutputGuardrail",
    "ToolOutputGuardrailData",
    "ToolOutputGuardrailResult",
    "ToolOutputGuardrailTripwireTriggered",
    "ToolTimeoutError",
    "Usage",
    "UserError",
    "__version__",
    "async_resume_run_state",
    "create_run_state_from_result",
    "default_handoff_history_mapper",
    "extensions",
    "function_tool",
    "handoff",
    "input_guardrail",
    "is_openai_responses_compaction_aware_session",
    "nest_handoff_history",
    "output_guardrail",
    "prompt_with_handoff_instructions",
    "resume_run_state",
    "retry_policies",
    "run_streamed",
    "sandbox",
    "set_default_openai_agent_registration",
    "set_default_openai_api",
    "set_default_openai_client",
    "set_default_openai_harness",
    "set_default_openai_key",
    "set_default_openai_responses_transport",
    "tool_input_guardrail",
    "tool_output_guardrail",
]