#!/usr/bin/env bash
# Linux installation is disabled until the native protection boundary is approved.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP="$ROOT/scripts/bootstrap/protected_bootstrap_v05.py"

if [ ! -r "$BOOTSTRAP" ] || [ ! -x /usr/bin/python3 ]; then
  echo "Protected Linux installer bootstrap unavailable; refusing installation." >&2
  exit 1
fi

exec /usr/bin/python3 -I -S -B "$BOOTSTRAP" --target-id linux-supervisor
