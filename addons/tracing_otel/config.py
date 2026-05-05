"""OpenTelemetry configuration for microagent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OpenTelemetryConfig:
    """Configuration for OpenTelemetry tracing."""
    
    service_name: str = "microagent"
    service_version: str = "0.1.0"
    endpoint: str = "http://localhost:4317"
    insecure: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    sampler: str = "parentbased_always_on"
    batch_processor: bool = True
    max_queue_size: int = 2048
    schedule_delay_millis: int = 5000
    max_export_batch_size: int = 512
    export_timeout_millis: int = 30000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "endpoint": self.endpoint,
            "insecure": self.insecure,
            "headers": self.headers,
            "resource_attributes": self.resource_attributes,
            "sampler": self.sampler,
            "batch_processor": self.batch_processor,
            "max_queue_size": self.max_queue_size,
            "schedule_delay_millis": self.schedule_delay_millis,
            "max_export_batch_size": self.max_export_batch_size,
            "export_timeout_millis": self.export_timeout_millis,
        }
    
    @classmethod
    def from_env(cls) -> "OpenTelemetryConfig":
        """Create config from environment variables."""
        import os
        
        return cls(
            service_name=os.getenv("OTEL_SERVICE_NAME", "microagent"),
            service_version=os.getenv("OTEL_SERVICE_VERSION", "0.1.0"),
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
            headers=dict(
                item.split("=", 1) 
                for item in os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "").split(",") 
                if "=" in item
            ),
            sampler=os.getenv("OTEL_TRACES_SAMPLER", "parentbased_always_on"),
        )