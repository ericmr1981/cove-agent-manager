#!/usr/bin/env bash
set -euo pipefail

# Scaffold a minimal agent-first project harness in the current directory.
# Safe by default: will NOT overwrite existing files.
#
# Usage:
#   bash scripts/scaffold_harness.sh [--force] [--install-guards]

FORCE=0
INSTALL_GUARDS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    --install-guards)
      INSTALL_GUARDS=1
      shift
      ;;
    --help|-h)
      echo "Usage: bash scripts/scaffold_harness.sh [--force] [--install-guards]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      exit 2
      ;;
  esac
done

write_file() {
  local path="$1"; shift

  if [[ -f "$path" && "$FORCE" -ne 1 ]]; then
    echo "[skip] $path exists"
    # Consume stdin so callers can always use heredocs.
    cat >/dev/null
    return 0
  fi

  mkdir -p "$(dirname "$path")"
  cat > "$path"
  echo "[write] $path"
}

write_file "CLAUDE.md" <<'EOF'
# Project Mission (CLAUDE.md)

## Mission
- TODO

## Acceptance target
- TODO (must be verifiable)

## Non-goals
- TODO

## Constraints
- Keep changes bounded and reversible
- Do not claim done without verification evidence

## Approval boundaries
- Deployment / destructive actions
- Credentials / billing / external side effects
- Product direction pivots
EOF

write_file "AGENTS.md" <<'EOF'
# AGENTS.md (index)

Keep this file short (~100 lines).

## Where to look
- Mission + global rules: CLAUDE.md
- Goal contract: harness/goal.md
- Current progress: CHANGELOG.md
- Structured checklist: features.json
- Bootstrap: init.sh
- Architecture rules: docs/architecture.md
- Quality/tech debt: docs/quality.md

## Default loop
1) Read CLAUDE.md + harness/goal.md + CHANGELOG.md
2) Pick one bounded bet that most reduces distance to the final goal
3) Implement + verify
4) Commit + log (include commit hash)
5) Continue unless blocker / approval boundary / major pivot
EOF

write_file "CHANGELOG.md" <<'EOF'
# Progress Log

Use one entry per bounded iteration. Include failures.
EOF

write_file "features.json" <<'EOF'
[
  {
    "id": "F-001",
    "title": "TODO: first feature",
    "passes": false,
    "verify": "TODO: command or manual oracle"
  }
]
EOF

write_file "harness.json" <<'EOF'
{
  "initCommand": "bash init.sh",
  "testCommand": "",
  "e2eCommand": "",
  "acceptanceSummary": "TODO"
}
EOF

write_file "HARNESS_LINKS.md" <<'EOF'
# Harness links

Fill this only if you keep governance docs outside the repo (e.g. Obsidian).

- repoRoot: <this-repo-root>
- externalRecordRoot: <optional>
EOF

write_file "harness/goal.md" <<'EOF'
# Goal Contract

## Final goal
- TODO

## Deliverable shape
- User-visible outcome:
- Technical outcome:
- Required evidence:

## Non-goals
- TODO

## Constraints
- TODO

## Approval boundaries
- Deployment / destructive actions
- Credentials / billing / external side effects
- Product direction pivots

## Reporting mode
- milestone-only

## Stop conditions
- Done when:
- Blocked when:
- Escalate when:
EOF

write_file "harness/handoff.md" <<'EOF'
# Handoff

## Why handoff
- context reset | session change | subagent return | other:

## Current state
- repo status:
- last known good commit:
- what currently passes:
- what currently fails:

## Evidence
- key artifacts:

## Next bet
1.
2.
3.
EOF

write_file "docs/architecture.md" <<'EOF'
# Architecture rules

Define dependency direction rules that can be checked mechanically.

Example:
- types -> repo -> service -> ui
EOF

write_file "docs/quality.md" <<'EOF'
# Quality / tech debt

Track known issues, flakiness, and quality ratings.
EOF

write_file "init.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "TODO: install deps / start services / run smoke test"
EOF

chmod +x init.sh || true

mkdir -p scripts tests plans harness/contracts harness/assignments harness/qa artifacts/screenshots artifacts/traces

if [[ "$INSTALL_GUARDS" -eq 1 ]]; then
  write_file "scripts/run_drift_check.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Drift check: verify harness files exist and progress log mentions HEAD commit.
# Usage:
#   bash scripts/run_drift_check.sh [<project-root>]
#
# If <project-root> is omitted, defaults to the parent of this script (repo root).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="${1:-$DEFAULT_ROOT}"

if [[ ! -d "$ROOT" ]]; then
  echo "[FAIL] project root not found: $ROOT"
  exit 2
fi

cd "$ROOT"

req_files=("CLAUDE.md" "AGENTS.md" "features.json" "init.sh")
missing=0
for f in "${req_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "[FAIL] missing: $f"
    missing=1
  fi
done

if [[ "$missing" -eq 1 ]]; then
  exit 2
fi

if [[ ! -f "harness.json" ]]; then
  echo "[WARN] missing: harness.json (recommended: set initCommand/testCommand/e2eCommand)"
fi

if [[ ! -f "harness/goal.md" ]]; then
  echo "[WARN] missing: harness/goal.md (recommended: define final goal, non-goals, constraints, approval boundaries)"
fi

LOG_FILE=""
if [[ -f "CHANGELOG.md" ]]; then
  LOG_FILE="CHANGELOG.md"
elif [[ -f "claude-progress.txt" ]]; then
  LOG_FILE="claude-progress.txt"
else
  echo "[WARN] missing progress log: CHANGELOG.md (recommended) or claude-progress.txt"
fi

if ! python3 -c 'import json; json.load(open("features.json"))' >/dev/null 2>&1; then
  echo "[FAIL] features.json is not valid JSON"
  exit 3
fi

if [[ ! -x "init.sh" ]]; then
  echo "[WARN] init.sh not executable (recommended: chmod +x init.sh)"
fi

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")
  if [[ -n "$LOG_FILE" && -n "$HEAD_SHA" ]]; then
    if ! grep -q "$HEAD_SHA" "$LOG_FILE"; then
      echo "[WARN] $LOG_FILE does not mention HEAD commit ($HEAD_SHA). Add an entry with: commit: $HEAD_SHA"
    fi
  fi
fi

echo "[OK] drift check passed"
EOF
  chmod +x scripts/run_drift_check.sh || true

  write_file "scripts/run_change_guard.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Change guard: drift check + run best available test command.
# Usage:
#   bash scripts/run_change_guard.sh [<project-root>] [--test "<cmd>"]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="$DEFAULT_ROOT"
TEST_CMD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --test)
      TEST_CMD="${2:-}"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash scripts/run_change_guard.sh [<project-root>] [--test \"<cmd>\"]"
      exit 0
      ;;
    *)
      ROOT="$1"
      shift
      ;;
  esac
done

if [[ ! -d "$ROOT" ]]; then
  echo "[FAIL] project root not found: $ROOT"
  exit 2
fi

bash "$SCRIPT_DIR/run_drift_check.sh" "$ROOT"

cd "$ROOT"

TEST_CMD="${TEST_CMD:-}"
if [[ -z "$TEST_CMD" && -f "harness.json" ]]; then
  TEST_CMD=$(python3 - <<'PY'
import json
try:
  with open('harness.json','r',encoding='utf-8') as f:
    j=json.load(f)
  print((j.get('testCommand') or '').strip())
except Exception:
  print('')
PY
)
fi

if [[ -z "$TEST_CMD" ]]; then
  if [[ -f "package.json" ]]; then
    TEST_CMD="npm test"
  elif [[ -f "pytest.ini" || -d "tests" ]]; then
    TEST_CMD="pytest -q"
  elif [[ -f "go.mod" ]]; then
    TEST_CMD="go test ./..."
  fi
fi

if [[ -z "$TEST_CMD" ]]; then
  echo "[WARN] no testCommand found. Set harness.json:testCommand or pass --test \"<cmd>\"."
  echo "[OK] change guard (no tests run)"
  exit 0
fi

echo "[RUN] $TEST_CMD"
set +e
bash -lc "$TEST_CMD"
code=$?
set -e

if [[ "$code" -ne 0 ]]; then
  echo "[FAIL] tests failed (exit=$code)"
  exit "$code"
fi

echo "[OK] change guard passed"
EOF
  chmod +x scripts/run_change_guard.sh || true
fi

if [[ ! -f "scripts/run_drift_check.sh" ]]; then
  echo "[hint] add guard scripts: scripts/run_drift_check.sh and scripts/run_change_guard.sh"
  echo "       or re-run with --install-guards"
fi

echo "Done. Next: fill CLAUDE.md + harness/goal.md, set harness.json commands, then add a runnable test oracle."
