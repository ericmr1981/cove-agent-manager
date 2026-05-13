# Cove — Agent Runtime 完整开发项目

## Mission
构建一个自托管的 Agent 运行时环境（Agent OS），让 AI Agent 像操作系统管理进程一样，被可靠地编排、执行和恢复。

核心要解决的 4 个问题：
1. Agent 崩溃不丢进度 — Session 持久化到 PostgreSQL，Harness 无状态
2. 超越单 Agent 能力天花板 — Planner 动态分解任务为特化 Worker
3. 避免上下文窗口限制 — Session ≠ Context 彻底分离
4. 降低大规模 Agent 调用成本 — 编排分层（Sonnet 80% + Opus 20%）

## Acceptance target
- [ ] Phase 0: 基础设施（2 周）— PostgreSQL Schema + Session Store MVP + FastAPI 骨架 + Docker Sandbox MVP
- [ ] Phase 1: 核心链路（3 周）— HarnessEngine wake/loop + Context Builder + Tool Router + Session Resume
- [ ] Phase 2: 可靠性（2 周）— 崩溃自动恢复 + Credential Vault + MCP Proxy + Sub-Agent
- [ ] Phase 3: 平台化（3 周）— Cove Console（对话/管线/Agent 监控）+ Auto Mode + 计费 + 健康检查
- [ ] Phase 4: 全领域扩展（持续）— K8s 部署 + 多模型 + Planner 动态分解

## Non-goals
- 不做 SaaS 平台（私有化部署优先）
- 不做全功能 Claude Code 替代品（Worker 是特化、削弱的）
- 不做自己的 LLM 推理引擎（基于 Anthropic API + 开源模型）

## Constraints
- Python 3.12+，FastAPI + SQLAlchemy async
- 所有修改必须有提交记录，CHANGELOG 引用 commit hash
- 功能完成前不可标注 passes=true，必须有可执行验证

## Approval boundaries
- OpenAI/Anthropic API Key 配置
- Docker 容器 escape 相关的安全策略
- 项目方向性 pivot
- PostgreSQL Schema migration 在生产环境执行
