#!/usr/bin/env bash
# Canonical Aureon launcher for Linux and macOS. Trading follows exchange keys in .env.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
# aureon.launch.master opens one containment unit and --stop tears it down.
exec "$PYTHON" -m aureon.launch.master "$@"
