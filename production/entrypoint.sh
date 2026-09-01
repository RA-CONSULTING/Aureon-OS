#!/usr/bin/env bash
# Legacy production entrypoint retained only as a terminal protection preflight.
set -euo pipefail

exec /usr/local/bin/python -I -S -B \
  /aureon/app/scripts/bootstrap/protected_bootstrap_v05.py \
  --target-id production-supervisor
