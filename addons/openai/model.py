"""OpenAI ChatCompletions model implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from microagent.models.interface import Model, ModelTracing
from microagent.items import TResponseInputItem
from microagent.agent_output import AgentOutputSchemaBase
from microagent.handoffs import Handoff
from microagent.tool import Tool


try:
    import openai
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIModel(Model):
    """OpenAI ChatCompletions model implementation."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI model."""
        if not HAS_OPENAI:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        self.model_name = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        self._kwargs = kwargs

    async def get_response(
        self,
        system_instructions: str | None,
        model_input: list[TResponseInputItem],
        model_settings: Any,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing = ModelTracing.ENABLED,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> Any:
        """Get non-streaming response from OpenAI."""
        # Prepare messages
        messages = []
        
        if system_instructions:
            messages.append({"role": "system", "content": system_instructions})
        
        messages.extend(model_input)
        
        # Prepare tools
        openai_tools = []
        for tool in tools:
            if hasattr(tool, 'to_openai_function'):
                openai_tools.append(tool.to_openai_function())
            else:
                # Basic tool conversion
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": getattr(tool, "name", "unknown"),
                        "description": getattr(tool, "description", ""),
                        "parameters": getattr(tool, "parameters", {"type": "object", "properties": {}}),
                    }
                })
        
        # Prepare request
        request_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "tools": openai_tools if openai_tools else None,
            "tool_choice": "auto" if openai_tools else None,
        }
        
        # Add model settings
        if model_settings:
            if hasattr(model_settings, 'temperature'):
                request_params["temperature"] = model_settings.temperature
            if hasattr(model_settings, 'max_tokens'):
                request_params["max_tokens"] = model_settings.max_tokens
            if hasattr(model_settings, 'top_p'):
                request_params["top_p"] = model_settings.top_p
        
        # Add response format for structured output
        if output_schema:
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": output_schema.model_json_schema(),
                    "strict": True,
                }
            }
        
        try:
            response = await self.client.chat.completions.create(**request_params)
            
            # Convert to internal format
            return self._convert_openai_response(response)
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    async def stream_response(
        self,
        system_instructions: str | None,
        model_input: list[TResponseInputItem],
        model_settings: Any,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Get streaming response from OpenAI."""
        # Prepare messages
        messages = []
        
        if system_instructions:
            messages.append({"role": "system", "content": system_instructions})
        
        messages.extend(model_input)
        
        # Prepare tools
        openai_tools = []
        for tool in tools:
            if hasattr(tool, 'to_openai_function'):
                openai_tools.append(tool.to_openai_function())
            else:
                # Basic tool conversion
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": getattr(tool, "name", "unknown"),
                        "description": getattr(tool, "description", ""),
                        "parameters": getattr(tool, "parameters", {"type": "object", "properties": {}}),
                    }
                })
        
        # Prepare request
        request_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "tools": openai_tools if openai_tools else None,
            "tool_choice": "auto" if openai_tools else None,
            "stream": True,
        }
        
        # Add model settings
        if model_settings:
            if hasattr(model_settings, 'temperature'):
                request_params["temperature"] = model_settings.temperature
            if hasattr(model_settings, 'max_tokens'):
                request_params["max_tokens"] = model_settings.max_tokens
            if hasattr(model_settings, 'top_p'):
                request_params["top_p"] = model_settings.top_p
        
        try:
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                yield self._convert_openai_chunk(chunk)
                
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    def _convert_openai_response(self, response: Any) -> Any:
        """Convert OpenAI response to internal format."""
        # This is a simplified conversion - in practice would need more detailed mapping
        return {
            "id": response.id,
            "object": "chat.completion",
            "created": response.created,
            "model": response.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                }
                            }
                            for tool_call in (choice.message.tool_calls or [])
                        ] if choice.message.tool_calls else None,
                    },
                    "finish_reason": choice.finish_reason,
                }
                for choice in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if response.usage else None,
        }

    def _convert_openai_chunk(self, chunk: Any) -> Dict[str, Any]:
        """Convert OpenAI streaming chunk to internal format."""
        return {
            "id": chunk.id,
            "object": "chat.completion.chunk",
            "created": chunk.created,
            "model": chunk.model,
            "choices": [
                {
                    "index": choice.index,
                    "delta": {
                        "role": choice.delta.role,
                        "content": choice.delta.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                }
                            }
                            for tool_call in (choice.delta.tool_calls or [])
                        ] if choice.delta.tool_calls else None,
                    },
                    "finish_reason": choice.finish_reason,
                }
                for choice in chunk.choices
            ],
        }

    async def get_retry_advice(self, error: Exception) -> Any:
        """Get retry advice for OpenAI errors."""
        if "rate_limit" in str(error).lower():
            return {"should_retry": True, "delay": 1.0}
        elif "timeout" in str(error).lower():
            return {"should_retry": True, "delay": 0.5}
        else:
            return {"should_retry": False, "delay": 0.0}