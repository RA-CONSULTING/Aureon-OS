#!/usr/bin/env bash
# Aureon production installer boundary: terminal HOLD.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
BOOTSTRAP="$ROOT/scripts/bootstrap/protected_bootstrap_v05.py"

if [[ ! -x "$PYTHON" || ! -r "$BOOTSTRAP" ]]; then
  echo "Aureon protected installer boundary is unavailable; refusing installation." >&2
  exit 1
fi

echo "Aureon installation and release are on terminal protection HOLD." >&2
exec "$PYTHON" -I -S -B "$BOOTSTRAP" --target-id production-supervisor
