"""AgentRunner for running agents."""

from __future__ import annotations

from typing import Any

from .agent import Agent


class AgentRunner:
    """Runner for executing agents."""

    @staticmethod
    def run_sync(
        agent: Agent,
        input: str | list[dict[str, Any]],
        context: Any = None,
        run_config: Any = None,
        hooks: Any = None,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Any:
        """Run agent synchronously."""
        # Simplified implementation for testing
        return {
            "_starting_agent_for_state": agent,
            "context_wrapper": context or {},
            "output": f"Response to: {input}",
        }

    @staticmethod
    async def run(
        agent: Agent,
        input: str | list[dict[str, Any]],
        context: Any = None,
        run_config: Any = None,
        hooks: Any = None,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Any:
        """Run agent asynchronously."""
        # Simplified implementation for testing
        return {
            "_starting_agent_for_state": agent,
            "context_wrapper": context or {},
            "output": f"Async response to: {input}",
        }

    @staticmethod
    def run_streamed(
        agent: Agent,
        input: str | list[dict[str, Any]],
        context: Any = None,
        run_config: Any = None,
        hooks: Any = None,
    ) -> Any:
        """Run agent with streaming output."""
        # Simplified implementation for testing
        class MockStreamingResult:
            def __init__(self):
                self.events_list = [
                    {"name": "run_start", "data": {"input": input}},
                    {"name": "message", "data": {"content": "Hello"}},
                    {"name": "run_complete", "data": {"output": f"Response to: {input}"}},
                ]

            async def events(self):
                for event in self.events_list:
                    yield event

        return MockStreamingResult()


__all__ = ["AgentRunner"]