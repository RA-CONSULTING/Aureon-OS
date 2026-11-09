#!/usr/bin/env bash
# Canonical Aureon launcher for Linux and macOS. Trading follows exchange keys in .env.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"

# One user scope for the whole session. Children that call setsid or setpgid
# stay in that scope. --stop and --status stay outside and tear the scope down.
# When the user manager is absent, master.py creates a cgroup or walks the pid tree.
if [[ "${1:-}" != "--stop" && "${1:-}" != "--status" && -z "${AUREON_LAUNCHER_INSIDE_SCOPE:-}" ]]; then
  if command -v systemd-run >/dev/null 2>&1; then
    unit="aureon-launcher-$$"
    if systemd-run --user --scope --collect --quiet --unit="${unit}-probe" -- true >/dev/null 2>&1; then
      export AUREON_LAUNCHER_SCOPE="$unit"
      export AUREON_LAUNCHER_INSIDE_SCOPE=1
      exec systemd-run --user --scope --collect --quiet --unit="$unit" -- \
        env AUREON_LAUNCHER_SCOPE="$unit" AUREON_LAUNCHER_INSIDE_SCOPE=1 \
        "$PYTHON" -m aureon.launch.master "$@"
    fi
  fi
fi

exec "$PYTHON" -m aureon.launch.master "$@"
