"""FakeModel — a deterministic in-process Model for tests and hello-world examples.

A `FakeModel` is seeded with a list of `FakeModelTurn`s. Each `get_response` call pops the next
turn and returns either:

- `final_output: str`    — an assistant message with plain text (terminates the run).
- `tool_calls: [...]`     — function-tool invocations (the runner will execute them then resume).

This makes the MVP Runner testable end-to-end without requiring an LLM API key.

Example:

    FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Tokyo"})]),
        FakeModelTurn(final_output="It is sunny in Tokyo."),
    ])
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..exceptions import UserError
from ..items import ModelResponse, TResponseInputItem, TResponseStreamEvent
from ..usage import RequestUsage, Usage
from .interface import Model, ModelTracing

if TYPE_CHECKING:
    from ..agent_output import AgentOutputSchemaBase
    from ..handoffs import Handoff
    from ..model_settings import ModelSettings
    from ..tool import Tool


@dataclass
class FakeModelTurn:
    """A single scripted model response.

    Exactly one of `final_output` / `tool_calls` must be provided.
    """

    final_output: str | None = None
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    usage: RequestUsage | None = None

    def __post_init__(self) -> None:
        if self.final_output is None and not self.tool_calls:
            raise UserError(
                "FakeModelTurn requires either final_output or tool_calls"
            )
        if self.final_output is not None and self.tool_calls:
            raise UserError(
                "FakeModelTurn cannot have both final_output and tool_calls"
            )


class FakeModel(Model):
    """Returns pre-scripted `ModelResponse`s, one per `get_response` call."""

    def __init__(self, turns: list[FakeModelTurn] | None = None) -> None:
        self._turns: list[FakeModelTurn] = list(turns or [])
        self._cursor: int = 0

    def queue_turn(self, turn: FakeModelTurn) -> None:
        """Append a new turn to the script (useful for multi-step tests)."""
        self._turns.append(turn)

    def _next_turn(self) -> FakeModelTurn:
        if self._cursor >= len(self._turns):
            # Fallback: return a benign empty final output instead of raising. Lets
            # resume-style flows survive a depleted script gracefully (tests rely on this).
            return FakeModelTurn(final_output="")
        turn = self._turns[self._cursor]
        self._cursor += 1
        return turn

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
        turn = self._next_turn()
        output_items: list[dict[str, Any]] = []
        if turn.final_output is not None:
            output_items.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": turn.final_output}],
                }
            )
        else:
            for name, args in turn.tool_calls:
                output_items.append(
                    {
                        "type": "function_call",
                        "name": name,
                        "arguments": json.dumps(args),
                        "call_id": f"call_{uuid.uuid4().hex[:12]}",
                    }
                )
        usage = Usage()
        req_usage = turn.usage or RequestUsage(input_tokens=1, output_tokens=1, total_tokens=2)
        usage.add(req_usage)
        return ModelResponse(
            output=output_items,
            usage=usage,
            response_id=f"fake_resp_{self._cursor}",
            request_id=f"fake_req_{self._cursor}",
        )

    async def stream_response(
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
        """Simple streaming: emit a single completed event carrying the same output."""
        response = await self.get_response(
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id=previous_response_id,
            conversation_id=conversation_id,
            prompt=prompt,
        )
        yield {"type": "response.completed", "response": {"output": response.output}}


__all__ = ["FakeModel", "FakeModelTurn"]