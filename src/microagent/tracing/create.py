"""Trace / span factory functions (13 semantic kinds)."""
from __future__ import annotations

from typing import Any

from .provider import get_trace_provider
from .span_data import (
    AgentSpanData,
    CustomSpanData,
    FunctionSpanData,
    GenerationSpanData,
    GuardrailSpanData,
    HandoffSpanData,
    MCPListToolsSpanData,
    ResponseSpanData,
    SpeechGroupSpanData,
    SpeechSpanData,
    TaskSpanData,
    TranscriptionSpanData,
    TurnSpanData,
)
from .spans import NoOpSpan, Span
from .traces import NoOpTrace, Trace


def get_current_trace() -> Trace | None:
    return get_trace_provider().get_current_trace()


def get_current_span() -> Span[Any] | None:
    return get_trace_provider().get_current_span()


def trace(
    workflow_name: str,
    trace_id: str | None = None,
    group_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tracing: dict[str, Any] | None = None,
    disabled: bool = False,
) -> Trace:
    """Create a new Trace.

    The default provider is `NoOpTraceProvider` which already elides all I/O, so the
    `disabled` flag is a no-op here. Exporter addons that replace the provider should
    respect it themselves.
    """
    return NoOpTrace(name=workflow_name)


# -- span factories (all return NoOpSpan by default; addons may override the provider) --


def agent_span(name: str, **kw: Any) -> Span[AgentSpanData]:
    return NoOpSpan(AgentSpanData(name=name, **kw))


def function_span(name: str, **kw: Any) -> Span[FunctionSpanData]:
    return NoOpSpan(FunctionSpanData(name=name, **kw))


def generation_span(**kw: Any) -> Span[GenerationSpanData]:
    return NoOpSpan(GenerationSpanData(**kw))


def guardrail_span(name: str, **kw: Any) -> Span[GuardrailSpanData]:
    return NoOpSpan(GuardrailSpanData(name=name, **kw))


def handoff_span(
    from_agent: str | None = None,
    to_agent: str | None = None,
    **kw: Any,
) -> Span[HandoffSpanData]:
    return NoOpSpan(HandoffSpanData(from_agent=from_agent, to_agent=to_agent, **kw))


def mcp_tools_span(server: str | None = None, **kw: Any) -> Span[MCPListToolsSpanData]:
    return NoOpSpan(MCPListToolsSpanData(server=server, **kw))


def response_span(response_id: str | None = None, **kw: Any) -> Span[ResponseSpanData]:
    return NoOpSpan(ResponseSpanData(response_id=response_id, **kw))


def speech_group_span(**kw: Any) -> Span[SpeechGroupSpanData]:
    return NoOpSpan(SpeechGroupSpanData(**kw))


def speech_span(**kw: Any) -> Span[SpeechSpanData]:
    return NoOpSpan(SpeechSpanData(**kw))


def task_span(name:str, **kw: Any) -> Span[TaskSpanData]:
    return NoOpSpan(TaskSpanData(name=name, **kw))


def transcription_span(**kw: Any) -> Span[TranscriptionSpanData]:
    return NoOpSpan(TranscriptionSpanData(**kw))


def turn_span(turn: int = 0, **kw: Any) -> Span[TurnSpanData]:
    return NoOpSpan(TurnSpanData(turn=turn, **kw))


def custom_span(name: str, data: dict[str, Any] | None = None) -> Span[CustomSpanData]:
    return NoOpSpan(CustomSpanData(name=name, data=data or {}))


__all__ = [
    "agent_span",
    "custom_span",
    "function_span",
    "generation_span",
    "get_current_span",
    "get_current_trace",
    "guardrail_span",
    "handoff_span",
    "mcp_tools_span",
    "response_span",
    "speech_group_span",
    "speech_span",
    "task_span",
    "trace",
    "transcription_span",
    "turn_span",
]