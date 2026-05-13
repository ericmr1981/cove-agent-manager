# Goal Contract — Cove Agent Manager

## Final goal
构建一个自托管的 Agent Runtime 环境（Cove），实现：
1. 基于 PostgreSQL 的不可变 Session 事件日志
2. 无状态 Harness 引擎（崩溃自动恢复）
3. Docker Sandbox 隔离执行环境
4. Planner 动态分解 + 拓扑分派 Worker
5. 5 个能力原语（READ_ONLY/READ_WRITE/EXECUTE/SEARCH/THINK）

## Deliverable shape
- 用户可见产出: REST API + WebSocket + Dashboard 可创建 Session、发送消息、查看日志
- 技术产出: PostgreSQL 分区表 + asyncio Harness 引擎 + Docker Sandbox Pool + Claude Agent SDK 适配
- 必需证据: Phase 0-3 每个阶段的可运行演示

## Non-goals
- 不替代 Claude Code（Worker 是特化的推理实例，非全功能 Agent）
- 不开发专用前端（Dashboard 保持基础版）
- 不做 LLM 推理引擎自托管（用 Anthropic API + 开源模型 fallback）

## Constraints
- Python 3.12+，async 全链路
- 设计文档：docs/cove-agent-manager-design.md（v2.1）
- Phase 0-3 总估时 ~11 周（1 人全栈）
- 优先私有化部署（Docker Compose + K8s）

## Approval boundaries
- API Key 安全存储方案
- Docker 安全策略（容器 escape 防御）
- PostgreSQL 生产迁移
- 项目方向变更

## Reporting mode
- milestone-only（阶段交付时汇报）
- 完成一个 Phase 后通知 Boss

## Stop conditions
- 完成时: Phase 0-3 全部验收通过
- 阻塞时: 团队无法继续（CC BI）| Claude Agent SDK 不满足需求
- 升级时: 重复失败 2 次后通知 Boss
