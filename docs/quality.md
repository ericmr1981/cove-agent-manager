# Quality / Tech Debt

## Known Issues

### High Priority
- ~~**F-012 Crash Recovery**: Not implemented.~~ ✅ Implemented (CrashRecoveryManager + 12 tests)
- ~~**F-024 WebSocket Extended Events**: Not implemented.~~ ✅ Implemented (4 new event types)
- ~~**F-019 Planner Dynamic Decomposition**: Not implemented.~~ ✅ Implemented Phase 1 MVP (35 tests)
- ~~**Context Builder Compaction**: Not implemented.~~ ✅ Implemented (27 tests)
- ~~**Test Coverage**: Only 4 of 12+ modules have dedicated tests.~~ ✅ 16 test files, 153 tests
- **F-002 PostgreSQL Schema**: Needs Docker PostgreSQL (certificate issue)

### Medium Priority
- **SQLite in tests**: Tests use `sqlite+aiosqlite` instead of PostgreSQL — potential prod mismatch.
- **Tool Call Parsing**: `HarnessEngine.loop()` has a `# TODO` for parsing tool_use from LLM responses.
- **datetime.utcnow()**: Deprecated — all uses migrated to timezone-aware UTC. (Fixed 2026-05-13)
- **quality.md was empty**: Now populated.

### Low Priority
- **Prometheus/Grafana**: No metrics or alerting integration yet.
- **Alembic Migrations**: Schema defined in ORM models but no migration scripts.
- **Dashboard Build Artifacts**: `dist/` and `node_modules/` not gitignored in dashboard subdir.

## Test Status

Run: `pytest tests/ -q`

Latest: 19 passed (with deprecation warnings before fix)
