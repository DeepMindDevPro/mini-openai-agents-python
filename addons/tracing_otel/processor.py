"""OpenTelemetry processor for microagent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from microagent.tracing import TracingProcessor, Trace, Span

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

from .config import OpenTelemetryConfig


class OpenTelemetryProcessor(TracingProcessor):
    """OpenTelemetry tracing processor for microagent."""

    def __init__(
        self,
        *,
        config: OpenTelemetryConfig | None = None,
    ) -> None:
        """Initialize OpenTelemetry processor."""
        if not HAS_OTEL:
            raise ImportError(
                "OpenTelemetry packages not installed. Install with: pip install opentelemetry-sdk opentelemetry-exporter-otlp"
            )
        
        self.config = config or OpenTelemetryConfig.from_env()
        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[Any] = None
        self._setup_tracer()

    def _setup_tracer(self) -> None:
        """Setup OpenTelemetry tracer."""
        # Create resource
        resource = Resource.create(
            {
                "service.name": self.config.service_name,
                "service.version": self.config.service_version,
                **self.config.resource_attributes,
            }
        )
        
        # Create tracer provider
        self._tracer_provider = TracerProvider(resource=resource)
        
        # Setup exporter
        if self.config.endpoint:
            exporter = OTLPSpanExporter(
                endpoint=self.config.endpoint,
                insecure=self.config.insecure,
                headers=self.config.headers,
            )
        else:
            exporter = ConsoleSpanExporter()
        
        # Setup processor
        if self.config.batch_processor:
            processor = BatchSpanProcessor(
                exporter,
                max_queue_size=self.config.max_queue_size,
                schedule_delay_millis=self.config.schedule_delay_millis,
                max_export_batch_size=self.config.max_export_batch_size,
                export_timeout_millis=self.config.export_timeout_millis,
            )
        else:
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            processor = SimpleSpanProcessor(exporter)
        
        # Add processor to provider
        self._tracer_provider.add_span_processor(processor)
        
        # Set as global tracer provider
        otel_trace.set_tracer_provider(self._tracer_provider)
        
        # Get tracer
        self._tracer = otel_trace.get_tracer(
            self.config.service_name,
            self.config.service_version,
        )

    def on_trace_start(self, trace: Trace) -> None:
        """Handle trace start."""
        if self._tracer is None:
            return
        
        # Create a span for the trace
        span = self._tracer.start_span(
            name=trace.name or "agent_trace",
            attributes={
                "trace.id": trace.trace_id,
                "trace.name": trace.name,
            }
        )
        
        # Store span in trace context
        trace._otel_span = span

    def on_trace_end(self, trace: Trace) -> None:
        """Handle trace end."""
        if hasattr(trace, '_otel_span') and trace._otel_span:
            trace._otel_span.end()

    def on_span_start(self, span: Span) -> None:
        """Handle span start."""
        if self._tracer is None:
            return
        
        # Get parent span from trace context
        parent_span = None
        if span.trace and hasattr(span.trace, '_otel_span'):
            parent_span = span.trace._otel_span
        
        # Create OpenTelemetry span
        otel_span = self._tracer.start_span(
            name=span.name,
            attributes=self._convert_attributes(span.attributes),
            parent=parent_span,
        )
        
        # Store span in span context
        span._otel_span = otel_span

    def on_span_end(self, span: Span) -> None:
        """Handle span end."""
        if hasattr(span, '_otel_span') and span._otel_span:
            # Set status based on span result
            if span.error:
                span._otel_span.set_status(
                    Status(StatusCode.ERROR, span.error.message)
                )
            else:
                span._otel_span.set_status(Status(StatusCode.OK))
            
            span._otel_span.end()

    def on_span_event(self, span: Span, event: Dict[str, Any]) -> None:
        """Handle span event."""
        if hasattr(span, '_otel_span') and span._otel_span:
            # Add event to span
            span._otel_span.add_event(
                name=event.get("name", "event"),
                attributes=event.get("attributes", {}),
                timestamp=event.get("timestamp"),
            )

    def _convert_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Convert attributes to OpenTelemetry format."""
        converted = {}
        for key, value in attributes.items():
            # Convert to OpenTelemetry attribute types
            if isinstance(value, (str, int, float, bool)):
                converted[key] = value
            elif value is None:
                converted[key] = ""
            else:
                converted[key] = str(value)
        return converted

    def shutdown(self) -> None:
        """Shutdown the processor."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()

    def force_flush(self) -> None:
        """Force flush all spans."""
        if self._tracer_provider:
            self._tracer_provider.force_flush()


# Convenience function to setup OpenTelemetry tracing
def setup_opentelemetry_tracing(
    *,
    config: OpenTelemetryConfig | None = None,
) -> OpenTelemetryProcessor:
    """Setup OpenTelemetry tracing for microagent."""
    processor = OpenTelemetryProcessor(config=config)
    
    from microagent.tracing import add_trace_processor
    add_trace_processor(processor)
    
    return processor