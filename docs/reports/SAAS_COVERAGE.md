# SaaS repo-wide coverage — does the platform cover the whole repository?

**Date:** 2026-07-25 · **Branch:** `claude/phenolic-fingerprint-connector-lyv59v` · **Audit:**
`aureon/saas/coverage.py` · **Benchmark:** b45 · **Endpoint:** `GET /api/coverage`

Made falsifiable. `python -m aureon.saas.coverage` reconciles three views of the `aureon/` package tree
and proves they agree — the SaaS covers the whole repo, and every domain reports real operational depth.

## Headline

**All covered: True** — **38/38** `aureon/` packages covered (coverage fraction **1.0**), **0 uncovered**,
**0 phantom**, **7 deep adapters**. Every covered domain carries a real operational health rollup.

Reproduce:

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 AUREON_AUDIT_MODE=1 \
  python -m aureon.saas.coverage           # prints the reconciliation, exit 0 iff all covered
python -m aureon.saas.coverage --report docs/reports/saas_coverage_run.md   # durable artifact
curl -s localhost:8080/api/coverage | jq .all_covered                        # live over the gateway
```

## What it reconciles

1. **Filesystem truth** — the real top-level packages under `aureon/` (a dir with an `__init__.py`):
   the ground truth of what the repo contains (38).
2. **Taxonomy** — the domains the SaaS maps to a product domain (`aureon/saas/domains.py`
   `_FS_TO_PRODUCT` ∪ `_ADAPTERS`).
3. **Catalog** — the domains the filesystem scan actually surfaced systems for (`build_catalog`).

A package **on disk but missing from the taxonomy** is `uncovered` (a real gap — the console would
default it silently). A taxonomy domain **with no package on disk** is `phantom` (a stale mapping).
`all_covered` is true only when both are empty. Both are empty.

## Deepened domain adapters — depth, not just reachability

Previously `/api/domains` reported only "is the package importable" for 31 of 38 domains (only 7 had a
real singleton adapter). Now **every** domain carries a real `health` rollup derived from the honest
filesystem scan — module count, dashboards, Queen-integrated count, ThoughtBus-wired count, wired
fraction, total LOC, and the distinct capability categories present. Examples from the live audit:

| domain | product | adapter | systems | dashboards | wired | LOC |
|:---|:---|:---:|---:|---:|---:|---:|
| `autonomous` | self-improvement | probe | 112 | 18 | 62 | 22,782 |
| `bio` | research | deep | 40 | 0 | 18 | 7,098 |
| `analytics` | accounting | probe | 40 | 1 | 35 | 7,501 |
| `bots` | trading | probe | 32 | 3 | 31 | 7,021 |
| `cognition` | cognition | deep | 4 | 2 | 4 | 605 |

(The 7 "deep" domains — `core, queen, operator, cognition, data_feeds, bio, observer` — additionally carry
a canonical singleton entry point in `_ADAPTERS`; the rest are surfaced by import-reachability + the real
rollup. `has_adapter` marks which.)

## Honest by construction

The audit is read-only — it scans the filesystem and the committed catalog, and **fabricates nothing**. A
domain with no scanned systems would report `health: null`, never a zero-with-confidence. The rollup
numbers are the real filesystem scan (`aureon/saas/catalog.py`), the same source that already backs
`/api/catalog` and `/api/domains`.

## What backs this

- Audit: `aureon/saas/coverage.py` — `reconcile()` (fs ↔ taxonomy), `build_coverage_audit()` (+ per-domain
  health), a deterministic report writer, and the `python -m` CLI (exit non-zero on any uncovered/phantom).
- Deepening: `aureon/saas/domains.py` — `domain_health()` + `domain_report(catalog=…)` roll the catalog
  scan up per domain; `aureon/saas/gateway.py` passes the catalog into `/api/domains` and adds
  `GET /api/coverage`.
- Benchmark **b45** (`tests/benchmarks/benchmark_aureon_scope.py`): proves 38/38 covered, fraction 1.0, no
  uncovered/phantom, every covered domain has a real health rollup, ≥7 deep adapters, deterministic +
  byte-identical artifact. Tier-A total: **45**.
- Tests: `tests/test_saas_coverage.py` (reconciliation, per-domain health, determinism, byte-identical
  report, CLI exit 0, deepened `domain_report`).
