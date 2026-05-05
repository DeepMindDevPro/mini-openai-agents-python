"""Per-span-kind data payload structs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpanData:
    """Base class for span payloads."""

    type: str = "custom"

    def export(self) -> dict[str, Any]:
        d = {"type": self.type}
        for k, v in self.__dict__.items():
            if k == "type":
                continue
            d[k] = v
        return d


@dataclass
class AgentSpanData(SpanData):
    type: str = "agent"
    name: str | None = None
    output_type: str | None = None
    handoffs: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


@dataclass
class CustomSpanData(SpanData):
    type: str = "custom"
    name: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionSpanData(SpanData):
    type: str = "function"
    name: str | None = None
    input: Any = None
    output: Any = None


@dataclass
class GenerationSpanData(SpanData):
    type: str = "generation"
    model: str | None = None
    input: Any = None
    output: Any = None
    usage: dict[str, Any] | None = None


@dataclass
class GuardrailSpanData(SpanData):
    type: str = "guardrail"
    name: str | None = None
    triggered: bool = False


@dataclass
class HandoffSpanData(SpanData):
    type: str = "handoff"
    from_agent: str | None = None
    to_agent: str | None = None


@dataclass
class MCPListToolsSpanData(SpanData):
    type: str = "mcp_tools"
    server: str | None = None


@dataclass
class ResponseSpanData(SpanData):
    type: str = "response"
    response_id: str | None = None


@dataclass
class SpeechGroupSpanData(SpanData):
    type: str = "speech_group"


@dataclass
class SpeechSpanData(SpanData):
    type: str = "speech"


@dataclass
class TaskSpanData(SpanData):
    type: str = "task"
    name: str | None = None


@dataclass
class TranscriptionSpanData(SpanData):
    type: str = "transcription"


@dataclass
class TurnSpanData(SpanData):
    type: str = "turn"
    turn: int = 0


__all__ = [
    "AgentSpanData",
    "CustomSpanData",
    "FunctionSpanData",
    "GenerationSpanData",
    "GuardrailSpanData",
    "HandoffSpanData",
    "MCPListToolsSpanData",
    "ResponseSpanData",
    "SpanData",
    "SpeechGroupSpanData",
    "SpeechSpanData",
    "TaskSpanData",
    "TranscriptionSpanData",
    "TurnSpanData",
]