"""OpenTelemetry tracing addon for microagent."""

from .processor import OpenTelemetryProcessor
from .config import OpenTelemetryConfig

__all__ = [
    "OpenTelemetryProcessor",
    "OpenTelemetryConfig",
]