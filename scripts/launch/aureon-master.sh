#!/usr/bin/env bash
# Canonical Aureon launcher for Linux. Live trading is not armed here.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" -m aureon.launch.master "$@"
