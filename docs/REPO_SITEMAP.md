# Aureon Repo-Wide Sitemap

Current tracked snapshot: 2026-07-12, generated from `git ls-files`.

This document is the end-user map for the whole repository. It explains where
each system lives, which capability it supports, which documents to read first,
and which integration surfaces matter when the repo is packaged into a product,
dashboard, SaaS workflow, or external diligence process.

Machine-readable companion: [`repo_sitemap.json`](repo_sitemap.json).
File-level navigation index: [`repo_navigation_index.json`](repo_navigation_index.json).
SaaS integration manifest: [`saas_integration_manifest.json`](saas_integration_manifest.json).
Supabase hardening review: [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md)
and [`supabase_hardening_manifest.json`](supabase_hardening_manifest.json), mirrored to
[`../frontend/public/aureon_supabase_hardening_manifest.json`](../frontend/public/aureon_supabase_hardening_manifest.json).
End-user task map: [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md) and
[`end_user_access_map.json`](end_user_access_map.json).
Frontend console surface: [`../frontend/src/components/RepoNavigationPanel.tsx`](../frontend/src/components/RepoNavigationPanel.tsx)
mounted at `#repo-map`.
Navigation contract validator, from repo root:
`python scripts/validation/validate_repo_navigation_contract.py`.

## How To Use This Sitemap

| Need | Start here | Then use |
|---|---|---|
| Understand the whole repo | [`../README.md`](../README.md) | This sitemap and [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md) |
| Evaluate capabilities | [`../CAPABILITIES.md`](../CAPABILITIES.md) | Capability groups below |
| Run or validate locally | [`../RUNNING.md`](../RUNNING.md) | [`../QUICK_START.md`](../QUICK_START.md) |
| Review investor/funder posture | [`investor/README.md`](investor/README.md) | [`investor/TERMINOLOGY.md`](investor/TERMINOLOGY.md) |
| Navigate by end-user task | [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md) | Capability-to-docs, systems, runtime/API surfaces, and safety gates |
| Search the tracked repo index | [`repo_navigation_index.json`](repo_navigation_index.json) | File-level categories, zones, capability IDs, and public frontend mirror |
| Integrate as SaaS | [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md), [`saas_integration_manifest.json`](saas_integration_manifest.json), [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md) | Env variable names, deployment surfaces, Supabase auth posture, hardening blockers, and production gates |
| Inspect all docs | [`INDEX.md`](INDEX.md) | Existing deep-dive docs by audience |
| Integrate as a product surface | [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md) | `frontend/`, `api/`, `server/`, `functions/`, `supabase/`, `netlify/`, `deploy/`, `production/` |

## Repository Zones

The repo should be read in five zones:

| Zone | Purpose | Main paths |
|---|---|---|
| Front door and diligence | Public explanation, investor/funder paths, claim discipline, archive access. | `README.md`, `docs/INDEX.md`, `docs/investor/`, `docs/archive/` |
| Operator runtime | Local services, launchers, trading runtime, workflow controllers, status endpoints. | `AUREON_PRODUCTION_LIVE.cmd`, `AUREON_DATA_OCEAN.cmd`, `aureon/`, `scripts/`, `cli/` |
| Product surfaces | Browser console, static/public artifacts, local/serverless APIs, deploy surfaces. | `frontend/`, `public/`, `flameborn/`, `api/`, `server/`, `functions/`, `netlify/`, `supabase/` |
| Evidence and research | Audits, research packets, grants evidence, validation files, copied local evidence. | `data/`, `docs/research/`, `VERIFICATION AND VALIDATION/`, `imports/`, `archive/` |
| Operations and packaging | Accounting support, deployment, production packaging, tests, CI, templates. | `Kings_Accounting_Suite/`, `deploy/`, `production/`, `packaging/`, `tests/`, `.github/`, `templates/` |

## Top-Level Directory Map

| Path | Tracked files | Role | End-user use |
|---|---:|---|---|
| [`.claude/`](../.claude/) | 1 | Assistant/project guidance. | Context for AI-assisted repo work. |
| [`.clawdhub/`](../.clawdhub/) | 1 | Cloud/developer support metadata. | Integration context. |
| [`.do/`](../.do/) | 1 | DigitalOcean/platform metadata. | Deployment context. |
| [`.github/`](../.github/) | 4 | GitHub automation and repository metadata. | CI/repo hygiene entrypoint. |
| [`Antarctic research/`](../Antarctic%20research/) | 56 | Research evidence folder. | Specialist research review. |
| [`api/`](../api/) | 1 | API route surface. | Product/API integration. |
| [`archive/`](../archive/) | 24 | Historical bundles and backups. | Audit history, not current front door. |
| [`aureon/`](../aureon/) | 994 | Main Python runtime and subsystem package. | Core implementation. |
| [`aureon_launcher/`](../aureon_launcher/) | 7 | Launcher support. | Local startup support. |
| [`cli/`](../cli/) | 6 | Command-line helpers. | Local operator tooling. |
| [`daemon_codes/`](../daemon_codes/) | 36 | Background automation code. | Service/background route review. |
| [`data/`](../data/) | 3,526 | Research, grants, datasets, copied evidence. | Evidence and funder review. |
| [`deploy/`](../deploy/) | 14 | Deployment scripts and service configs. | Infrastructure setup. |
| [`docs/`](../docs/) | 381 | Documentation, runbooks, research, architecture. | Primary reading system. |
| [`flameborn/`](../flameborn/) | 59 | Companion UI/runtime material. | Product surface review. |
| [`frontend/`](../frontend/) | 4,292 | React/Vite console and public artifacts. | End-user browser experience. |
| [`functions/`](../functions/) | 1 | Serverless function surface. | Hosted integration route. |
| [`imports/`](../imports/) | 1,242 | Imported historical/source bundles. | Migration and provenance review. |
| [`integrations/`](../integrations/) | 21 | External integration support. | Connector review. |
| [`Kings_Accounting_Suite/`](../Kings_Accounting_Suite/) | 227 | Accounting, filing-support, statutory-pack tooling. | Back-office workflow review. |
| [`memory/`](../memory/) | 1 | Local memory/context artifact. | Operator context. |
| [`netlify/`](../netlify/) | 1 | Netlify function/deploy surface. | Hosted web integration. |
| [`packaging/`](../packaging/) | 2 | Package/build helpers. | Release packaging. |
| [`production/`](../production/) | 15 | Production install/runtime assets. | Product deployment path. |
| [`public/`](../public/) | 58 | Public static assets. | Browser/static publishing. |
| [`scripts/`](../scripts/) | 306 | Diagnostics, runners, reports, validation scripts. | Operator and maintainer tasks. |
| [`server/`](../server/) | 7 | Node/server bridge surface. | Backend integration route. |
| [`skills/`](../skills/) | 12 | Local skill registries and interactions. | Capability extension route. |
| [`supabase/`](../supabase/) | 160 | Supabase config, migrations, functions. | SaaS data/backend integration. |
| [`templates/`](../templates/) | 6 | UI/document templates. | Product and report generation. |
| [`tests/`](../tests/) | 330 | Regression and validation tests. | Acceptance and safety checks. |
| [`tools/`](../tools/) | 5 | Focused utility scripts. | Maintenance and diagnostics. |
| [`VERIFICATION AND VALIDATION/`](../VERIFICATION%20AND%20VALIDATION/) | 14 | Formal validation documents. | Evidence and diligence. |
| [`wisdom_data/`](../wisdom_data/) | 12 | Research/context data. | Specialist research review. |

## Root Entry Points

| Path | Role |
|---|---|
| [`../README.md`](../README.md) | Formal repo front door. |
| [`../INDEX.md`](../INDEX.md) | Legacy broad documentation index with deep links. |
| [`../RUNNING.md`](../RUNNING.md) | Single source for local run commands. |
| [`../QUICK_START.md`](../QUICK_START.md) | Fast local orientation. |
| [`../CAPABILITIES.md`](../CAPABILITIES.md) | Current capability matrix. |
| [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md) | Whole-system operating model. |
| [`../DATA_FLOW.md`](../DATA_FLOW.md) | Data flow and architecture notes. |
| [`../LIVE_PROOF.md`](../LIVE_PROOF.md) | Proof and runtime evidence guide. |
| [`../AUDIT_SUMMARY.md`](../AUDIT_SUMMARY.md) | Consolidated audit summary. |
| [`../AUREON_PRODUCTION_LIVE.cmd`](../AUREON_PRODUCTION_LIVE.cmd) | Windows production supervisor entrypoint. |
| [`../AUREON_DATA_OCEAN.cmd`](../AUREON_DATA_OCEAN.cmd) | Data/research supervisor entrypoint. |
| [`../AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1`](../AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1) | Full local runtime launcher. |

## Capability-To-System Map

| Capability group | Primary systems | Main docs | Integration surface |
|---|---|---|---|
| Evidence automation | `docs/`, `data/`, `frontend/public/`, generated `state/` outputs | [`../LIVE_PROOF.md`](../LIVE_PROOF.md), [`CLAIMS_AND_EVIDENCE.md`](CLAIMS_AND_EVIDENCE.md) | Audit files, JSON mirrors, evidence ledgers |
| Operator runtime | `aureon/autonomous/`, `aureon/exchanges/`, root launchers | [`../RUNNING.md`](../RUNNING.md), [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md) | Local HTTP endpoints, manifests, status JSON |
| Trading and exchange readiness | `aureon/exchanges/`, `aureon/trading/`, `aureon/portfolio/`, `aureon/strategies/` | [`../CAPABILITIES.md`](../CAPABILITIES.md), [`LIVE_TRADING_RUNBOOK.md`](LIVE_TRADING_RUNBOOK.md) | `http://127.0.0.1:8791/api/terminal-state` and related runtime endpoints |
| Data ocean and research fabric | `data/research/`, `aureon/data_feeds/`, `aureon/search/`, `imports/` | [`../RUNNING.md`](../RUNNING.md), [`research/`](research/) | Data ocean status files, research inventories, copied evidence |
| Frontend/operator console | `frontend/src/`, `frontend/public/`, `public/`, `templates/` | [`FLAMEBORN_INTEGRATION.md`](FLAMEBORN_INTEGRATION.md), [`dashboards/DASHBOARD_GUIDE.md`](dashboards/DASHBOARD_GUIDE.md) | React/Vite app, static artifacts, generated public JSON |
| Coding, skills, and desktop handoff | `aureon/code_architect/`, `aureon/inhouse_ai/`, `aureon/autonomous/`, `skills/` | [`../CAPABILITIES.md`](../CAPABILITIES.md), [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md) | Mind hub, coding prompt route, skill manifests, dry-run desktop handoff |
| Warehouse operations support | root `aureon_location_transfer_*`, `current_balance_*`, `docs/warehouse/` | [`azyra_warehouse_admin_reality_check.md`](azyra_warehouse_admin_reality_check.md), [`warehouse/`](warehouse/) | Manifest rows, evidence captures, held-review states |
| Accounting and filing support | `Kings_Accounting_Suite/`, accounting bridges under `aureon/` | [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md), [`../CAPABILITIES.md`](../CAPABILITIES.md) | Generated support packs and manual filing evidence |
| Grant and funder evidence | `data/research/grants/`, `docs/investor/` | [`investor/README.md`](investor/README.md), [`../README.md`](../README.md) | Applications ledgers, pipeline JSON, copied evidence sets |
| SaaS/backend/deploy readiness | `api/`, `server/`, `functions/`, `netlify/`, `supabase/`, `deploy/`, `production/` | [`deployment/`](deployment/), [`SECURITY.md`](SECURITY.md), [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md) | Serverless routes, Supabase migrations/functions, deploy manifests, hardening manifest |
| Testing and validation | `tests/`, `scripts/validation/`, `VERIFICATION AND VALIDATION/` | [`INTEGRATION_TEST_STATUS.md`](INTEGRATION_TEST_STATUS.md), [`STATE_FILES.md`](STATE_FILES.md) | Pytest suites, validation scripts, formal proof artifacts |
| Archive and provenance | `archive/`, `docs/archive/`, `imports/` | [`archive/README_legacy_20260712.md`](archive/README_legacy_20260712.md) | Preserved history; not the current product front door |

## SaaS Integration Map

| Layer | Current repo surface | Integration notes |
|---|---|---|
| Web app | `frontend/`, `public/`, `templates/` | Primary user-facing surface. Frontend reads tracked and generated public artifacts. |
| Local runtime API | `aureon/exchanges/unified_market_status_server.py`, mind hub modules | Local HTTP endpoints are documented in `RUNNING.md`; they require local runtime startup. |
| Server/backend bridge | `server/`, `api/`, `functions/`, `netlify/` | Hosted or serverless integration points; use after confirming environment variables and auth boundaries. |
| Database/backend-as-a-service | `supabase/config.toml`, `supabase/migrations/`, `supabase/functions/` | SaaS data plane and edge-function surface. Treat migrations as schema authority and resolve the Supabase hardening review before production. |
| Deployment | `deploy/`, `production/`, `.do/`, `Dockerfile`, `docker-compose.yml`, `app.yaml`, `Procfile` | Multiple deployment paths exist; pick one target and document env vars before production. |
| Generated state | `state/` paths named in docs, runtime manifests, audit JSON | Often generated locally and intentionally not tracked. Do not assume absent generated files are missing source code. |
| Public generated mirrors | `frontend/public/` | Tracked adaptive skills, repo-navigation manifests, file-level navigation index, SaaS integration manifest, and Supabase hardening manifest exist here; runtime JSON mirrors may be generated here during local operation. |
| Security and controls | `docs/SECURITY.md`, guarded runtime routes, tests | Keep credentials out of tracked docs; live actions remain operator-controlled. |

Detailed readiness checklist: [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md).
Supabase hardening blocker list: [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md).
Task-based access map: [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md).

## End-User Navigation Paths

| User type | Recommended path |
|---|---|
| New evaluator | `README.md` -> this sitemap -> `SYSTEM_OVERVIEW.md` -> `CAPABILITIES.md`. |
| Investor | `README.md` -> `docs/investor/README.md` -> this sitemap -> `AUDIT_SUMMARY.md`. |
| Grant or funder reviewer | `README.md` -> `docs/investor/README.md` -> `data/research/grants/` inventory. |
| Operator | `RUNNING.md` -> `QUICK_START.md` -> `CAPABILITIES.md` -> runtime endpoints. |
| Frontend/SaaS integrator | this sitemap -> `END_USER_ACCESS_MAP.md` -> frontend `#repo-map` -> `api/`/`server/`/`functions/` -> `supabase/` -> `deploy/`. |
| Backend/data integrator | this sitemap -> `aureon/` -> `data/` -> `supabase/` -> tests. |
| Maintainer | this sitemap -> `docs/INDEX.md` -> `tests/` -> `scripts/validation/`. |

## Organizational Rules

- Keep `README.md` concise and investor-readable.
- Put whole-repo navigation in this sitemap and `docs/INDEX.md`.
- Put run commands in `RUNNING.md`, not scattered across new docs.
- Put capability claims in `CAPABILITIES.md` or link them to evidence.
- Put formal terminology in `docs/investor/TERMINOLOGY.md`.
- Run `python scripts/validation/generate_repo_navigation_index.py` after broad
  file moves. Run `python scripts/validation/generate_saas_integration_manifest.py`
  after env or deployment changes. Run
  `python scripts/validation/generate_supabase_hardening_manifest.py` after
  Supabase auth or function changes. Then run
  `python scripts/validation/validate_repo_navigation_contract.py` after changing
  navigation docs, public manifests, file indexes, SaaS manifests, hardening
  manifests, or Supabase function auth settings.
- Preserve historical language under `archive/`, `docs/archive/`, or `imports/`.
- Treat `state/`, `docs/audits/`, and named runtime JSON files as generated
  outputs unless they are present in `git ls-files`.
- Do not publish secrets, live credentials, customer identifiers, or private
  transaction evidence in public docs.

## Current SaaS-Readiness Gaps To Track

This sitemap makes the repository navigable, but SaaS readiness still depends on
target-specific decisions:

- Choose one canonical deployment target before production packaging.
- Produce an environment variable inventory per target.
- Confirm which generated runtime JSON files should be committed, mirrored, or
  generated at runtime.
- Confirm authentication and authorization boundaries for any hosted endpoint.
- Resolve high-risk public Supabase Edge Function routes before public SaaS use.
- Keep live trading, warehouse mutation, filing, payment, and security-testing
  routes explicitly operator-controlled.
