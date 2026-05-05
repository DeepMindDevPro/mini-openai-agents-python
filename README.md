# microagent

> Provider-neutral, industrial-grade, lightweight Python Agent framework.
> **Core + addon ecosystem**, designed to preserve the DNA of `openai-agents` while shedding its OpenAI bias and heavyweight components.

## 🎯 Design Philosophy

Three root principles, enforced at the code level:

1. **Runner is only orchestration** — business logic is horizontally sliced into `run_internal/`
2. **Contract is architecture** — `RunState` schema versioning, positional API compatibility, stream event literals all written into the type system
3. **Open interfaces + registries** — `Session` Protocol, `Model` ABC, `TracingProcessor`, entry-point addons

## ✨ Highlights

- **Runner-only-orchestration**: `run.py` ≤500 lines, all complexity in `run_internal/`
- **Stream & non-stream aligned**: both paths share `get_new_response` / `process_turn_output`
- **RunState v1.0 HITL pause/resume**: schema-versioned, fail-fast forward-compat
- **4-way Guardrails × 3 behaviors** + Human-in-the-Loop Approvals
- **NoOp Tracing by default** (zero-cost), OpenTelemetry-friendly exporter addon
- **Provider-neutral**: OpenAI, Anthropic, and any LLM via addon (see `addons/`)
- **Session Protocol**: 4 async methods to integrate any storage backend

## 🚀 Quickstart

```python
from microagent import Agent, Runner, function_tool


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is sunny."


agent = Agent(
    name="Assistant",
    instructions="You are a helpful weather assistant.",
    tools=[get_weather],
)

# Requires a Model implementation; see addons/
# result = await Runner.run(agent, "What is the weather in Tokyo?")
# print(result.final_output)
```

## 📦 Installation

```bash
# Core only
pip install microagent

# With OpenAI ChatCompletions adapter
pip install "microagent[openai]"

# With OpenTelemetry tracing
pip install "microagent[otel]"
```

## 🧩 Addon Ecosystem (roadmap)

| Addon | Status | Description |
|---|---|---|
| `microagent-openai` | v0.2 | OpenAI ChatCompletions & Responses adapter |
| `microagent-anthropic` | v0.3 | Anthropic Claude adapter |
| `microagent-mcp` | v0.3 | MCP stdio/SSE/HTTP clients |
| `microagent-sandbox` | v0.4 | Local/Docker sandbox runtime |
| `microagent-session-sqlite` | v0.2 | SQLite persistent session |
| `microagent-session-redis` | v0.3 | Redis session |
| `microagent-tracing-otel` | v0.2 | OpenTelemetry exporter |

## 📊 Size Targets

| Metric | Target | Compared to `openai-agents` |
|---|---|---|
| Core source LoC | ~11,000 | 18% |
| Core wheel size | ~1.2 MB | 30% |
| Cold import time | <80 ms | 25% |
| Strict deps | 2 (pydantic, typing-extensions) | 25% |

## 🗺️ Roadmap

- **v0.1 (current)**: Full directory skeleton, all core abstractions, minimal Runner
- **v0.2**: Full HITL/resume, Guardrails, Tracing NoOp, SQLite session, OpenAI addon
- **v1.0**: Addon entry-points, OTel exporter, multi-provider routing, full test coverage ≥90%

## 📜 License

MIT