"""Turn resolution — convert a `ModelResponse` into `RunItem`s and the next control step.

MVP supports two output shapes emitted by `FakeModel` / OpenAI ChatCompletions adapters:

- `{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": ...}]}`
- `{"type": "function_call", "name": ..., "arguments": ..., "call_id": ...}`

Reasoning items (`type == "reasoning"`) and MCP/approval items are dispatched to the
registry in `items.py`; addons can register new handlers without touching this file.
"""
from __future__ import annotations

import json
from typing import Any

from ..agent import Agent
from ..agent_output import AgentOutputSchemaBase
from ..exceptions import ModelBehaviorError
from ..handoffs import Handoff
from ..items import (
    MessageOutputItem,
    ModelResponse,
    RunItem,
    ToolCallItem,
    ToolCallOutputItem,
)
from ..run_context import RunContextWrapper
from ..tool import FunctionTool, Tool
from ..tool_context import ToolContext
from .run_steps import (
    NextStepFinalOutput,
    NextStepHandoff,
    NextStepInterruption,
    NextStepRunAgain,
    ProcessedResponse,
    SingleStepResult,
)


def _extract_text_from_message(output_item: dict[str, Any]) -> str:
    content = output_item.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for c in content:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
        return "".join(parts)
    return ""


def process_model_response(
    *,
    agent: Agent[Any],
    response: ModelResponse,
    tools: list[Tool],
    handoffs: list[Handoff],
    output_schema: AgentOutputSchemaBase | None,
) -> ProcessedResponse:
    """Parse a ModelResponse into RunItems + next-step intent.

    MVP rules:
    - Any `function_call` whose name matches a handoff ⇒ `handoff_target` is set.
    - Any `function_call` whose name matches a tool    ⇒ emit `ToolCallItem`.
    - An assistant `message` item                       ⇒ emit `MessageOutputItem`.
    - If `output_schema` is set and we see a message, validate the text as structured output.
    """
    processed = ProcessedResponse()
    tool_by_name = {getattr(t, "name", ""): t for t in tools}
    handoff_by_name = {h.tool_name: h for h in handoffs}

    for output_item in response.output:
        item_type = output_item.get("type")

        if item_type == "message":
            text = _extract_text_from_message(output_item)
            msg_item = MessageOutputItem(agent=agent, raw_item=output_item)
            processed.new_items.append(msg_item)
            # Resolve final output only for plain-text or structured-output agents.
            if output_schema is None:
                processed.final_output = text
            else:
                try:
                    processed.final_output = output_schema.validate_json(text)
                except ModelBehaviorError:
                    # Keep the text raw; Runner will escalate.
                    processed.final_output = text

        elif item_type == "function_call":
            name = output_item.get("name") or ""
            if name in handoff_by_name:
                processed.handoff_target = handoff_by_name[name].agent
                # Synthesize the matching HandoffCallItem so history stays consistent.
                from ..items import HandoffCallItem

                processed.new_items.append(HandoffCallItem(agent=agent, raw_item=output_item))
                continue
            if name in tool_by_name:
                processed.has_tool_calls = True
                processed.new_items.append(
                    ToolCallItem(agent=agent, raw_item=output_item)
                )
            else:
                raise ModelBehaviorError(
                    f"Model called unknown tool {name!r}. Available tools: "
                    f"{sorted(tool_by_name)} handoffs: {sorted(handoff_by_name)}"
                )

        elif item_type == "reasoning":
            from ..items import ReasoningItem

            processed.new_items.append(ReasoningItem(agent=agent, raw_item=output_item))

    return processed


async def execute_tools_and_side_effects(
    *,
    agent: Agent[Any],
    processed: ProcessedResponse,
    context_wrapper: RunContextWrapper[Any],
    tools: list[Tool],
) -> list[RunItem]:
    """Run every tool call in the processed response and produce `ToolCallOutputItem`s.

    v0.2: concurrent execution with timeouts, approvals, and guardrails.
    """
    from .tool_execution import execute_function_tool_calls
    
    # Extract tool call items
    tool_call_items = [
        item for item in processed.new_items 
        if isinstance(item, ToolCallItem)
    ]
    
    if not tool_call_items:
        return []
    
    # Execute with concurrency and timeouts
    outputs = await execute_function_tool_calls(
        tool_call_items=tool_call_items,
        tools=tools,
        context_wrapper=context_wrapper,
        agent=agent,
        timeout=30.0,  # Default timeout
        max_concurrency=10,  # Default max concurrency
        input_guardrails=[],  # TODO: get from agent config
        output_guardrails=[],  # TODO: get from agent config
    )
    
    return outputs


def build_next_step(processed: ProcessedResponse) -> Any:
    if processed.handoff_target is not None:
        return NextStepHandoff(target=processed.handoff_target)
    if processed.has_pending_approvals and processed.pending_approvals:
        return NextStepInterruption(interruptions=list(processed.pending_approvals))
    if processed.has_tool_calls:
        return NextStepRunAgain()
    if processed.final_output is not None or not processed.new_items:
        return NextStepFinalOutput(final_output=processed.final_output)
    return NextStepRunAgain()


__all__ = [
    "build_next_step",
    "execute_tools_and_side_effects",
    "process_model_response",
]