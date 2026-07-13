# Aureon End-User Access Map

Current tracked snapshot: 2026-07-13.

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
Directory organization tree:
[`repo_organization_tree.json`](repo_organization_tree.json) and
[`../frontend/public/aureon_repo_organization_tree.json`](../frontend/public/aureon_repo_organization_tree.json).
Navigation readiness audit:
[`repo_navigation_readiness.json`](repo_navigation_readiness.json) and
[`../frontend/public/aureon_repo_navigation_readiness.json`](../frontend/public/aureon_repo_navigation_readiness.json).
Navigation completion audit:
[`repo_navigation_completion_audit.json`](repo_navigation_completion_audit.json) and
[`../frontend/public/aureon_repo_navigation_completion_audit.json`](../frontend/public/aureon_repo_navigation_completion_audit.json).
Capability access matrix:
[`capability_access_matrix.json`](capability_access_matrix.json) and
[`../frontend/public/aureon_capability_access_matrix.json`](../frontend/public/aureon_capability_access_matrix.json).
System integration map:
[`system_integration_map.json`](system_integration_map.json) and
[`../frontend/public/aureon_system_integration_map.json`](../frontend/public/aureon_system_integration_map.json).
Capability registry:
[`capability_registry.json`](capability_registry.json) and
[`../frontend/public/aureon_capability_registry.json`](../frontend/public/aureon_capability_registry.json).
SaaS integration manifest:
[`saas_integration_manifest.json`](saas_integration_manifest.json) and
[`../frontend/public/aureon_saas_integration_manifest.json`](../frontend/public/aureon_saas_integration_manifest.json).
SaaS integration handoff:
[`saas_integration_handoff.json`](saas_integration_handoff.json) and
[`../frontend/public/aureon_saas_integration_handoff.json`](../frontend/public/aureon_saas_integration_handoff.json).
Supabase hardening manifest:
[`supabase_hardening_manifest.json`](supabase_hardening_manifest.json) and
[`../frontend/public/aureon_supabase_hardening_manifest.json`](../frontend/public/aureon_supabase_hardening_manifest.json).
Autonomous frontend manifests:
[`audits/aureon_saas_system_inventory.json`](audits/aureon_saas_system_inventory.json),
[`audits/aureon_frontend_unification_plan.json`](audits/aureon_frontend_unification_plan.json),
[`audits/aureon_frontend_evolution_queue.json`](audits/aureon_frontend_evolution_queue.json),
[`audits/aureon_organism_runtime_status.json`](audits/aureon_organism_runtime_status.json),
[`audits/aureon_autonomous_capability_switchboard.json`](audits/aureon_autonomous_capability_switchboard.json),
and their `frontend/public/` mirrors.
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
| Repo navigation | Browse all systems and how they relate. | [`REPO_SITEMAP.md`](REPO_SITEMAP.md), [`SYSTEM_INTEGRATION_MAP.md`](SYSTEM_INTEGRATION_MAP.md), [`CAPABILITY_REGISTRY.md`](CAPABILITY_REGISTRY.md), [`INDEX.md`](INDEX.md), [`repo_navigation_index.json`](repo_navigation_index.json), [`repo_organization_tree.json`](repo_organization_tree.json), [`repo_navigation_readiness.json`](repo_navigation_readiness.json), [`repo_navigation_completion_audit.json`](repo_navigation_completion_audit.json), [`capability_access_matrix.json`](capability_access_matrix.json), [`system_integration_map.json`](system_integration_map.json), [`capability_registry.json`](capability_registry.json) | `docs/`, root docs, `frontend/public/`, `frontend/src/components/RepoNavigationPanel.tsx` | `#repo-map`, `frontend/public/aureon_repo_sitemap.json`, `frontend/public/aureon_repo_navigation_index.json`, `frontend/public/aureon_repo_organization_tree.json`, `frontend/public/aureon_repo_navigation_readiness.json`, `frontend/public/aureon_repo_navigation_completion_audit.json`, `frontend/public/aureon_capability_access_matrix.json`, `frontend/public/aureon_system_integration_map.json`, `frontend/public/aureon_capability_registry.json` | Keep generated counts current after major moves. |
| SaaS integration | See deploy surfaces, env groups, auth boundaries, public manifests, and release steps. | [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md), [`saas_integration_manifest.json`](saas_integration_manifest.json), [`saas_integration_handoff.json`](saas_integration_handoff.json), [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md), [`supabase_hardening_manifest.json`](supabase_hardening_manifest.json) | `frontend/`, `supabase/`, `api/`, `server/`, `functions/`, `netlify/`, `deploy/`, `production/` | `docs/repo_sitemap.json`, `frontend/public/aureon_saas_integration_manifest.json`, `frontend/public/aureon_saas_integration_handoff.json`, `frontend/public/aureon_supabase_hardening_manifest.json`, frontend public manifests | Public endpoints require review before production. |
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
| `frontend/public/aureon_capability_registry.json` | Current capability registry generated from `CAPABILITIES.md`, with resolved surfaces, runtime references, systems, public artifacts, and access routes. |
| `frontend/public/aureon_capability_access_matrix.json` | End-user route matrix for every current capability, including start points, related systems, runtime/API surfaces, and safety gates. |
| `frontend/public/aureon_repo_navigation_index.json` | File-level repo index generated from `git ls-files` for searchable end-user navigation. |
| `frontend/public/aureon_repo_organization_tree.json` | Directory hierarchy generated from `git ls-files` for parent/child structural navigation. |
| `frontend/public/aureon_repo_navigation_readiness.json` | Pass/fail readiness audit for sitemap freshness, capability routing, system mapping, public mirrors, and SaaS blockers. |
| `frontend/public/aureon_repo_navigation_completion_audit.json` | Requirement-by-requirement completion proof for repo-wide navigation, capability routing, system mapping, public access, and SaaS integration readiness. |
| `frontend/public/aureon_system_integration_map.json` | System-to-capability integration map covering all 29 current implementation capabilities, access routes, entrypoints, public artifacts, validation references, readiness status, and safety gates. |
| `frontend/public/aureon_saas_integration_manifest.json` | SaaS integration contract generated from env examples, deployment config, and Supabase auth settings. |
| `frontend/public/aureon_saas_integration_handoff.json` | SaaS integration handoff for public manifest publishing, deployment surfaces, env names, Supabase hardening, readiness gates, and release steps. |
| `frontend/public/aureon_supabase_hardening_manifest.json` | Supabase Edge Function hardening contract generated from `supabase/config.toml` and function source presence. |
| `frontend/public/aureon_saas_system_inventory.json` | SaaS surface inventory for frontend, Supabase, dashboard, and blocker visibility. |
| `frontend/public/aureon_frontend_unification_plan.json` | Canonical screen plan and migration queue for reducing dashboard drift. |
| `frontend/public/aureon_frontend_evolution_queue.json` | Ordered frontend work queue for adapting discovered surfaces into the product shell. |
| `frontend/public/aureon_organism_runtime_status.json` | Safe-observation runtime status, blind spots, feed freshness, and action gating. |
| `frontend/public/aureon_autonomous_capability_switchboard.json` | Capability-mode switchboard for autonomous routes, blockers, and frontend work orders. |
| `frontend/src/components/RepoNavigationPanel.tsx` | End-user console surface that renders the public manifests at `#repo-map`. |

These files contain paths, labels, and safety notes only. They do not contain
credentials, private runtime state, customer data, or local evidence exports.
Validate that contract with
`python scripts/validation/validate_repo_navigation_contract.py` before
publishing navigation or SaaS-shell changes.
