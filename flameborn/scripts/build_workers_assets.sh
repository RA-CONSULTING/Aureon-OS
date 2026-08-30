#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist-workers"
SOURCE_DIR="$PROJECT_DIR/cloudflare-ui"
STAGE_DIR="$(mktemp -d "$PROJECT_DIR/.dist-workers.XXXXXX")"

cleanup() {
  rm -rf -- "$STAGE_DIR"
}
trap cleanup EXIT

for file in index.html app.js style.css _headers .assetsignore; do
  if [[ ! -f "$SOURCE_DIR/$file" ]]; then
    echo "Missing Cloudflare UI asset: $SOURCE_DIR/$file" >&2
    exit 1
  fi
  cp "$SOURCE_DIR/$file" "$STAGE_DIR/$file"
done

if [[ "$DIST_DIR" != "$PROJECT_DIR/dist-workers" ]]; then
  echo "Refusing unexpected asset output path: $DIST_DIR" >&2
  exit 1
fi
rm -rf -- "$DIST_DIR"
mv "$STAGE_DIR" "$DIST_DIR"
trap - EXIT

echo "Zbudowano assets do: $DIST_DIR"
