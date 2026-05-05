# Contributor Guide

This document codifies the **architectural invariants** of `microagent`. Treat it as a PR review contract.

---

## 1. Mandatory Rules

### 1.1 Runner Orchestration Boundary

- `src/microagent/run.py` hosts **only** `Runner` (public) and `AgentRunner` (experimental).
- All business logic lives in `src/microagent/run_internal/`.
- When `run.py` grows, refactor helpers into `run_internal/` and re-export via `run_internal/run_loop.py`.

### 1.2 Stream ↔ Non-Stream Alignment

- `run_single_turn` and `run_single_turn_streamed` must share the same helpers:
  - `get_new_response` / `process_model_response` / `execute_tools_and_side_effects`
- New stream item names **must** be registered in `src/microagent/stream_events.py`.
- Tests under `tests/test_streaming_alignment.py` enforce behavior mirroring.

### 1.3 RunState Schema Policy

- `CURRENT_SCHEMA_VERSION` bumps **must** come with a one-line entry in `SCHEMA_VERSION_SUMMARIES`.
- Import-time assertion in `run_state.py` enforces this.
- Forward compatibility is **fail-fast**: older SDKs refuse newer snapshots.
- Released schema versions are frozen; unreleased branch-local versions may be squashed.

### 1.4 Public API Positional Compatibility

- Positional parameter and dataclass field order of public constructors is a compatibility contract:
  - `RunConfig`, `FunctionTool`, `Agent`, `AgentHookContext`, …
- New optional fields must be **appended** at the end.
- If reordering is truly necessary, add a compatibility shim + regression test.

### 1.5 Synchronized Update Points for New Run Items

Adding a new tool / output / approval item type requires coordinated changes across:

- `src/microagent/items.py` (RunItem dataclass + to_input_item)
- `src/microagent/run_internal/items.py` (normalization + dedupe + rejection builders)
- `src/microagent/run_internal/run_steps.py` (ProcessedResponse + NextStep variants)
- `src/microagent/run_internal/turn_resolution.py` (model output → RunItem extraction)
- `src/microagent/run_internal/tool_execution.py` (+ `tool_planning.py` if applicable)
- `src/microagent/stream_events.py` (stream event name Literal)
- `src/microagent/run_state.py` (serialization/deserialization)
- `src/microagent/run_internal/session_persistence.py` (save/rewind)

### 1.6 Stream Event Name Stability

Existing stream event names (e.g. `"tool_called"`, `"handoff_occurred"`) are **contracts**. Fixing typos or renaming them is a breaking change and requires a major version bump.

---

## 2. Architecture Decision Records

### 2.1 Provider Neutrality

Core is **provider-neutral**. No OpenAI-specific logic in `src/microagent/` except:

- `models/interface.py` (abstract)
- `models/fake_model.py` (testing only)

OpenAI / Anthropic / Bedrock support lives in addon packages.

### 2.2 Tracing Default NoOp

Default trace provider is `NoOpTraceProvider`. Exporters (OTel, console) are opt-in via:

```python
from microagent.tracing import add_trace_processor
```

### 2.3 Session Protocol

`Session` is a `@runtime_checkable Protocol` with 4 async methods. Third parties integrate by implementing the Protocol; they do not need to subclass `SessionABC` (internal use only).

### 2.4 MCP in Core?

Core retains `MCPServer` Protocol and `Agent.mcp_servers` field. Concrete stdio/SSE/HTTP transports live in `microagent-mcp` addon.

---

## 3. Development Workflow

### 3.1 Prereqs

- Python ≥3.10
- `uv` or `pip` for dependency management

### 3.2 Commands

```bash
# Sync deps
uv sync

# Format + lint
uv run ruff format .
uv run ruff check .

# Type check
uv run mypy src/microagent
uv run pyright src/microagent

# Tests
uv run pytest -v

# Coverage (target ≥90%)
uv run coverage run -m pytest && uv run coverage report
```

### 3.3 Required Checks Before PR

1. `ruff format` — clean
2. `ruff check` — no errors
3. `mypy strict` — pass
4. `pyright` — no errors
5. `pytest` — all green
6. Coverage ≥ 90%
7. If schema changed — matching entry in `SCHEMA_VERSION_SUMMARIES`
8. If new Item type — all 8 sync points updated (see §1.5)

---

## 4. Commit & PR Guidelines

- Commit messages: concise, imperative (`Add X`, not `Added X`).
- Small, focused commits.
- PR titles follow conventional style: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`.
- Every PR with runtime code changes must include tests.