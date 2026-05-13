# Architecture Rules — Cove Agent Manager

## 依赖方向

```
Session Store (持久化层)
  ↓ 无状态调用
Harness Engine (推理循环)
  ↓ 隔离执行
Sandbox Manager (容器管理)
  ↓ 安全注入
Security Layer (凭据 + MCP)
  ↓
API Gateway (入口)
  ↓
Dashboard (Web UI)
```

独立垂直：
```
Orchestration Layer (编排层)
  └── PlannerAgent → Worker → Reviewer
  └── 不依赖 Harness 引擎内部状态
```

## 关键规则
- Session 不可变追加，Harness 不可直接修改已写入的 Event
- Harness 完全无状态：所有状态在 Session Store 和 Sandbox 中
- Sandbox 不与外部网络直连，必须经过 MCP Proxy
- 凭据永不进入 Sandbox 容器
- Worker 不需要看到其他 Worker 的思考过程，只需要看到产出（handoff.json）

## 设计文档
完整设计见 `docs/cove-agent-manager-design.md`
