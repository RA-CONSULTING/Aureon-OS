# Defense & Validation surface

The console's **Defense & Validation** page (sidebar → *Defense & Validation*, route `/defense`) surfaces
the whole `aureon/bio` family — the derived-signal **sensor lanes**, the **statistical-validity dossier**
(b28–b33: conformance · FPR · power · calibration · multiplicity · false-discovery), and the **cognitive
immune layer** (b34 integrity guard · b35 swarm defense · b36 MCP membrane) — grouped and status-badged.

## Where it comes from

- **Endpoint:** `GET /api/defense` → `aureon/saas/defense_catalog.py::build_defense_catalog()`, mounted
  in `aureon/saas/gateway.py` behind the same bearer/tenancy guard + provenance stamp as the other
  SaaS routes.
- **Status source (honest, no fabrication):** the committed Tier-A benchmark report
  `tests/benchmarks/report.json` — each bio entry's real `passed` / `metrics` / `evidence` /
  `invariants`, joined on module path and grouped. A **live bus-trace overlay**
  (`bus_trace.read_trace_latest(<trace>)`) lifts a module's honesty `boundary` and marks it `live` when
  it has actually run (benchmark or CLI).
- **`truth_status`** per module: `live` (a recent bus-trace exists) · `real_derived` (from the committed
  report) · `no_data` (neither). The top-level surface degrades to `no_data` with an honest empty state
  when the report is absent.

## What it does NOT do

- It **never runs or imports the bio modules on a web request** — the endpoint is pure-read over the
  report + trace files (no numpy-heavy cold-boot, no φ engine execution).
- It **never fabricates**: a module with no benchmark row and no trace shows `no_data`, and the frontend
  renders honest empty/offline states (Stage-3 real-data contract).

## Frontend

`frontend/src/shell/pages/DefensePage.tsx` (registered via one `NavItem` in `frontend/src/shell/nav.ts`)
renders three grouped sections of cards — one per bio module — with a pass/fail badge, a provenance
`truth_status` badge, the top metrics, the invariant tally, and the module's honesty `boundary` when
present. A compact "Defense & Validation" tile on the Overview page shows the `passing/total` roll-up and
links here. Both follow the shell design system (shadcn `Card`/`Badge`, lucide icons, no emoji) and the
no-fake-data discipline.
