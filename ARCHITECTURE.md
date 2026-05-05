# microagent — 详细架构图设计

> 本文档以**架构图为主,文字为辅**,覆盖 10 张从宏观到微观的 Mermaid 图,按"分层 → 执行流 → 契约 → 扩展点"的顺序呈现 mini 版的完整架构。

---

## 图 1:同心圆分层(L0–L4)

按照 `AGENTS.md §1.1` 约定的 "Runner 仅编排,业务关进 `run_internal/`" 原则,整个框架分成 5 个同心圆。

```mermaid
graph TB
    subgraph L0["L0 · Public API Surface (__init__.py)"]
        L0A[Agent / Runner / AgentRunner]
        L0B[RunConfig / RunState / RunResult / RunResultStreaming]
        L0C[function_tool / handoff / Session / Tool]
        L0D[InputGuardrail / OutputGuardrail / ToolInput/OutputGuardrail]
        L0E[RunHooks / AgentHooks / RunContextWrapper]
        L0F[MultiProvider / FakeModel / Model]
        L0G[StreamEvent × 3 / tracing × 13 Span]
    end

    subgraph L1["L1 · Domain Abstractions"]
        L1A["agent.py<br/>(Agent / AgentBase / StopAtTools)"]
        L1B["items.py<br/>(13 RunItem + ItemHelpers + ModelResponse)"]
        L1C["handoffs.py<br/>(Handoff / HandoffInputData / nest_handoff_history)"]
        L1D["guardrail.py + tool_guardrails.py<br/>(4 位 Guardrail × 3 行为)"]
        L1E["lifecycle.py<br/>(RunHooks / AgentHooks)"]
        L1F["agent_output.py / agent_tool_input.py<br/>/ agent_tool_state.py / _tool_identity.py"]
        L1G["run_context.py / tool_context.py<br/>(RunContextWrapper + Approval ledger)"]
    end

    subgraph L2["L2 · Runner Orchestration"]
        L2A["run.py<br/>Runner.run / run_sync / run_streamed<br/>(≈290 行)"]
        L2B["agent_runner.py<br/>AgentRunner(实验性)"]
        L2C["streaming.py<br/>run_streamed 入口"]
        L2D["run_state_resume.py<br/>resume_run_state / create_run_state_from_result"]
    end

    subgraph L3["L3 · run_internal × 20 (切片)"]
        L3A["run_loop.py<br/>single_turn + re-export 面板"]
        L3B[turn_preparation + turn_resolution]
        L3C[tool_execution + tool_planning + tool_actions]
        L3D[guardrails + approvals]
        L3E[oai_conversation 三视图去重]
        L3F[model_retry + prompt_cache_key + run_grouping]
        L3G[tool_use_tracker + session_persistence]
        L3H["error_handlers + streaming<br/>+ _asyncio_progress + items + run_steps"]
    end

    subgraph L4["L4 · Plugins and Backends"]
        L4A["models/<br/>Model ABC + FakeModel + MultiProvider"]
        L4B["memory/<br/>Session Protocol + InMemorySession"]
        L4C["tool/<br/>FunctionTool + Tool Protocol"]
        L4D["sandbox/<br/>Manifest + Capability + BaseSandboxSession"]
        L4E["tracing/<br/>NoOp 默认 + 13 Span"]
        L4F["extensions/<br/>handoff_filters + handoff_prompt + visualization"]
    end

    subgraph ADDON["Addons (进程外扩展)"]
        AD1[addons/openai OpenAI ChatCompletions]
        AD2[addons/session_sqlite]
        AD3[addons/tracing_otel]
    end

    L0 --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 -.可选装.-> ADDON
```

**不变量**:
- L2 **只持有 ≈290 行**,绝不跨 L3 直接写业务
- L3 的 20 个切片对 L2 暴露 `run_loop.py` 单一 import 面板
- L4 全部默认行为都是 **NoOp / In-Memory / FakeModel**,重资产上云靠 addon

---

## 图 2:完整模块拓扑(40+ 文件全景)

```mermaid
graph LR
    classDef public fill:#e0f2fe,stroke:#0284c7
    classDef domain fill:#fef3c7,stroke:#d97706
    classDef runner fill:#fecaca,stroke:#dc2626
    classDef internal fill:#ddd6fe,stroke:#7c3aed
    classDef plugin fill:#d1fae5,stroke:#059669

    INIT["__init__.py<br/>(公开 API 面板)"]:::public
    CFG["_config.py<br/>(全局默认 openai key / client / api)"]:::public

    AGENT[agent.py]:::domain
    ITEMS[items.py]:::domain
    HAND[handoffs.py]:::domain
    GUARD[guardrail.py]:::domain
    TGUARD[tool_guardrails.py]:::domain
    LIFE[lifecycle.py]:::domain
    AOUT[agent_output.py]:::domain
    AINP[agent_tool_input.py]:::domain
    ASTAT[agent_tool_state.py]:::domain
    TID[_tool_identity.py]:::domain
    RCTX[run_context.py]:::domain
    TCTX[tool_context.py]:::domain
    PROMPT[prompts.py]:::domain
    MS[model_settings.py]:::domain
    RC[run_config.py]:::domain
    REH[run_error_handlers.py]:::domain
    RETRY[retry.py]:::domain
    EXC[exceptions.py]:::domain
    USAGE[usage.py]:::domain
    STRICT[strict_schema.py]:::domain
    FSCH[function_schema.py]:::domain

    RUN[run.py Runner]:::runner
    ARUN[agent_runner.py]:::runner
    STRM[streaming.py]:::runner
    RSRES[run_state_resume.py]:::runner
    RSTATE[run_state.py]:::runner
    RESULT[result.py]:::runner
    REPL[repl.py]:::runner
    STREAMEV[stream_events.py]:::runner

    RL[run_loop.py]:::internal
    TP[turn_preparation.py]:::internal
    TR[turn_resolution.py]:::internal
    TEXEC[tool_execution.py]:::internal
    TPLAN[tool_planning.py]:::internal
    TACT[tool_actions.py]:::internal
    GRD[guardrails.py]:::internal
    APRV[approvals.py]:::internal
    OCONV[oai_conversation.py]:::internal
    MRETRY[model_retry.py]:::internal
    PCACHE[prompt_cache_key.py]:::internal
    RGRP[run_grouping.py]:::internal
    TUT[tool_use_tracker.py]:::internal
    SESP[session_persistence.py]:::internal
    EHI[error_handlers.py]:::internal
    ITMI[items.py_internal]:::internal
    RSTI[run_steps.py]:::internal
    STRMI[streaming.py_internal]:::internal
    ASYP[_asyncio_progress.py]:::internal

    MODI[models/interface.py]:::plugin
    FAKEM[models/fake_model.py]:::plugin
    MULTI[models/multi_provider.py]:::plugin
    SESSP[memory/session.py]:::plugin
    IMS[memory/in_memory_session.py]:::plugin
    FTOOL[tool/function.py]:::plugin
    TOUT[tool/outputs.py]:::plugin
    TORG[tool/origin.py]:::plugin
    SBM[sandbox/manifest.py]:::plugin
    SBC[sandbox/capability.py]:::plugin
    SBS[sandbox/session.py]:::plugin
    SBO[sandbox/options.py]:::plugin
    TRAC[tracing/*]:::plugin
    EXT[extensions/*]:::plugin

    INIT --> RUN & AGENT & ITEMS & CFG
    RUN --> RL & RSTATE & RESULT & STREAMEV & RCTX & REH
    RUN --> OCONV & TUT & MRETRY & PCACHE & APRV & EHI
    STRM --> RUN
    RSRES --> RUN & RSTATE
    ARUN --> RL

    RL --> TP & TR & GRD & TEXEC & SESP & ITMI & RSTI & RGRP
    TR --> ITEMS & TEXEC & RSTI
    TEXEC --> FTOOL & TCTX & TGUARD & EXC
    TP --> AGENT & AOUT & HAND & MODI & RC
    GRD --> GUARD
    APRV --> RCTX & ITEMS
    OCONV --> ITEMS
    MRETRY --> RETRY
    PCACHE --> RSTATE & MS & RGRP
    TUT --> ITEMS & MS
    SESP --> SESSP
    EHI --> REH & EXC

    AGENT --> MS & HAND & AOUT & PROMPT & GUARD & LIFE & FTOOL & TORG
    ITEMS --> USAGE & TID
    HAND --> ITEMS & RCTX
    FTOOL --> FSCH & STRICT & TCTX & TGUARD
    MS --> RETRY
    RC --> MS & GUARD & HAND & SESSP
    RSTATE --> ITEMS
    RESULT --> ITEMS & STREAMEV

    MODI --> ITEMS & AOUT & HAND & MS
    FAKEM --> MODI
    MULTI --> MODI & EXC
    IMS --> SESSP
    SBC --> SBM & FTOOL & ITEMS
    SBS --> SBM
    SBO --> SBM
    EXT --> HAND & ITEMS
```

---

## 图 3:`run_internal/` 切片关系(20 个文件的依赖网)

```mermaid
graph TB
    subgraph CORE["核心主干"]
        RLOOP[run_loop.py<br/>⭐ re-export 面板]
        TPREP[turn_preparation.py<br/>resolve tools/handoffs/model]
        TRESO[turn_resolution.py<br/>ModelResponse → RunItem + NextStep]
        RSTEPS[run_steps.py<br/>NextStepFinal/Handoff/Interruption/RunAgain]
    end

    subgraph TOOLS["工具执行"]
        TEXEC[tool_execution.py<br/>并发 + timeout + guardrail]
        TPLAN[tool_planning.py<br/>stub]
        TACT[tool_actions.py<br/>stub]
    end

    subgraph GUARDS["守护门 × 审批"]
        GRD[guardrails.py<br/>Input/Output 串行]
        APRV[approvals.py<br/>三态决策 + rejection 合成]
    end

    subgraph STATE["状态与追踪"]
        OCONV[oai_conversation.py<br/>三视图去重]
        TUT[tool_use_tracker.py<br/>reset_tool_choice]
        SESP[session_persistence.py<br/>history 合并]
        ITMS[items.py<br/>normalize/dedupe/rejection]
    end

    subgraph RETRY["重试 × 缓存"]
        MRETRY[model_retry.py<br/>call_with_retry 指数退避+抖动]
        PCK[prompt_cache_key.py<br/>PromptCacheKeyResolver]
        RGRP[run_grouping.py<br/>conversation/session/group/run]
    end

    subgraph STREAM["流式 & 异常"]
        STRMI[streaming.py<br/>queue 扇出]
        EHI[error_handlers.py<br/>max_turns/model_refusal 降级]
        ASYP[_asyncio_progress.py<br/>cancelled coro 内省]
    end

    RLOOP --> TPREP
    RLOOP --> TRESO
    RLOOP --> GRD
    RLOOP --> TEXEC
    RLOOP --> SESP
    RLOOP --> ITMS
    RLOOP --> RSTEPS
    RLOOP --> RGRP

    TRESO --> RSTEPS
    TRESO --> TEXEC
    TEXEC --> ITMS
    TEXEC --> APRV

    APRV --> ITMS

    PCK --> RGRP
    MRETRY -.被调用.-> RLOOP

    STRMI -.填充 queue.-> RSTEPS
    EHI -.兜底.-> RSTEPS

    OCONV -.三视图.-> ITMS
    TUT -.reset.-> TRESO
```

**关键依赖规则**:
- **禁止反向依赖**:L3 不能 import L2(`run.py`)
- **禁止横穿 `run_internal/` 以外**:切片之间只能通过 `run_loop.py` re-export 面板暴露
- 所有 L3 文件都 `from ..xxx import` domain/contract,**绝不**直接 `from ..run import`

---

## 图 4:`Runner.run` 单轮执行流(时序)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant R as Runner.run
    participant CTX as RunContextWrapper
    participant TUT as AgentToolUseTracker
    participant OC as OpenAIServerConversationTracker
    participant TP as turn_preparation
    participant M as Model
    participant TR as turn_resolution
    participant TE as tool_execution
    participant EH as error_handlers

    U->>R: run(agent, input, max_turns=10, ...)
    R->>CTX: _coerce_context(context)
    R->>TUT: new AgentToolUseTracker()
    R->>OC: new OpenAIServerConversationTracker(conv_id, prev_id)

    loop 每一轮(turn ≤ max_turns)
        alt turn > max_turns
            R->>EH: build_run_error_data + maybe_handle_run_error
            alt handler 返回 final_output
                EH-->>R: RunErrorHandlerResult(final_output=...)
                R-->>U: RunResult(final_output=降级输出)
            else 没有 handler
                EH-->>R: None
                R-->>U: raise MaxTurnsExceeded
            end
        end
        R->>TP: get_all_tools / get_handoffs / get_model / maybe_filter_model_input
        TP-->>R: tools, handoffs, system_instructions, effective_input
        R->>M: get_response(system, input, tools, handoffs, ...)
        Note over M: 可选经 model_retry.call_with_retry 包裹<br/>(指数退避 + 抖动 + provider advice)
        M-->>R: ModelResponse(output, usage, response_id)
        R->>OC: record_response(response)
        R->>TR: process_model_response → ProcessedResponse
        TR-->>R: RunItem[] + final_output/handoff_target/has_tool_calls

        alt 有 tool_calls
            R->>TE: execute_tools_and_side_effects(并发+timeout+guardrail)
            TE-->>R: ToolCallOutputItem[]
            R->>TUT: record_run_items → maybe_reset_tool_choice
        end

        R->>TR: build_next_step(processed) → NextStep
        alt NextStepFinalOutput
            R-->>U: RunResult(final_output)
        else NextStepHandoff(target)
            Note over R: current_agent = target<br/>continue
        else NextStepInterruption(approvals)
            R-->>U: RunResult(interruptions=[...])<br/>等待 HITL approve/reject
        else NextStepRunAgain
            Note over R: 再开一轮
        end
    end
```

---

## 图 5:`RunState` 生命周期 × HITL pause/resume

```mermaid
stateDiagram-v2
    [*] --> Running: Runner.run(...)

    Running --> Running: NextStepRunAgain
    Running --> Running: NextStepHandoff
    Running --> Paused: NextStepInterruption<br/>(ToolApprovalItem)
    Running --> Final: NextStepFinalOutput
    Running --> Errored: MaxTurnsExceeded<br/>/ ModelRefusalError

    Paused --> Paused: run_state.approve(call_id)<br/>run_state.reject(call_id, reason)
    Paused --> Resumed: resume_run_state(run_state, new_input)
    Resumed --> Running: Runner.run + combined history

    Errored --> Recovered: error_handlers.max_turns / model_refusal
    Recovered --> Final

    Final --> Snapshot: create_run_state_from_result(result)
    Snapshot --> [*]: state.to_json()  # schema_version=1.0

    Snapshot --> Restored: RunState.from_json(text)
    Restored --> Resumed

    note right of Paused
      RunState 持久化:
      - generated_items
      - model_responses
      - approved_call_ids
      - rejected_call_ids(含 reason)
      - generated_prompt_cache_key
      - conversation_history
      - current_turn / current_agent
    end note

    note left of Errored
      RunErrorHandlers 提供:
      max_turns  降级 final_output
      model_refusal  降级 final_output
    end note
```

---

## 图 6:RunItem 家族 × RunState Schema

```mermaid
classDiagram
    class RunItemBase {
        agent: Agent (weakref)
        raw_item: T
        type: Literal
        release_agent()
        to_input_item()
    }

    class MessageOutputItem {
        type = "message_output_item"
    }
    class ToolCallItem {
        type = "tool_call_item"
        tool_origin: ToolOrigin
    }
    class ToolCallOutputItem {
        type = "tool_call_output_item"
        output: Any
    }
    class ToolApprovalItem {
        call_id: str
        tool_name: str
        tool_namespace: str
        tool_lookup_key: NamedToolLookupKey
    }
    class HandoffCallItem
    class HandoffOutputItem {
        source_agent / target_agent
    }
    class ReasoningItem
    class MCPApprovalRequestItem
    class MCPApprovalResponseItem
    class MCPListToolsItem
    class ToolSearchCallItem
    class ToolSearchOutputItem
    class CompactionItem

    RunItemBase <|-- MessageOutputItem
    RunItemBase <|-- ToolCallItem
    RunItemBase <|-- ToolCallOutputItem
    RunItemBase <|-- ToolApprovalItem
    RunItemBase <|-- HandoffCallItem
    RunItemBase <|-- HandoffOutputItem
    RunItemBase <|-- ReasoningItem
    RunItemBase <|-- MCPApprovalRequestItem
    RunItemBase <|-- MCPApprovalResponseItem
    RunItemBase <|-- MCPListToolsItem
    RunItemBase <|-- ToolSearchCallItem
    RunItemBase <|-- ToolSearchOutputItem
    RunItemBase <|-- CompactionItem

    class RunState {
        +CURRENT_SCHEMA_VERSION = "1.0"
        _starting_agent
        _current_agent
        _max_turns / _current_turn
        _conversation_id / _previous_response_id
        _generated_items: list~RunItem~
        _model_responses: list~ModelResponse~
        _conversation_history
        _generated_prompt_cache_key
        _approved_call_ids: set~str~
        _rejected_call_ids: dict~str,str~
        +approve(call_id)
        +reject(call_id, reason)
        +set_prompt_cache_key(key)
        +to_dict() / to_json()
        +from_dict() / from_json()
        +get_conversation_history()
    }

    RunState "1" o-- "0..*" RunItemBase : _generated_items
```

---

## 图 7:服务端会话三视图去重(`OpenAIServerConversationTracker`)

```mermaid
graph LR
    subgraph INPUT["待发送 model_input[]"]
        I1["item#1<br/>role=user"]
        I2["item#2<br/>type=function_call_output<br/>call_id=c_42"]
        I3["item#3<br/>id=msg_abc"]
    end

    subgraph TRACKER["OpenAIServerConversationTracker 三视图"]
        V1["视图1 · 对象身份<br/>sent_items: set~int~<br/>server_items: set~int~"]
        V2["视图2 · provider stable id<br/>server_item_ids: set~str~<br/>server_tool_call_ids: set~str~"]
        V3["视图3 · 内容指纹<br/>sent_item_fingerprints: set~SHA256~"]
    end

    subgraph FILTER["filter_outgoing()"]
        F1{已在<br/>sent_items?}
        F2{id ∈<br/>server_item_ids?}
        F3{call_id + output<br/>∈ server_tool_call_ids?}
        F4{fingerprint ∈<br/>sent_item_fingerprints?}
        KEEP[保留 delta]
        DROP[丢弃重复]
    end

    INPUT --> F1
    F1 -->|是| DROP
    F1 -->|否| F2
    F2 -->|是| DROP
    F2 -->|否| F3
    F3 -->|是| DROP
    F3 -->|否| F4
    F4 -->|是| DROP
    F4 -->|否| KEEP

    V1 -.被查询.-> F1
    V2 -.被查询.-> F2
    V2 -.被查询.-> F3
    V3 -.被查询.-> F4

    KEEP -->|发送后| MARK[mark_input_as_sent<br/>更新三视图]
    MARK --> V1 & V2 & V3

    subgraph HYDRATE["resume 场景"]
        STATE["RunState 快照<br/>(原 Python 对象身份丢失)"]
        HYD["hydrate_from_state()<br/>用 provider_id + fingerprint<br/>重建视图2/3"]
    end
    STATE --> HYD --> V2
    HYD --> V3
```

**为什么三视图**:
- 只有 id 不够:Python 对象重建时 `id()` 变化 → 靠 provider_id 兜底
- provider_id 不一定有:`FakeModel` 用占位 ID → 靠 fingerprint 兜底
- fingerprint 也不绝对:`tool_search` 返回匿名项 → 三者联合才能稳定去重

---

## 图 8:Tool 执行流水线

```mermaid
graph TB
    START["turn_resolution<br/>识别到 function_call"]
    BUILD[建立 ToolCallItem]
    CHECK{needs_approval?}
    APPR_REQ[生成 ToolApprovalItem<br/>NextStepInterruption]

    subgraph EXEC["execute_function_tool_calls"]
        SEM[asyncio.Semaphore<br/>max_concurrency=10]
        LOOP[对每个 ToolCallItem]
        INPG[ToolInputGuardrail 串行]
        GATE1{guardrail behavior}
        BUILD_CTX[ToolContext.from_run_context<br/>tool_name / call_id / tool_arguments]
        INVOKE[await tool.on_invoke_tool<br/>asyncio.wait_for(timeout)]
        OUTPG[ToolOutputGuardrail 串行]
        GATE2{output guardrail behavior}
        OK_OUT[ToolCallOutputItem]
        REJ_OUT[合成 reject_content 输出]
        TO_ERR{timeout?}
        TO_HANDLE[timeout_error_function 或<br/>ToolTimeoutError]
    end

    APPROVED[HITL approve 后]
    REJECTED[HITL reject 后]
    REJ_ITEM[function_rejection_item<br/>call_id + message]

    START --> BUILD --> CHECK
    CHECK -->|是| APPR_REQ
    APPR_REQ --> APPROVED
    APPR_REQ --> REJECTED
    REJECTED --> REJ_ITEM
    APPROVED --> SEM
    CHECK -->|否| SEM

    SEM --> LOOP --> INPG --> GATE1
    GATE1 -->|allow| BUILD_CTX
    GATE1 -->|reject_content| REJ_OUT
    GATE1 -->|raise_exception| STOP[ToolInputGuardrailTripwireTriggered]
    BUILD_CTX --> INVOKE
    INVOKE --> TO_ERR
    TO_ERR -->|是| TO_HANDLE
    TO_ERR -->|否| OUTPG
    OUTPG --> GATE2
    GATE2 -->|allow| OK_OUT
    GATE2 -->|reject_content| REJ_OUT
    GATE2 -->|raise_exception| STOP2[ToolOutputGuardrailTripwireTriggered]

    OK_OUT --> DONE[回到 turn_resolution]
    REJ_OUT --> DONE
    REJ_ITEM --> DONE
    TO_HANDLE --> DONE
```

---

## 图 9:Guardrails 四位 × 三行为 × HITL Approvals 一体化

```mermaid
graph LR
    subgraph PRE["turn 前 / 模型前"]
        IG["InputGuardrail<br/>(仅首轮 + 起始 Agent)"]
    end
    subgraph MID["工具边界"]
        TIG["ToolInputGuardrail<br/>(工具执行前)"]
        TOG["ToolOutputGuardrail<br/>(工具执行后)"]
    end
    subgraph POST["final output 前"]
        OG["OutputGuardrail<br/>(agent 输出 final 时)"]
    end

    subgraph BEHAVIOR["3 行为"]
        B1[Allow<br/>继续执行]
        B2[RejectContent<br/>合成 tool output 返给模型]
        B3[RaiseException<br/>中止 run + 专属 Tripwire 异常]
    end

    subgraph HITL["HITL Approvals"]
        H1[ToolApprovalItem<br/>暂停到 RunState]
        H2[RunContextWrapper._approvals<br/>ledger 按 tool_name+call_id]
        H3["approve_tool(always_approve)<br/>reject_tool(message, always_reject)"]
        H4[get_approval_decision<br/>→ approved/pending/rejected+msg]
        H5[sticky_rejection_message<br/>/ rejection_messages per call_id]
    end

    IG --> B1 & B2 & B3
    OG --> B1 & B2 & B3
    TIG --> B1 & B2 & B3
    TOG --> B1 & B2 & B3

    TIG -.tool.needs_approval.-> H1
    H1 --> H2
    H2 --> H3
    H3 --> H4
    H4 --> H5
    H4 -.approved.-> B1
    H4 -.rejected.-> B2
```

---

## 图 10:扩展性矩阵(8 条开口)

```mermaid
graph TB
    subgraph CORE["microagent core(≈9K 行)"]
        direction TB
        PM[Model ABC]
        PS[Session Protocol]
        PT[Tool Protocol]
        PG[Guardrail Callable]
        PH[TracingProcessor Protocol]
        PSB[BaseSandboxSession / Capability]
        PMCP[MCPServer 字段占位]
        PCFG[set_default_openai_* 全局配置]
    end

    subgraph ADDONS["Addons"]
        AO[addons/openai<br/>OpenAIChatCompletionsModel + Provider]
        AS[addons/session_sqlite<br/>SQLiteSession]
        AT[addons/tracing_otel<br/>OTel BatchExporter]
    end

    subgraph FUTURE["未来 Addon 生态"]
        F1[microagent-anthropic]
        F2[microagent-mcp<br/>stdio/SSE/HTTP transport]
        F3[microagent-sandbox-docker]
        F4[microagent-sandbox-e2b]
        F5[microagent-session-redis]
        F6[microagent-realtime]
        F7[microagent-voice]
    end

    subgraph REG["注册机制"]
        R1[MultiProvider.register prefix → provider]
        R2[CapabilityRegistry.register type → class]
        R3[BaseSandboxClientOptions._subclass_registry<br/>Pydantic type 字段自动多态]
        R4[add_trace_processor]
        R5[Agent.mcp_servers = [...]]
    end

    PM --> AO
    PS --> AS
    PH --> AT
    PM -.-> F1
    PMCP -.-> F2
    PSB -.-> F3 & F4
    PS -.-> F5
    PM -.-> F6
    PM -.-> F7

    AO --> R1
    AT --> R4
    F2 --> R5
    F3 --> R2 & R3
    F4 --> R2 & R3
    F5 --> PS
```

---

## 11. 关键不变量总表(AGENTS.md 落地)

| § | 不变量 | 责任文件 | 违反后果 |
|---|---|---|---|
| 1.1 | Runner 仅编排 | `run.py` ≤ 300 行 | PR 评审 reject |
| 1.2 | Stream ↔ Non-Stream 对齐 | `run_loop.py` 共享 `run_single_turn` | stream 测试失败 |
| 1.3 | `CURRENT_SCHEMA_VERSION` + `SCHEMA_VERSION_SUMMARIES` | `run_state.py` import 期断言 | import 直接 AssertionError |
| 1.4 | 公共 API 位置参数顺序 | `RunConfig / FunctionTool / Agent / AgentHookContext` | 位置回归测试失败 |
| 1.5 | 新 Item 类型 ⇒ 8 处同步 | `items.py` + `run_internal/items.py` + `run_steps.py` + `turn_resolution.py` + `tool_execution.py` + `stream_events.py` + `run_state.py` + `session_persistence.py` | 运行时类型错配 |
| 1.6 | StreamEvent 名称冻结 | `stream_events.py` Literal | 破坏外部消费者合约 |

---

## 12. 一页式执行心法

```mermaid
graph LR
    A["1. 公共 API 极薄<br/>Runner.run + 9 kwargs"]
    B["2. 契约即架构<br/>schema 版本/位置参数/Literal 名称<br/>全部写进类型系统"]
    C["3. 开口 + 注册表<br/>Protocol / ABC / Pydantic _subclass_registry<br/>/ MultiProvider prefix"]
    D["4. 默认零成本<br/>NoOp Tracing / In-Memory Session / FakeModel"]
    E["5. 业务水平切片<br/>run_internal × 20,通过 run_loop.py 单一面板暴露"]
    F["6. Runner 只做控制流<br/>Final / Handoff / Interruption / RunAgain"]

    A --> F
    B --> A
    C --> D
    E --> F
    D --> A
```

> **"Runner 只做编排,复杂度关进 `run_internal/`;一切对外即契约,一切对内即注册表。"**
>
> 这一句话在 mini 版里由 5 个同心圆 × 20 个切片 × 8 条扩展开口 × 6 条强制不变量共同兑现 — 以 ~9K LoC 的核心体量,承载了与 openai-agents-python 同构的工业级骨架。