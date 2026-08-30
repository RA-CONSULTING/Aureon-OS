# SaaS connection verification — is the platform working and is every connection wired?

**Date:** 2026-07-25 · **Branch:** `claude/phenolic-fingerprint-connector-lyv59v` · **Verifier:**
`aureon/saas/connection_verifier.py`

Made repeatable and honest. `python -m aureon.saas.connection_verifier` boots the operator Flask app
in-process, GETs every registered JSON route, and cross-checks the endpoints the React console calls
against the routes the operator actually serves. Read-only — it never mutates state, places a trade, or
moves money.

## Headline

**Healthy: True** — surface **37 ok · 2 honest-unavailable · 0 faults** (of 39 JSON GET routes) · parity
**36/36 console endpoints served · 0 missing**.

- A **fault** (500 / crash / HTML where JSON is due) or a **missing** endpoint (the console calls a path
  the operator does not serve) is a real problem. There are none.
- An **honest-unavailable** is a self-declared 503 for a configured-off feature — the no-fake-data policy
  working as intended, not a bug (see below).

Reproduce:

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 AUREON_AUDIT_MODE=1 \
  python -m aureon.saas.connection_verifier            # prints the table, exit 0 iff healthy
python -m aureon.saas.connection_verifier --report docs/reports/saas_connections_run.md   # durable artifact
```

## The two honest-unavailable endpoints

`/api/billing/balance` and `/api/billing/usage` return **503 — "tenancy bridge disabled
(AUREON_SUPABASE_JWT_SECRET unset)"**. Multi-tenant billing needs a Supabase bridge that is not
configured in a bare/offline deploy. `/api/billing/status` reports this truthfully
(`configured: false`, `tenancy_bridge: off`, `missing_env: [SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]`).
This is degradation-by-design, surfaced honestly — never a fabricated balance.

## Frontend ↔ backend parity

Every endpoint the current console (`frontend/src/shell/`, 29 paths incl. the `POST /api/cognition/reason`
and health probes) **and** the legacy trading console (`frontend/src/App.tsx` + `components/`, 7 paths)
calls now resolves on the one operator gateway.

### Legacy endpoints wired this pass (`aureon/operator/legacy_runtime_api.py`)

Previously these 7 lived only on a standalone status server (`unified_market_status_server` on
`127.0.0.1:8790`), so through the operator they 404'd. They now mount on the gateway — read-only or
notify-only, serving **real state or an explicit unavailable, never a fabricated value**:

| endpoint | backing | honest behavior offline |
|:---|:---|:---|
| `GET /api/terminal-state` | `unified_market_status_server._read_status()` | `ok` + booting/stale payload when the trader hasn't written `state/unified_runtime_status.json` |
| `GET /api/flight-test` | `._flight_test()` | real `checks` + `reboot_advice`, computed from state |
| `GET /api/reboot-advice` | same flight-test payload | console reads its `reboot_advice` sub-object |
| `GET /api/env-credentials` | `._env_credentials_status()` | masked presence only — `secret_policy: metadata_only_no_values_returned` |
| `GET /api/bots` | (no per-bot log-tail source wired) | `{ "bots": [] }` — console renders "No bots reporting yet.", never invented tails |
| `GET /api/trades` | (no symbol-keyed trade source) | `{ "trades": {} }` — never `mock: true` with fabricated trades |
| `POST /api/notifications/telegram` | real Telegram Bot API when `TELEGRAM_BOT_TOKEN`/chat present | else `503 { ok: false, reason: "telegram not configured" }` — never a faked send |

> Note (honest divergence): the SaaS gateway serves `/api/status` as **platform health**; the legacy
> `StatusPanel` component historically expected a trading-balance shape at the same path. The route is
> served (parity counts it), and the current shell console consumes the platform-health shape — the
> legacy component's shape mismatch is flagged here, not silently "fixed".

## What backs this

- Verifier: `aureon/saas/connection_verifier.py` — `verify_surface` (route sweep + classify),
  `verify_frontend_parity` (console-vs-registered cross-check), `verify_all`, a durable report writer, and
  the `python -m` CLI (exit non-zero only on faults / missing endpoints).
- Tests: `tests/test_saas_connection_verifier.py` (no faults · parity all-served · byte-identical report ·
  CLI exit 0) and `tests/test_legacy_runtime_api.py` (each legacy endpoint resolves honestly, no raw
  secrets, empty-not-fabricated bots/trades, honest telegram 503).
- Registration: `register_legacy_runtime_routes(app)` in `aureon/operator/operator_server.py:create_app`,
  guarded like every other `register_*` mount (a wiring failure logs a warning; the operator still serves).
