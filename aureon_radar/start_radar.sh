#!/usr/bin/env bash
# Thin wrapper. The canonical entry is python -m aureon.launch.master.
# This file does not copy .env and does not arm live trading.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" -m aureon.launch.master "$@"
