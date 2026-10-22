#!/bin/bash
set -euo pipefail

# Unified production entrypoint.
# Defaults to dry-run unless `AUREON_LIVE_TRADING=1` or `--live` is passed.

cd "$(dirname "$0")/.."

exec python -u aureon_master_launcher.py --production "$@"

