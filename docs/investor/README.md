# Aureon Investor, Public, And Funder Guide

This guide explains how to review Aureon without needing to interpret every
legacy term or every historical research section first. It is written for three
audiences: investors, public GitHub readers, and grant or funder reviewers.

## Executive View

Aureon is a local-first evidence automation platform. It combines code,
metadata, operator interfaces, ledgers, research artifacts, and validation
outputs so complex work can be inspected before it is acted on.

The repository is broad, but the current investment thesis is narrow:

- Evidence-heavy workflows need auditable local control.
- Operators need a single place to see runtime state, proof, blockers, and next
  actions.
- Sensitive workflows need clear separation between analysis, preparation,
  review, and live mutation.
- Research and grant material needs to be categorized so reviewers can separate
  validated evidence from exploratory work.

## Audience Paths

| Audience | What to inspect | Recommended path |
|---|---|---|
| Investor diligence | Capability categories, evidence discipline, current product surfaces, and risk boundaries. | Start with this guide, then read [`../../SYSTEM_OVERVIEW.md`](../../SYSTEM_OVERVIEW.md), [`../../CAPABILITIES.md`](../../CAPABILITIES.md), and [`../../AUDIT_SUMMARY.md`](../../AUDIT_SUMMARY.md). |
| Public GitHub reader | Setup, architecture, module map, research history, contribution route, and preserved archive. | Start with [`../INDEX.md`](../INDEX.md), [`../REPO_SITEMAP.md`](../REPO_SITEMAP.md), [`../END_USER_ACCESS_MAP.md`](../END_USER_ACCESS_MAP.md), [`../SAAS_INTEGRATION_READINESS.md`](../SAAS_INTEGRATION_READINESS.md), [`../../QUICK_START.md`](../../QUICK_START.md), and [`../../RUNNING.md`](../../RUNNING.md). |
| Grant or funder reviewer | Gary/Aureon evidence inventory, grant ledgers, funder-safe research packets, and claim support. | Start with [`../../data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md`](../../data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md), then review [`../../data/research/grants/pipeline.json`](../../data/research/grants/pipeline.json) and [`../../data/research/grants/autopilot_status.json`](../../data/research/grants/autopilot_status.json). |

## Capability Categories

| Category | Description | Review evidence |
|---|---|---|
| Evidence automation | Captures local state, ledgers, screenshots, reports, and validation records for review. | [`../../AUDIT_SUMMARY.md`](../../AUDIT_SUMMARY.md), [`../../LIVE_PROOF.md`](../../LIVE_PROOF.md), [`../CLAIMS_AND_EVIDENCE.md`](../CLAIMS_AND_EVIDENCE.md) |
| Operator runtime | Coordinates local services, dashboards, guarded command paths, and runtime status. | [`../../RUNNING.md`](../../RUNNING.md), [`../../SYSTEM_OVERVIEW.md`](../../SYSTEM_OVERVIEW.md), [`../../frontend/`](../../frontend/) |
| Research and metadata fabric | Organizes research packets, indexes, copied evidence, generated records, and route-level metadata. | [`../../docs/`](../../docs/), [`../../data/research/grants/`](../../data/research/grants/) |
| Controlled domain workflows | Applies the operator model to trading research, warehouse support, accounting support, and filing-support preparation. | [`../../aureon/`](../../aureon/), [`../../Kings_Accounting_Suite/`](../../Kings_Accounting_Suite/), [`../../tests/`](../../tests/) |
| Evidence coherence framework | Provides terminology, routing concepts, prompt support, and validation research for deciding whether more proof is needed. | [`../components/README_HARMONIC_NEXUS.md`](../components/README_HARMONIC_NEXUS.md), [`../HNC_UNIFIED_WHITE_PAPER.md`](../HNC_UNIFIED_WHITE_PAPER.md) |

## Claim Status Model

Use this status model when reading the repository:

| Status | Meaning | How it should be written |
|---|---|---|
| Implemented | Code, docs, tests, or runbooks exist in the repo. | "Aureon includes..." with a link to the file or directory. |
| Evidence-backed | A claim is supported by a ledger, report, screenshot, test, or reproducible command. | "Evidence is recorded in..." with a direct path. |
| Operator-controlled | The workflow can prepare or support action, but sensitive mutation remains gated. | "Aureon prepares/reviews/routes..." rather than "Aureon autonomously performs..." |
| Experimental research | The material is exploratory or theoretical. | "Research hypothesis", "experimental framework", or "prototype". |
| Historical archive | The material is retained for continuity, not current positioning. | "Archived historical material" with a link to the archive. |

## What Reviewers Should Not Infer

Aureon documentation should not imply claims that are not directly evidenced in
the repository.

- Do not infer revenue, customer traction, signed partnerships, regulatory
  approval, funder eligibility, or live production adoption unless a specific
  evidence file supports it.
- Do not treat legacy metaphors as current product language.
- Do not treat research hypotheses as verified commercial results.
- Do not treat local evidence folders as public disclosures of private customer
  or credential material.

## Suggested Review Sequence

1. Read the root [`../../README.md`](../../README.md) for the current formal map.
2. Read [`TERMINOLOGY.md`](TERMINOLOGY.md) so internal labels are translated into
   formal review language.
3. Read the repo-wide sitemap in [`../REPO_SITEMAP.md`](../REPO_SITEMAP.md) to
   see capability groups, related systems, and SaaS integration surfaces.
4. Read [`../END_USER_ACCESS_MAP.md`](../END_USER_ACCESS_MAP.md) to see
   task-based capability access, related systems, runtime/API surfaces, and
   safety gates.
5. Read [`../SAAS_INTEGRATION_READINESS.md`](../SAAS_INTEGRATION_READINESS.md)
   for access paths, env/config groups, deploy surfaces, auth boundaries, and
   production gates.
6. Review architecture in [`../../SYSTEM_OVERVIEW.md`](../../SYSTEM_OVERVIEW.md)
   and [`../../DATA_FLOW.md`](../../DATA_FLOW.md).
7. Review claims through [`../CLAIMS_AND_EVIDENCE.md`](../CLAIMS_AND_EVIDENCE.md)
   and audit/proof documents.
8. Review the Gary/Aureon evidence inventory under
   [`../../data/research/grants/`](../../data/research/grants/).
9. Use the archived README only for project history:
   [`../archive/README_legacy_20260712.md`](../archive/README_legacy_20260712.md).

## Investor-Ready Summary Language

Use this concise description when introducing the repository:

> Aureon is a local-first evidence automation platform for high-control
> workflows. It combines operator dashboards, automation scripts, research
> metadata, validation artifacts, and controlled execution gates so reviewers can
> inspect what a workflow knows, what evidence exists, and what action remains
> blocked or ready for human approval.

This wording is intentionally conservative. It describes the system without
adding unsupported commercial, regulatory, or performance claims.
