# Aureon SaaS Integration Readiness

Current tracked snapshot: 2026-07-13.

This document turns the repo-wide sitemap into a SaaS integration checklist. It
identifies source surfaces, end-user access paths, environment variables, auth
boundaries, generated artifacts, and production gates that must stay visible for
safe integration.

Primary map: [`REPO_SITEMAP.md`](REPO_SITEMAP.md). Machine-readable map:
[`repo_sitemap.json`](repo_sitemap.json).
Machine-readable SaaS integration manifest:
[`saas_integration_manifest.json`](saas_integration_manifest.json), mirrored to
[`../frontend/public/aureon_saas_integration_manifest.json`](../frontend/public/aureon_saas_integration_manifest.json).
Supabase hardening review:
[`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md), with generated
manifest [`supabase_hardening_manifest.json`](supabase_hardening_manifest.json)
mirrored to
[`../frontend/public/aureon_supabase_hardening_manifest.json`](../frontend/public/aureon_supabase_hardening_manifest.json).
Autonomous frontend manifests are mounted as public, audit-backed JSON for the
operator console: SaaS inventory, frontend unification plan, frontend evolution
queue, organism runtime status, and autonomous capability switchboard.
End-user task map: [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md).
Frontend console route: `#repo-map`, implemented by
[`../frontend/src/components/RepoNavigationPanel.tsx`](../frontend/src/components/RepoNavigationPanel.tsx).
File-level navigation index:
[`repo_navigation_index.json`](repo_navigation_index.json), mirrored to
[`../frontend/public/aureon_repo_navigation_index.json`](../frontend/public/aureon_repo_navigation_index.json).
Directory organization tree:
[`repo_organization_tree.json`](repo_organization_tree.json), mirrored to
[`../frontend/public/aureon_repo_organization_tree.json`](../frontend/public/aureon_repo_organization_tree.json).
Navigation readiness audit:
[`repo_navigation_readiness.json`](repo_navigation_readiness.json), mirrored to
[`../frontend/public/aureon_repo_navigation_readiness.json`](../frontend/public/aureon_repo_navigation_readiness.json).
Capability access matrix:
[`capability_access_matrix.json`](capability_access_matrix.json), mirrored to
[`../frontend/public/aureon_capability_access_matrix.json`](../frontend/public/aureon_capability_access_matrix.json).
System integration map:
[`SYSTEM_INTEGRATION_MAP.md`](SYSTEM_INTEGRATION_MAP.md), with generated
manifest [`system_integration_map.json`](system_integration_map.json) mirrored to
[`../frontend/public/aureon_system_integration_map.json`](../frontend/public/aureon_system_integration_map.json).
Capability registry:
[`CAPABILITY_REGISTRY.md`](CAPABILITY_REGISTRY.md), with generated registry
[`capability_registry.json`](capability_registry.json) mirrored to
[`../frontend/public/aureon_capability_registry.json`](../frontend/public/aureon_capability_registry.json).
Manifest generation and validation, from repo root:
`python scripts/validation/generate_repo_navigation_index.py`, then
`python scripts/validation/generate_saas_integration_manifest.py`, then
`python scripts/validation/generate_supabase_hardening_manifest.py`, then
`python scripts/validation/generate_system_integration_map.py`, then
`python scripts/validation/generate_capability_registry.py`, then
`python scripts/validation/generate_repo_navigation_readiness.py`, then
`python scripts/validation/validate_repo_navigation_contract.py`.

## Canonical Integration Shape

Use this shape when turning the repo into a product or SaaS workflow:

```text
End user
  -> frontend/ React/Vite console
  -> public/static artifacts and generated frontend mirrors
  -> Supabase functions, migrations, and auth-gated data plane
  -> local or hosted Aureon runtime connector
  -> operator-controlled live-action routes
  -> evidence ledgers, audit files, and generated state
```

The safest current product posture is local-first SaaS integration: the browser
and Supabase surfaces can be hosted, while trading, warehouse, filing, payment,
desktop, and sensitive mutation routes remain operator-controlled and separately
gated.

## End-User Access Matrix

| User need | Entry point | Related systems | Access mode | Gate before production |
|---|---|---|---|---|
| Understand the product | [`../README.md`](../README.md), [`REPO_SITEMAP.md`](REPO_SITEMAP.md) | `docs/`, `docs/investor/` | Public docs | Keep claims evidence-backed. |
| Browse all capabilities | [`../CAPABILITIES.md`](../CAPABILITIES.md), [`REPO_SITEMAP.md`](REPO_SITEMAP.md) | `aureon/`, `frontend/`, `data/`, `Kings_Accounting_Suite/` | Public docs | Keep capability status current. |
| Run locally | [`../RUNNING.md`](../RUNNING.md) | Root launchers, `aureon/`, `frontend/` | Local operator | Validate `.env` and dry-run/live flags. |
| Use the web console | `frontend/` | `frontend/src/`, `frontend/public/`, `public/` | Browser app | Confirm build env and runtime data source. |
| Navigate capabilities in a SaaS shell | [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md), [`repo_navigation_index.json`](repo_navigation_index.json), [`repo_organization_tree.json`](repo_organization_tree.json), [`capability_access_matrix.json`](capability_access_matrix.json), [`capability_registry.json`](capability_registry.json), [`system_integration_map.json`](system_integration_map.json), [`saas_integration_manifest.json`](saas_integration_manifest.json), [`supabase_hardening_manifest.json`](supabase_hardening_manifest.json), frontend `#repo-map` | `docs/`, `docs/audits/`, `frontend/public/`, `frontend/src/components/RepoNavigationPanel.tsx` | Static JSON manifests, file-level index, directory tree, capability access matrix, capability registry, system integration map, SaaS integration contract, Supabase hardening contract, autonomous frontend manifests, and console tab | Keep public manifests secret-free. |
| Read runtime state | `http://127.0.0.1:8791/api/terminal-state` | `aureon/exchanges/`, status server | Local HTTP | Do not expose publicly without auth and redaction. |
| Read thought/action state | `http://127.0.0.1:13002/api/thoughts` | Mind hub, self-questioning loop | Local HTTP | Do not expose publicly without auth and redaction. |
| Trigger coding workflow | `/api/coding/prompt` and `/api/coding/status` | `aureon/autonomous/`, `aureon/code_architect/`, `skills/` | Local operator/API | Keep code proposals review-gated. |
| Review grant/funder evidence | `data/research/grants/`, `docs/investor/` | Grant ledgers, copied evidence, pipeline JSON | Public or controlled disclosure | Redact private evidence before sharing. |
| Use accounting/filing support | `Kings_Accounting_Suite/` | Accounting tools and support packs | Local operator | Filing remains manual unless separately authorized. |
| Integrate hosted backend | `supabase/`, `api/`, `server/`, `functions/`, `netlify/` | Supabase functions, Node bridges, serverless routes | Hosted/API | Apply auth matrix below before production. |
| Deploy product surface | `deploy/`, `production/`, `app.yaml`, Docker files | DigitalOcean, Docker, Netlify, Cloudflare, Supabase | Hosted deployment | Choose one target and maintain an env inventory. |

## Environment Variable Inventory

This inventory is based on `.env.example`, `deploy/env.example`, and `app.yaml`.
It lists variable names only, not secret values.

| Group | Variables | Source |
|---|---|---|
| Supabase frontend | `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` | `app.yaml` |
| Supabase runtime | `SUPABASE_URL`, `SUPABASE_ANON_KEY` | `app.yaml` |
| Exchange credentials | `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `CAPITAL_API_KEY`, `CAPITAL_IDENTIFIER`, `CAPITAL_PASSWORD` | `.env.example`, `deploy/env.example`, `app.yaml` |
| Exchange mode flags | `KRAKEN_DRY_RUN`, `BINANCE_DRY_RUN`, `ALPACA_DRY_RUN`, `ALPACA_PAPER`, `CAPITAL_DEMO`, `CAPITAL_DEMO_MODE`, `BINANCE_UK_MODE`, `BINANCE_USE_TESTNET`, `BINANCE_TESTNET`, `USE_TESTNET` | `.env.example`, `deploy/env.example`, `app.yaml` |
| Runtime/platform | `PORT`, `MODE`, `PYTHONIOENCODING`, `PYTHONUNBUFFERED`, `AUREON_STATE_DIR`, `AUREON_REDIS_URL`, `KRAKEN_NONCE_PATH`, `KRAKEN_PRIVATE_LOCK_PATH` | `deploy/env.example`, `app.yaml` |
| Safety and product switches | `LIVE`, `REAL_DATA_ONLY`, `AUREON_DRY_RUN`, `DRY_RUN`, `PAPER_TRADING`, `PAPER_MODE`, `PAPER`, `SIMULATION_MODE`, `DEMO_MODE`, `STATUS_MOCK`, `IG_DEMO`, `AUREON_COMMAND_CENTER_DEMO`, `SIMULATED_ATTACKS`, `SENTIENCE_FORCE_PERFECT`, `AUREON_ENABLE_AUTONOMOUS_CONTROL`, `AUREON_REQUIRE_ALL_EXCHANGES`, `AUREON_SKIP_KRAKEN_SEED` | `deploy/env.example`, `app.yaml` |
| Feature enablement | `ENABLE_ALPACA`, `ENABLE_KRAKEN`, `ENABLE_BINANCE`, `ENABLE_CAPITAL`, `STARTING_CAPITAL` | `deploy/env.example` |
| Optional data providers | `COINAPI_KEY` | `.env.example` |

Production rule: keep credentials in the target secret store. Do not commit
filled `.env` files, customer identifiers, exchange passwords, or private
evidence exports.

## Deployment Surfaces

| Surface | Files | Current role | Readiness note |
|---|---|---|---|
| Local Windows operator | `AUREON_PRODUCTION_LIVE.cmd`, `AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1`, `RUNNING.md` | Current primary local run path. | Best current source of truth for operator startup. |
| Frontend app | `frontend/package.json`, `frontend/src/`, `frontend/public/` | React/Vite product surface. | Build with `npm run build`; confirm env values before hosted use. |
| Supabase backend | `supabase/config.toml`, `supabase/functions/`, `supabase/migrations/` | Hosted functions, auth settings, schema migrations. | Auth matrix and hardening review below must be resolved before production. |
| DigitalOcean App Platform | `app.yaml`, `deploy/` | App spec and startup scripts. | Already names `main` and env keys; secrets must be configured in platform. |
| Docker/production package | `Dockerfile`, `docker-compose.yml`, `production/` | Container and installer assets. | Current production docs include older language; use sitemap/readiness docs as current public framing. |
| Node/server bridge | `server/` | Optional WebSocket/server bridge. | Treat as component surface, not canonical product API until reviewed. |
| Serverless routes | `api/`, `functions/`, `netlify/`, `deploy/cloudflare/` | RSS/proxy/worker style routes. | Confirm auth, CORS, and data redaction per route. |

## Supabase Auth Boundary

Current `supabase/config.toml` declares 87 functions:

| Auth mode | Count | Production interpretation |
|---|---:|---|
| `verify_jwt = true` | 73 | Auth-gated; still needs role-level and payload validation review. |
| `verify_jwt = false` | 14 | Public at Supabase edge; must be read-only, anonymous-safe, or separately protected in function code before production. |

The generated hardening manifest classifies those functions by public exposure,
mutation/ingest/sensitive-state signals, and required controls. The current
manifest identifies zero high-risk public routes blocking production:
[`supabase_hardening_manifest.json`](supabase_hardening_manifest.json).

Public functions currently configured with `verify_jwt = false`:

`fetch-kraken-market-data`, `sync-exchange-assets`, `aureon-chat`,
`ingest-telescope-state`, `fetch-binance-market-data`, `fetch-schumann-data`,
`fetch-all-tickers`, `verify-exchange-connectivity`, `interpret-frequency`,
`ingest-10-9-1-packet`, `backend-health-check`, `ingest-auris-state`,
`ingest-kelly-computation`, and `ai-commentary`.

Public endpoint production gates:

- Market-data fetchers and health checks can remain public only if they expose no
  user credentials, account balances, private positions, or private evidence.
- Public ingestion routes must validate source, schema, size, rate limits, and
  replay behavior before public hosting.
- `force-validated-trade`, `confirm-trade`, `poll-trade-confirmations`,
  `test-exchange-connection`, `ingest-trades`, `ingest-terminal-state`, and
  `ingest-brain-state` are now JWT gated and remain subject to explicit
  role/payload review before production because their names or purpose imply
  mutation, user-sensitive validation, or operational state writes.
- Auth-gated trade, balance, gas-tank, emergency-stop, credential, monitor, and
  user-market routes must remain JWT-gated and need role/payload checks inside
  each function.
- Regenerate the hardening manifest after any Supabase function auth change so
  the docs and frontend public mirror keep the same blocker count.

## Generated Artifact Policy

| Artifact class | Examples | Policy |
|---|---|---|
| Source docs | `README.md`, `docs/REPO_SITEMAP.md`, `docs/SAAS_INTEGRATION_READINESS.md` | Tracked and reviewed. |
| Public static/generated assets | `frontend/public/` | Tracked when intentionally published; runtime mirrors may be generated. |
| Public navigation manifests | `frontend/public/aureon_repo_sitemap.json`, `frontend/public/aureon_end_user_access_map.json`, `frontend/public/aureon_capability_access_matrix.json`, `frontend/public/aureon_capability_registry.json`, `frontend/public/aureon_repo_navigation_index.json`, `frontend/public/aureon_repo_organization_tree.json`, `frontend/public/aureon_repo_navigation_readiness.json`, `frontend/public/aureon_system_integration_map.json`, `frontend/public/aureon_saas_integration_manifest.json`, `frontend/public/aureon_supabase_hardening_manifest.json`, `frontend/public/aureon_saas_system_inventory.json`, `frontend/public/aureon_frontend_unification_plan.json`, `frontend/public/aureon_frontend_evolution_queue.json`, `frontend/public/aureon_organism_runtime_status.json`, `frontend/public/aureon_autonomous_capability_switchboard.json` | Tracked, secret-free access contracts, capability access matrix, capability registry, file-level index, directory tree, navigation readiness audit, system integration map covering all current implementation capabilities, SaaS integration manifest, Supabase hardening manifest, SaaS inventory, frontend unification plan, evolution queue, organism status, and capability switchboard for UI/SaaS shells. |
| Runtime state | `state/aureon_wake_up_manifest.json`, `state/aureon_data_ocean_status.json`, local SQLite registries | Generated locally unless explicitly committed. Do not treat absence from git as missing source. |
| Audit outputs | `docs/audits/*` named in run docs | Generated by runtime/audit jobs; commit only curated public-safe outputs. |
| Private evidence | Screenshots, customer data, credentials, transaction records, local live ledgers | Keep private unless redacted and intentionally published. |
| Archives/imports | `archive/`, `docs/archive/`, `imports/` | Preserve for provenance; do not use as current product copy. |

## SaaS Production Gates

Before calling a hosted deployment production-ready, complete these gates:

1. Choose one canonical target for the hosted product surface.
2. Confirm all required environment variables for that target and store secrets
   in the platform secret store.
3. Review every public Supabase function using
   `python scripts/validation/generate_supabase_hardening_manifest.py`; either
   prove it is anonymous-safe or gate it with JWT plus role checks.
4. Define CORS, rate limits, payload limits, logging, and redaction policy for
   hosted API routes.
5. Decide which runtime JSON artifacts are generated locally, mirrored to
   frontend public assets, or persisted in Supabase.
6. Keep live trading, warehouse mutation, filing, payment, desktop control, and
   security-testing actions operator-controlled.
7. Run `python scripts/validation/generate_repo_navigation_index.py` after broad
   file moves. Run `python scripts/validation/generate_repo_organization_tree.py`
   after hierarchy or broad file moves. Run `python scripts/validation/generate_capability_access_matrix.py`
   after capability route changes. Run `python scripts/validation/generate_system_integration_map.py`
   after system or public-artifact routing changes. Run
   `python scripts/validation/generate_capability_registry.py` after capability
   table or surface-reference changes. Run
   `python scripts/validation/generate_saas_integration_manifest.py`
   after env or deployment changes. Run
   `python scripts/validation/generate_supabase_hardening_manifest.py` after
   Supabase auth or function changes. Run
   `python scripts/validation/generate_repo_navigation_readiness.py` after
   regenerating navigation, capability, system, SaaS, or hardening manifests.
   Then run
   `python scripts/validation/validate_repo_navigation_contract.py` after
   navigation, public manifest, file-index, capability-registry,
   system-integration-map, SaaS-manifest, hardening-manifest, or Supabase
   auth-setting changes.
8. Run the relevant local checks in `RUNNING.md` and the target deployment smoke
   checks before publishing an external URL.
