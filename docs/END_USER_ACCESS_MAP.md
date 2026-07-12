# Aureon End-User Access Map

Current tracked snapshot: 2026-07-12.

This map connects end-user needs to the repo systems, docs, runtime surfaces,
frontend-public manifests, and safety gates that make each capability accessible.
It complements the repo-wide sitemap and is designed for product/SaaS shells that
need to expose Aureon capabilities without making users browse the whole repo.

Machine-readable companion: [`end_user_access_map.json`](end_user_access_map.json).
Frontend-public mirrors:
[`../frontend/public/aureon_end_user_access_map.json`](../frontend/public/aureon_end_user_access_map.json)
and
[`../frontend/public/aureon_repo_sitemap.json`](../frontend/public/aureon_repo_sitemap.json).
Frontend console route: `#repo-map`, implemented by
[`../frontend/src/components/RepoNavigationPanel.tsx`](../frontend/src/components/RepoNavigationPanel.tsx).
File-level public index:
[`repo_navigation_index.json`](repo_navigation_index.json) and
[`../frontend/public/aureon_repo_navigation_index.json`](../frontend/public/aureon_repo_navigation_index.json).
Contract validation command, from repo root:
`python scripts/validation/validate_repo_navigation_contract.py`.

## Access Principles

- Start users from a task, not from a folder name.
- Each task must point to a current doc, source system, evidence surface, and
  safety gate.
- Sensitive actions stay operator-controlled even when their surrounding
  dashboard or documentation is public.
- Frontend-public JSON gives the UI a stable navigation contract without
  exposing secrets or private runtime state.

## Capability Access Matrix

| Capability | End-user action | Primary docs | Related systems | Runtime or API surface | Safety gate |
|---|---|---|---|---|---|
| Product overview | Understand what Aureon is and where to start. | [`../README.md`](../README.md), [`REPO_SITEMAP.md`](REPO_SITEMAP.md) | `docs/`, `docs/investor/` | Public docs and frontend public manifest | Claims must remain evidence-backed. |
| Repo navigation | Browse all systems and how they relate. | [`REPO_SITEMAP.md`](REPO_SITEMAP.md), [`INDEX.md`](INDEX.md), [`repo_navigation_index.json`](repo_navigation_index.json) | `docs/`, root docs, `frontend/public/`, `frontend/src/components/RepoNavigationPanel.tsx` | `#repo-map`, `frontend/public/aureon_repo_sitemap.json`, `frontend/public/aureon_repo_navigation_index.json` | Keep generated counts current after major moves. |
| SaaS integration | See deploy surfaces, env groups, and auth boundaries. | [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md) | `frontend/`, `supabase/`, `api/`, `server/`, `functions/`, `netlify/`, `deploy/`, `production/` | `docs/repo_sitemap.json`, frontend public manifests | Public endpoints require review before production. |
| Local runtime | Start and validate the local operator runtime. | [`../RUNNING.md`](../RUNNING.md), [`../QUICK_START.md`](../QUICK_START.md) | Root launchers, `aureon/`, `scripts/` | `http://127.0.0.1:8791/api/terminal-state` | Validate env and dry-run/live mode first. |
| Operator console | Use the browser console and public artifacts. | [`FLAMEBORN_INTEGRATION.md`](FLAMEBORN_INTEGRATION.md), [`dashboards/DASHBOARD_GUIDE.md`](dashboards/DASHBOARD_GUIDE.md) | `frontend/`, `frontend/public/`, `public/`, `templates/` | `http://127.0.0.1:8081/`, `frontend/public/*` | Runtime data must be redacted before public hosting. |
| Trading readiness | Review exchange state, readiness, and action blockers. | [`../CAPABILITIES.md`](../CAPABILITIES.md), [`LIVE_TRADING_RUNBOOK.md`](LIVE_TRADING_RUNBOOK.md) | `aureon/exchanges/`, `aureon/trading/`, `aureon/portfolio/`, `aureon/strategies/` | `/api/terminal-state`, `/api/flight-test`, `/api/reboot-advice` | Live action requires credentials, fresh data, and operator approval. |
| Research and evidence | Inspect research, claims, grants evidence, and proof artifacts. | [`CLAIMS_AND_EVIDENCE.md`](CLAIMS_AND_EVIDENCE.md), [`investor/README.md`](investor/README.md) | `data/`, `docs/research/`, `VERIFICATION AND VALIDATION/`, `imports/` | Research inventories and public-safe files | Private evidence must be redacted before sharing. |
| Grant/funder review | Review Gary/Aureon evidence and funding material. | [`investor/README.md`](investor/README.md), [`../data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md`](../data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md) | `data/research/grants/`, `docs/investor/` | Pipeline JSON, applications ledger, copied evidence set | Do not imply unsupported eligibility or submission status. |
| Accounting and filing support | Generate and review accounting or statutory support packs. | [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md), [`../CAPABILITIES.md`](../CAPABILITIES.md) | `Kings_Accounting_Suite/`, accounting bridges under `aureon/` | Generated local support packs | Filing and payment remain manual unless separately authorized. |
| Coding and skills | Route code, skill, and desktop handoff work. | [`../CAPABILITIES.md`](../CAPABILITIES.md), [`../SYSTEM_OVERVIEW.md`](../SYSTEM_OVERVIEW.md) | `aureon/code_architect/`, `aureon/inhouse_ai/`, `aureon/autonomous/`, `skills/` | `/api/coding/prompt`, `/api/coding/status`, skill manifests | Code proposals and desktop actions stay review-gated. |
| Deployment | Choose and prepare a hosted target. | [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md), [`deployment/`](deployment/) | `app.yaml`, `deploy/`, `production/`, `supabase/`, `netlify/` | Platform-specific app, Docker, Supabase, Netlify, Cloudflare surfaces | Pick one target and store secrets outside git. |
| Validation | Run checks and prove the map remains navigable. | [`STATE_FILES.md`](STATE_FILES.md), [`INTEGRATION_TEST_STATUS.md`](INTEGRATION_TEST_STATUS.md) | `tests/`, `scripts/validation/`, `VERIFICATION AND VALIDATION/` | Pytest and validation scripts | Checks must match the capability being claimed. |
| Archive and provenance | Inspect preserved historical material. | [`archive/README_legacy_20260712.md`](archive/README_legacy_20260712.md) | `archive/`, `docs/archive/`, `imports/` | Archived files | Archive is history, not current product copy. |

## Frontend Public Contract

The frontend can read these static files without needing repo traversal:

| Public file | Purpose |
|---|---|
| `frontend/public/aureon_repo_sitemap.json` | Public navigation manifest for top-level systems, docs, and SaaS surfaces. |
| `frontend/public/aureon_end_user_access_map.json` | Capability-to-access map for task-driven UI navigation. |
| `frontend/public/aureon_repo_navigation_index.json` | File-level repo index generated from `git ls-files` for searchable end-user navigation. |
| `frontend/src/components/RepoNavigationPanel.tsx` | End-user console surface that renders the public manifests at `#repo-map`. |

These files contain paths, labels, and safety notes only. They do not contain
credentials, private runtime state, customer data, or local evidence exports.
Validate that contract with
`python scripts/validation/validate_repo_navigation_contract.py` before
publishing navigation or SaaS-shell changes.
