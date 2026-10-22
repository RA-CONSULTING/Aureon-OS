#!/usr/bin/env bash
set -euo pipefail

# Helper to manage large artifacts via GitHub Releases
# Usage:
#   ./scripts/artifacts.sh download   # download release assets into artifacts/
#   ./scripts/artifacts.sh upload     # upload local artifacts to release v1.0-artifacts
#
RELEASE_TAG=${RELEASE_TAG:-v1.0-artifacts}
REPO=${REPO:-RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-}
ARTIFACT_DIR=${ARTIFACT_DIR:-artifacts}

function ensure_gh() {
  if ! command -v gh >/dev/null; then
    echo "gh CLI not found. Install from https://cli.github.com/" >&2
    exit 1
  fi
}

function download() {
  ensure_gh
  mkdir -p "$ARTIFACT_DIR"
  echo "Downloading release $RELEASE_TAG to $ARTIFACT_DIR..."
  gh release download "$RELEASE_TAG" --repo "$REPO" -D "$ARTIFACT_DIR"
  echo "Done. Files are in $ARTIFACT_DIR"
}

function upload() {
  ensure_gh
  if [ ! -d "$ARTIFACT_DIR" ]; then
    echo "No $ARTIFACT_DIR directory found. Place files to upload there." >&2
    exit 1
  fi

  echo "Creating release $RELEASE_TAG (if missing) and uploading assets..."
  gh release create "$RELEASE_TAG" --repo "$REPO" --title "$RELEASE_TAG" --notes "AUREON large artifacts" || true

  for f in "$ARTIFACT_DIR"/*; do
    [ -e "$f" ] || continue
    echo "Uploading $f..."
    gh release upload "$RELEASE_TAG" "$f" --repo "$REPO" --clobber
  done

  echo "Upload complete. Release: https://github.com/${REPO}/releases/tag/${RELEASE_TAG}"
}

case ${1-} in
  download)
    download
    ;;
  upload)
    upload
    ;;
  *)
    echo "Usage: $0 {download|upload}"
    exit 2
    ;;
esac
