#!/usr/bin/env bash
# Remote deployment is disabled until the native protection boundary is approved.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BOOTSTRAP="$REPO_ROOT/scripts/bootstrap/protected_bootstrap_v05.py"

if [ ! -r "$BOOTSTRAP" ] || [ ! -x /usr/bin/python3 ]; then
  echo "Protected deployment bootstrap unavailable; refusing remote mutation." >&2
  exit 1
fi

exec /usr/bin/python3 -I -S -B "$BOOTSTRAP" --target-id linux-supervisor
