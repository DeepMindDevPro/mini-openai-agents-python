"""v0.2 features demo - streaming, RunState resume, OpenAI addon, etc."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from microagent import (
    Agent,
    AsyncOpenAI,
    FakeModel,
    FakeModelTurn,
    Runner,
    RunState,
    create_run_state_from_result,
    resume_run_state,
    function_tool,
)
from microagent.run_internal.streaming import create_stream_generator
from microagent.run_internal.run_grouping import generate_prompt_cache_key


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is sunny with a temperature of 72°F."


@function_tool
def calculate_distance(origin: str, destination: str) -> str:
    """Calculate the distance between two cities."""
    return f"The distance from {origin} to {destination} is 500 miles."


async def demo_streaming() -> None:
    """Demo streaming functionality."""
    print("\n=== Streaming Demo ===")
    
    # Create a fake model that simulates streaming
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Tokyo"})]),
        FakeModelTurn(final_output="The weather in Tokyo is sunny with a temperature of 72°F."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Run with streaming
    streaming_result = Runner.run_streamed(agent, "What's the weather in Tokyo?")
    
    # Process streaming events
    events = []
    async for event in streaming_result.events():
        events.append(event)
        print(f"Event: {event.name}")
    
    print(f"Final output: {streaming_result.final_output}")
    print(f"Total events: {len(events)}")


async def demo_runstate_resume() -> None:
    """Demo RunState resume functionality."""
    print("\n=== RunState Resume Demo ===")
    
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Paris"})]),
        FakeModelTurn(final_output="The weather in Paris is partly cloudy with a temperature of 68°F."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Initial run
    print("Initial run...")
    result = await Runner.run(agent, "What's the weather in Paris?")
    print(f"Initial result: {result.final_output}")
    
    # Create RunState from result
    run_state = create_run_state_from_result(result, "What's the weather in Paris?")
    print(f"Created RunState with {len(run_state._generated_items)} items")
    
    # Resume with new input
    print("Resuming with new input...")
    resumed_result = resume_run_state(
        run_state=run_state,
        new_input="Now what's the weather in London?",
    )
    print(f"Resumed result: {resumed_result.final_output}")


async def demo_openai_addon() -> None:
    """Demo OpenAI addon functionality."""
    print("\n=== OpenAI Addon Demo ===")
    
    # This would require actual OpenAI API key
    # For demo purposes, we'll show the structure
    
    print("OpenAI addon structure:")
    print("- addons/openai/model.py: OpenAIModel class")
    print("- addons/openai/provider.py: OpenAIProvider class")
    print("- Support for streaming responses")
    print("- Support for tool calls")
    print("- Support for structured output")
    
    # Example usage (commented out to avoid API calls)
    """
    from addons.openai import OpenAIProvider
    
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    model = provider.get_model("gpt-4o-mini")
    
    agent = Agent(
        name="OpenAI Assistant",
        instructions="You are a helpful assistant.",
        tools=[get_weather, calculate_distance],
        model=model,
    )
    
    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(f"OpenAI result: {result.final_output}")
    """


async def demo_prompt_cache_key() -> None:
    """Demo prompt cache key generation."""
    print("\n=== Prompt Cache Key Demo ===")
    
    system_instructions = "You are a helpful weather assistant."
    model_input = [
        {"role": "user", "content": "What's the weather in Tokyo?"},
    ]
    model_name = "gpt-4o-mini"
    tools = ["get_weather"]
    
    cache_key = generate_prompt_cache_key(
        system_instructions=system_instructions,
        model_input=model_input,
        model_name=model_name,
        tools=tools,
    )
    
    print(f"Generated cache key: {cache_key}")
    print(f"Cache key length: {len(cache_key)} characters")
    
    # Show that same inputs generate same key
    cache_key2 = generate_prompt_cache_key(
        system_instructions=system_instructions,
        model_input=model_input,
        model_name=model_name,
        tools=tools,
    )
    
    print(f"Same inputs generate same key: {cache_key == cache_key2}")


async def demo_tool_execution() -> None:
    """Demo tool execution with concurrency."""
    print("\n=== Tool Execution Demo ===")
    
    model = FakeModel([
        FakeModelTurn(tool_calls=[
            ("get_weather", {"city": "Tokyo"}),
            ("calculate_distance", {"origin": "Tokyo", "destination": "Osaka"}),
        ]),
        FakeModelTurn(final_output="Weather and distance information provided."),
    ])
    
    agent = Agent(
        name="Multi-Tool Assistant",
        instructions="Use available tools to answer questions.",
        tools=[get_weather, calculate_distance],
        model=model,
    )
    
    result = await Runner.run(agent, "What's the weather in Tokyo and how far is it from Osaka?")
    print(f"Tool execution result: {result.final_output}")
    
    # Count tool calls
    tool_calls = [item for item in result.new_items if item.type == "tool_call_item"]
    print(f"Total tool calls: {len(tool_calls)}")


async def main() -> None:
    """Run all v0.2 demos."""
    print("=== microagent v0.2 Features Demo ===")
    
    await demo_streaming()
    await demo_runstate_resume()
    await demo_openai_addon()
    await demo_prompt_cache_key()
    await demo_tool_execution()
    
    print("\n=== All demos completed ===")


if __name__ == "__main__":
    asyncio.run(main())