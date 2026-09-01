#!/usr/bin/env bash
# Integration health cannot be asserted before protected runtime admission.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
PYTHON_EXE="$REPO_ROOT/.venv/bin/python"
BOOTSTRAP="$REPO_ROOT/scripts/bootstrap/protected_bootstrap_v05.py"

if [[ ! -x "$PYTHON_EXE" || ! -r "$BOOTSTRAP" ]]; then
  echo "Fixed protected integration bootstrap unavailable; refusing health claim." >&2
  exit 1
fi

exec "$PYTHON_EXE" -I -S -B "$BOOTSTRAP" --target-id flameborn-runtime
