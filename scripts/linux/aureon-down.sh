#!/usr/bin/env bash
# Aureon — stop the whole system (Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PATH="$ROOT/.venv/bin:$PATH"
export AUREON_ROOT="$ROOT"
export AUREON_PYTHON="$ROOT/.venv/bin/python"
export AUREON_START_SWARM=false
export AUREON_START_FRONTEND=false

if [ -S state/supervisor.sock ]; then
  if .venv/bin/supervisorctl -c deploy/supervisord.linux.conf shutdown; then
    echo "Legacy Aureon supervisor shutdown acknowledged over its checkout socket."
  else
    echo "Legacy supervisor did not acknowledge shutdown; no PID signal was sent." >&2
    exit 1
  fi
elif [ -f state/supervisord.pid ]; then
  echo "Unverified legacy PID file present; refusing to signal a potentially recycled PID." >&2
  echo "Verify process identity and ownership outside this script before manual shutdown." >&2
  exit 1
else
  echo "Aureon does not appear to be running (no supervisor socket/pid)."
fi
