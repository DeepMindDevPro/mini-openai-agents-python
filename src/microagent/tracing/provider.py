"""TraceProvider — global singleton that owns processors.

Default: `NoOpTraceProvider`. To export traces, register a `TracingProcessor` via
`add_trace_processor` or swap the provider via `set_trace_provider`.

The provider holds a `contextvars.ContextVar` stack of current trace/span so that nested async
calls see the correct scope without explicit plumbing. Processor mutations go through a
`threading.Lock` so multi-processor setups are safe under concurrent exporters.
"""
from __future__ import annotations

import abc
import contextvars
import threading
from typing import Any

from .processor_interface import TracingProcessor
from .spans import Span
from .traces import Trace

_CURRENT_TRACE: contextvars.ContextVar[Trace | None] = contextvars.ContextVar(
    "microagent_current_trace", default=None
)
_CURRENT_SPAN: contextvars.ContextVar[Span[Any] | None] = contextvars.ContextVar(
    "microagent_current_span", default=None
)


class TraceProvider(abc.ABC):
    """Global factory for traces and spans."""

    disabled: bool = False

    @abc.abstractmethod
    def get_current_trace(self) -> Trace | None: ...

    @abc.abstractmethod
    def get_current_span(self) -> Span[Any] | None: ...

    def register_processor(self, processor: TracingProcessor) -> None:
        pass

    def set_processors(self, processors: list[TracingProcessor]) -> None:
        pass

    def set_disabled(self, disabled: bool) -> None:
        self.disabled = disabled


class NoOpTraceProvider(TraceProvider):
    """Default — produces NoOp traces / spans, ignores processors."""

    def __init__(self) -> None:
        self._processors: list[TracingProcessor] = []
        self._lock = threading.Lock()

    def get_current_trace(self) -> Trace | None:
        return _CURRENT_TRACE.get()

    def get_current_span(self) -> Span[Any] | None:
        return _CURRENT_SPAN.get()

    def register_processor(self, processor: TracingProcessor) -> None:
        with self._lock:
            self._processors.append(processor)

    def set_processors(self, processors: list[TracingProcessor]) -> None:
        with self._lock:
            self._processors = list(processors)


_default_provider: TraceProvider = NoOpTraceProvider()


def get_trace_provider() -> TraceProvider:
    return _default_provider


def set_trace_provider(provider: TraceProvider) -> None:
    global _default_provider
    _default_provider = provider


def add_trace_processor(processor: TracingProcessor) -> None:
    _default_provider.register_processor(processor)


def set_trace_processors(processors: list[TracingProcessor]) -> None:
    _default_provider.set_processors(processors)


def set_tracing_disabled(disabled: bool) -> None:
    _default_provider.set_disabled(disabled)


# Internal helpers used by span/trace factories


def _push_trace(trace: Trace) -> contextvars.Token[Trace | None]:
    return _CURRENT_TRACE.set(trace)


def _pop_trace(token: contextvars.Token[Trace | None]) -> None:
    _CURRENT_TRACE.reset(token)


def _push_span(span: Span[Any]) -> contextvars.Token[Span[Any] | None]:
    return _CURRENT_SPAN.set(span)


def _pop_span(token: contextvars.Token[Span[Any] | None]) -> None:
    _CURRENT_SPAN.reset(token)


__all__ = [
    "NoOpTraceProvider",
    "TraceProvider",
    "add_trace_processor",
    "get_trace_provider",
    "set_trace_processors",
    "set_trace_provider",
    "set_tracing_disabled",
]