"""Tests exercising parity with `openai-agents-python` core design highlights.

Each test corresponds to one bullet in `ARCHITECTURE_ANALYSIS.md`.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from microagent import (
    Agent,
    FakeModel,
    FakeModelTurn,
    MultiProvider,
    RunConfig,
    RunContextWrapper,
    Runner,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    UserError,
    function_tool,
    is_openai_responses_compaction_aware_session,
    prompt_with_handoff_instructions,
)
from microagent.extensions.handoff_filters import (
    keep_last_n_messages,
    remove_all_tools,
)
from microagent.extensions.visualization import draw_graph
from microagent.handoffs import HandoffInputData
from microagent.memory import InMemorySession
from microagent.models.interface import ModelProvider
from microagent.run_internal.approvals import get_approval_decision
from microagent.run_internal.oai_conversation import OpenAIServerConversationTracker
from microagent.run_internal.prompt_cache_key import PromptCacheKeyResolver
from microagent.run_internal.tool_use_tracker import (
    AgentToolUseTracker,
    maybe_reset_tool_choice,
)
from microagent.run_state import RunState
from microagent.sandbox import (
    BaseSandboxClientOptions,
    Capability,
    CapabilityRegistry,
    Manifest,
    MountEntry,
)


# --- #1 RunErrorHandlers integration ----------------------------------------


@pytest.mark.asyncio
async def test_max_turns_error_handler_converts_to_final_output() -> None:
    # Script that would loop forever via synthetic tool calls.
    model = FakeModel(
        [FakeModelTurn(tool_calls=[("noop", {})])] * 5
    )

    @function_tool
    def noop() -> str:
        return "ok"

    agent = Agent(name="Looper", instructions=None, tools=[noop], model=model)

    def handler(payload: RunErrorHandlerInput) -> RunErrorHandlerResult:
        return RunErrorHandlerResult(final_output="recovered")

    result = await Runner.run(
        agent,
        "go",
        max_turns=2,
        error_handlers={"max_turns": handler},
    )
    assert result.final_output == "recovered"


# --- #2 AgentToolUseTracker + reset_tool_choice -----------------------------


def test_agent_tool_use_tracker_reset_and_serialization() -> None:
    agent = Agent(name="A", instructions=None, reset_tool_choice=True)
    tracker = AgentToolUseTracker()

    tracker.add_tool_use(agent, ["lookup"])
    assert tracker.has_used_tools(agent)
    assert "lookup" in tracker.as_serializable()["A"]

    from microagent.model_settings import ModelSettings

    settings = ModelSettings(tool_choice="required")
    reset = maybe_reset_tool_choice(agent, tracker, settings)
    assert reset.tool_choice is None

    # Round-trip serialization.
    restored = AgentToolUseTracker.from_serializable(tracker.as_serializable())
    assert restored.as_serializable() == tracker.as_serializable()


# --- #3 OpenAIServerConversationTracker three-view dedupe --------------------


def test_oai_conversation_tracker_dedupe_via_fingerprint_and_id() -> None:
    tracker = OpenAIServerConversationTracker(conversation_id="conv_1")
    assert tracker.is_active

    first = {"role": "user", "content": "hello", "id": "item_1"}
    tracker.mark_input_as_sent([first])

    # Same object identity → filtered.
    assert tracker.filter_outgoing([first]) == []
    # Same ID but different object → still filtered.
    clone_by_id = {"role": "user", "content": "hello", "id": "item_1"}
    assert tracker.filter_outgoing([clone_by_id]) == []
    # New item not yet acknowledged → kept.
    new_item = {"role": "user", "content": "next"}
    assert tracker.filter_outgoing([new_item]) == [new_item]


# --- #4 PromptCacheKeyResolver ----------------------------------------------


def test_prompt_cache_key_resolver_is_stable_and_persists_to_runstate() -> None:
    state = RunState(original_input="q", starting_agent=None)
    resolver = PromptCacheKeyResolver.from_run_state(run_state=state)
    from microagent.model_settings import ModelSettings

    class _SentinelModel:
        supports_prompt_cache_key = True

    key1 = resolver.resolve(
        ModelSettings(),
        model=_SentinelModel(),
        conversation_id="c1",
        session=None,
        group_id=None,
    )
    key2 = resolver.resolve(
        ModelSettings(),
        model=_SentinelModel(),
        conversation_id="c1",
        session=None,
        group_id=None,
    )
    assert isinstance(key1, str) and len(key1) == 64
    assert key1 == key2
    assert state._generated_prompt_cache_key == key1


# --- #5 Approvals decision helper -------------------------------------------


def test_get_approval_decision_pending_vs_approved_vs_rejected() -> None:
    from microagent.items import ToolApprovalItem

    ctx = RunContextWrapper(context={})
    approval = ToolApprovalItem(
        agent=Agent(name="X", instructions=None),
        raw_item={"type": "function_call", "name": "t", "call_id": "c1"},
        call_id="c1",
        tool_name="t",
    )

    status, _ = get_approval_decision(context=ctx, approval=approval)
    assert status == "pending"

    ctx.approve_tool(approval)
    status, _ = get_approval_decision(context=ctx, approval=approval)
    assert status == "approved"

    other = ToolApprovalItem(
        agent=approval.agent, raw_item=approval.raw_item, call_id="c2", tool_name="t"
    )
    ctx.reject_tool(other, message="nope")
    status, msg = get_approval_decision(context=ctx, approval=other)
    assert status == "rejected"
    assert msg == "nope"


# --- #6 MultiProvider prefix routing ----------------------------------------


def test_multiprovider_routes_by_prefix_and_rejects_unknown() -> None:
    class _StubProvider(ModelProvider):
        def __init__(self, tag: str) -> None:
            self.tag = tag

        def get_model(self, model_name):  # type: ignore[override]
            return f"{self.tag}:{model_name}"  # type: ignore[return-value]

    provider = MultiProvider(
        {"openai": _StubProvider("oai"), "claude": _StubProvider("ant")},
        default_prefix="openai",
    )
    assert provider.get_model("openai/gpt-4o-mini") == "oai:gpt-4o-mini"
    assert provider.get_model("claude/opus") == "ant:opus"
    # Bare name falls back to default prefix.
    assert provider.get_model("gpt-4o") == "oai:gpt-4o"

    with pytest.raises(UserError):
        provider.get_model("grok/xyz")


# --- #7 Sandbox Capability + BaseSandboxClientOptions registry --------------


def test_sandbox_base_options_registry_dispatches_polymorphically() -> None:
    opts = BaseSandboxClientOptions.from_dict({"type": "unix_local", "workspace": "/tmp/x"})
    assert opts.type == "unix_local"
    assert getattr(opts, "workspace") == "/tmp/x"
    # Registered prefixes cover the built-ins.
    assert "unix_local" in BaseSandboxClientOptions.list_registered_types()
    assert "docker" in BaseSandboxClientOptions.list_registered_types()


def test_sandbox_capability_manifest_roundtrip() -> None:
    manifest = Manifest(capabilities=["shell"]).with_mount(
        MountEntry(source="/etc/hosts", target="/etc/hosts", kind="file")
    ).with_env(FOO="bar")
    assert len(manifest.mounts) == 1
    assert manifest.env["FOO"] == "bar"

    class EchoCapability(Capability):
        type: str = "echo"

        def tools(self):  # type: ignore[override]
            return []

    CapabilityRegistry.register("echo", EchoCapability)
    assert CapabilityRegistry.resolve("echo") is EchoCapability


# --- #8 Handoff filters -----------------------------------------------------


def test_handoff_filters_remove_tools_and_keep_last_n() -> None:
    history = [
        {"role": "user", "content": "hi"},
        {"type": "function_call", "name": "f", "call_id": "c1", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": "ok"},
        {"role": "assistant", "content": "done"},
    ]
    data = HandoffInputData(input_history=history)
    cleaned = remove_all_tools(data)
    assert all(
        (not isinstance(it, dict)) or it.get("type") not in {"function_call", "function_call_output"}
        for it in cleaned.input_history
    )

    truncated = keep_last_n_messages(data, 2)
    assert len(truncated.input_history) == 2


# --- #9 Handoff prompt helper -----------------------------------------------


def test_prompt_with_handoff_instructions_prepends_prefix() -> None:
    merged = prompt_with_handoff_instructions("You are helpful.")
    assert "System context" in merged
    assert merged.endswith("You are helpful.")


# --- #10 Visualization ------------------------------------------------------


def test_draw_graph_produces_dot_source() -> None:
    child = Agent(name="Child", instructions=None)
    parent = Agent(name="Parent", instructions=None, handoffs=[child])
    dot = draw_graph(parent)
    assert dot.startswith("digraph G")
    assert "Parent" in dot
    assert "Child" in dot


# --- #11 Session capability detection ---------------------------------------


def test_is_openai_responses_compaction_aware_session_duck_type() -> None:
    session = InMemorySession("s1")
    assert not is_openai_responses_compaction_aware_session(session)

    setattr(session, "supports_openai_responses_compaction", True)
    assert is_openai_responses_compaction_aware_session(session)


# --- #12 RunState JSON round-trip keeps tracker + cache key ----------------


def test_runstate_json_roundtrip_is_schema_versioned() -> None:
    state = RunState(original_input="hello", starting_agent=None)
    state.set_prompt_cache_key("abc")
    state.approve("call_1")
    state.reject("call_2", "denied")

    payload = state.to_json()
    data = json.loads(payload)
    assert data["schema_version"] == "1.0"

    restored = RunState.from_json(payload)
    assert restored._generated_prompt_cache_key == "abc"
    assert "call_1" in restored._approved_call_ids
    assert restored._rejected_call_ids["call_2"] == "denied"