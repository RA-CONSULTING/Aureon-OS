#!/usr/bin/env bash
# Canonical Aureon launcher for Linux and macOS. Trading follows exchange keys in .env.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" -m aureon.launch.master "$@"
