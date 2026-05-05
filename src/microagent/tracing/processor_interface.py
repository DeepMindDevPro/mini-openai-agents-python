"""TracingProcessor Protocol."""
from __future__ import annotations

import abc
from typing import Any, Protocol, runtime_checkable

from .spans import Span
from .traces import Trace


@runtime_checkable
class TracingProcessor(Protocol):
    """A consumer of trace / span lifecycle events.

    Typical implementations include:
      - `ConsoleProcessor` (addon): prints events to stderr.
      - `OTelProcessor` (addon): forwards to OpenTelemetry.
      - Third-party: New Relic, Datadog, etc.
    """

    def on_trace_start(self, trace: Trace) -> None: ...

    def on_trace_end(self, trace: Trace) -> None: ...

    def on_span_start(self, span: Span[Any]) -> None: ...

    def on_span_end(self, span: Span[Any]) -> None: ...

    def force_flush(self) -> None: ...

    def shutdown(self) -> None: ...


class TracingExporter(abc.ABC):
    """Batch exporter base for addons that batch-export trace items."""

    @abc.abstractmethod
    def export(self, items: list[Trace | Span[Any]]) -> None: ...


__all__ = ["TracingExporter", "TracingProcessor"]