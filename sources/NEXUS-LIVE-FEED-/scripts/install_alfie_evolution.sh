#!/usr/bin/env bash
set -euo pipefail

ZIP_PATH="${1:-ALFIE_Evolution_v1.zip}"
DEST_DIR="${2:-ALFIE_Runtime}"

python3 "$(dirname "$0")/install_alfie_evolution.py" --zip "$ZIP_PATH" --dest "$DEST_DIR" "${@:3}"
