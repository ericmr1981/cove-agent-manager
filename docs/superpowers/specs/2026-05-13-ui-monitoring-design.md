# Cove Console — 人类交互 UI + 任务管线 + Agent 状态监控

> Phase 3 扩展设计：在基础 Session Dashboard 之上，构建包含对话界面、任务管线可视化、Agent 实时监控的一体化 Web 控制台。
> 版本：v1.0 | 2026-05-13

---

## 1. 设计目标

在 Cove 现有后端架构之上，构建一个**一体化的 Web 控制台**，覆盖三种核心交互场景：

| 场景 | 用户行为 | 信息需求 |
|------|----------|----------|
| **对话交互** | 发送任务、查看回复、审批权限 | 实时事件流、工具调用可视化、Sandbox 状态 |
| **任务管线** | 查看任务分解、跟踪 Worker 进度、诊断失败 | DAG 拓扑图、子任务状态、事件日志 |
| **Agent 监控** | 查看 Agent 健康、资源消耗、Session 列表 | 卡片摘要、汇总指标、Session 级联信息 |

### 1.1 核心约束

- **单一入口**：所有视图通过标签页切换，不拆分独立页面
- **实时优先**：WebSocket 推送优先于轮询，事件流驱动 UI 更新
- **前端轻量**：React + Vite，不引入复杂状态管理库（React context + hooks 足够）
- **后端无状态**：所有 UI 所需状态来自已有的 Session Store 和新增的 Agent 状态查询 API
- **渐进增强**：Phase 3 先出 MVP（对话 + 基础状态），后续迭代增强

---

## 2. 标签页架构

```
┌─────────────────────────────────────────────────────────────┐
│  💬 对话  │  📋 任务管线  │  🤖 Agent 状态  │  ⚙️ 设置    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                  ┌──────────────────────────┐               │
│                  │    当前标签页内容         │               │
│                  │     (按标签切换)          │               │
│                  └──────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Tab 优先级定义

- **💬 对话** — 默认 Tab，程序启动时激活
- **📋 任务管线** — 当 Session 中 Planner 完成分解后自动高亮提示
- **🤖 Agent 状态** — 当有 Agent 状态变更时显示角标数字
- **⚙️ 设置** — Session 配置、模型选择、权限模式、Sandbox 配置

### 2.2 全局导航栏

每个 Tab 共享的顶部区域，包含：
- 当前 Session 名称/ID
- Session 运行状态指示器（运行中/已完成/失败）
- 快速操作按钮：中断、恢复、Fork
- Token 用量和费用概览

---

## 3. 💬 对话 Tab

### 3.1 核心交互模型

以 Claude Code 的终端对话界面为参考，适配为 Web UI：

```
┌──────────────────────────────────────────────────┐
│  消息列表 (scroll)                                │
│                                                   │
│  ┌──────────────────────────────────┐             │
│  │ You: Refactor auth to JWT        │             │
│  ├──────────────────────────────────┤             │
│  │ 🤖 Cove · Sonnet                │             │
│  │  分析代码结构...                  │             │
│  │  ┌──────────────────────────┐    │             │
│  │  │ $ grep -n "auth" *.py    │    │             │
│  │  │ src/auth.py:42 ...       │    │             │
│  │  └──────────────────────────┘    │             │
│  │  ⬤ 正在读取 auth.py...          │             │
│  ├──────────────────────────────────┤             │
│  │ 🔒 需要权限: 编辑 jwt.py         │             │
│  │  [允许] [拒绝] [始终允许]         │             │
│  ├──────────────────────────────────┤             │
│  │ 🤖 Worker-A · Sonnet            │             │
│  │  JWT 实现完成，正在测试...        │             │
│  └──────────────────────────────────┘             │
│                                                   │
│  ┌─────────────────────────┬──────────┐           │
│  │ 输入消息...              │ 发送     │           │
│  └─────────────────────────┴──────────┘           │
├──────────────────────────────────────────────────┤
│  Session 侧边栏                                   │
│  模型: Sonnet | Tokens: 1,234/10k                │
│  工具: Read · Edit · Bash                        │
│  Sandbox: python:3.12  ⬤ running                 │
│  权限模式: acceptEdits                            │
└──────────────────────────────────────────────────┘
```

### 3.2 消息类型渲染

| 事件类型 | UI 渲染 |
|----------|---------|
| `user_message` | 用户头像 + 文本内容 + 附件列表 |
| `assistant_message` | Agent 头像 + 模型标签 + Markdown 渲染 |
| `assistant_thinking` | 折叠面板，"正在思考..." + 点击展开 |
| `tool_use` | 代码块风格，显示命令/参数 |
| `tool_result` | 输出预览（可折叠长输出） |
| `tool_error` | 红色错误框 + 错误详情 |
| `system` | 灰条系统消息 |
| `permission_request` | 交互式审批卡片（允许/拒绝/始终允许） |
| `compaction` | "上下文已压缩" 提示条 |

### 3.3 权限审批交互

- `permission_request` 事件触发内联审批卡片
- 三种决策：允许（单次）、拒绝（单次）、始终允许（本次 Session）
- 审批后卡片更新为决策结果，不可再次操作
- 审批通过后自动继续执行（无需用户再次发送消息）

### 3.4 右侧 Session 面板

- **模型信息**：当前模型 + Token 用量（已用/限额）
- **工具列表**：当前 Session 已启用的工具
- **Sandbox 状态**：容器运行状态 + 镜像名 + 运行时长
- **权限模式**：当前权限策略（auto/acceptEdits/bypass）
- **费用统计**：当前 Session 累计费用
- **Agent 列表**：当前 Session 涉及的 Agent（Planner + Workers）

---

## 4. 📋 任务管线 Tab

### 4.1 可视化模型

用 DAG（有向无环图）展示任务分解和执行拓扑：

```
                     ┌──────────────┐
                     │   🧠 Planner  │
                     │   任务分解     │
                     │   ✅ 完成     │
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ 🔧 Worker-A │ │ 🔧 Worker-B │ │ 🔧 Worker-C │
     │ 实现 JWT   │ │ 更新测试   │ │ 迁移中间件  │
     │ ██████░░ 60%│ │ ████████ 80%│ │ ⏳ 排队中   │
     │ READ_WRITE  │ │ EXECUTE    │ │ READ_WRITE  │
     │ Sonnet      │ │ Haiku      │ │ Sonnet      │
     └────────────┘ └─────┬──────┘ └────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │  👁️ Reviewer │
                  │  质量审查     │
                  │  ⏳ 等待输入  │
                  └──────────────┘
```

### 4.2 节点状态颜色

| 状态 | 颜色 | 说明 |
|------|------|------|
| `pending` | 灰色虚线 | 尚未开始 |
| `running` | 蓝色实线 | 执行中 |
| `completed` | 绿色 | 已完成 |
| `failed` | 红色 | 失败 |
| `retrying` | 黄色 | 重试中 |
| `skipped` | 灰色实线 | 因依赖失败跳过 |

### 4.3 交互能力

- 点击 Worker 节点展开详情（当前工具调用、进度）
- 悬停显示摘要 Tooltip（模型、耗时、Token）
- 失败节点可点击查看错误日志
- 支持手动重试失败 Worker

### 4.4 事件日志

DAG 下方展示实时事件日志，格式：
```
10:23:01  ←  Planner: 任务分解完成 → 3 个子任务
10:23:05  →  Worker-A 已创建 (READ_WRITE · Sonnet)
10:23:05  →  Worker-B 已创建 (EXECUTE · Haiku)
10:25:12  !  Worker-B 失败: test_auth.py:42 assertion error
10:25:13  ↻  Worker-B 正在重试 (第 1/3 次)
```

---

## 5. 🤖 Agent 状态 Tab

### 5.1 卡片网格

顶部展示当前会话中所有 Agent 实例的实时状态卡片：

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 🧠 Planner      │ │ 🔧 Worker-A    │ │ 🔧 Worker-B    │
│ 状态: ⬤ running │ │ 状态: ⬤ running │ │ 状态: ⬤ error  │
│ 任务: auth重构   │ │ 任务: 实现 JWT  │ │ 任务: 更新测试  │
│ ████████░░░ 65% │ │ ██████░░░░ 40% │ │ ██████████ 80% │
│ 模型: Opus      │ │ 模型: Sonnet   │ │ 模型: Haiku    │
│ 耗时: 2m        │ │ 耗时: 1m       │ │ 耗时: 30s     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 5.2 汇总指标条

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  活跃     │ │  已完成   │ │  费用     │ │  运行时长  │
│  3       │ │  12      │ │  $0.42   │ │  18m      │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 5.3 Session 列表

底部表格展示所有 Session（包括历史），支持：

| 列 | 说明 |
|----|------|
| Session ID | UUID 前 8 位 |
| 项目 | Session 归属项目 |
| Agent | 涉及 Agent 列表 |
| 状态 | ⬤ 运行中 / ⬤ 已完成 / ⬤ 失败 |
| Tokens | 累计消耗 |
| 耗时 | Session 运行时长 |
| 操作 | 查看/恢复/删除 |

---

## 6. WebSocket 事件扩展

现有 WebSocket 协议基础上，增加 UI 所需的实时事件类型：

### 6.1 新增事件

```json
// Agent 状态变更
{ "type": "agent_status", "agent_id": "worker-a", "status": "running", "progress": 0.4, "current_tool": "Edit" }

// 任务拓扑更新
{ "type": "pipeline_update", "dag": { "nodes": [...], "edges": [...] } }

// Worker 进度更新
{ "type": "worker_progress", "worker_id": "worker-a", "progress": 0.6, "message": "正在写入 jwt.py..." }

// 汇总指标更新（定期推送 5s 间隔）
{ "type": "metrics_snapshot", "active_agents": 3, "total_completed": 12, "cost_usd": 0.42, "uptime": 1080 }
```

### 6.2 后端数据源

| 事件类型 | 数据来源 |
|----------|----------|
| `agent_status` | HarnessEngine + Sub-Agent 系统 |
| `pipeline_update` | Planner 分解结果 + Worker 生命周期 |
| `worker_progress` | Harness loop 内事件流 |
| `metrics_snapshot` | Session Store 聚合查询 |

---

## 7. 影响范围分析

### 7.1 新 Feature 清单（补充 features.json）

| ID | Title | Phase |
|----|-------|-------|
| F-021 | 对话界面（Web Chat）：消息渲染、输入、权限审批 | Phase 3 |
| F-022 | 任务管线 DAG 可视化 | Phase 3 |
| F-023 | Agent 状态实时监控面板 | Phase 3 |
| F-024 | WebSocket 扩展事件（agent_status / pipeline_update / worker_progress） | Phase 2→3 |
| F-025 | Session 列表与生命周期管理 UI | Phase 3 |

### 7.2 对现有设计的影响

- **Phase 2 WebSocket** 需扩展事件类型（新增 agent_status、pipeline_update 等）
- **Phase 2 Sub-Agent 系统** 需暴露 Worker 进度和状态查询接口
- **Phase 3 Dashboard** 估时从 3d 扩展（见第 8 节）
- 后端无需新增存储层，所有数据可从已有的 Session Events + Planner 分解结果派生

### 7.3 不需要变更的部分

- Session Store 数据模型不需要改（已有 event types 足够派生大部分 UI 状态）
- Harness 引擎不需要感知前端存在（纯 WebSocket 推送，无状态）
- Permission 系统不需要变更（审批流程已通过 WebSocket 实现）

---

## 8. Phase 3 修订路线图

原 Phase 3 估时 2 周，增加控制台 UI 后扩展为 3 周：

### 修订后 Phase 3（3 周）

```
目标：Cove Console + 基础产品化
```

| 任务 | 产出 | 估时 |
|------|------|------|
| WebSocket 事件扩展 | agent_status / pipeline_update 等 | 1d |
| 对话 Tab 前端 | 消息渲染 + 输入 + 权限审批 | 3d |
| 任务管线 Tab 前端 | DAG 可视化 + 事件日志 | 2d |
| Agent 状态 Tab 前端 | 卡片网格 + 汇总指标 + Session 列表 | 2d |
| Session 管理 API 补充 | 列表/恢复/Fork UI 对应的后端 API | 1d |
| 项目管理 API | project CRUD + 成员管理 | 2d |
| Auto Mode 模型分类器 | 基于 LLM 的权限自动裁决 | 3d |
| 计费/Token 统计 | usage tracking | 2d |
| Healthcheck + Alerting | Prometheus metrics + Grafana | 2d |

### 里程碑更新

```
Week 2  ──►  MVP 骨架可跑
Week 5  ──►  端到端：创建 session → Claude 写代码 → commit
Week 7  ──►  崩溃恢复 + 凭据隔离 到位
Week 10 ──►  Cove Console（对话 + 管线 + Agent 监控）上线
Week 12 ──►  可对外 Alpha 测试
```
