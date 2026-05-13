# Cove — Agent Runtime 完整设计方案

> 一个自托管的 Agent 运行时环境。基于 Anthropic Managed Agents 的 OS 抽象哲学 + Claude Agent SDK 的推理引擎能力，实现角色编排、组件解耦、Session 独立于 Context 的 Agent OS。
> 版本：v2.1 | 2026-05-13

---

## 目录

1. [产品定位：Agent OS 而非 SaaS](#1-产品定位agent-os-而非-saas)
2. [核心设计哲学](#2-核心设计哲学)
3. [核心架构](#3-核心架构)
4. [Session 持久化层](#4-session-持久化层)
5. [Harness Orchestrator](#5-harness-orchestrator)
6. [Sandbox Manager](#6-sandbox-manager)
7. [安全隔离层](#7-安全隔离层)
8. [API 设计](#8-角色编排系统)
9. [角色编排系统](#9-api-设计)
10. [部署架构](#10-部署架构)
11. [实施路线图](#11-实施路线图)
12. [技术选型与 FAQ](#12-技术选型与-faq)
13. [附录](#13-附录)

---

## 1. 产品定位：Agent OS 而非 SaaS

### 1.1 本质定义

**Cove 是一个自托管的 Agent Runtime**——不是 SaaS 平台的复刻，而是 Agent 计算范式的底层运行环境。

类比：Java 有 JVM，Docker 有 Container Runtime——Agent 需要自己的 Runtime。Cove 之于 Anthropic Managed Agents，如同 Kubernetes 之于 Borg：**哲学复刻，实现自托。**

### 1.2 解决的根本问题

传统 Agent 框架（LangChain/AutoGPT/早期 Claude Code）有三个结构缺陷：

| 缺陷 | 根因 | Cove 方案 |
|------|------|-----------|
| Agent 崩溃 = 全丢 | Session 和 Harness 耦合在同一进程 | **Session 外化**：不可变 append-only 事件日志，完全独立于推理进程 |
| 单 Agent 瓶颈 | 一个 Agent 承担全部工具/上下文/推理 | **角色编排**：任务分解 + 特化 Worker + 按角色选择分配组件 |
| 上下文不可逆 | Context Window = Message History | **Session ≠ Context**：Session 记录一切永不去弃，Context 是每轮选择性构建的瞬时视图 |

### 1.3 OS 类比

| OS 概念 | Agent Runtime 概念 | 说明 |
|---------|-------------------|------|
| 进程 | Agent 角色（特化推理实例） | 隔离、独立、可恢复、可并行 |
| 文件系统 | Session（持久化事件日志） | append-only、外部化、可查询 |
| 调度器 | Harness（推理循环 + 工具路由） | 完全无状态，cattle 模式 |
| 内存 | Context Window（选择性构建） | 每轮推理从 Session + Sandbox 动态组装 |
| 设备驱动 | Sandbox + MCP Proxy | 统一 `execute(name, input) → string` |
| 权限 | role-scoped 工具白名单 + 凭据隔离 | 不分配多余能力 |
| IPC | Session Events 查询 + 结构化 Handoff | 不靠对话摘要传递信息 |

### 1.4 与 Anthropic Managed Agents 的关键差异

| 维度 | Anthropic MA | Cove |
|------|-------------|------|
| 模型 | Claude 独占 | 可插拔（Claude + 开源模型） |
| Sandbox | 受限容器 | Docker / K8s Pod（可定制） |
| Session Store | 黑盒托管 | 自托管 PostgreSQL + 可插拔适配器 |
| 部署 | SaaS only | 可私有化部署（K8s/Docker Compose） |
| 角色定义 | 隐含在 Task 工具内部 | **显式编排层**：动态生成 + 能力原语 |
| Session vs Context | 隐含（上下文窗口约束） | **显式分离**：Session 永久存储 ≠ Context 瞬时构建 |

---

## 2. 核心设计哲学

### 2.1 Session ≠ Context：Agent OS 的根本创新

传统 Agent 框架把 Session 和 Context 混为一谈——消息历史就是上下文窗口。Cove 将它们彻底分离：

```
Session (永久存储)              Context (瞬时推理)
┌─────────────────┐            ┌──────────────────────┐
│ Event 1..10000  │            │ "你现在看到了          │
│ 全部工具调用     │  Harness   │  Event 9850-9950,     │
│ 全部思考过程     │ ═════════► │  加上 compaction     │
│ 全部用户消息     │  选择性    │  对前 9800 的总结,    │
│ 全部子Agent日志  │  构建     │  和这个系统提示"       │
└─────────────────┘            └──────────────────────┘
       ↑                              ↑
   永不丢失                      每次推理重新构建
```

**这意味着：**
- 你可以回退到任意时间点的 Session 切片，用不同的提示词或模型重新推理
- Compaction/trimmming 变为可逆：原始事件永远在 Session 中，Context 只是视图
- Agent 崩溃后恢复的不是 "上一个 Worker 的大脑状态"，而是 "上一个 Worker 所看到的事件流"

### 2.2 Worker ≠ Claude Code：角色特化的推理实例

Claude Code 是一个**全功能 Agent**——自带全套工具、权限、上下文。Worker 是 Cove 中的**被削弱的、角色特化的推理实例**：

```
Claude Code 实例                Cove Worker
┌──────────────────┐          ┌──────────────────┐
│ 全量工具           │          │ 2-3 个工具        │
│ 全权限模式         │          │ role-scoped 权限  │
│ 本地 Session       │          │ Cove Session Store│
│ 全量 Context        │          │ 选择性 Context   │
│ 项目全貌           │          │ 只看任务相关      │
└──────────────────┘          └──────────────────┘
     全功能                        削弱的特化
```

Claude Agent SDK 的价值不是 "提供 Claude Code 实例"，而是**暴露可定制的推理 API**——让 Cove 能够按角色组装不同的推理引擎、工具集、权限和上下文。

### 2.3 编排模型：动态角色生成 + 能力原语

**不预先定义角色，只定义能力原语。** 角色由 Planner Agent 在任务时动态生成：

```
能力原语（预设，极少量）
├── Read-only 探索：Read + Grep + Glob  │  只读 Sandbox
├── Read-Write 实施：Read + Edit + Bash  │  读写 Sandbox
├── Execute 验证：Bash + Read           │  隔离网络 Sandbox
├── Search 检索：WebSearch + WebFetch   │  不需要 Sandbox
└── Think 推理：无工具                  │  不需要 Sandbox

Planner 的动态职责：
  收到任务 → 分解为子任务 → 匹配能力原语 →
  为每个子任务注入角色特定的系统提示 →
  Harness 实例化为 Worker

结果：角色数量 = 任务复杂度，而非开发者预判力。
     不需要 "审阅者角色" 和 "安全审查者角色" 两个定义——
     Planner 面对代码审查时生成一个，面对安全审查时生成另一个，
     共享工具集但 system prompt 不同。
```

### 2.4 编排的分层模型

不需要一个 "最强模型" 包揽一切。编排应该分层：

```
Scheduler (Sonnet)
  │ 收任务、分派、监控进度 — 分类/匹配问题，非深度推理
  │
  ├──► Planner (Sonnet→Opus)
  │    复杂任务的结构化分解 — 间歇性调用
  │
  ├──► Worker A (Sonnet/Haiku)
  │ ├──► Worker B (Sonnet/Haiku)
  │ └──► Worker C (Sonnet/Haiku)
  │    执行层 — 占 ~75% 总调用量
  │
  └──► Reviewer (Sonnet/Opus)
       质量检查 — 间歇性调用
```

**默认配置：Scheduler + Workers 用 Sonnet，Planner + Reviewer 复杂任务上升级 Opus。** 算力分布：Opus ~20%，Sonnet ~80%。

---

## 3. 核心架构

### 2.1 三层抽象

```
┌─────────────────────────────────────────────────────────┐
│                    Cove Agent Manager                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────┐ │
│  │   Session    │  │    Harness     │  │   Sandbox   │ │
│  │   (日志层)    │  │  (推理引擎层)   │  │  (执行环境层) │ │
│  │              │  │                │  │             │ │
│  │ append-only  │  │ wake(sid)      │  │ provision() │ │
│  │ getEvents()  │  │ loop()         │  │ execute()   │ │
│  │ emitEvent()  │  │ tool_route()   │  │ destroy()   │ │
│  └──────┬───────┘  └───────┬────────┘  └──────┬──────┘ │
│         │                  │                   │         │
│         ▼                  ▼                   ▼         │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────┐ │
│  │ PostgreSQL   │  │ Control Plane  │  │ Docker/K8s  │ │
│  │ + Redis      │  │ (event loop)   │  │ Pod Pool     │ │
│  └──────────────┘  └────────────────┘  └─────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  Security Layer                   │   │
│  │   Credential Vault  │  MCP Proxy  │  Network ACL │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │                    API Gateway                     │   │
│  │   REST + WebSocket  │  Auth  │  Rate Limit        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心接口（操作系统抽象）

```python
# Session 接口 — 持久化事件日志
class SessionInterface(Protocol):
    async def emit_event(session_id: str, event: Event) -> None: ...
    async def get_session(session_id: str) -> Session: ...
    async def get_events(session_id: str, offset: int, limit: int) -> list[Event]: ...

# Harness 接口 — 推理循环
class HarnessInterface(Protocol):
    async def wake(session_id: str) -> HarnessInstance: ...
    async def loop(instance: HarnessInstance) -> AsyncIterator[Event]: ...
    async def route_tool_call(instance: HarnessInstance, tool: ToolCall) -> ToolResult: ...

# Sandbox 接口 — 执行环境
class SandboxInterface(Protocol):
    async def provision(spec: SandboxSpec) -> SandboxInstance: ...
    async def execute(instance: SandboxInstance, name: str, input: dict) -> str: ...
    async def destroy(instance: SandboxInstance) -> None: ...
```

### 2.3 数据流

```
User API ──► Session.emitEvent() ──► Harness.wake() ──► Claude/LLM
                                                              │
                                                         tool call?
                                                              │
                              ┌───────────────────────────────┤
                              ▼                               ▼
                      Sandbox.execute()              MCP Proxy.call()
                              │                               │
                              ▼                               ▼
                      Session.emitEvent()  ◄── Result ◄──────┘
                              │
                              ▼
                      Harness.loop() ──► next turn...
```

---

## 4. Session 持久化层

### 3.1 设计原则

- **不可变追加**：Event 一旦写入，永不修改
- **外部化**：Session 独立于 Harness 和 Sandbox 生存
- **可查询**：支持按 offset/limit 切片、按时间范围过滤
- **幂等**：UUID 去重，支持安全重试

### 3.2 Event 模型

```python
@dataclass
class Event:
    """Session 中的单条事件"""
    uuid: str                    # 幂等键
    session_id: str              # 所属 session
    sequence: int                # 全局递增序号
    timestamp: datetime          # 写入时间（服务端时钟）
    
    # 事件类型
    kind: Literal[
        "user_message",          # 用户提交消息
        "assistant_message",     # Assistant 回复
        "assistant_thinking",    # Thinking block
        "tool_use",              # 工具调用
        "tool_result",           # 工具结果
        "tool_error",            # 工具错误
        "system",                # 系统事件（session 创建/恢复/结束）
        "permission_request",    # 权限请求
        "permission_decision",   # 权限决策
        "compaction",            # 上下文压缩事件
        "checkpoint",            # 检查点（用于断点续传）
    ]
    
    # 载荷（按 kind 不同）
    data: dict[str, Any]
    
    # 元数据
    parent_uuid: str | None      # 因果关系链
    agent_id: str | None         # 子 Agent ID（多 Brain 场景）
    cost_tokens: int | None      # token 消耗
    cost_usd: float | None       # 费用
```

### 3.3 数据库设计

```sql
-- PostgreSQL Schema

-- 核心 Event 表（按 session_id 分区）
CREATE TABLE events (
    uuid         UUID PRIMARY KEY,           -- 幂等键
    session_id   UUID NOT NULL,              -- 分区键
    sequence     BIGSERIAL,                  -- 全局递增
    
    kind         VARCHAR(50) NOT NULL,
    data         JSONB NOT NULL,
    
    parent_uuid  UUID,
    agent_id     VARCHAR(100),
    cost_tokens  INTEGER,
    cost_usd     NUMERIC(12,6),
    
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 去重约束
    UNIQUE (uuid)
) PARTITION BY HASH (session_id);

-- 16 个分区（可扩展）
CREATE TABLE events_p0  PARTITION OF events FOR VALUES WITH (modulus 16, remainder 0);
CREATE TABLE events_p1  PARTITION OF events FOR VALUES WITH (modulus 16, remainder 1);
-- ... p2-p15 ...

-- 索引
CREATE INDEX idx_events_session_seq ON events (session_id, sequence);
CREATE INDEX idx_events_created_at    ON events (created_at);
CREATE INDEX idx_events_data_gin      ON events USING GIN (data jsonb_path_ops);

-- Session 元数据表
CREATE TABLE sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_key   VARCHAR(255) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/paused/completed/failed
    
    -- 摘要信息（增量维护）
    title         VARCHAR(500),
    summary       TEXT,
    event_count   INTEGER NOT NULL DEFAULT 0,
    token_total   INTEGER NOT NULL DEFAULT 0,
    cost_total    NUMERIC(12,6) NOT NULL DEFAULT 0,
    
    -- 时间戳
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ,
    
    -- 索引
    UNIQUE (project_key, id)
);

CREATE INDEX idx_sessions_project ON sessions (project_key);
CREATE INDEX idx_sessions_status  ON sessions (project_key, status);
CREATE INDEX idx_sessions_updated ON sessions (project_key, updated_at DESC);

-- Subagent 会话（子 Brain）
CREATE TABLE subagent_sessions (
    parent_session_id UUID NOT NULL REFERENCES sessions(id),
    agent_id          VARCHAR(100) NOT NULL,
    sub_session_id    UUID NOT NULL,
    
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (parent_session_id, agent_id, sub_session_id)
);

-- 增量 Summary 表
CREATE TABLE session_summaries (
    session_id    UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    summary       TEXT NOT NULL,
    key_points    JSONB,                    -- [{point, source_uuids}]
    token_count   INTEGER,
    
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (session_id)
);
```

### 3.4 Session Store Service

```python
# session_store/service.py

class SessionStoreService:
    """Session 持久化服务 — Cove Agent Manager 的「文件系统」"""
    
    def __init__(
        self,
        db: AsyncEngine,           # PostgreSQL
        cache: Redis,              # Redis（热数据缓存）
        event_bus: EventBus,       # NATS/Redis Streams（实时推送）
    ):
        self.db = db
        self.cache = cache
        self.event_bus = event_bus
    
    async def emit_event(self, session_id: str, event: Event) -> Event:
        """写入事件（幂等）"""
        # 1. 幂等检查（Redis 布隆过滤器 + DB 确认）
        if await self._is_duplicate(event.uuid):
            logger.info(f"Duplicate event {event.uuid} ignored")
            return event
        
        # 2. 写入 PostgreSQL
        async with self.db.begin() as conn:
            await conn.execute(insert(events_table).values(...))
            await conn.execute(
                update(sessions_table)
                .where(sessions_table.c.id == session_id)
                .values(
                    event_count=sessions_table.c.event_count + 1,
                    token_total=sessions_table.c.token_total + (event.cost_tokens or 0),
                    cost_total=sessions_table.c.cost_total + (event.cost_usd or 0),
                    updated_at=func.now(),
                )
            )
        
        # 3. 增量更新 Summary（异步，不阻塞写入）
        await self._update_summary_async(session_id, event)
        
        # 4. 推送到 Event Bus（实时流）
        await self.event_bus.publish(f"session:{session_id}", event.to_json())
        
        return event
    
    async def get_events(
        self, session_id: str, 
        offset: int = 0, limit: int = 100
    ) -> list[Event]:
        """按位置切片查询"""
        cache_key = f"events:{session_id}:{offset}:{limit}"
        
        # 热数据优先读 Redis
        cached = await self.cache.get(cache_key)
        if cached:
            return [Event.from_json(e) for e in json.loads(cached)]
        
        # 冷数据查 DB
        rows = await self.db.execute(
            select(events_table)
            .where(events_table.c.session_id == session_id)
            .order_by(events_table.c.sequence)
            .offset(offset).limit(limit)
        )
        events = [Event.from_row(r) for r in rows]
        
        # 写入缓存（TTL 5min）
        await self.cache.setex(cache_key, 300, Event.list_to_json(events))
        
        return events
    
    async def load_full_session(self, session_id: str) -> FullSession:
        """加载完整 session（resume 用）"""
        session = await self._get_session_meta(session_id)
        events = await self._load_all_events(session_id)  # 流式加载
        sub_sessions = await self._load_subagent_sessions(session_id)
        return FullSession(meta=session, events=events, sub_sessions=sub_sessions)
    
    async def list_sessions(
        self, project_key: str, 
        status: str | None = None,
        limit: int = 20, offset: int = 0
    ) -> list[SessionMeta]:
        """列出项目下的所有 session"""
        query = select(sessions_table).where(
            sessions_table.c.project_key == project_key
        ).order_by(sessions_table.c.updated_at.desc())
        
        if status:
            query = query.where(sessions_table.c.status == status)
        
        rows = await self.db.execute(query.offset(offset).limit(limit))
        return [SessionMeta.from_row(r) for r in rows]
    
    async def get_session_summary(self, session_id: str) -> SessionSummary:
        """获取实时 Summary"""
        return await self._get_cached_or_compute_summary(session_id)
```

### 3.5 Claude Agent SDK 适配器

```python
# sdk_adapter/session_store_adapter.py
from claude_agent_sdk.types import SessionStore, SessionStoreEntry, SessionKey

class CoveSessionStoreAdapter(SessionStore):
    """将 Cove Session Store Service 适配为 SDK SessionStore Protocol"""
    
    def __init__(self, api_client: CoveAPIClient, project_key: str):
        self.api = api_client
        self.project_key = project_key
    
    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None:
        """SDK 写入 → Cove API"""
        events = [
            CoveEvent.from_session_store_entry(e, key) for e in entries
        ]
        await self.api.emit_events(key["session_id"], events)
    
    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        """SDK 读取 → Cove API"""
        try:
            response = await self.api.get_events(
                session_id=key["session_id"],
                offset=0, limit=100_000,  # 完整加载
            )
            return [e.to_session_store_entry() for e in response.events]
        except NotFoundError:
            return None
    
    async def list_sessions(self, project_key: str) -> list[SessionStoreListEntry]:
        """列出 session 列表"""
        resp = await self.api.list_sessions(project_key=project_key)
        return [s.to_session_store_list_entry() for s in resp.sessions]
    
    async def delete(self, key: SessionKey) -> None:
        """删除 session"""
        await self.api.delete_session(key["session_id"])
    
    async def list_subkeys(self, key: SessionListSubkeysKey) -> list[str]:
        """列出子 agent 会话"""
        resp = await self.api.list_subagent_sessions(key["session_id"])
        return [s.agent_id for s in resp.sub_agents]
```

---

## 5. Harness Orchestrator

### 4.1 设计原则

- **完全无状态**：不持久化任何运行状态
- **Cattle 模式**：崩溃即重启，无人工干预
- **多实例**：可平行运行多个 Harness 实例
- **可插拔**：支持不同 Harness 实现（Claude Code / 自定义）

### 4.2 Harness 生命周期

```
  ┌─────────┐    wake(sid)    ┌──────────┐    crash/done   ┌─────────┐
  │  IDLE   │ ──────────────► │  ACTIVE  │ ──────────────► │  DEAD   │
  └─────────┘                 └──────────┘                 └─────────┘
                                    │                          │
                                    │ loop iteration           │ auto restart?
                                    ▼                          │
                              ┌──────────┐                     │
                              │ INFERRING│◄────────────────────┘
                              └──────────┘
                                    │
                              tool call detected
                                    │
                                    ▼
                              ┌──────────┐
                              │EXECUTING │ ──► execute() → emitEvent()
                              └──────────┘         │
                                    ▲              │
                                    └──────────────┘
```

### 4.3 Harness Engine 实现

```python
# harness/engine.py

class HarnessEngine:
    """Harness 编排引擎 — Cove Agent Manager 的「进程调度器」"""
    
    def __init__(
        self,
        llm_client: LLMClient,           # Claude API / 开源模型
        session_store: SessionStoreService,
        sandbox_manager: SandboxManager,
        mcp_registry: MCPRegistry,
        security: SecurityLayer,
        event_bus: EventBus,
    ):
        self.llm = llm_client
        self.session = session_store
        self.sandbox = sandbox_manager
        self.mcp = mcp_registry
        self.security = security
        self.event_bus = event_bus
    
    async def wake(self, session_id: str) -> HarnessInstance:
        """唤醒一个 Harness 实例
        
        1. 从 Session Store 加载完整事件日志
        2. 回放未完成的事件，确定恢复点
        3. 创建新的 Sandbox（如需要）
        4. 返回就绪的 HarnessInstance
        """
        # 加载 session
        full_session = await self.session.load_full_session(session_id)
        
        if full_session.meta.status == "completed":
            raise SessionAlreadyCompleted(session_id)
        
        # 找到最后的 checkpoint
        last_checkpoint = self._find_last_checkpoint(full_session.events)
        
        # 准备 Sandbox
        sandbox = None
        if self._session_needs_sandbox(full_session):
            sandbox_spec = self._infer_sandbox_spec(full_session)
            sandbox = await self.sandbox.provision(sandbox_spec)
        
        return HarnessInstance(
            session_id=session_id,
            session=full_session,
            last_checkpoint=last_checkpoint,
            sandbox=sandbox,
            engine=self,
        )
    
    async def loop(self, instance: HarnessInstance) -> AsyncIterator[Event]:
        """主推理循环
        
        标准流程（匹配 Anthropic Managed Agents 的 harness loop）：
        1. 从 Session 加载最近 N 个 events → Claude 的 context window
        2. 调用 Claude（含上下文组织 + compaction 逻辑）
        3. 解析响应中的 tool_use
        4. 路由到 Sandbox.execute() 或 MCP Proxy
        5. emitEvent() 写回 Session
        6. 回到 1，直到 done / max_turns / budget
        """
        turn = 0
        pending_tool_results = []
        
        while turn < instance.max_turns and instance.remaining_budget > 0:
            # 1. 构建 context window
            context = await self._build_context(instance)
            
            # 2. 调用 LLM
            async for chunk in self.llm.stream(context):
                event = self._parse_chunk(chunk, instance)
                
                if event:
                    # 3. emitEvent（实时）
                    await self.session.emit_event(instance.session_id, event)
                    yield event
                    
                    # 4. 检测 tool_call
                    if event.kind == "tool_use":
                        result = await self._execute_tool(event, instance)
                        pending_tool_results.append(result)
                        
                        # emitResult
                        result_event = Event(
                            kind="tool_result",
                            session_id=instance.session_id,
                            data=result.to_dict(),
                            parent_uuid=event.uuid,
                        )
                        await self.session.emit_event(
                            instance.session_id, result_event
                        )
                        yield result_event
            
            # 5. 检查是否需要 compaction
            if self._should_compact(context):
                await self._compact_context(instance)
            
            # 6. 检查是否完成
            if self._is_turn_complete(pending_tool_results):
                await self._complete_session(instance)
                break
            
            turn += 1
        
        # 清理 Sandbox（如不需要保留）
        if instance.sandbox:
            await self.sandbox.destroy(instance.sandbox)
    
    async def _build_context(self, instance: HarnessInstance) -> Context:
        """构建 LLM 的上下文窗口
        
        从 Session 取最近的 events，应用：
        - compaction（旧消息压缩为 summary）
        - trimming（删除旧的 tool result / thinking block）
        - 注入 system prompt + tools + MCP servers + agent skills
        """
        # 取最近事件
        recent_events = await self.session.get_events(
            instance.session_id,
            offset=max(0, instance.event_count - CONTEXT_WINDOW_EVENTS),
            limit=CONTEXT_WINDOW_EVENTS,
        )
        
        # 上下文工程
        messages = []
        system_sections = []
        
        for event in recent_events:
            if event.kind in ("compaction", "system"):
                # Compaction 事件替换被压缩的历史
                system_sections.append(event.data.get("summary", ""))
            elif event.kind == "user_message":
                messages.append({"role": "user", "content": event.data["content"]})
            elif event.kind == "assistant_message":
                messages.append({"role": "assistant", "content": event.data["content"]})
            elif event.kind == "tool_use":
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "name": event.data["name"],
                        "input": event.data["input"],
                        "id": event.uuid,
                    }]
                })
            elif event.kind in ("tool_result", "tool_error"):
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": event.parent_uuid,
                        "content": event.data.get("output", ""),
                        "is_error": event.kind == "tool_error",
                    }]
                })
        
        return Context(
            system="\n".join(system_sections) if system_sections else instance.system_prompt,
            messages=messages,
            tools=instance.tools,
            mcp_servers=instance.mcp_servers,
            max_tokens=instance.model_max_tokens,
        )
    
    async def _execute_tool(
        self, tool_event: Event, instance: HarnessInstance
    ) -> ToolResult:
        """路由工具调用到 Sandbox 或 MCP Proxy"""
        tool_name = tool_event.data["name"]
        tool_input = tool_event.data["input"]
        
        # 权限检查
        permission = await self.security.check_tool_permission(
            instance.session_id, tool_name, tool_input
        )
        if not permission.allowed:
            # 生成 PermissionRequest 事件
            request_event = Event(
                kind="permission_request",
                session_id=instance.session_id,
                data={
                    "tool_name": tool_name,
                    "input": tool_input,
                    "reason": permission.reason,
                }
            )
            await self.session.emit_event(instance.session_id, request_event)
            return ToolResult(error="Permission denied", is_error=True)
        
        # 路由决策
        if self._is_sandbox_tool(tool_name):
            # Sandbox 执行
            result = await instance.sandbox.execute(tool_name, tool_input)
        elif self._is_mcp_tool(tool_name):
            # MCP Proxy 执行（带凭据注入）
            result = await self.mcp.execute_with_credentials(
                tool_name, tool_input, instance.session_id
            )
        else:
            result = ToolResult(error=f"Unknown tool: {tool_name}", is_error=True)
        
        return result
    
    async def route_tool_call(
        self, instance: HarnessInstance, tool_call: ToolCall
    ) -> ToolResult:
        """外部工具调用路由（供手动触发使用）"""
        return await self._execute_tool_impl(instance, tool_call)
    
    def _find_last_checkpoint(self, events: list[Event]) -> Event | None:
        for event in reversed(events):
            if event.kind == "checkpoint":
                return event
        return None
    
    def _should_compact(self, context: Context) -> bool:
        """上下文超过 80% 窗口时触发 compaction"""
        return context.estimated_tokens > context.max_tokens * 0.8
    
    async def _compact_context(self, instance: HarnessInstance):
        """压缩上下文：
        1. 删除旧的 thinking blocks 和 tool results
        2. 生成 summary 替换被压缩的事件
        3. 写入 compaction event 到 Session
        """
        # 调用 LLM 生成 summary
        summary = await self.llm.compact(instance.recent_events[:COMPACT_THRESHOLD])
        
        compaction_event = Event(
            kind="compaction",
            session_id=instance.session_id,
            data={
                "summary": summary,
                "compacted_count": COMPACT_THRESHOLD,
                "compacted_uuids": [e.uuid for e in instance.recent_events[:COMPACT_THRESHOLD]],
            }
        )
        await self.session.emit_event(instance.session_id, compaction_event)
```

### 4.4 Harness Manager（编排层）

```python
# harness/manager.py

class HarnessManager:
    """管理多个 Harness 实例的编排器"""
    
    def __init__(self, engine: HarnessEngine, event_bus: EventBus):
        self.engine = engine
        self.event_bus = event_bus
        self._instances: dict[str, HarnessInstance] = {}
        self._instance_tasks: dict[str, asyncio.Task] = {}
    
    async def start_session(self, session_id: str) -> HarnessInstance:
        """启动一个新 session 的 Harness"""
        instance = await self.engine.wake(session_id)
        self._instances[session_id] = instance
        
        # 异步运行 loop（不阻塞调用者）
        task = asyncio.create_task(self._run_loop(instance))
        self._instance_tasks[session_id] = task
        
        # 注册崩溃恢复
        task.add_done_callback(
            lambda t: asyncio.create_task(self._handle_instance_crash(session_id, t))
        )
        
        return instance
    
    async def _run_loop(self, instance: HarnessInstance):
        """运行 Harness loop，实时推送事件到 Event Bus"""
        async for event in self.engine.loop(instance):
            # 通过 WebSocket 推送给客户端
            await self.event_bus.publish(
                f"session:{instance.session_id}",
                event.to_json()
            )
    
    async def _handle_instance_crash(
        self, session_id: str, task: asyncio.Task
    ):
        """Harness 崩溃自动恢复"""
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return  # 正常取消
        
        logger.error(f"Harness {session_id} crashed: {exc}")
        
        # 重试策略
        retry_count = self._retry_counts.get(session_id, 0)
        if retry_count < MAX_RETRIES:
            self._retry_counts[session_id] = retry_count + 1
            backoff = min(2 ** retry_count, 60)  # 指数退避，上限 60s
            
            await asyncio.sleep(backoff)
            
            # 恢复：从 Session 重放
            logger.info(f"Restarting harness {session_id} (attempt {retry_count + 1})")
            await self.start_session(session_id)
        else:
            # 标记 session 失败
            await self.engine.session.emit_event(session_id, Event(
                kind="system",
                session_id=session_id,
                data={"type": "harness_failed", "error": str(exc)},
            ))
    
    async def stop_session(self, session_id: str):
        """优雅关闭 Harness"""
        if session_id in self._instance_tasks:
            self._instance_tasks[session_id].cancel()
            del self._instance_tasks[session_id]
        if session_id in self._instances:
            del self._instances[session_id]
    
    async def get_active_sessions(self) -> list[str]:
        """获取活跃 session 列表"""
        return list(self._instances.keys())
    
    async def health_check(self) -> dict:
        """健康检查"""
        return {
            "active_sessions": len(self._instances),
            "active_tasks": len(self._instance_tasks),
            "sessions": {
                sid: {
                    "status": "running",
                    "turn": inst.current_turn,
                    "tokens": inst.total_tokens,
                }
                for sid, inst in self._instances.items()
            }
        }
```

---

## 6. Sandbox Manager

### 5.1 设计原则

- **Cattle 模式**：Sandbox 是牛群，不是宠物
- **统一接口**：`execute(name, input) → string`
- **按需创建**：只在工具调用时 provision
- **安全隔离**：凭据永不进入 Sandbox
- **可插拔**：支持 Docker / K8s Pod / 远程 VM

### 5.2 Sandbox Pool 实现

```python
# sandbox/manager.py

@dataclass
class SandboxSpec:
    """Sandbox 规格定义"""
    image: str = "cove/sandbox:latest"    # Docker image
    cpu: str = "1"                         # CPU 配额
    memory: str = "512Mi"                   # 内存配额
    disk: str = "10Gi"                      # 磁盘配额
    timeout: int = 3600                     # 最长存活时间（秒）
    env: dict[str, str] = field(default_factory=dict)
    network: Literal["isolated", "restricted", "full"] = "restricted"
    mounts: list[VolumeMount] = field(default_factory=list)
    repo_clone_url: str | None = None       # Git clone URL（含 token）
    repo_branch: str = "main"

@dataclass
class SandboxInstance:
    id: str
    spec: SandboxSpec
    container_id: str
    status: Literal["provisioning", "ready", "executing", "dead"]
    created_at: datetime
    last_used_at: datetime
    tool_results: dict[str, Any] = field(default_factory=dict)  # execute() 结果缓存

class SandboxManager:
    """Sandbox 生命周期管理器"""
    
    def __init__(
        self,
        docker_client: aiodocker.Docker,
        pool_config: PoolConfig,
    ):
        self.docker = docker_client
        self.config = pool_config
        self._active: dict[str, SandboxInstance] = {}        # session_id → instance
        self._pool: dict[str, list[SandboxInstance]] = {}    # warm pool（按 spec hash）
        self._idle_cleanup_task: asyncio.Task | None = None
    
    async def provision(self, session_id: str, spec: SandboxSpec) -> SandboxInstance:
        """创建 Sandbox — 对应 Managed Agents 的 provision({resources})"""
        
        # 1. 尝试从 warm pool 获取
        spec_hash = self._hash_spec(spec)
        instance = await self._try_pool_get(spec_hash)
        
        if instance is None:
            # 2. 冷启动：创建容器
            instance = await self._create_container(session_id, spec)
        
        # 3. 记录
        self._active[session_id] = instance
        
        # 4. 启动空闲清理任务
        if self._idle_cleanup_task is None:
            self._idle_cleanup_task = asyncio.create_task(self._idle_cleanup_loop())
        
        return instance
    
    async def _create_container(
        self, session_id: str, spec: SandboxSpec
    ) -> SandboxInstance:
        """Docker 容器冷启动"""
        
        # 安全：处理 Git auth（注入 remote URL 而非环境变量）
        env = dict(spec.env)
        init_commands = []
        
        if spec.repo_clone_url:
            # Token 已经 baked into clone URL，不在环境变量中暴露
            init_commands.append(f"git clone --branch {spec.repo_branch} {spec.repo_clone_url} /workspace")
            init_commands.append("cd /workspace")
        
        # 创建容器
        container_config = {
            "Image": spec.image,
            "Cmd": ["/bin/sleep", "infinity"],  # 保持容器运行
            "Env": [f"{k}={v}" for k, v in env.items()],
            "HostConfig": {
                "Memory": self._parse_memory(spec.memory),
                "NanoCpus": self._parse_cpu(spec.cpu),
                "NetworkMode": {
                    "isolated": "none",
                    "restricted": "bridge",
                    "full": "host",
                }.get(spec.network, "bridge"),
                "AutoRemove": True,
                "Mounts": [
                    {"Type": "bind", "Source": m.source, "Target": m.target}
                    for m in spec.mounts
                ],
            },
        }
        
        container = await self.docker.containers.create_or_replace(
            name=f"cove-sandbox-{session_id[:8]}",
            config=container_config,
        )
        await container.start()
        
        # 执行初始化命令（git clone 等）
        for cmd in init_commands:
            exec_result = await container.exec_run(["sh", "-c", cmd])
            if exec_result.exit_code != 0:
                await container.delete(force=True)
                raise SandboxProvisionError(f"Init command failed: {cmd}")
        
        instance = SandboxInstance(
            id=f"sbx-{session_id[:12]}",
            spec=spec,
            container_id=container.id,
            status="ready",
            created_at=datetime.utcnow(),
            last_used_at=datetime.utcnow(),
        )
        
        logger.info(f"Sandbox {instance.id} provisioned (cold start)")
        return instance
    
    async def execute(
        self, instance: SandboxInstance, tool_name: str, tool_input: dict
    ) -> str:
        """在 Sandbox 中执行工具调用 — Managed Agents 的 execute(name, input) → string"""
        
        instance.status = "executing"
        instance.last_used_at = datetime.utcnow()
        
        # 根据工具类型分发
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            
            # 超时保护
            timeout = min(tool_input.get("timeout", 30000), 120000)  # max 2min
            
            container = await self.docker.containers.get(instance.container_id)
            exec_result = await container.exec_run(
                ["sh", "-c", command],
                demux=True,
            )
            
            output = exec_result.output[0] or b""
            stderr = exec_result.output[1] or b""
            
            # 合成最终输出
            result_parts = []
            if output:
                result_parts.append(output.decode("utf-8", errors="replace"))
            if stderr:
                result_parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")
            if exec_result.exit_code != 0:
                result_parts.append(f"\n[Exit code: {exec_result.exit_code}]")
            
            result = "\n".join(result_parts) or "(no output)"
            
        elif tool_name == "Read":
            filepath = tool_input["file_path"]
            command = f"cat {shlex.quote(str(filepath))}"
            container = await self.docker.containers.get(instance.container_id)
            exec_result = await container.exec_run(["sh", "-c", command])
            result = exec_result.output.decode("utf-8", errors="replace")
            
        elif tool_name == "Edit":
            filepath = tool_input["file_path"]
            old_str = tool_input["old_string"]
            new_str = tool_input["new_string"]
            # 使用 Python 在容器内执行 replace
            script = f'''python3 -c "
import sys
path = {shlex.quote(str(filepath))}
old = sys.argv[1]
new = sys.argv[2]
with open(path, 'r') as f:
    content = f.read()
if old not in content:
    print('ERROR: old_string not found in file', file=sys.stderr)
    sys.exit(1)
content = content.replace(old, new, 1)
with open(path, 'w') as f:
    f.write(content)
print('File edited successfully.')
" {shlex.quote(old_str)} {shlex.quote(new_str)}'''
            container = await self.docker.containers.get(instance.container_id)
            exec_result = await container.exec_run(["sh", "-c", script])
            result = exec_result.output.decode("utf-8", errors="replace")
        else:
            # 通用工具执行（MCP tools 不通过 Sandbox）
            result = f"Unsupported tool in sandbox: {tool_name}"
        
        instance.status = "ready"
        instance.tool_results[tool_name] = result
        
        return result
    
    async def destroy(self, instance: SandboxInstance):
        """销毁 Sandbox 实例"""
        try:
            container = await self.docker.containers.get(instance.container_id)
            await container.delete(force=True)
            logger.info(f"Sandbox {instance.id} destroyed")
        except DockerError as e:
            if e.status == 404:
                pass  # 已经不存在了
            else:
                logger.warning(f"Failed to destroy sandbox {instance.id}: {e}")
        
        instance.status = "dead"
        self._active.pop(instance.spec.session_id, None)
    
    async def _try_pool_get(self, spec_hash: str) -> SandboxInstance | None:
        """从 warm pool 获取预热实例"""
        pool = self._pool.get(spec_hash, [])
        if pool:
            return pool.pop()
        return None
    
    async def _idle_cleanup_loop(self, interval: int = 60):
        """定期清理空闲 Sandbox"""
        while True:
            await asyncio.sleep(interval)
            now = datetime.utcnow()
            
            # 清理超时实例
            for sid, instance in list(self._active.items()):
                idle_seconds = (now - instance.last_used_at).total_seconds()
                if idle_seconds > instance.spec.timeout:
                    logger.info(f"Sandbox {instance.id} idle timeout ({idle_seconds}s)")
                    await self.destroy(instance)
            
            # 清理 warm pool 中过期的实例
            for spec_hash, pool in list(self._pool.items()):
                self._pool[spec_hash] = [
                    inst for inst in pool
                    if (now - inst.created_at).total_seconds() < self.config.pool_max_age
                ]

### 5.3 Kubernetes Sandbox Provider（扩展）

```yaml
# sandbox/k8s/template.yaml
apiVersion: v1
kind: Pod
metadata:
  name: cove-sandbox-{{ session_id }}
  labels:
    app: cove-sandbox
    session: "{{ session_id }}"
  annotations:
    cove/tool-timeout: "{{ timeout }}"
spec:
  restartPolicy: Never
  terminationGracePeriodSeconds: 10
  containers:
  - name: workspace
    image: "{{ image }}"
    command: ["/bin/sleep", "infinity"]
    resources:
      requests:
        cpu: "{{ cpu }}"
        memory: "{{ memory }}"
      limits:
        cpu: "{{ cpu_limit }}"
        memory: "{{ memory_limit }}"
    env:
{% for key, value in env.items() %}
    - name: "{{ key }}"
      value: "{{ value }}"
{% endfor %}
    volumeMounts:
{% for mount in mounts %}
    - name: "{{ mount.name }}"
      mountPath: "{{ mount.path }}"
{% endfor %}
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop: ["ALL"]
  volumes:
{% for mount in mounts %}
  - name: "{{ mount.name }}"
    emptyDir: {}
{% endfor %}
  networkPolicy:
    podSelector:
      matchLabels:
        app: cove-sandbox
    policyTypes: ["Egress"]
    egress:
    - to:
      - namespaceSelector: {}
        podSelector:
          matchLabels:
            app: cove-harness
      ports:
      - port: 8080
```

---

## 7. 安全隔离层

### 6.1 凭据隔离策略

```
┌──────────────────────────────────────────────────────┐
│                   Vault (HashiCorp / K8s Secret)      │
│                                                        │
│  Git Token ──► Clone URL 注入 ──► git remote (Sandbox) │
│  OAuth Token ──► MCP Proxy 注入 ──► External API      │
│  API Key ──► Env Injection ──► Harness Config         │
│                                                        │
│  ⚠️ NEVER in Sandbox: 明文凭据                         │
│  ⚠️ NEVER in Session events: 凭据信息                   │
└──────────────────────────────────────────────────────┘
```

### 6.2 凭据管理器

```python
# security/vault.py

@dataclass
class Credential:
    id: str
    kind: Literal["git_token", "oauth_token", "api_key", "ssh_key"]
    value: str  # 加密存储
    scope: list[str]  # 允许访问的 resource
    session_binding: str | None  # 绑定到特定 session
    expires_at: datetime | None
    created_at: datetime

class CredentialVault:
    """凭据保管库
    
    结构化确保凭据永不进入 Sandbox：
    - Git token：在 Sandbox provision 时注入 clone URL
    - OAuth token：通过 MCP Proxy 注入 API 调用
    - API key：通过 Harness env 注入（不进 Sandbox）
    """
    
    def __init__(self, secret_store: SecretStore):
        self.store = secret_store  # HashiCorp Vault / K8s Secrets / AWS Secrets Manager
    
    async def get_git_token(self, repo_url: str, session_id: str) -> str:
        """获取 Git token 并注入到 clone URL（永不过 Sandbox 环境变量）"""
        cred = await self.store.get(f"git:{repo_url}")
        if not cred:
            raise CredentialNotFound(f"No git token for {repo_url}")
        
        # 注入到 URL：https://x-access-token:<token>@github.com/user/repo.git
        if "github.com" in repo_url:
            return repo_url.replace(
                "https://github.com",
                f"https://x-access-token:{cred.value}@github.com"
            )
        return repo_url.replace("https://", f"https://oauth2:{cred.value}@")
    
    async def inject_oauth(self, provider: str, session_id: str):
        """通过 MCP Proxy 注入 OAuth token"""
        cred = await self.store.get(f"oauth:{provider}:{session_id}")
        if not cred:
            raise CredentialNotFound(f"No OAuth token for {provider}")
        return cred.value
    
    async def store(self, cred: Credential) -> str:
        """安全存储凭据"""
        key = f"{cred.kind}:{cred.id}"
        await self.store.put(key, cred)
        return key
    
    async def rotate(self, cred_id: str, new_value: str):
        """轮换凭据"""
        cred = await self.store.get(cred_id)
        cred.value = new_value
        cred.created_at = datetime.utcnow()
        await self.store.put(cred_id, cred)
```

### 6.3 MCP Proxy

```python
# security/mcp_proxy.py

class MCPProxy:
    """MCP 代理 — 在凭据和 Sandbox 之间的安全边界
    
    Sandbox 中的代码调用 MCP tool → 请求转发到 Proxy
    → Proxy 从 Vault 取凭证 → 注入并调用外部服务
    → 结果返回 Sandbox。
    
    Sandbox 永远不会看到凭据。
    """
    
    def __init__(self, vault: CredentialVault, mcp_registry: MCPRegistry):
        self.vault = vault
        self.registry = mcp_registry
    
    async def execute_with_credentials(
        self, tool_name: str, tool_input: dict, session_id: str
    ) -> ToolResult:
        """代理执行 MCP 工具调用，注入凭据"""
        
        # 解析工具对应的 provider 和所需凭据
        tool_def = await self.registry.get_tool(tool_name)
        if not tool_def:
            return ToolResult(error=f"Unknown MCP tool: {tool_name}", is_error=True)
        
        # 从 Vault 获取凭据
        credentials = {}
        for required_cred in tool_def.required_credentials:
            cred_value = await self.vault.get_for_session(
                required_cred, session_id
            )
            credentials[required_cred] = cred_value
        
        # 注入凭据到 tool_input
        enriched_input = {
            **tool_input,
            "_credentials": credentials,  # 仅 Proxy 可见
        }
        
        # 调用实际的 MCP server（凭据由 Proxy 持有）
        try:
            result = await self.registry.call_tool(tool_name, enriched_input)
            
            # 从结果中剥离凭据（防止意外泄露）
            result = self._sanitize_output(result)
            
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(error=str(e), is_error=True)
    
    def _sanitize_output(self, raw: dict) -> dict:
        """从输出中移除凭据相关信息"""
        sensitive_keys = {"token", "key", "secret", "password", "auth", "credential"}
        if isinstance(raw, dict):
            return {k: self._sanitize_output(v) for k, v in raw.items()
                    if k.lower() not in sensitive_keys}
        elif isinstance(raw, list):
            return [self._sanitize_output(item) for item in raw]
        return raw
```

### 6.4 权限系统

```python
# security/permissions.py

class PermissionSystem:
    """Agent 权限系统 — 对应 Claude Code 的六种权限模式"""
    
    PermissionMode = Literal[
        "default",          # 标准模式，危险操作需审批
        "acceptEdits",      # 自动接受文件编辑
        "plan",             # 仅规划，不执行
        "bypassPermissions", # 绕过所有权限
        "dontAsk",          # 未预批准则拒绝
        "auto",             # 模型分类器自动决定
    ]
    
    def __init__(self, vault: CredentialVault):
        self.mode: dict[str, PermissionMode] = {}  # session_id → mode
        self.allow_rules: dict[str, list[ToolPermissionRule]] = {}
        self.classifier: AutoModeClassifier | None = None  # auto 模式的模型分类器
    
    async def check_tool_permission(
        self, session_id: str, tool_name: str, tool_input: dict
    ) -> PermissionDecision:
        """检查工具调用权限"""
        mode = self.mode.get(session_id, "default")
        
        if mode == "bypassPermissions":
            return PermissionDecision(allowed=True)
        
        if mode == "plan":
            return PermissionDecision(allowed=False, reason="Plan mode: no execution")
        
        if mode == "dontAsk":
            # 仅允许 allow_rules 中预先批准的工具
            if not self._is_allowed(session_id, tool_name, tool_input):
                return PermissionDecision(allowed=False, reason="Not in allow list")
        
        # Auto mode：模型分类器判断
        if mode == "auto" and self.classifier:
            risk = await self.classifier.assess(tool_name, tool_input)
            if risk.level == "critical":
                return PermissionDecision(
                    allowed=False,
                    reason=f"Auto mode blocked: {risk.explanation}",
                    require_user_approval=True,
                )
            return PermissionDecision(allowed=True, auto_mode_decision=True)
        
        # Default / acceptEdits：检查工具类型
        if self._is_dangerous(tool_name, tool_input):
            return PermissionDecision(
                allowed=False,
                reason=f"Dangerous tool '{tool_name}' requires user approval",
                require_user_approval=True,
            )
        
        return PermissionDecision(allowed=True)
    
    def _is_dangerous(self, tool_name: str, tool_input: dict) -> bool:
        """判断工具是否危险"""
        dangerous_patterns = {
            "Bash": ["rm -rf", "sudo", "chmod 777", "> /dev/", "mkfs"],
            "WebFetch": ["file://", "127.0.0.1", "localhost"],
        }
        if tool_name in dangerous_patterns:
            command = str(tool_input).lower()
            return any(pattern.lower() in command for pattern in dangerous_patterns[tool_name])
        return False
```

---

## 8. API 设计

### 7.1 REST API

```
Base URL: https://api.cove.sh/v1
Auth: Bearer <project-token>
```

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/sessions` | 创建新 session |
| `GET` | `/sessions` | 列出 project 下的 sessions |
| `GET` | `/sessions/{id}` | 获取 session 详情 + 实时 summary |
| `POST` | `/sessions/{id}/messages` | 发送用户消息（启动或继续） |
| `POST` | `/sessions/{id}/interrupt` | 中断当前执行 |
| `POST` | `/sessions/{id}/permissions` | 响应权限请求 |
| `DELETE` | `/sessions/{id}` | 删除 session |
| `POST` | `/sessions/{id}/fork` | Fork session |
| `GET` | `/sessions/{id}/events` | 获取 session 事件流 |
| `GET` | `/sessions/{id}/events?offset=N&limit=M` | 切片查询事件 |
| `POST` | `/sessions/{id}/resume` | 恢复暂停的 session |
| `GET` | `/projects/{key}/status` | 项目状态 |

### 7.2 关键 API 详设

#### `POST /sessions` — 创建 Session

```json
{
  "project_key": "my-agent-project",
  "config": {
    "system_prompt": "You are a helpful coding assistant...",
    "model": "claude-sonnet-4-5",
    "max_turns": 50,
    "max_budget_usd": 10.0,
    "permission_mode": "auto",
    "tools": ["Bash", "Read", "Edit", "WebSearch"],
    "mcp_servers": {
      "github": { "type": "http", "url": "..." },
      "database": { "type": "stdio", "command": "..." }
    },
    "sandbox": {
      "image": "cove/sandbox:python-3.12",
      "repo_clone_url": "github.com/user/repo",
      "network": "restricted"
    },
    "agents": {
      "code-reviewer": {
        "description": "Reviews code for bugs and style",
        "prompt": "You are a senior code reviewer...",
        "tools": ["Read", "Grep"],
        "model": "claude-opus-4-1"
      }
    }
  }
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "created_at": "2026-05-12T14:00:00Z",
  "ws_url": "wss://api.cove.sh/v1/sessions/550e8400.../stream"
}
```

#### `POST /sessions/{id}/messages` — 发送消息

```json
{
  "content": "Refactor the authentication module to use JWT",
  "attachments": [
    { "type": "file", "path": "auth.py", "content": "..." }
  ]
}
```

**Response:** `202 Accepted` + WebSocket 实时推送

### 7.3 WebSocket API（实时事件流）

```
wss://api.cove.sh/v1/sessions/{id}/stream
```

**Client → Server:**
```json
{ "type": "user_message", "content": "...", "id": "msg-uuid" }
{ "type": "interrupt" }
{ "type": "permission_response", "request_id": "...", "decision": "allow" }
{ "type": "set_permission_mode", "mode": "acceptEdits" }
```

**Server → Client:**
```json
{ "type": "event", "event": { "kind": "assistant_message", "data": {...} } }
{ "type": "permission_request", "tool": "Bash", "command": "...", "request_id": "..." }
{ "type": "session_status", "status": "completed", "stats": {...} }
{ "type": "error", "code": "MAX_TURNS", "message": "..." }
```

---

## 9. 角色编排系统

### 9.1 核心原则：不预设角色，只定义能力原语

传统多 Agent 框架（CrewAI 等）要求开发者**预先定义角色**——审阅 Agent、安全 Agent、测试 Agent……两周后需要第 9 个角色，三周后需要第 15 个。角色数量随使用线性增长。

Cove 反其道而行：**角色由 Planner Agent 在任务时动态生成。** 预设的只有极少的能力原语（工具组合模式）。

```python
# orchestration/capability_primitives.py

class CapabilityPrimitive(Enum):
    """能力原语 —— Cove 预设的 5 种工具组合模式"""

    READ_ONLY = "read-only"       # Read + Grep + Glob
    READ_WRITE = "read-write"     # Read + Edit + Bash
    EXECUTE = "execute"           # Bash + Read （隔离网络）
    SEARCH = "search"             # WebSearch + WebFetch
    THINK = "think"               # 无工具（纯粹推理）

PRIMITIVE_CONFIG: dict[CapabilityPrimitive, WorkerConfig] = {
    CapabilityPrimitive.READ_ONLY: WorkerConfig(
        tools=["Read", "Grep", "Glob"],
        sandbox=SandboxSpec(network="isolated", read_only_rootfs=True),
        permission_mode="bypassPermissions",
        typical_model="claude-sonnet-4-5",
    ),
    CapabilityPrimitive.READ_WRITE: WorkerConfig(
        tools=["Read", "Edit", "Bash"],
        sandbox=SandboxSpec(network="restricted"),
        permission_mode="acceptEdits",
        typical_model="claude-sonnet-4-5",
    ),
    CapabilityPrimitive.EXECUTE: WorkerConfig(
        tools=["Bash", "Read"],
        sandbox=SandboxSpec(network="isolated", timeout=600),
        permission_mode="bypassPermissions",
        typical_model="claude-haiku-4-5",
    ),
    CapabilityPrimitive.SEARCH: WorkerConfig(
        tools=["WebSearch", "WebFetch"],
        sandbox=None,  # 不需要 Sandbox
        permission_mode="bypassPermissions",
        typical_model="claude-haiku-4-5",
    ),
    CapabilityPrimitive.THINK: WorkerConfig(
        tools=[],
        sandbox=None,  # 不需要 Sandbox
        permission_mode="default",
        typical_model="claude-opus-4-1",
    ),
}
```

### 9.2 动态角色生成流程

```
Planner Agent 收到任务
        │
        ▼
  1. LLM 分解任务
     输入: "重构 auth 模块，添加 JWT 支持，写测试"
     输出: [
       {index: 0, desc: "探索 auth.py 当前结构", capability: "read-only"},
       {index: 1, desc: "实现 JWT token 逻辑", capability: "read-write"},
       {index: 2, desc: "编写单元测试", capability: "execute"},
       {index: 3, desc: "审查变更安全性", capability: "think"},
     ]
        │
        ▼
  2. 匹配能力原语 → 生成角色
     子任务 0 → READ_ONLY Worker (role_name: "explorer-abc123")
        tools: [Read, Grep, Glob]
        sandbox: 只读 rootfs
        prompt: "探索 auth.py 当前结构，输出接口签名和数据流"

     子任务 1 → READ_WRITE Worker (role_name: "implementer-def456")
        tools: [Read, Edit, Bash]
        sandbox: 读写
        prompt: "实现 JWT token 的签发和验证"

     子任务 2 → EXECUTE Worker (role_name: "tester-ghi789")
        tools: [Bash, Read]
        sandbox: 隔离网络
        prompt: "为 JWT auth 模块编写并运行单元测试"

     子任务 3 → THINK Worker (role_name: "reviewer-jkl012")
        tools: []  (无工具，纯推理)
        sandbox: 无
        prompt: "审查 JWT 实现的潜在安全问题"
        dependencies: [0, 1, 2]  ← 等实施者和测试者完成
        │
        ▼
  3. 分派（尊重依赖关系）
     ├── Worker 0, 1, 2 → 并行启动（无依赖）
     └── Worker 3 → 等 0/1/2 完成后启动
```

### 9.3 编排器核心实现

```python
# orchestration/planner.py

@dataclass
class RoleSpec:
    """动态生成的角色规格 —— 不是预定义的 Agent 类"""
    role_name: str                    # 运行时生成: "explorer-20260513-a3f2"
    capability: CapabilityPrimitive   # 匹配的能力原语
    system_prompt: str                # 任务特定的 —— 同一原语不同 prompt = 不同角色
    context_hints: list[str]          # Session 查询提示（只看什么事件）
    dependencies: list[int]           # 依赖的子任务索引
    model: str
    sandbox: SandboxSpec | None

class PlannerAgent:
    """规划 + 编排 Agent —— Cove 的调度器"""

    def __init__(self, llm, harness, session_store):
        self.llm = llm
        self.harness = harness
        self.session = session_store

    async def execute(self, task: str, parent_session: str) -> list[WorkerResult]:
        """入口：收任务 → 分解 → 分发 → 收结果"""

        # 1. 分解
        subtasks = await self._decompose(task, parent_session)

        # 2. 为每个子任务生成角色
        roles = [
            RoleSpec(
                role_name=f"{self._match_primitive(s).value}-{short_uuid()}",
                capability=self._match_primitive(s),
                system_prompt=self._build_prompt(s),
                context_hints=s.context_hints,
                dependencies=s.dependencies,
                model=PRIMITIVE_CONFIG[self._match_primitive(s)].typical_model,
                sandbox=PRIMITIVE_CONFIG[self._match_primitive(s)].sandbox,
            )
            for s in subtasks
        ]

        # 3. 拓扑分派（并行无依赖，串行有依赖）
        return await self._dispatch_topological(roles, subtasks, parent_session)

    async def _decompose(self, task: str, sid: str) -> list[SubtaskDef]:
        """LLM 分解任务"""
        recent = await self.session.get_events(sid, offset=0, limit=30)
        response = await self.llm.complete(
            f"Decompose task into subtasks (JSON). Task: {task}"
        )
        return parse_subtasks(response)

    def _match_primitive(self, sub: SubtaskDef) -> CapabilityPrimitive:
        """匹配能力原语"""
        return {
            "read-only": CapabilityPrimitive.READ_ONLY,
            "read-write": CapabilityPrimitive.READ_WRITE,
            "execute": CapabilityPrimitive.EXECUTE,
            "search": CapabilityPrimitive.SEARCH,
            "think": CapabilityPrimitive.THINK,
        }[sub.capability_needed]

    def _build_prompt(self, sub: SubtaskDef) -> str:
        """为动态角色生成系统提示 —— 只告诉它需要的"""
        tools = PRIMITIVE_CONFIG[self._match_primitive(sub)].tools
        return (
            f"You are a specialized worker.\n\n"
            f"Task: {sub.description}\n"
            f"Available tools: {', '.join(tools)}\n"
            f"Do only what your tools allow. Return a structured result."
        )

    async def _dispatch_topological(
        self, roles, subtasks, parent_id
    ) -> list[WorkerResult]:
        """拓扑排序分派 —— 依赖满足的并行启动"""
        completed: dict[int, WorkerResult] = {}
        running: dict[int, asyncio.Task] = {}

        while len(completed) < len(roles):
            # 找所有依赖已满足的角色
            ready = [
                i for i in range(len(roles))
                if i not in completed and i not in running
                and all(d in completed for d in roles[i].dependencies)
            ]
            if not ready and not running:
                raise OrchestrationError("Deadlock detected")

            # 并行启动所有就绪的 Worker
            for i in ready:
                # 注入依赖结果到 Context
                dep_outputs = "\n".join(
                    f"Result from {roles[d].role_name}: {completed[d].output}"
                    for d in roles[i].dependencies
                )
                running[i] = asyncio.create_task(
                    self._run_worker(roles[i], dep_outputs)
                )

            # 等待任意一个完成
            done, _ = await asyncio.wait(running.values(),
                return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                result = task.result()
                idx = next(i for i, t in running.items() if t is task)
                completed[idx] = result
                del running[idx]

        return [completed[i] for i in range(len(roles))]

    async def _run_worker(self, role: RoleSpec, context: str) -> WorkerResult:
        """运行单个 Worker —— Harness 实例化"""
        worker_sid = str(uuid.uuid4())
        async for event in self.harness.execute_worker(
            session_id=worker_sid,
            system_prompt=role.system_prompt,
            task=context,
            tools=PRIMITIVE_CONFIG[role.capability].tools,
            sandbox=role.sandbox,
        ):
            if event.kind == "assistant_message" and event.data.get("is_final"):
                return WorkerResult(
                    role_name=role.role_name,
                    session_id=worker_sid,
                    output=event.data["content"],
                )
        return WorkerResult(role_name=role.role_name, session_id=worker_sid, output="")
```

### 9.4 为什么动态角色优于预设角色

```
预设角色方案：
  需要事先定义 "code-reviewer" 和 "security-reviewer" 两个 Agent 类型
  下个月需要 "performance-reviewer" → 再加一个
  六个月后你有 20 个角色定义，一半已经不用了

Cove 动态角色：
  Planner 收到 "审查代码质量"
    → 生成 system_prompt: "审查代码风格、可读性、错误处理。关注命名、注释。"
    → tools: [Read, Grep]

  Planner 收到 "审查安全漏洞"
    → 生成 system_prompt: "审查 SQL 注入、XSS、敏感数据泄露。关注验证逻辑。"
    → tools: [Read, Grep, Bash]  ← 同一原语但加了 Bash 用于跑 SAST

  同一个能力原语 READ_ONLY，不同的 system prompt → 两种完全不同的角色。
  开发者不预判角色 —— Planner 在现场生成。
```

### 9.5 跨 Agent 知识传递：不靠摘要，靠查询

```
错误做法                          正确做法
Agent A                          Session（共享不可变日志）
  │                              ├── Event 1: Agent A Read auth.py
  │ 读代码、推理                     ├── Event 2: Agent A 输出接口签名
  │                              ├── Event 3: Agent A Write interface.py
  │                              ├── Event 4: Agent A 的工具调用结果
  ▼                              └── Event 5: Agent A 完成
Agent B 收到 "Agent A 说接口是 X"     │
  │ (已经经过压缩摘要)                  Agent B 需要时:
  │                              ├── getEvents(hint="auth") → 找到 Agent A 读了什么
  │                              ├── Sandbox Read "interface.py" → 读到完整接口
  ▼                              └── 不需要看到 Agent A 的 500 行思考过程
信息丢失，偏差累积                       │
                                    └── 信息完整保留，精确按需获取
```

**关键：** 结构化 Handoff（`interface.py`）取代对话摘要。Session Events 是知识索引。
Worker 不需要知道上一个 Worker"想了什么"，只需要知道它"产出了什么"。

### 9.6 模型分层策略

```
编排层模型分配（算力分布）
├── Scheduler (Sonnet)     — 收任务、分派、监控进度 (~5%)
│   推理负担：分类/匹配问题，非深度推理
│
├── Planner (Sonnet/Opus)  — 复杂任务的结构化分解 (~10%)
│   间歇性调用，非每一轮
│
├── Workers (Sonnet/Haiku) — 占 ~75% 总调用量
│   ├── READ_ONLY / READ_WRITE → Sonnet
│   ├── EXECUTE / SEARCH → Haiku
│   └── THINK → Opus (需要深度推理时)
│
└── Reviewer (Sonnet/Opus) — 质量检查 (~10%)
   间歇性调用

默认配置：Scheduler + Workers 用 Sonnet，Planner + Reviewer 在复杂任务升级 Opus。
不需要一个"最强模型"包揽一切 — 分层调度节省 ~80% 成本但几乎不损失质量。
```

### 9.7 多 Agent 场景的知识命中率分析

**结论：分散工作提高命中率，因为噪音被提前过滤。**

| | 单一 Agent | Cove 多 Agent |
|---|---|---|
| **上下文大小** | 全量（项目全局 + 对话历史） | 每 Worker 只看任务相关 |
| **噪音** | 高（无关文件、无关历史） | 低（精确过滤） |
| **信息保真** | 高（看到原文） | 高（Session 查询 + Sandbox Read） |
| **跨子任务干扰** | 存在（一个 Agent 同时想多个问题） | 无（Worker 隔离） |

三个保障命中率的机制：
1. **Session Events 作为知识索引** — 后启动的 Worker 精确查询相关事件，不加载全量历史
2. **外部化上下文对象** — 代码、测试输出、接口定义存在 Sandbox 文件系统中，不经 Agent 压缩传递
3. **角色定制 Compaction** — 实施者保留代码变更 + 测试结果，丢弃审阅意见（防止推理污染）

## 10. 部署架构

### 9.1 生产部署拓扑

```
                                ┌──────────────┐
                                │   CDN/Proxy  │
                                │ (Cloudflare) │
                                └──────┬───────┘
                                       │
                                ┌──────▼───────┐
                                │  API Gateway │ (FastAPI + uvicorn)
                                │  + WebSocket │
                                └──────┬───────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────▼────────┐    ┌─────────▼─────────┐    ┌─────────▼────────┐
     │ Harness Workers │    │  Sandbox Nodes    │    │  Support Services │
     │  (K8s Deploy)   │    │  (K8s Pod Pool)   │    │                   │
     │                 │    │                   │    │ ┌───────────────┐ │
     │ ┌─────────────┐ │    │ ┌───────────────┐ │    │ │ PostgreSQL    │ │
     │ │ Engine x N  │ │    │ │ Container x N │ │    │ │ (HA/Patroni)  │ │
     │ └─────────────┘ │    │ └───────────────┘ │    │ └───────────────┘ │
     │                 │    │                   │    │ ┌───────────────┐ │
     │ Auto-scale      │    │ Pre-provisioned   │    │ │ Redis Cluster │ │
     │ HPA: CPU/Memory │    │ Warm Pool         │    │ │ (Cache+MQ)    │ │
     └─────────────────┘    └───────────────────┘    │ └───────────────┘ │
                                                      │ ┌───────────────┐ │
                                                      │ │ NATS / Redis  │ │
                                                      │ │ Streams (Bus) │ │
                                                      │ └───────────────┘ │
                                                      │ ┌───────────────┐ │
                                                      │ │ Vault         │ │
                                                      │ │ (Secrets)     │ │
                                                      │ └───────────────┘ │
                                                      └───────────────────┘
```

### 9.2 Kubernetes 资源配置

```yaml
# deployment/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cove-api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cove-api
  template:
    metadata:
      labels:
        app: cove-api
    spec:
      containers:
      - name: api
        image: cove/api-gateway:latest
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 8001
          name: ws
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: cove-db
              key: url
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 15

---
# deployment/harness-workers.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cove-harness-workers
spec:
  replicas: 5  # HPA auto-scales
  selector:
    matchLabels:
      app: cove-harness
  template:
    metadata:
      labels:
        app: cove-harness
    spec:
      containers:
      - name: harness
        image: cove/harness-engine:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: cove-llm
              key: anthropic-key
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cove-redis
              key: url
        resources:
          requests:
            cpu: 1000m
            memory: 1Gi
          limits:
            cpu: 4000m
            memory: 4Gi
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock

---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cove-harness-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cove-harness-workers
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 9.3 单机开发部署（Docker Compose）

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cove
      POSTGRES_USER: cove
      POSTGRES_PASSWORD: dev-only
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: |
      -c max_connections=200
      -c shared_buffers=256MB

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes --maxmemory 512mb

  api:
    build: ./api
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://cove:dev-only@postgres:5432/cove
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on: [postgres, redis]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  harness:
    build: ./harness
    environment:
      DATABASE_URL: postgresql+asyncpg://cove:dev-only@postgres:5432/cove
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on: [postgres, redis, api]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  pgdata:
```

---

## 11. 实施路线图

### Phase 0：基础设施（2 周）

```
目标：可运行的骨架
```

| 任务 | 产出 | 估时 |
|------|------|------|
| 项目脚手架 | monorepo 结构 + CI | 2d |
| PostgreSQL Event Schema | Migration + 索引 | 1d |
| Session Store Service MVP | emitEvent / getEvents / listSessions | 2d |
| API Gateway 骨架 | FastAPI + WebSocket | 2d |
| Claude Agent SDK 集成 | 本地调用链路打通 | 1d |
| Docker Sandbox MVP | 单容器创建/执行/销毁 | 2d |

### Phase 1：核心链路（3 周）

```
目标：端到端可运行：创建 Session → Claude 回复 → 工具执行 → 结果返回
```

| 任务 | 产出 | 估时 |
|------|------|------|
| Harness Engine wake/loop | 完整推理循环 | 5d |
| Context Builder | compaction / trimming / prompt 构建 | 3d |
| Tool Router | Bash/Read/Edit → Sandbox execute | 2d |
| WebSocket 实时事件推送 | Server → Client stream | 2d |
| Session Resume | 从 Event 重放恢复 | 2d |
| Permission System | 六种模式 + 权限检查 | 1d |

### Phase 2：可靠性和安全（2 周）

```
目标：崩溃恢复 + 凭据隔离 + 多 Agent
```

| 任务 | 产出 | 估时 |
|------|------|------|
| Harness 崩溃自动恢复 | cattle pattern | 2d |
| Credential Vault | 凭据安全存储 | 2d |
| MCP Proxy | OAuth 代理注入 | 2d |
| Sub-Agent 系统 | 并行子 Agent | 3d |
| Session Store 适配器 | SDK adapter for Cove | 1d |

### Phase 3：平台化（2 周）

```
目标：Dashboard + 监控 + Autopilot
```

| 任务 | 产出 | 估时 |
|------|------|------|
| 项目管理 API | project CRUD + 成员管理 | 2d |
| Session Dashboard | Web UI 基础版 | 3d |
| Auto Mode 模型分类器 | 基于 LLM 的权限自动裁决 | 3d |
| 计费/Token 统计 | usage tracking | 2d |
| Healthcheck + Alerting | Prometheus metrics + Grafana | 2d |

### Phase 4：生产和扩展（持续）

```
目标：私有化部署 + 多模型 + 企业功能
```

| 任务 | 产出 | 估时 |
|------|------|------|
| K8s 完整部署 | Helm chart + HPA | 3d |
| 多模型支持 | Ollama / vLLM 集成 | 3d |
| 私有化部署方案 | air-gapped install | 5d |
| Skills 市场 | 社区 Skills 注册 | 5d |
| SOC2 / 合规 | 审计日志 + 数据加密 | 10d |

**总估时：Phase 0-3 ≈ 11 周（1 人全栈），Phase 4 取决于团队规模。**

### 里程碑

```
Week 2  ──►  MVP 骨架可跑
Week 5  ──►  端到端：创建 session → Claude 写代码 → commit
Week 7  ──►  崩溃恢复 + 凭据隔离 到位
Week 9  ──►  Dashboard + 基础产品化
Week 11 ──►  可对外 Alpha 测试
```

---

## 12. 技术选型与 FAQ

### 11.1 推荐栈

| 层 | 技术 | 理由 |
|----|------|------|
| **语言** | Python 3.12+ | 复用 Claude Agent SDK；async 生态成熟 |
| **Web 框架** | FastAPI + uvicorn | 原生 async、WebSocket、自动 OpenAPI |
| **数据库** | PostgreSQL 16 | 分区表、JSONB、全文搜索、成熟 |
| **缓存/消息** | Redis 7 | 热数据缓存 + Pub/Sub + Streams |
| **任务队列** | asyncio + NATS（备选） | 内置 async，无需 Celery |
| **容器运行时** | Docker + aiodocker | 成熟的容器 API，Sandbox 隔离 |
| **编排** | Kubernetes | HPA、Pod 隔离、滚动更新 |
| **凭据管理** | HashiCorp Vault（生产） / K8s Secrets（开发） | 标准凭据管理 |
| **LLM** | Anthropic API（主） + Ollama/vLLM（自托管） | Claude 为主，开源模型备选 |
| **前端** | React + Vite（Dashboard） | 快速开发，生态丰富 |
| **监控** | Prometheus + Grafana + Loki | 标准监控栈 |
| **CI/CD** | GitHub Actions + ArgoCD | 代码到部署全自动化 |

### 11.2 Python 依赖

```toml
[project]
name = "cove-agent-manager"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    # Claude Agent SDK（核心引擎）
    "claude-agent-sdk>=0.1.81",
    
    # Web
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "websockets>=12",
    
    # Database
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    
    # Cache & Messaging
    "redis[hiredis]>=5.0",
    
    # Docker
    "aiodocker>=0.21",
    
    # Auth
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    
    # Utilities
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
    "anyio>=4.0",
    "structlog>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx-ws>=0.6",       # WebSocket testing
    "testcontainers>=4.0",  # Docker integration tests
    "ruff>=0.5",
    "mypy>=1.10",
]
```


### 12.4 FAQ：架构决策问答

**Q1: 是否需要最强模型作为总编排？**

**A: 不需要。编排分层解决。** Scheduler（Sonnet）收任务和分派——这是分类/匹配问题，非深度推理。只有 Planner 和 Reviewer 在复杂任务上间歇性用 Opus。Opus 占 ~20% 调用量，Sonnet 占 ~80%。全部用 Opus 编排会导致成本翻倍但质量几乎无提升。

**Q2: 多 Agent 分散工作是否会降低知识命中率？**

**A: 不会——反而提高命中率，因为噪音被提前过滤。** 传统多 Agent 用对话摘要传递信息，逐级压缩导致信息丢失。Cove 用三个机制保证命中率：
1. Session Events 作为知识索引——Worker 精确查询而非全量加载
2. 外部化上下文对象——代码文件存在 Sandbox 中，Worker 直接 Read，不经压缩
3. 角色定制 Compaction——只保留该角色需要的信息，丢弃干扰

**Q3: Worker 是由 Claude Code 扮演的吗？**

**A: 不是。Worker 是 Cove 自己的推理实例。** Claude Code 是全功能 Agent（全部工具+全部权限+全部上下文）。Worker 是被裁剪的——只给角色需要的 2-3 个工具、选择性上下文、role-scoped 权限。Claude Agent SDK 的作用是暴露可定制的推理 API，让 Cove 组装 Worker，而不是提供 Claude Code 实例。

**Q4: Session 和 Context 有什么区别？**

**A: Session 是永久存储的不可变事件日志。Context 是每轮推理从 Session 选择性构建的瞬时视图。** 这意味着：compaction/trimming 可逆（原始事件永远在 Session 中）、Agent 崩溃后通过重放 Session 恢复、可以用不同模型在相同 Session 上重新推理。

**Q5: 是否需要预先设计很多 Worker 角色？**

**A: 不需要。只定义 5 个能力原语（只读/读写/执行/搜索/推理），角色在运行时由 Planner 动态生成。** 同一原语 + 不同 system prompt = 不同角色。开发者不预判需求，Planner 在现场生成正确的角色定义。


### 11.3 与 Anthropic Managed Agents 的关键差异

| 维度 | Anthropic MA | Cove AM |
|------|-------------|---------|
| **Harness 实现** | 自研（不公开） | Claude Agent SDK + 开源 |
| **Session Store** | 托管黑盒 | PostgreSQL + 可插拔适配器 |
| **Sandbox Runtime** | 受限容器 | Docker / K8s / 自定义 |
| **LLM** | Claude 独占 | Claude + Ollama/vLLM/OpenRouter |
| **私部署** | ❌ | ✅ K8s/Compose |
| **MCP 扩展** | 有限 | 完全可扩展 |
| **Sub-Agent** | Task Agent | AgentDefinition（复用 SDK） |
| **外部存储适配** | 待定 | Redis / S3 / PG 参考实现已提供 |

---

## 13. 附录

### A. 关键设计决策记录 (ADR)

| 决策 | 理由 | 替代方案 |
|------|------|----------|
| Session 用 PG 分区表而非时序库 | 团队熟悉 PG，JSONB 灵活；1 万 events/s 以内 PG 足够 | ClickHouse（过早优化） |
| Sandbox 用 Docker 非 gVisor/Firecracker | 快速启动优先；重度安全场景后期补 | Firecracker microVM（启动慢） |
| Python 非 Go | 可复用 Claude Agent SDK | Go 性能更好但无 SDK 复用 |
| asyncio 非 Trio | FastAPI + SDK 都基于 asyncio | Trio 结构化并发更安全 |
| LLM 非自推理 | Claude API 是核心价值，自推理留在 Phase 4 | vLLM（运维复杂） |

### B. 风险矩阵

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| Claude API 审查/限流 | 产品不可用 | 低 | 多模型 fallback（Phase 4） |
| Container escape 安全漏洞 | 数据泄露 | 低 | least-privilege + read-only rootfs |
| Session Store 性能瓶颈 | 写延迟增大 | 中 | 分区 + 读写分离 + Redis 前置 |
| SDK API breaking changes | 代码需要适配 | 高 | pin 版本 + CI 自动升级检测 |
| TTFT 过大（用户感知卡顿） | 体验差 | 中 | warm pool + streaming |

### C. 性能目标

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| Session 创建 | < 200ms | API P95 延迟 |
| TTFT（首 token 时间） | < 1s（无 Sandbox）< 5s（有 Sandbox） | WebSocket 首 event |
| Event 写入延迟 | < 50ms P99 | emitEvent RTT |
| Sandbox provision | < 3s（warm）/ < 15s（cold） | provision RTT |
| Tool execute 延迟 | < 500ms + 命令执行时间 | execute RTT |
| Session resume | < 1s | wake → 首次推理 |

### D. 参考仓库结构

```
cove-agent-manager/
├── api/                        # FastAPI Gateway
│   ├── main.py                 # 应用入口
│   ├── routes/
│   │   ├── sessions.py
│   │   ├── projects.py
│   │   └── websocket.py
│   ├── middleware/
│   │   ├── auth.py
│   │   └── ratelimit.py
│   └── schemas.py
│
├── session_store/              # Session 持久化
│   ├── models.py               # SQLAlchemy models
│   ├── service.py              # SessionStoreService
│   ├── event_bus.py            # Redis/NATS EventBus
│   └── migrations/
│
├── harness/                    # Harness 引擎
│   ├── engine.py               # HarnessEngine
│   ├── manager.py              # HarnessManager
│   ├── context_builder.py      # 上下文构建 + compaction
│   ├── tool_router.py          # 工具路由
│   └── sdk_adapter.py          # Cove → SDK SessionStore adapter
│
├── sandbox/                    # Sandbox 管理
│   ├── manager.py              # SandboxManager
│   ├── providers/
│   │   ├── docker.py           # Docker provider
│   │   ├── k8s.py              # K8s Pod provider
│   │   └── remote.py           # Remote VM provider
│   └── templates/
│       └── sandbox-pod.yaml
│
├── security/                   # 安全层
│   ├── vault.py                # CredentialVault
│   ├── mcp_proxy.py            # MCP Proxy
│   ├── permissions.py          # PermissionSystem
│   └── audit.py                # 审计日志
│
├── orchestration/              # 编排
│   ├── subagent.py             # Sub-Agent 系统
│   └── workflow.py             # 工作流引擎
│
├── dashboard/                  # React Dashboard（可选）
│   ├── src/
│   └── package.json
│
├── docker-compose.yml          # 本地开发
├── k8s/                        # K8s 部署
│   ├── api-gateway.yaml
│   ├── harness-workers.yaml
│   └── hpa.yaml
│
├── tests/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── architecture.md
    └── api-reference.md
```

---

## 14. Planner 动态分解迭代路径

### 14.1 整体评估

| 维度 | 评分 | 解释 |
|------|------|------|
| 技术可行性 | 7/10 | 主体可做，边界情况需要大量工程打磨 |
| 分解质量（软件工程） | 7/10 | Claude 在编码任务上经过大量 RL 训练，分解质量较高 |
| 分解质量（开放任务） | 5/10 | 调研/策略类分解依赖上下文丰富度，稳定性不足 |
| 依赖推断 | 5/10 | 语义依赖尚可，数据流依赖是盲区（假并行问题） |
| 原语覆盖度 | 9/10 | 5 个覆盖 95% 场景，缺 DEPLOY/COMMUNICATE 两个边缘原语 |
| 错误恢复 | 4/10 | 级联重跑、数据流损坏、假并行等场景尚未覆盖 |
| 成本效率 | 7/10 | 复杂任务值得，简单任务 overhead 过高（需跳过机制） |

**综合判断：值得做，但不建议一次性全量上线。**

---

### 14.2 四阶段迭代路径

#### Phase 1：限定领域 + 跳过机制（MVP）

**目标：只在软件工程类任务启用动态分解，其他走预设 DAG**

| 子任务 | 产出 | 估时 |
|--------|------|------|
| 任务分类器 | 输入 task → 判定是否启用 Planner 分解 | 2d |
| 简化分解器 | 只输出 subtasks（不含 dependencies，Worker 顺序执行） | 3d |
| 跳过机制 | 小任务直接执行，不走 Planner | 1d |
| 结构化 Handoff 协议 | Worker 结束时输出 handoff.json（结论+文件列表+注意项） | 2d |
| 分解质量门控 | 每次分解后自动验证子任务数量在合理范围内 | 1d |

**Phase 1 的限制：**
- 不假设 Worker 并行，顺序执行
- 不依赖 dependencies 标注
- 只处理
- 只处理软件工程类任务（重构、功能实现、bug 修复）
- 分解结果人工审阅后才进入执行

---

#### Phase 2：并行执行 + Handoff 协议（核心能力）

**目标：拓扑分派上线，Worker 按依赖图并行启动**

| 子任务 | 产出 | 估时 |
|--------|------|------|
| 依赖推断增强 | LLM 输出 dependencies + 后处理校验 | 3d |
| 拓扑调度器 | `_dispatch_topological` 实现（FIRST_COMPLETED 等待模式） | 3d |
| 文件级依赖追踪 | Sandbox 监控文件变更 → 自动推断数据依赖 | 3d |
| Handoff 强制执行 | 每个 Worker 结束时必须输出 `handoff.json`，Scheduler 检查 | 2d |
| 上下文注入 | Planner 主动把前置 Worker 的 handoff 注入下游 Context | 2d |

**依赖推断增强策略（双保险）：**
```
LLM 输出：[{idx:0, dep:[]}, {idx:1, dep:[]}, {idx:2, dep:[0,1]}]
         ↓ 后处理校验
1. 文件交叠检查：subtask 0 和 1 都写同一个文件？→ 加串行依赖
2. 路径交集检查：subtask 1 写 /src/auth/，subtask 2 读 /src/auth/？→ 加依赖
3. 最低延迟约束：不允许链表长度 > 5（强制拆分）
```

**Phase 2 的限制：**
- 依赖推断仍可能有假并行（A/B 标注为并行但 B 实际需要 A 的产出）
- 需要监控文件冲突率作为质量指标

---

#### Phase 3：错误恢复 + 级联管理（生产就绪）

**目标：Worker 失败后不污染下游，自动恢复**

| 子任务 | 产出 | 估时 |
|--------|------|------|
| 悲观调度模式 | 有依赖的 Worker 在依赖完成前不启动 | 2d |
| 乐观调度模式 | 依赖失败时自动标记下游 Worker 输出为 stale | 2d |
| 增量重跑 | 只重跑读取了错误产物的 Worker | 3d |
| 并行监测 | 检测两个 Worker 是否修改了相同文件 → 触发 Reviewer | 2d |
| 死锁检测 | 标注依赖的循环引用检测 + 超时回退 | 1d |

**调度模式选择策略：**
```
任务类型             推荐模式             理由
小改动（1-2 文件）    悲观调度             便宜，不差那点延迟
模块重构（3-5 文件）  乐观调度             并行性价比高
大型重构（10+ 文件）   悲观调度             文件冲突概率太高
搜索+写作（调研类）   乐观调度             文件冲突概率低
```

**Phase 3 的限制：**
- 增量重跑需要精确追踪 Worker 读/写了哪些文件
- 文件级追踪会增加 Sandbox 开销

---

#### Phase 4：全领域扩展 + 自我优化（成熟）

**目标：覆盖所有任务类型，Planner 自我进化**

| 子任务 | 产出 | 估时 |
|--------|------|------|
| 分解缓存 | 相同任务描述+上下文的分解结果缓存（稳定输出） | 2d |
| 分解模板 | 高频任务类型（特征实现、bug 修复、调研报告）的 structured few-shot | 2d |
| 非软件工程扩展 | 调研/分析/运维/文档等任务类型的分解适配 | 3d |
| 命中率监控 | Worker 冲突率、重跑率、分解稳定性仪表盘 | 2d |
| 自动跳过阈值 | 基于历史数据自动决定是否走 Planner（成本收益模型） | 3d |
| 第 6/7 原语扩展 | DEPLOY（CI/CD 工具链）+ COMMUNICATE（通知/邮件） | 2d |

---

### 14.3 五个核心挑战及缓解方案

#### 挑战 1：分解质量不稳定

**现象：** 同样任务不同次分解输出不同数量和结构的子任务，导致成本不可预测、用户感知不一致。

**缓解方案（按优先级）：**
1. **分解缓存**（Phase 4）：相同任务描述+上下文返回稳定分解
2. **分解模板**（Phase 4）：高频任务使用 few-shot，减少模型自由发挥空间
3. **质量门控**（Phase 1）：子任务数量超过预期范围 → 要求重新分解
4. **人工干预**（Phase 1）：高风险任务分解结果先过人工审阅

#### 挑战 2：隐式依赖导致数据流损坏

**现象：** Worker A 和 B 被标注为可并行，但 B 依赖 A 修改的代码 → B 在旧版本上工作 → 输出不可用。

**缓解方案：**
1. **文件级依赖追踪**（Phase 2）：监控 Sandbox 文件变更矩阵
   ```
   Worker A: writes /src/auth/token.py, /src/auth/types.py
   Worker B: reads /src/auth/types.py  ← 有数据依赖！
   Scheduler 自动将 B 的策略从 "parallel" 降级为 "wait_for_A"
   ```
2. **乐观合并 + 冲突检测**（Phase 3）：允许并行，但检测到文件冲突时触发 Reviewer 介入
3. **文件版本戳**：Sandbox 中每个文件记录 Worker 写入时间戳，读时检查版本

#### 挑战 3：Worker 间信息传递效率

**现象：** Worker A 的 Event 日志有 1000+ 行，Worker B 需要知道 A 的最终结论，但 B 是特化 Worker 不应去 parse A 的全量日志。

**缓解方案：**
1. **结构化 Handoff 协议**（Phase 1，强制执行于 Phase 2）：
   ```json
   {
     "conclusion": "JWT 方案选择 RS256，定义了 3 个接口",
     "files_created": ["/src/auth/jwt.py", "/src/auth/types.py"],
     "files_modified": [],
     "pending_decisions": [],
     "warnings": ["JWT secret 仍未存储为环境变量"]
   }
   ```
2. **主动注入**（Phase 2）：Scheduler 不依赖 Worker B 自己去 Session 查，而是把 A 的 handoff 直接注入到 B 的 System Prompt 中

#### 挑战 4：失败重试的级联效应

**现象：** Worker A 失败后重启成功，但 B 和 C 已经在 A 第一次运行失败前启动并读取了错误产物。

**缓解方案：**
1. **乐观调度 + 重跑**（Phase 3）：A 失败 → B 和 C 的输出标记为 stale → A 重跑成功 → B 和 C 重跑
2. **悲观调度**（Phase 3）：高风险任务（大型重构）等待 A 完成确认后才启动 B 和 C
3. **增量重跑**（Phase 3）：重跑前检查 Worker B 是否真正读取了 A 的错误产物——如果 B 只读了 A 未影响的部分，跳过重跑

#### 挑战 5：Planner 自身的成本与延迟

**现象：** 对于简单任务，Planner 分解的 overhead（~1s + ~500 tokens）占比过高。

**缓解方案：**
1. **跳过机制**（Phase 1）：小任务不走 Planner，直接执行
2. **跳过阈值**（Phase 4）：基于历史数据学习的成本收益模型
3. **任务分类器**（Phase 1）：分类器判断 → 走 Planner / 走预设 DAG / 直执行

---

### 14.4 实施顺序总结

```
Phase 1 ── 限定领域 + 跳过机制
  │ 只做软件工程任务
  │ 顺序执行，不并行
  │ Handoff 协议落地
  ▼
Phase 2 ── 并行 + 依赖推断
  │ 拓扑分派
  │ 文件级依赖追踪
  │ 上下文主动注入
  ▼
Phase 3 ── 错误恢复 + 级联管理
  │ 乐观/悲观调度模式切换
  │ 增量重跑
  │ 冲突检测
  ▼
Phase 4 ── 全领域 + 自我优化
  │ 分解缓存 + 模板
  │ 命中率监控
  │ 自动跳过阈值
  │ 第 6/7 原语
```

**关键决策点（每阶段结束时）：**
- Phase 1 → Phase 2：分解质量是否达到 80%+ 人工验收率？不足则回退改进
- Phase 2 → Phase 3：Worker 文件冲突率是否 < 10%？超过则收紧悲观调度默认值
- Phase 3 → Phase 4：增量重跑覆盖率是否 > 95%（没有漏标的 stale Worker）？

---

*设计文档版本 v2.1 | 2026-05-13 | 基于 Anthropic Managed Agents + Claude Agent SDK 架构推导*

*下一阶段：可将本设计分为 4 个并行 sub-agent 分别深化 Phase 0-3 的实现细节。*
