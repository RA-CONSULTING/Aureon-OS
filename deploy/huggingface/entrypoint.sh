#!/usr/bin/env bash
# Aureon OS public Space: guarded, paper-only, read-only at the public edge.
set -euo pipefail
umask 077

ROOT=/app/aureon-os
RT=$ROOT/runtime
mkdir -p \
  "$RT/logs" "$RT/nginx" "$RT/pgsock" "$RT/pgdata" "$RT/home" \
  "$RT/fusion-state" "$RT/sero-home" "$RT/state" "$RT/model" "$RT/hf-home"
chmod -R u+rwX "$RT"

export SERO_WORKSPACE=$ROOT
export PYTHONPATH=$ROOT
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export HOME=$RT/home

# Public-release invariants are unconditional. Space variables or secrets cannot
# arm exchange activity, local actions, billing, self-repair, or a provider fallback.
export AUREON_PUBLIC_READ_ONLY=1
export AUREON_LIVE_TRADING=0
export AUREON_FUSION_ARM_LIVE=""
export AUREON_DISABLE_REAL_ORDERS=1
export AUREON_DISABLE_EXCHANGE_MUTATIONS=1
export AUREON_ORDER_INTENT_PUBLISH=0
export AUREON_AUTONOMY_MODE=guarded
export AUREON_DEPLOYMENT_HOLD=1
export AUREON_OPERATOR_ALLOW_LIVE=""
export AUREON_LOCAL_ACTIONS_ARMED=0
export AUREON_UNIFIED_ORDER_EXECUTOR=0
export AUREON_DRY_RUN=1
export DRY_RUN=1
export AUREON_CODE_AUTO_APPROVE=0
export AUREON_SOUL_ACT=0
export AUREON_BILLING_CHARGE_ENABLED=0
export AUREON_BILLING_METERING_ENABLED=0
export AUREON_SOVEREIGN_MODE=0
export AUREON_ACCEPT_LIVE_RISK=0
export AUREON_ENABLE_AUTONOMOUS_CONTROL=0
export AUREON_ACTIVATE_ON_IMPORT=0
export AUREON_DISABLE_LIVE_BACKGROUND_STARTUP=1
export AUREON_WRITE_STATIC_MANIFESTS=0
export AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1
export AUREON_AUDIT_MODE=1
export PYTHON_DOTENV_DISABLED=1
export AUREON_ENV_FILE=/dev/null
export DOTENV_PATH=/dev/null

# Never inherit exchange, provider, session, or Hub credentials into the demo.
unset \
  KRAKEN_API_KEY KRAKEN_API_SECRET KRAKEN_PRIVATE_KEY KRAKEN_SECRET \
  BINANCE_API_KEY BINANCE_API_SECRET BINANCE_SECRET_KEY BINANCE_KEY BINANCE_SECRET \
  ALPACA_API_KEY ALPACA_SECRET_KEY ALPACA_API_SECRET ALPACA_KEY ALPACA_SECRET \
  APCA_API_KEY_ID APCA_API_SECRET_KEY \
  CAPITAL_API_KEY CAPITAL_IDENTIFIER CAPITAL_PASSWORD CAPITAL_EMAIL CAPITAL_USER \
  CAPITAL_API_PASSWORD CAPITAL_API_SECRET \
  COINBASE_API_KEY COINBASE_API_SECRET COINAPI_API_KEY COINAPI_KEY \
  COINGECKO_API_KEY FRED_API_KEY FMP_API_KEY NASA_API_KEY FIRMS_MAP_KEY \
  NOAA_API_KEY USGS_API_KEY ETHERSCAN_API_KEY ALCHEMY_API_KEY COVALENT_API_KEY \
  GLASSNODE_API_KEY UNUSUAL_WHALES_API_KEY WORLD_NEWS_API_KEY \
  OPENAI_API_KEY XAI_API_KEY GEMINI_API_KEY ANTHROPIC_API_KEY \
  DEEPSEEK_API_KEY MISTRAL_API_KEY GROQ_API_KEY OPENROUTER_API_KEY PERPLEXITY_API_KEY \
  OLLAMA_API_KEY AUREON_OLLAMA_API_KEY AUREON_LLM_API_KEY AUREON_OWN_LLM_API_KEY \
  QUICKBOOKS_CLIENT_ID QUICKBOOKS_CLIENT_SECRET QUICKBOOKS_AUTH_CODE \
  QUICKBOOKS_RETURNED_STATE QUICKBOOKS_EXPECTED_STATE QUICKBOOKS_REALM_ID \
  QUICKBOOKS_CLIENT_CREDENTIAL_VAULT QUICKBOOKS_TOKEN_VAULT \
  TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID MASTER_ENCRYPTION_KEY AUREON_MASTER_ENCRYPTION_KEY \
  AUREON_ACCOUNTING_APPROVAL_HMAC_KEY AUREON_INGEST_TOKEN INGEST_TOKEN \
  AUREON_HNC_PACKET_MASTER_KEY AUREON_HNC_PACKET_LEGACY_MASTER_KEY \
  AUREON_SUPABASE_JWT_SECRET SUPABASE_SERVICE_ROLE_KEY \
  HF_TOKEN HUGGING_FACE_HUB_TOKEN

# Own-model-only routing. Audit mode suppresses import side effects; this explicit
# allowance permits only the adapter's strict literal-loopback HTTP transport.
export AUREON_MODEL_REPOSITORY=GaryLeckey/aureon-7b
export AUREON_MODEL_DIR=$RT/model
export AUREON_MODEL_EXPECTED_SHA256=48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb
export AUREON_OWN_LLM_BASE_URL=http://127.0.0.1:11435/v1
export AUREON_OWN_LLM_MODEL=aureon-7b-v65k
export AUREON_LLM_BASE_URL=$AUREON_OWN_LLM_BASE_URL
export AUREON_LLM_MODEL=$AUREON_OWN_LLM_MODEL
export AUREON_EXTERNAL_LLM_FALLBACK=none
export AUREON_COGNITION_PREFER_LOCAL=1
export AUREON_LLM_OFFLINE=0
export AUREON_DISABLE_LLM_HTTP=0
export AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1
export AUREON_LLM_PREFER_NATIVE=0
export AUREON_LLM_SKIP_PROBE=0
export AUREON_LLM_HEALTH_TIMEOUT_S=5
export AUREON_LLM_PROBE_TIMEOUT_S=120
export AUREON_LLM_REQUEST_TIMEOUT_S=600
export AUREON_OPERATOR_WAIT_OWN_MODEL=1
export AUREON_OWN_MODEL_STARTUP_TIMEOUT_S=1800
export HF_HOME=$RT/hf-home
export TOKENIZERS_PARALLELISM=false

if [[ ! "${AUREON_MODEL_REVISION:-}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[entrypoint] AUREON_MODEL_REVISION must be the full lowercase GaryLeckey/aureon-7b Hub commit" >&2
  exit 1
fi

# Operator gateway: production authentication remains in force behind nginx.
# nginx injects these random per-boot values only into reviewed internal reads.
export AUREON_OPERATOR_HOST=127.0.0.1
export AUREON_OPERATOR_PORT=8790
export AUREON_OPERATOR_ENV=production
export AUREON_OPERATOR_RATE_RPS=2
export AUREON_OPERATOR_RATE_BURST=4
export AUREON_OPERATOR_MAX_BODY=16384
export AUREON_OPERATOR_TRUSTED_PROXY_CIDRS=127.0.0.0/8
export AUREON_OPERATOR_HTTP_PROCESSES=1
export AUREON_OPERATOR_REPLICAS=1
export AUREON_OPERATOR_THREADS=4
export AUREON_OPERATOR_TIMEOUT_S=600
export AUREON_OPERATOR_MAX_RETRIES=0
export AUREON_OPERATOR_MAX_TOKENS=64
export AUREON_OPERATOR_TEMPERATURE=0
export AUREON_OPERATOR_MAX_WORKERS=1
AUREON_OPERATOR_API_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
export AUREON_OPERATOR_API_KEY

# Fusion APIs are also loopback-only. Only their status read is exposed.
export AUREON_FUSION_BIND=127.0.0.1
AUREON_FUSION_API_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
export AUREON_FUSION_API_TOKEN
export AUREON_FUSION_RATE_LIMIT=120
export AUREON_FUSION_RATE_WINDOW_S=60
export AUREON_FUSION_CACHE_TTL_S=30
export AUREON_REDIS_URL=redis://127.0.0.1:6379/0
export AUREON_ERROR_WEBHOOK_URL=http://127.0.0.1:8088/envelope
export AUREON_ERROR_SINK_BIND=127.0.0.1
export AUREON_ERROR_SINK_PORT=8088
export AUREON_ERROR_SINK_PATH=$RT/logs/errors.jsonl

# Shared runtime paths. Fusion authority state is never read from the checkout.
export AUREON_RUNTIME_DIR=$RT
export AUREON_PGSOCK=$RT/pgsock
export SERO_RUNTIME_HOME=$RT/sero-home
export SERO_STATE_ROOT=$RT/state
export SERO_FUSION_STATE=$RT/fusion-state
export AUREON_FUSION_ORGAN_ALLOWLIST=hnc_core

# A restart must not consume an approval artifact left by an earlier process.
rm -f -- \
  "$SERO_FUSION_STATE/capital_release.flag" \
  "$SERO_FUSION_STATE/queen_mind_restart_approved.json"

# Postgres is local-only and uses the supported selfhost schema.
export PGDATA=$RT/pgdata
export PGPORT=5433
export PGHOST=127.0.0.1
PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort | tail -1 || true)
export AUREON_PG_BIN="$PG_BIN"
if [ -z "$PG_BIN" ]; then
  echo "[entrypoint] required postgres binaries are absent" >&2
  exit 1
fi
export PATH="$PG_BIN:$PATH"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  echo "[entrypoint] initdb at $PGDATA"
  initdb -U postgres -A trust >/dev/null
  chmod 775 "$RT/pgsock"
fi
(
  for _ in $(seq 1 90); do
    pg_isready -h "$PGHOST" -p "$PGPORT" -U postgres >/dev/null 2>&1 && break
    sleep 2
  done
  if [ ! -f "$RT/pg_schema_applied" ] && pg_isready -h "$PGHOST" -p "$PGPORT" -U postgres >/dev/null 2>&1; then
    psql -h "$PGHOST" -p "$PGPORT" -U postgres -c "SELECT 1" >/dev/null
    createdb -h "$PGHOST" -p "$PGPORT" -U postgres aureon 2>/dev/null || true
    psql -h "$PGHOST" -p "$PGPORT" -U postgres -d aureon -v ON_ERROR_STOP=1 \
      -f "$ROOT/deploy/selfhost/postgres/01_roles.sql"
    psql -h "$PGHOST" -p "$PGPORT" -U postgres -d aureon -v ON_ERROR_STOP=1 \
      -f "$ROOT/deploy/selfhost/postgres/02_tables.sql"
    psql -h "$PGHOST" -p "$PGPORT" -U postgres -d aureon -v ON_ERROR_STOP=1 \
      -f "$ROOT/supabase/migrations/20260811210525_lock_down_legacy_public_tables.sql"
    touch "$RT/pg_schema_applied"
    echo "[entrypoint] postgres schema applied (roles, tables, RLS lockdown)"
  fi
) &

for d in logs unified_logs hnc_daemon_logs; do
  mkdir -p "$SERO_STATE_ROOT/$d"
  chmod -R u+rwX "$SERO_STATE_ROOT/$d"
done

# Render only random per-boot internal bearer values. No value is logged.
python3 - <<'PY'
import os
from pathlib import Path
src = Path("/app/aureon-os/deploy/huggingface/nginx.conf")
dst = Path(os.environ["AUREON_RUNTIME_DIR"]) / "nginx.conf"
text = src.read_text(encoding="utf-8")
text = text.replace("__AUREON_OPERATOR_KEY__", os.environ["AUREON_OPERATOR_API_KEY"])
text = text.replace("__AUREON_FUSION_TOKEN__", os.environ["AUREON_FUSION_API_TOKEN"])
dst.write_text(text, encoding="utf-8")
print("[entrypoint] rendered runtime/nginx.conf with per-boot internal credentials")
PY

echo "[entrypoint] handing off to supervisord; /healthz is liveness and /readyz is strict"
exec /usr/bin/supervisord -c "$ROOT/deploy/huggingface/supervisord.conf"
