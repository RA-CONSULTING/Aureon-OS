#!/usr/bin/env bash
# Aureon — show process + health status (Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PATH="$ROOT/.venv/bin:$PATH"
export AUREON_ROOT="$ROOT"
export AUREON_PYTHON="$ROOT/.venv/bin/python"
export AUREON_START_SWARM=false
export AUREON_START_FRONTEND=false

echo "── legacy supervisor processes (not protection evidence) ──"
if [ -S state/supervisor.sock ]; then
  .venv/bin/supervisorctl -c deploy/supervisord.linux.conf status || true
else
  echo "supervisor not running (no state/supervisor.sock)"
fi
