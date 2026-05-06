"""Tool execution helpers.

v0.2 implementation: async tool execution with concurrency, timeouts, and guardrail composition.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from concurrent.futures import TimeoutError as FutureTimeoutError

from ..tool import FunctionTool, Tool
from ..tool_context import ToolContext
from ..run_context import RunContextWrapper
from ..items import ToolCallItem, ToolCallOutputItem, RunItem
from ..tool_guardrails import ToolInputGuardrail, ToolOutputGuardrail
from ..exceptions import ToolTimeoutError, UserError


async def execute_function_tool_calls(
    *,
    tool_call_items: List[ToolCallItem],
    tools: List[Tool],
    context_wrapper: RunContextWrapper[Any],
    agent: Any,
    timeout: float = 30.0,
    max_concurrency: int = 10,
    input_guardrails: List[ToolInputGuardrail] = None,
    output_guardrails: List[ToolOutputGuardrail] = None,
) -> List[RunItem]:
    """Execute function tool calls with concurrency and timeouts."""
    if input_guardrails is None:
        input_guardrails = []
    if output_guardrails is None:
        output_guardrails = []
    
    # Map tools by name
    tool_map = {getattr(tool, "name", ""): tool for tool in tools}
    
    # Create execution coroutines guarded by a concurrency semaphore.
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_guarded(tool: FunctionTool, call_id: str, args_json: str) -> RunItem:
        async with semaphore:
            return await _execute_single_tool(
                tool=tool,
                call_id=call_id,
                args_json=args_json,
                context_wrapper=context_wrapper,
                agent=agent,
                timeout=timeout,
                input_guardrails=input_guardrails,
                output_guardrails=output_guardrails,
            )

    coros: list[Any] = []
    for item in tool_call_items:
        raw = item.raw_item
        if not isinstance(raw, dict):
            continue

        name = raw.get("name") or ""
        call_id = raw.get("call_id") or ""
        args_json = raw.get("arguments") or "{}"

        tool = tool_map.get(name)
        if not isinstance(tool, FunctionTool):
            raise UserError(f"Tool {name!r} is not a FunctionTool")

        coros.append(
            _run_guarded(
                tool=tool,
                call_id=call_id,
                args_json=args_json,
            )
        )

    # Execute all coroutines concurrently, capturing exceptions.
    results = await asyncio.gather(*coros, return_exceptions=True)
    
    # Process results
    output_items: List[RunItem] = []
    for result in results:
        if isinstance(result, Exception):
            # Handle errors
            error_msg = str(result)
            output_item = ToolCallOutputItem(
                agent=agent,
                raw_item={
                    "type": "function_call_output",
                    "call_id": "unknown",
                    "output": f"Error: {error_msg}",
                },
                output=f"Error: {error_msg}",
            )
            output_items.append(output_item)
        elif result is not None:
            output_items.append(result)
    
    return output_items


async def _execute_single_tool(
    *,
    tool: FunctionTool,
    call_id: str,
    args_json: str,
    context_wrapper: RunContextWrapper[Any],
    agent: Any,
    timeout: float,
    input_guardrails: List[ToolInputGuardrail],
    output_guardrails: List[ToolOutputGuardrail],
) -> ToolCallOutputItem:
    """Execute a single tool with guardrails."""
    # Apply input guardrails
    for guardrail in input_guardrails:
        try:
            result = await guardrail.run(
                context=context_wrapper,
                agent=agent,
                tool_name=getattr(tool, "name", ""),
                tool_arguments=args_json,
            )
            if result.output.tripwire_triggered:
                raise UserError(f"Input guardrail triggered: {result.output.message}")
        except Exception as e:
            raise UserError(f"Input guardrail error: {e}")
    
    # Create tool context
    tool_ctx = ToolContext.from_run_context(
        context_wrapper,
        tool_name=getattr(tool, "name", ""),
        tool_call_id=call_id,
        tool_arguments=args_json,
        agent=agent,
    )
    
    # Execute tool with timeout
    try:
        result = await asyncio.wait_for(
            tool.on_invoke_tool(tool_ctx, args_json),
            timeout=timeout,
        )
        
        # Apply output guardrails
        for guardrail in output_guardrails:
            try:
                result_obj = await guardrail.run(
                    context=context_wrapper,
                    agent=agent,
                    tool_name=getattr(tool, "name", ""),
                    tool_output=result,
                )
                if result_obj.output.tripwire_triggered:
                    raise UserError(f"Output guardrail triggered: {result_obj.output.message}")
            except Exception as e:
                raise UserError(f"Output guardrail error: {e}")
        
        # Create output item
        output_item = ToolCallOutputItem(
            agent=agent,
            raw_item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": result if isinstance(result, str) else json.dumps(result, default=str),
            },
            output=result,
        )
        
        return output_item
        
    except asyncio.TimeoutError:
        raise ToolTimeoutError(
            f"Tool {getattr(tool, 'name', '')} timed out after {timeout} seconds"
        )
    except Exception as e:
        raise UserError(f"Tool execution error: {e}")


async def execute_computer_actions(
    *,
    actions: List[Dict[str, Any]],
    context_wrapper: RunContextWrapper[Any],
    agent: Any,
    timeout: float = 30.0,
) -> List[RunItem]:
    """Execute computer actions."""
    # Placeholder for computer action execution
    # This would integrate with computer addon
    results: List[RunItem] = []
    
    for action in actions:
        # Simulate action execution
        result = {
            "type": "computer_action_result",
            "action_id": action.get("id"),
            "status": "completed",
            "details": f"Executed {action.get('type', 'unknown')} action",
        }
        
        # Create run item
        from ..items import ToolCallOutputItem
        output_item = ToolCallOutputItem(
            agent=agent,
            raw_item=result,
            output=json.dumps(result),
        )
        results.append(output_item)
    
    return results


async def execute_shell_calls(
    *,
    calls: List[Dict[str, Any]],
    context_wrapper: RunContextWrapper[Any],
    agent: Any,
    timeout: float = 30.0,
) -> List[RunItem]:
    """Execute shell calls."""
    # Placeholder for shell call execution
    # This would integrate with sandbox addon
    results: List[RunItem] = []
    
    for call in calls:
        # Simulate shell execution
        command = call.get("command", "")
        result = {
            "type": "shell_call_result",
            "command": command,
            "exit_code": 0,
            "stdout": f"Executed: {command}",
            "stderr": "",
        }
        
        # Create run item
        from ..items import ToolCallOutputItem
        output_item = ToolCallOutputItem(
            agent=agent,
            raw_item=result,
            output=json.dumps(result),
        )
        results.append(output_item)
    
    return results


async def execute_apply_patch_calls(
    *,
    patches: List[Dict[str, Any]],
    context_wrapper: RunContextWrapper[Any],
    agent: Any,
    timeout: float = 30.0,
) -> List[RunItem]:
    """Execute apply patch calls."""
    # Placeholder for apply patch execution
    # This would integrate with sandbox addon
    results: List[RunItem] = []
    
    for patch in patches:
        # Simulate patch application
        result = {
            "type": "apply_patch_result",
            "patch_id": patch.get("id"),
            "status": "applied",
            "details": f"Applied patch: {patch.get('description', 'unknown')}",
        }
        
        # Create run item
        from ..items import ToolCallOutputItem
        output_item = ToolCallOutputItem(
            agent=agent,
            raw_item=result,
            output=json.dumps(result),
        )
        results.append(output_item)
    
    return results


def maybe_reset_tool_choice(
    *,
    agent: Any,
    tools: List[Tool],
    reset_after_tool_use: bool = True,
) -> None:
    """Reset tool choice after tool use if needed."""
    if reset_after_tool_use:
        # Reset to auto tool choice
        agent._tool_choice = "auto"


__all__ = [
    "execute_function_tool_calls",
    "execute_computer_actions",
    "execute_shell_calls",
    "execute_apply_patch_calls",
    "maybe_reset_tool_choice",
]