# AGENTS.md — Cove Agent Manager 项目索引

## Where to look
- 项目使命与约束: CLAUDE.md
- 最终目标与审批边界: harness/goal.md
- 当前进度: CHANGELOG.md
- 功能状态: features.json
- 环境启动: init.sh
- 设计完整文档: docs/cove-agent-manager-design.md（2562 行 v2.1）
- 架构规则: docs/architecture.md
- 质量/技术债: docs/quality.md

## 项目结构
```
cove-agent-manager/
├── CLAUDE.md            # 使命 + 约束
├── AGENTS.md            # 索引（本文件）
├── harness.json         # 命令入口
├── features.json        # 功能清单
├── CHANGELOG.md         # 进度日志
├── init.sh              # 环境启动
├── docs/                # 设计文档
├── harness/             # 目标 + 合约
├── scripts/             # 保护脚本
├── tests/               # 测试
└── artifacts/           # 日志/截图
```

## 设计参考
- 设计文档: docs/cove-agent-manager-design.md
  - §1-2: 产品定位与设计哲学
  - §3: 核心架构（Session/Harness/Sandbox 三层接口）
  - §4: Session 持久化层（PostgreSQL 分区 + Redis 缓存）
  - §5: Harness Orchestrator（无状态推理循环）
  - §6: Sandbox Manager（Docker Pool）
  - §7: 安全隔离层（Vault + MCP Proxy）
  - §9: 角色编排系统（Planner + 5 能力原语 + 拓扑分派）
  - §11: 实施路线图（Phase 0-4）
  - §12: 技术选型
  - §14: Planner 动态分解迭代路径

## 默认工作循环
1) 读取 CLAUDE.md + harness/goal.md + CHANGELOG.md
2) 选取一个最接近最终目标的可验证步骤
3) 实现并验证
4) git commit + 更新 CHANGELOG（包含 commit hash）
5) 运行 `bash scripts/run_change_guard.sh` 验证
6) 除非有 blocker / 审批边界 / 重大 pivot，否则继续
