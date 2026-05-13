# Progress Log — Cove Agent Manager

## [2026-05-13] 项目初始化
- 创建项目骨架: cove-agent-manager/
- 设计文档 v2.1 完成（2562 行）
- 搭建项目 harness（CLAUDE.md / AGENTS.md / goal.md / features.json / init.sh / guard scripts）
- 初始功能清单: Phase 0-4 全部特征（20 个 feature）
- 首轮 guard check 通过
- commit: 0364169

## [2026-05-13] 设计阶段
- Cove Agent Manager 设计文档 v1.0 完成（2357 行）
- 包含完整架构设计：Session/Harness/Sandbox/Security/Orchestration
- 实施路线图 Phase 0-4
- v2.0 升级核心设计哲学：Session≠Context、Worker≠Claude Code、动态角色生成、分层编排
- v2.1 新增 Planner 动态分解迭代路径（§14，~190 行）

## [2026-05-13] Cove Console 设计与实现
- 新增 Phase 3 Cove Console 设计：4 标签页 Web 控制台（对话/任务管线/Agent 状态/设置）
- 定义 WebSocket 扩展事件：agent_status / pipeline_update / worker_progress / metrics_snapshot
- 构建 React + Vite + Tailwind 前端脚手架，13+ 个组件
- 实现 Claude Code 风格对话界面，含 8 种消息类型渲染 + 权限审批
- 实现任务管线 DAG 可视化（@xyflow/react）+ 实时事件日志
- 实现 Agent 状态实时监控面板（卡片网格 + 指标条 + Session 表格）
- 实现 Settings 配置表单（模型/工具/权限/Sandbox）
- 实现 WebSocket Context 驱动实时数据流
- 新增 5 个 feature (F-021 ~ F-025)
- Phase 3 估时从 2 周扩展为 3 周
- TypeScript 编译 + Vite 构建 + Vitest 测试全部通过
- commit: 8ff023d

## [2026-05-13] 补齐缺失 — 核心可靠性 + 测试覆盖
- F-012: 崩溃自动恢复（cattle pattern）实现 — CrashRecoveryManager + 12 tests
- F-024: WebSocket 扩展事件实现 — agent_status / pipeline_update / worker_progress / metrics_snapshot
- Context Builder: 新增 compaction/trimming 算法 + token 预估 + 27 tests
- 补齐 7 个缺失测试文件: tool_router, permissions, session_resume, subagent, mcp_proxy, auto_mode, usage_tracking
- 修复 datetime.utcnow() 弃用警告 (models.py)
- 更新 quality.md 跟踪已知问题
- 完整测试套件: 118 passed, 0 failed

## [2026-05-13] Planner 动态分解 + 最终验证
- F-019: Planner Agent 动态分解 Phase 1 MVP — TaskClassifier + 简化分解器 + 跳过机制 + Handoff 协议
- 新增 `cove/orchestration/planner.py` — PlannerAgent, TaskClassifier, SubTask, DecompositionResult
- 新增 `tests/test_planner.py` — 35 tests
- F-006: 修复 verify 命令名不匹配 (`test_harness_loop` → `test_loop_yields_events`)
- F-004: FastAPI health 端点验证通过 (curl /health → {"status": "ok"})
- 完整测试套件: 152 passed, 0 failed

## [2026-05-13] PostgreSQL 标准化 — 测试默认使用 PostgreSQL
- tests/conftest.py: 默认数据库从 SQLite 改为 PostgreSQL (postgresql+asyncpg)
- 所有测试文件统一使用 conftest 的 `store` fixture，移除各自硬编码的 SQLite 连接
- 修复 `EventModel.__table_args__`：移除不成熟的 `LIST (session_id)` 分区（需要手动管理分区）
- 修复 `SessionStoreService.get_session()`：invalid UUID 返回 None 而非报错
- 修复 `SessionModel`/`EventModel`：`created_at`/`updated_at` 使用 `DateTime(timezone=True)`
- 测试通过 `COVE_TEST_DATABASE_URL` 环境变量可切换数据库（默认 PostgreSQL）

## [2026-05-13] PostgreSQL Schema 修复 + F-002 验证通过
- F-002: PostgreSQL Schema 验证通过 (pg 16 partitioned table + sessions table)
- 修复 EventModel: 分区表主键必须包含分区列 `session_id`
- 修复 EventModel: 唯一约束必须包含分区列 `session_id`
- 通过 `mirror.gcr.io` 解决 Docker Hub 证书被 ClashX Pro 拦截的问题
