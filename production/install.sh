#!/usr/bin/env bash
# Existing Aureon installer for Linux and macOS. Safe to re-run.
# Installs the toolchain it can, builds the UI, writes .env once, then
# starts the organism through scripts/launch/aureon-master.sh.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
UI_URL="http://127.0.0.1:5173/"

say() {
  printf '%s\n' "$*"
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo "$@"
  else
    say "Need root or passwordless sudo to install system packages." >&2
    return 1
  fi
}

have() {
  command -v "$1" >/dev/null 2>&1
}

install_apt() {
  pkgs=""
  if ! have python3 || ! python3 -c "import venv, ssl" >/dev/null 2>&1; then
    pkgs="$pkgs python3 python3-venv python3-pip ca-certificates"
  fi
  have node || pkgs="$pkgs nodejs"
  have npm || pkgs="$pkgs npm"
  have git || pkgs="$pkgs git"
  have curl || pkgs="$pkgs curl"
  if [ -z "$pkgs" ]; then
    say "system toolchain already present"
    return 0
  fi
  say "installing system packages:${pkgs}"
  as_root apt-get update
  # shellcheck disable=SC2086
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y $pkgs
}

install_dnf() {
  pkgs=""
  have python3 || pkgs="$pkgs python3 python3-pip"
  have node || pkgs="$pkgs nodejs"
  have npm || pkgs="$pkgs npm"
  have git || pkgs="$pkgs git"
  have curl || pkgs="$pkgs curl"
  if [ -z "$pkgs" ]; then
    say "system toolchain already present"
    return 0
  fi
  say "installing system packages:${pkgs}"
  # shellcheck disable=SC2086
  as_root dnf install -y $pkgs
}

install_brew() {
  if ! have brew; then
    say "Homebrew is not installed. Using python3, node, and npm if they are already on PATH."
    return 0
  fi
  have python3 || brew install python
  have node || brew install node
  have git || brew install git
  have curl || brew install curl
}

install_system() {
  os="$(uname -s)"
  if [ "$os" = "Darwin" ]; then
    install_brew
    return 0
  fi
  if have apt-get; then
    install_apt
    return 0
  fi
  if have dnf; then
    install_dnf
    return 0
  fi
  say "No apt-get, dnf, or Homebrew. Using the toolchain already on PATH."
}

ensure_env() {
  # Writes .env from .env.example when .env is absent. An existing file is kept.
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  export AUREON_INSTALL_ROOT="$ROOT"
  python3 -c 'import os, sys
from pathlib import Path
from aureon.launch.master import _ensure_local_env
ok, detail = _ensure_local_env(Path(os.environ["AUREON_INSTALL_ROOT"]))
print(detail)
sys.exit(0 if ok else 1)'
}

ensure_frontend() {
  if ! have node || ! have npm; then
    say "node and npm are still not on PATH after the toolchain step." >&2
    return 1
  fi
  (
    cd "$ROOT/frontend"
    if [ ! -f node_modules/vite/bin/vite.js ]; then
      npm install --no-audit --no-fund
    else
      say "frontend packages already present"
    fi
    npm run build
  )
}

docker_note() {
  if have docker && docker info >/dev/null 2>&1; then
    say "docker daemon is available; the launcher will pull and build images"
  else
    say "docker daemon is not available; the launcher will use native fallbacks"
  fi
}

wait_for_ui() {
  say "Aureon UI: ${UI_URL}"
  python3 -c 'import os, sys, time, urllib.request
url = os.environ["AUREON_UI_URL"]
for _ in range(45):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                print("Aureon UI is reachable: %s (HTTP 200)" % url)
                sys.exit(0)
    except Exception:
        time.sleep(2)
print("Aureon UI did not answer at %s" % url, file=sys.stderr)
sys.exit(1)'
}

install_system
have python3 || { say "python3 is not on PATH." >&2; exit 1; }
ensure_env
ensure_frontend
docker_note
export SERO_WORKSPACE="$ROOT"
export AUREON_UI_URL="$UI_URL"
bash "$ROOT/scripts/launch/aureon-master.sh"
wait_for_ui
