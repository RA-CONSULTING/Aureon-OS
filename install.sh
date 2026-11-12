#!/usr/bin/env bash
# Boot Aureon OS locally: operator API, HNC/Auris/QGITA, public MCP, dashboard.
# Does not read .env. Does not call an external language-model API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (3.11 or newer)." >&2
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(
        f"python {sys.version_info.major}.{sys.version_info.minor} is too old; 3.11 or newer is required"
    )
PY

if [[ "${1:-}" == "--stop" ]]; then
  if [[ ! -x .venv/bin/python ]]; then
    echo "No .venv yet. Nothing to stop." >&2
    exit 1
  fi
  exec .venv/bin/python scripts/plug_and_play.py --stop
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required for the dashboard (Node 20 or newer)." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  if ! python3 -m venv .venv; then
    echo "Could not create .venv. On Debian/Ubuntu: sudo apt-get install python3-venv" >&2
    exit 1
  fi
fi

# Order safety defaults. An evaluator who later adds exchange keys
# still gets no orders unless they deliberately flip these switches.
export AUREON_LIVE_TRADING=0
export AUREON_DISABLE_REAL_ORDERS=1
export AUREON_DISABLE_EXCHANGE_MUTATIONS=1

# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-plug.lock

if [[ ! -x frontend/node_modules/.bin/vite ]]; then
  npm ci --ignore-scripts --prefix frontend
fi

exec python scripts/plug_and_play.py "$@"
