#!/usr/bin/env bash
# Aureon + Flameborn unified runtime boundary: terminal HOLD.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
BOOTSTRAP="$ROOT/scripts/bootstrap/protected_bootstrap_v05.py"

if [[ ! -x "$PYTHON" || ! -r "$BOOTSTRAP" ]]; then
  echo "Protected Flameborn bootstrap unavailable; refusing startup." >&2
  exit 1
fi

exec "$PYTHON" -I -S -B "$BOOTSTRAP" --target-id flameborn-runtime
