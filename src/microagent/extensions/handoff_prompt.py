"""Recommended prompt prefix for agents that participate in handoffs."""
from __future__ import annotations

RECOMMENDED_PROMPT_PREFIX = (
    "# System context\n"
    "You are part of a multi-agent system, designed to make agent coordination and "
    "execution easy. Agents use two primary abstractions: **Agents** and **Handoffs**. "
    "An agent encompasses instructions and tools and can hand off a conversation to "
    "another agent when appropriate. Handoffs are achieved by calling a handoff "
    "function, generally named `transfer_to_<agent_name>`. Transfers between agents are "
    "handled seamlessly in the background; do not mention or draw attention to these "
    "transfers in your conversation with the user.\n"
)


def prompt_with_handoff_instructions(prompt: str) -> str:
    """Prepend the recommended handoff system context to an agent prompt."""
    return f"{RECOMMENDED_PROMPT_PREFIX}\n\n{prompt}"


__all__ = ["RECOMMENDED_PROMPT_PREFIX", "prompt_with_handoff_instructions"]