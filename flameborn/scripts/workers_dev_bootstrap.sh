#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
DO_DEPLOY="${1:-}"

case "$DO_DEPLOY" in
  ""|"--deploy") ;;
  *)
    echo "Usage: bash scripts/workers_dev_bootstrap.sh [--deploy]"
    exit 64
    ;;
esac

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "Missing CLOUDFLARE_API_TOKEN in the process environment or private .env file."
  exit 1
fi

if [[ "$DO_DEPLOY" == "--deploy" ]]; then
  # Deliberately before npm, Wrangler authentication, or deployment.
  # Values are validated without printing, generating, or persisting secrets.
  node "$PROJECT_DIR/scripts/validate_workers_deploy_config.mjs" "$PROJECT_DIR/wrangler.jsonc"
fi

cd "$PROJECT_DIR"

echo "Instaluję zależności npm..."
npm install

echo "Buduję assets dla Workers..."
npm run cf:build

echo "Sprawdzam autoryzację Wrangler..."
if ! npx wrangler whoami; then
  echo
  echo "Wrangler authentication is incomplete; refusing to continue."
  echo "CLOUDFLARE_ACCOUNT_ID alone does not replace valid authentication."
  exit 2
fi

if [[ "$DO_DEPLOY" == "--deploy" ]]; then
  echo "Wdrażam na workers.dev..."
  npm run cf:deploy
else
  echo "Bootstrap gotowy. Aby wdrożyć, uruchom:"
  echo "  bash scripts/workers_dev_bootstrap.sh --deploy"
fi
