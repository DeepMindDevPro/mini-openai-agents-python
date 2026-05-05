"""Model provider contracts.

`Model` is the abstract base every provider implementation (OpenAI / Anthropic / fake / ...)
must satisfy. Two methods are required:

    async def get_response(...)      — non-streaming; returns a `ModelResponse`.
    async def stream_response(...)    — streaming; yields `TResponseStreamEvent` dicts.

The signature is identical to the upstream SDK's so addons can interop 1:1, minus the hard
dependency on OpenAI's Responses types. We pass lightweight dicts as `TResponseInputItem`,
letting each provider adapter translate to its native shape.

`Model.get_retry_advice(...)` is an opt-in extension point: providers can surface replay-safety
and retry-after hints to the Runner. The default implementation returns `None`.

`ModelTracing` provides 3 levels of observability granularity for compliance use cases.

Multi-provider routing (`"openai/gpt-4o"`, `"claude/opus"`, ...) is offered by the optional
`MultiProvider` helper registered from the addon ecosystem; core keeps only the abstract
`ModelProvider` contract so addons can plug in without hard dependencies.
"""
from __future__ import annotations

import abc
import enum
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ..items import ModelResponse, TResponseInputItem, TResponseStreamEvent

if TYPE_CHECKING:
    from ..agent_output import AgentOutputSchemaBase
    from ..handoffs import Handoff
    from ..model_settings import ModelSettings
    from ..retry import ModelRetryAdvice, ModelRetryAdviceRequest
    from ..tool import Tool


class ModelTracing(enum.Enum):
    """How much data should be included in model-level tracing spans."""

    DISABLED = 0
    """No spans created."""

    ENABLED = 1
    """Full tracing including inputs/outputs (default)."""

    ENABLED_WITHOUT_DATA = 2
    """Spans created but inputs/outputs are redacted (compliance mode)."""

    def is_disabled(self) -> bool:
        return self == ModelTracing.DISABLED

    def include_data(self) -> bool:
        return self == ModelTracing.ENABLED


class Model(abc.ABC):
    """The base interface for calling an LLM."""

    async def close(self) -> None:
        """Release any persistent resources (sockets, pools). Default is a no-op."""
        return None

    def get_retry_advice(
        self, request: ModelRetryAdviceRequest
    ) -> ModelRetryAdvice | None:
        """Return provider-specific retry guidance, or None to defer to the default policy."""
        return None

    @abc.abstractmethod
    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> ModelResponse:
        """Single non-streaming model call.

        Args:
            system_instructions: System prompt (or None for provider default).
            input: A user-facing string or a list of input items.
            model_settings: Tuning parameters.
            tools: Available tools (may be empty).
            output_schema: If set, the LLM must produce structured output matching this schema.
            handoffs: Candidate handoff targets (treated as tools by most providers).
            tracing: Tracing granularity.
            previous_response_id: Upstream server-conversation hint (OpenAI Responses).
            conversation_id: Server-managed conversation id (OpenAI Conversations).
            prompt: Provider-specific prompt config (OpenAI Prompt; ignored by neutral providers).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        """Streaming model call. Yields provider-shaped events.

        The Runner adapts these to `stream_events.RawResponsesStreamEvent`.
        """
        raise NotImplementedError


class ModelProvider(abc.ABC):
    """Factory + router for resolving `Model` instances by string name.

    Used by `RunConfig.model_provider` to map `agent.model: str` references to concrete models.
    """

    @abc.abstractmethod
    def get_model(self, model_name: str | None) -> Model:
        """Return a Model implementation for the given name (or a default)."""
        raise NotImplementedError


__all__ = ["Model", "ModelProvider", "ModelTracing"]