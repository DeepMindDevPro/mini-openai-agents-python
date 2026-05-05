"""Smoke tests for v0.1 MVP — verifies import + hello-world + basic tool call."""
from __future__ import annotations

import asyncio

import pytest


def test_package_imports_cleanly() -> None:
    """All public API symbols should be importable with no side effects."""
    import microagent  # noqa: F401

    assert hasattr(microagent, "Agent")
    assert hasattr(microagent, "Runner")
    assert hasattr(microagent, "function_tool")
    assert hasattr(microagent, "FakeModel")
    assert hasattr(microagent, "RunState")
    assert hasattr(microagent, "CURRENT_SCHEMA_VERSION")
    assert hasattr(microagent, "__version__")


def test_run_state_schema_has_entry_for_current_version() -> None:
    from microagent import CURRENT_SCHEMA_VERSION, SCHEMA_VERSION_SUMMARIES

    assert CURRENT_SCHEMA_VERSION in SCHEMA_VERSION_SUMMARIES
    assert SCHEMA_VERSION_SUMMARIES[CURRENT_SCHEMA_VERSION].strip() != ""


def test_stream_event_names_are_literals() -> None:
    """Stream event names are a contract — this test freezes them."""
    from typing import get_args, get_type_hints

    from microagent.stream_events import RunItemStreamEvent

    # With `from __future__ import annotations`, dataclass field.type is a string;
    # use `get_type_hints` to resolve the real Literal annotation.
    hints = get_type_hints(RunItemStreamEvent)
    allowed = set(get_args(hints["name"]))
    assert "message_output_created" in allowed
    assert "tool_called" in allowed
    assert "handoff_occurred" in allowed  # correct spelling by design


@pytest.mark.asyncio
async def test_hello_world_with_fake_model() -> None:
    """End-to-end smoke: FakeModel produces final_output, no tools involved."""
    from microagent import Agent, FakeModel, FakeModelTurn, Runner

    model = FakeModel([FakeModelTurn(final_output="Hello from FakeModel.")])
    agent = Agent(name="Smoke", instructions="Be terse.", model=model)

    result = await Runner.run(agent, "Hi!")
    assert result.final_output == "Hello from FakeModel."
    assert result.last_agent is agent
    assert len(result.new_items) >= 1


@pytest.mark.asyncio
async def test_function_tool_invocation() -> None:
    """The Runner should dispatch a tool call and feed its output back to the model."""
    from microagent import Agent, FakeModel, FakeModelTurn, Runner, function_tool

    calls: list[str] = []

    @function_tool
    def greet(name: str) -> str:
        """Greet someone by name."""
        calls.append(name)
        return f"Hello, {name}!"

    model = FakeModel(
        [
            FakeModelTurn(tool_calls=[("greet", {"name": "World"})]),
            FakeModelTurn(final_output="Greeting done."),
        ]
    )
    agent = Agent(
        name="ToolAgent",
        instructions="Use the greet tool.",
        tools=[greet],
        model=model,
    )
    result = await Runner.run(agent, "Say hi to World")
    assert result.final_output == "Greeting done."
    assert calls == ["World"]


def test_runner_run_sync_hello_world() -> None:
    """`Runner.run_sync` should wrap the async path transparently."""
    from microagent import Agent, FakeModel, FakeModelTurn, Runner

    model = FakeModel([FakeModelTurn(final_output="sync hello")])
    agent = Agent(name="Sync", instructions=None, model=model)
    result = Runner.run_sync(agent, "hey")
    assert result.final_output == "sync hello"