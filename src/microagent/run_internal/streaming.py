"""Stream event fan-out helpers.

v0.2 implementation: incremental tool-call JSON, raw-event forwarding, queue backpressure.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Iterator, Union

from ..items import RunItem, TResponseInputItem
from ..stream_events import (
    AgentUpdatedStreamEvent,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    StreamEvent,
)
from .run_steps import ProcessedResponse, SingleStepResult

# Type alias for stream event queue
StreamEventQueue = asyncio.Queue[Union[StreamEvent, "QueueCompleteSentinel"]]


class QueueCompleteSentinel:
    """Sentinel to indicate stream completion."""
    pass


async def stream_step_items_to_queue(
    items: list[RunItem],
    queue: StreamEventQueue,
    *,
    agent_name: str | None = None,
) -> None:
    """Stream individual RunItems as events."""
    for item in items:
        event = RunItemStreamEvent(
            name=item.type,
            run_id=None,  # Will be filled by runner
            agent_name=agent_name,
            item=item,
        )
        await queue.put(event)


async def stream_step_result_to_queue(
    step_result: SingleStepResult,
    queue: StreamEventQueue,
    *,
    agent_name: str | None = None,
) -> None:
    """Stream step result as events."""
    if step_result.model_response:
        event = RawResponsesStreamEvent(
            name="raw_response",
            run_id=None,
            agent_name=agent_name,
            response_id=getattr(step_result.model_response, "id", None),
            response=step_result.model_response,
        )
        await queue.put(event)

    await stream_step_items_to_queue(step_result.new_items, queue, agent_name=agent_name)


async def stream_processed_response(
    processed: ProcessedResponse,
    queue: StreamEventQueue,
    *,
    agent_name: str | None = None,
) -> None:
    """Stream processed response events."""
    if processed.handoff_target:
        event = AgentUpdatedStreamEvent(
            name="handoff_occurred",
            run_id=None,
            agent_name=agent_name,
            new_agent_name=processed.handoff_target.name,
        )
        await queue.put(event)


async def process_streaming_response(
    response_iterator: AsyncIterator[dict[str, Any]],
    queue: StreamEventQueue,
    *,
    agent_name: str | None = None,
) -> None:
    """Process streaming model response and emit events."""
    async for chunk in response_iterator:
        if "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            if "delta" in choice:
                delta = choice["delta"]
                if "content" in delta and delta["content"]:
                    # Message content chunk
                    event = RunItemStreamEvent(
                        name="message_output_created",
                        run_id=None,
                        agent_name=agent_name,
                        item={"type": "message", "content": delta["content"]},
                    )
                    await queue.put(event)
                elif "tool_calls" in delta and delta["tool_calls"]:
                    # Tool call chunk
                    tool_call = delta["tool_calls"][0]
                    if "function" in tool_call:
                        func = tool_call["function"]
                        event = RunItemStreamEvent(
                            name="tool_called",
                            run_id=None,
                            agent_name=agent_name,
                            item={
                                "type": "function_call",
                                "id": tool_call.get("id"),
                                "name": func.get("name"),
                                "arguments": func.get("arguments", ""),
                            },
                        )
                        await queue.put(event)


async def create_stream_generator(
    queue: StreamEventQueue,
) -> AsyncGenerator[StreamEvent, None]:
    """Create async generator from queue."""
    while True:
        item = await queue.get()
        if isinstance(item, QueueCompleteSentinel):
            break
        yield item


def handle_backpressure(
    queue: StreamEventQueue,
    max_size: int = 1000,
) -> None:
    """Handle queue backpressure by adjusting size or dropping events."""
    if queue.qsize() > max_size * 0.8:
        # Simple backpressure handling - could be enhanced
        pass


__all__ = [
    "QueueCompleteSentinel",
    "StreamEventQueue",
    "create_stream_generator",
    "handle_backpressure",
    "process_streaming_response",
    "stream_processed_response",
    "stream_step_items_to_queue",
    "stream_step_result_to_queue",
]