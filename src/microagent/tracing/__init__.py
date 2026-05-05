"""Tracing subsystem.

Default: NoOp — zero-cost. Exporters (OTel, OpenAI backend, console) are opt-in addons.

Span factories (13 semantic kinds):
- agent / custom / function / generation / guardrail / handoff / mcp_tools
- response / speech / speech_group / task / transcription / turn

Each span factory is a context manager that yields a `Span[SpanData]`.

Invariant: Every addon exporter receives both `Trace` and `Span` in export order.
"""

from .config import TracingConfig
from .create import (
    agent_span,
    custom_span,
    function_span,
    generation_span,
    get_current_span,
    get_current_trace,
    guardrail_span,
    handoff_span,
    mcp_tools_span,
    response_span,
    speech_group_span,
    speech_span,
    task_span,
    trace,
    transcription_span,
    turn_span,
)
from .processor_interface import TracingProcessor
from .provider import (
    add_trace_processor,
    get_trace_provider,
    set_trace_processors,
    set_trace_provider,
    set_tracing_disabled,
)
from .span_data import (
    AgentSpanData,
    CustomSpanData,
    FunctionSpanData,
    GenerationSpanData,
    GuardrailSpanData,
    HandoffSpanData,
    MCPListToolsSpanData,
    ResponseSpanData,
    SpanData,
    SpeechGroupSpanData,
    SpeechSpanData,
    TaskSpanData,
    TranscriptionSpanData,
    TurnSpanData,
)
from .spans import NoOpSpan, Span, SpanError
from .traces import NoOpTrace, Trace
from .util import gen_span_id, gen_trace_id

__all__ = [
    "AgentSpanData",
    "CustomSpanData",
    "FunctionSpanData",
    "GenerationSpanData",
    "GuardrailSpanData",
    "HandoffSpanData",
    "MCPListToolsSpanData",
    "NoOpSpan",
    "NoOpTrace",
    "ResponseSpanData",
    "Span",
    "SpanData",
    "SpanError",
    "SpeechGroupSpanData",
    "SpeechSpanData",
    "TaskSpanData",
    "Trace",
    "TracingConfig",
    "TracingProcessor",
    "TranscriptionSpanData",
    "TurnSpanData",
    "add_trace_processor",
    "agent_span",
    "custom_span",
    "function_span",
    "gen_span_id",
    "gen_trace_id",
    "generation_span",
    "get_current_span",
    "get_current_trace",
    "get_trace_provider",
    "guardrail_span",
    "handoff_span",
    "mcp_tools_span",
    "response_span",
    "set_trace_processors",
    "set_trace_provider",
    "set_tracing_disabled",
    "speech_group_span",
    "speech_span",
    "task_span",
    "trace",
    "transcription_span",
    "turn_span",
]