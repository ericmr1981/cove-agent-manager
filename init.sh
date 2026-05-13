#!/usr/bin/env bash
set -euo pipefail

echo "[cove] Initializing environment..."

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'; print('[ok] Python', sys.version)"

# Check Docker
if command -v docker &>/dev/null; then
  echo "[ok] Docker found: $(docker --version)"
else
  echo "[warn] Docker not found. Sandbox features will be unavailable."
fi

# Check PostgreSQL
if command -v psql &>/dev/null; then
  echo "[ok] psql found"
else
  echo "[warn] psql not found (expected if using Docker PostgreSQL)"
fi

# Create directories
mkdir -p artifacts/logs artifacts/traces

echo "[cove] Environment ready."
echo "[cove] Next: install deps with 'pip install -e .' (after pyproject.toml is ready)"
