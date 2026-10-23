#!/usr/bin/env bash
# Existing Aureon installer for Linux and macOS. Safe to re-run.
# Installs the toolchain it can, writes .env once, and starts the preflight UI.
# Live trading stays off. This script does not place an order.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UI_PORT="${AUREON_UI_PORT:-8080}"
UI_URL="http://127.0.0.1:${UI_PORT}/"
export AUREON_LIVE_TRADING=0
export AUREON_SIMULATED_BOOT=0
export AUREON_UI_PORT="$UI_PORT"
export AUREON_UI_URL="$UI_URL"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

have() { command -v "$1" >/dev/null 2>&1; }

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif have sudo; then
    sudo -n "$@"
  else
    return 1
  fi
}

install_system() {
  if have apt-get; then
    local pkgs=()
    if ! have python3 || ! python3 -c "import venv, ssl" >/dev/null 2>&1; then
      pkgs+=(python3 python3-venv python3-pip ca-certificates)
    fi
    have git || pkgs+=(git)
    have curl || pkgs+=(curl)
    if [ "${#pkgs[@]}" -eq 0 ]; then
      echo "system toolchain already present"
      return 0
    fi
    as_root apt-get update
    DEBIAN_FRONTEND=noninteractive as_root apt-get install -y "${pkgs[@]}"
  elif have dnf; then
    as_root dnf install -y python3 python3-pip git curl || echo "dnf install skipped"
  elif [ "$(uname -s)" = "Darwin" ] && have brew; then
    have python3 || brew install python
    have git || brew install git
    have curl || brew install curl
  else
    echo "No apt-get, dnf, or Homebrew. Using the Python already on PATH."
  fi
}

ensure_venv() {
  if [ ! -x "$ROOT/.venv/bin/python" ]; then
    python3 -m venv "$ROOT/.venv"
  fi
  PY="$ROOT/.venv/bin/python"
  "$PY" -m pip install --disable-pip-version-check -q \
    'aiohttp>=3.9' 'websocket-client>=1.6' 'requests>=2.32' 'python-dotenv>=1.0' 'rich>=13.7'
}

ensure_env() {
  if [ ! -f "$ROOT/.env" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    printf '\nAUREON_LIVE_TRADING=0\nAUREON_SIMULATED_BOOT=0\n' >> "$ROOT/.env"
    echo "wrote .env from .env.example with live trading left off"
  else
    echo ".env already present; installer left it unchanged"
  fi
}

wait_for_ui() {
  echo "Aureon UI: ${UI_URL}"
  "$PY" - <<'PY'
import os
import sys
import time
import urllib.request

url = os.environ["AUREON_UI_URL"]
for _ in range(45):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            status = getattr(resp, "status", 200)
            if 200 <= status < 300:
                print(f"Aureon UI is reachable: {url} (HTTP 200)")
                raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:
        time.sleep(2)
print(f"Aureon UI did not answer at {url}", file=sys.stderr)
raise SystemExit(1)
PY
}

install_system
if ! have python3; then
  echo "Python 3 is required." >&2
  exit 1
fi
ensure_venv
ensure_env

"$PY" -m aureon.autonomous.aureon_master_launcher --preflight &
launcher_pid=$!
cleanup() {
  kill "$launcher_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
wait_for_ui
wait "$launcher_pid"
