# Aureon

Local-first evidence automation and operator runtime.

Aureon is a working repository for auditable automation across trading research,
operator consoles, warehouse and accounting support, research indexing, and
controlled live-action workflows. The repository is best read as an evidence
system: code, ledgers, audits, generated interfaces, and research artifacts are
kept together so reviewers can understand what exists, what is experimental, and
what is ready for controlled use.

This README is the formal front door. The previous long-form README has been
preserved unchanged at
[`docs/archive/README_legacy_20260712.md`](docs/archive/README_legacy_20260712.md).

## Reader Routes

| Reader | Start here | Purpose |
|---|---|---|
| Investor diligence | [`docs/investor/README.md`](docs/investor/README.md) | Business-readable map of the platform, capability categories, evidence posture, and review sequence. |
| Public GitHub review | [`docs/INDEX.md`](docs/INDEX.md) | Guided navigation for setup, architecture, operations, research, and contribution paths. |
| Repo-wide sitemap | [`docs/REPO_SITEMAP.md`](docs/REPO_SITEMAP.md) | Whole-repo organization, capability groups, related systems, and SaaS integration surfaces. |
| End-user access map | [`docs/END_USER_ACCESS_MAP.md`](docs/END_USER_ACCESS_MAP.md) | Task-based access to capabilities, docs, related systems, runtime surfaces, and safety gates. |
| Frontend repo map | [`frontend/src/components/RepoNavigationPanel.tsx`](frontend/src/components/RepoNavigationPanel.tsx) | Console tab mounted at `#repo-map` for browsing public repo and capability manifests. |
| File-level repo index | [`docs/repo_navigation_index.json`](docs/repo_navigation_index.json) | Generated `git ls-files` index mirrored to the frontend public folder for searchable repo navigation. |
| SaaS integration manifest | [`docs/saas_integration_manifest.json`](docs/saas_integration_manifest.json) | Generated env-name, deployment-surface, Supabase auth, and production-gate contract for SaaS shells. |
| SaaS integration readiness | [`docs/SAAS_INTEGRATION_READINESS.md`](docs/SAAS_INTEGRATION_READINESS.md) | End-user access matrix, env/config inventory, deploy surfaces, auth boundaries, and production gates. |
| Supabase hardening review | [`docs/SUPABASE_HARDENING_REVIEW.md`](docs/SUPABASE_HARDENING_REVIEW.md) | Generated public/JWT Edge Function classification, production blockers, and hardening gates. |
| Navigation contract check | [`scripts/validation/validate_repo_navigation_contract.py`](scripts/validation/validate_repo_navigation_contract.py) | Checks public manifests, repo counts, Supabase auth counts, and key navigation links. |
| Grant or funder review | [`data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md`](data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md) | Catalogued Gary/Aureon metadata and research evidence gathered for funder-safe review. |
| Technical review | [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md), [`DATA_FLOW.md`](DATA_FLOW.md), [`CAPABILITIES.md`](CAPABILITIES.md) | System architecture, data flow, and capability inventory. |
| Operator review | [`RUNNING.md`](RUNNING.md), [`QUICK_START.md`](QUICK_START.md), [`LIVE_PROOF.md`](LIVE_PROOF.md) | Runtime entry points, operating notes, and proof artifacts. |

## What Aureon Is

Aureon is a local-first operating layer for evidence-heavy automation. It brings
together scripts, services, dashboards, ledgers, research packets, and validation
outputs so that a human operator can inspect the state of a workflow before any
serious action is taken.

The repository is organized around five current capability pillars:

| Pillar | What it covers | Representative evidence |
|---|---|---|
| Evidence automation | Local files, ledgers, screenshots, reports, and audit artifacts that document work before and after action. | [`AUDIT_SUMMARY.md`](AUDIT_SUMMARY.md), [`LIVE_PROOF.md`](LIVE_PROOF.md), [`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md) |
| Operator console and runtime | Frontend surfaces, local services, status endpoints, guarded command paths, and production startup notes. | [`frontend/`](frontend/), [`RUNNING.md`](RUNNING.md), [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) |
| Data and research fabric | Metadata, research files, generated indexes, and route evidence that make large local knowledge sets reviewable. | [`docs/`](docs/), [`data/research/grants/`](data/research/grants/), [`INDEX.md`](INDEX.md) |
| Controlled domain automation | Trading research, warehouse support, accounting support, filing-support preparation, and related operator workflows. | [`aureon/`](aureon/), [`Kings_Accounting_Suite/`](Kings_Accounting_Suite/), [`tests/`](tests/) |
| Evidence coherence research | HNC/Auris research, prompt routing, validation concepts, and experimental reasoning frameworks. | [`docs/components/README_HARMONIC_NEXUS.md`](docs/components/README_HARMONIC_NEXUS.md), [`docs/HNC_UNIFIED_WHITE_PAPER.md`](docs/HNC_UNIFIED_WHITE_PAPER.md) |

## Repository Map

| Path | Role |
|---|---|
| [`aureon/`](aureon/) | Main Python package and domain modules. |
| [`frontend/`](frontend/) | Operator console, generated public proof surfaces, and TypeScript UI work. |
| [`docs/`](docs/) | Architecture, runbooks, audits, research notes, security guidance, and navigation. |
| [`data/research/grants/`](data/research/grants/) | Grant, funder, and Gary/Aureon evidence ledgers and copied research material. |
| [`Kings_Accounting_Suite/`](Kings_Accounting_Suite/) | Accounting, statutory-pack, and filing-support tooling. |
| [`scripts/`](scripts/) | Launch, diagnostic, migration, reporting, and helper scripts. |
| [`tests/`](tests/) | Regression tests and focused validation coverage. |
| [`archive/`](archive/) | Historical bundles and retained project material. |
| [`docs/archive/`](docs/archive/) | Documentation snapshots preserved for audit history. |

## Evidence And Claim Discipline

Aureon documentation should separate current capability, validated evidence,
experimental research, and historical archive material.

- Current capability means the repository contains code, runbooks, tests, or
  reproducible artifacts that support the statement.
- Evidence-backed claims should link to the file, ledger, report, or command
  that establishes them.
- Research hypotheses should be described as research, not production facts.
- Archived language remains available for audit history, but it should not be
  treated as the current investor-facing description of the project.
- The repository does not add unsupported revenue, customer, partner,
  performance, regulatory, or eligibility claims.

For formal wording, see
[`docs/investor/TERMINOLOGY.md`](docs/investor/TERMINOLOGY.md). For the current
claim table, see
[`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md).

## Operating Boundaries

Aureon is designed for controlled local operation. Live trading, warehouse
mutation, filing support, payment activity, and other sensitive workflows require
explicit operator review, valid credentials, and route-specific evidence. Public
documentation describes capability and repository state; it is not financial,
legal, tax, or regulatory advice.

Sensitive customer names, private credentials, owner names, transaction
references, and local evidence that should remain private are not published in
this front-door README.

## Getting Oriented

1. Read the investor and funder guide:
   [`docs/investor/README.md`](docs/investor/README.md).
2. Use the documentation index:
   [`docs/INDEX.md`](docs/INDEX.md).
3. Use the repo-wide sitemap:
   [`docs/REPO_SITEMAP.md`](docs/REPO_SITEMAP.md).
4. Use the end-user access map:
   [`docs/END_USER_ACCESS_MAP.md`](docs/END_USER_ACCESS_MAP.md).
5. Use the frontend repo map at `#repo-map`:
   [`frontend/src/components/RepoNavigationPanel.tsx`](frontend/src/components/RepoNavigationPanel.tsx).
6. Search the file-level repo index:
   [`docs/repo_navigation_index.json`](docs/repo_navigation_index.json).
7. Review the generated SaaS integration manifest:
   [`docs/saas_integration_manifest.json`](docs/saas_integration_manifest.json).
8. Review the Supabase hardening review and manifest:
   [`docs/SUPABASE_HARDENING_REVIEW.md`](docs/SUPABASE_HARDENING_REVIEW.md) and
   [`docs/supabase_hardening_manifest.json`](docs/supabase_hardening_manifest.json).
9. Review SaaS integration readiness:
   [`docs/SAAS_INTEGRATION_READINESS.md`](docs/SAAS_INTEGRATION_READINESS.md).
10. Review architecture and capability evidence:
   [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md),
   [`CAPABILITIES.md`](CAPABILITIES.md), and
   [`DATA_FLOW.md`](DATA_FLOW.md).
11. Review claims and validation:
   [`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md),
   [`AUDIT_SUMMARY.md`](AUDIT_SUMMARY.md), and
   [`LIVE_PROOF.md`](LIVE_PROOF.md).
12. Regenerate and validate the navigation contract:
   `python scripts/validation/generate_repo_navigation_index.py`, then
   `python scripts/validation/generate_saas_integration_manifest.py`, then
   `python scripts/validation/generate_supabase_hardening_manifest.py`, then
   `python scripts/validation/validate_repo_navigation_contract.py`.
13. Inspect preserved historical context:
   [`docs/archive/README_legacy_20260712.md`](docs/archive/README_legacy_20260712.md).

## Preservation Note

This front door is a presentation and categorization update. It does not remove
the prior README content from the repository. The archived README remains
available so that investors, reviewers, operators, and maintainers can trace the
project history while relying on the current formal terminology above.
