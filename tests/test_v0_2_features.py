"""Tests for v0.2 features."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from microagent import (
    Agent,
    FakeModel,
    FakeModelTurn,
    Runner,
    RunState,
    create_run_state_from_result,
    resume_run_state,
    async_resume_run_state,
    function_tool,
)
from microagent.run_internal.run_grouping import (
    generate_prompt_cache_key,
    get_cache_key_hierarchy,
    select_best_cache_key,
)
from microagent.run_internal.streaming import (
    QueueCompleteSentinel,
    create_stream_generator,
    stream_step_items_to_queue,
)


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is sunny."


@function_tool
def calculate_distance(origin: str, destination: str) -> str:
    """Calculate the distance between two cities."""
    return f"The distance from {origin} to {destination} is 500 miles."


@pytest.mark.asyncio
async def test_streaming_basic() -> None:
    """Test basic streaming functionality."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Tokyo"})]),
        FakeModelTurn(final_output="The weather in Tokyo is sunny."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Test streaming result creation
    streaming_result = Runner.run_streamed(agent, "What's the weather in Tokyo?")
    assert streaming_result is not None
    assert hasattr(streaming_result, '_event_queue')


@pytest.mark.asyncio
async def test_runstate_creation_and_resume() -> None:
    """Test RunState creation and resume functionality."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Paris"})]),
        FakeModelTurn(final_output="The weather in Paris is partly cloudy."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Initial run
    result = await Runner.run(agent, "What's the weather in Paris?")
    assert result.final_output == "The weather in Paris is partly cloudy."
    
    # Create RunState from result
    run_state = create_run_state_from_result(result, "What's the weather in Paris?")
    assert run_state is not None
    assert run_state._starting_agent is agent
    assert len(run_state._generated_items) > 0
    
    # Test conversation history extraction
    history = run_state.get_conversation_history()
    assert len(history) > 0
    assert any(item.get("role") == "user" for item in history)


def test_runstate_resume_sync() -> None:
    """Test RunState resume with sync function."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "London"})]),
        FakeModelTurn(final_output="The weather in London is rainy."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Initial run
    result = Runner.run_sync(agent, "What's the weather in London?")
    run_state = create_run_state_from_result(result, "What's the weather in London?")
    
    # Resume with new input
    resumed_result = resume_run_state(
        run_state=run_state,
        new_input="Now what's the weather in Berlin?",
    )
    
    assert resumed_result is not None
    assert isinstance(resumed_result.final_output, str)


@pytest.mark.asyncio
async def test_runstate_resume_async() -> None:
    """Test RunState resume with async function."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Madrid"})]),
        FakeModelTurn(final_output="The weather in Madrid is sunny."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    # Initial run
    result = await Runner.run(agent, "What's the weather in Madrid?")
    run_state = create_run_state_from_result(result, "What's the weather in Madrid?")
    
    # Resume with new input
    resumed_result = await async_resume_run_state(
        run_state=run_state,
        new_input="Now what's the weather in Barcelona?",
    )
    
    assert resumed_result is not None
    assert isinstance(resumed_result.final_output, str)


def test_prompt_cache_key_generation() -> None:
    """Test prompt cache key generation."""
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
    
    assert isinstance(cache_key, str)
    assert len(cache_key) == 64  # SHA-256 hash length
    
    # Test consistency
    cache_key2 = generate_prompt_cache_key(
        system_instructions=system_instructions,
        model_input=model_input,
        model_name=model_name,
        tools=tools,
    )
    
    assert cache_key == cache_key2


def test_cache_key_hierarchy() -> None:
    """Test cache key hierarchy generation."""
    hierarchy = get_cache_key_hierarchy(
        conversation_id="conv123",
        session_id="sess456",
        group_id="group789",
        run_id="run101",
    )
    
    assert len(hierarchy) == 5
    assert hierarchy[0] == "run:run101"
    assert hierarchy[1] == "group:group789"
    assert hierarchy[2] == "session:sess456"
    assert hierarchy[3] == "conversation:conv123"
    assert hierarchy[4] == "global"


def test_select_best_cache_key() -> None:
    """Test cache key selection."""
    prompt_cache_key = "abc123def456"
    hierarchy = ["run:run1", "group:group1", "session:sess1", "global"]
    existing_keys = ["group:group1:abc123def456", "global:abc123def456"]
    
    best_key = select_best_cache_key(
        prompt_cache_key=prompt_cache_key,
        hierarchy=hierarchy,
        existing_keys=existing_keys,
    )
    
    assert best_key == "group:group1:abc123def456"


@pytest.mark.asyncio
async def test_tool_execution_with_concurrency() -> None:
    """Test tool execution with concurrency."""
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
    
    assert result is not None
    assert isinstance(result.final_output, str)
    
    # Count tool calls
    tool_calls = [item for item in result.new_items if item.type == "tool_call_item"]
    assert len(tool_calls) == 2


@pytest.mark.asyncio
async def test_streaming_queue_operations() -> None:
    """Test streaming queue operations."""
    import asyncio
    from microagent.items import MessageOutputItem
    
    # Create a queue
    queue = asyncio.Queue()
    
    # Create some items
    items = [
        MessageOutputItem(
            agent=None,  # type: ignore
            raw_item={"type": "message", "content": "Hello"},
        )
    ]
    
    # Test streaming items to queue
    await stream_step_items_to_queue(items, queue, agent_name="test_agent")
    
    # Get item from queue
    event = await queue.get()
    assert event.name == "message_output_item"
    assert event.agent_name == "test_agent"


@pytest.mark.asyncio
async def test_runstate_approve_reject() -> None:
    """Test RunState approve/reject functionality."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Rome"})]),
        FakeModelTurn(final_output="The weather in Rome is sunny."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    result = await Runner.run(agent, "What's the weather in Rome?")
    run_state = create_run_state_from_result(result, "What's the weather in Rome?")
    
    # Test approve/reject methods
    run_state.approve("tool_call_123")
    run_state.reject("tool_call_456", "Tool not allowed")
    
    # Test set_prompt_cache_key
    run_state.set_prompt_cache_key("test_cache_key_123")
    assert run_state._generated_prompt_cache_key == "test_cache_key_123"


def test_runstate_json_serialization() -> None:
    """Test RunState JSON serialization."""
    model = FakeModel([
        FakeModelTurn(tool_calls=[("get_weather", {"city": "Vienna"})]),
        FakeModelTurn(final_output="The weather in Vienna is cloudy."),
    ])
    
    agent = Agent(
        name="Weather Assistant",
        instructions="Answer weather questions using the provided tool.",
        tools=[get_weather],
        model=model,
    )
    
    result = Runner.run_sync(agent, "What's the weather in Vienna?")
    run_state = create_run_state_from_result(result, "What's the weather in Vienna?")
    
    # Test to_json
    json_str = run_state.to_json()
    assert isinstance(json_str, str)
    
    # Parse JSON to verify structure
    data = json.loads(json_str)
    assert "schema_version" in data
    assert data["schema_version"] == "1.0"


@pytest.mark.asyncio
async def test_tool_execution_with_timeouts() -> None:
    """Test tool execution with timeouts."""
    # This would test the timeout functionality in tool_execution.py
    # For now, we'll just verify the functions exist
    from microagent.run_internal.tool_execution import (
        execute_function_tool_calls,
        execute_computer_actions,
        execute_shell_calls,
        execute_apply_patch_calls,
        maybe_reset_tool_choice,
    )
    
    assert callable(execute_function_tool_calls)
    assert callable(execute_computer_actions)
    assert callable(execute_shell_calls)
    assert callable(execute_apply_patch_calls)
    assert callable(maybe_reset_tool_choice)


def test_nest_handoff_history() -> None:
    """Test nest_handoff_history functionality."""
    from microagent.handoffs import nest_handoff_history, HandoffInputData
    
    # Create test data
    input_data = HandoffInputData(
        input_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well"},
        ],
        context=None,
        agent=None,
        target_agent=None,
    )
    
    # Test with long history (>20 items)
    long_history = [{"role": "user", "content": f"Message {i}"} for i in range(25)]
    long_input_data = HandoffInputData(
        input_history=long_history,
        context=None,
        agent=None,
        target_agent=None,
    )
    
    result = nest_handoff_history(long_input_data)
    assert len(result.input_history) < len(long_history)  # Should be compacted


if __name__ == "__main__":
    # Run tests manually if needed
    asyncio.run(test_streaming_basic())
    asyncio.run(test_runstate_creation_and_resume())
    test_runstate_resume_sync()
    asyncio.run(test_runstate_resume_async())
    test_prompt_cache_key_generation()
    test_cache_key_hierarchy()
    test_select_best_cache_key()
    asyncio.run(test_tool_execution_with_concurrency())
    asyncio.run(test_streaming_queue_operations())
    asyncio.run(test_runstate_approve_reject())
    test_runstate_json_serialization()
    asyncio.run(test_tool_execution_with_timeouts())
    test_nest_handoff_history()
    print("All tests passed!")