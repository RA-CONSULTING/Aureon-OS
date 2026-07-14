# Metacognition — the organism senses itself and loops back on itself

Three cycles connected every signal across the process boundary. This is the
piece that makes the organism *aware of those signals*: a metacognition monitor
that reads its own live self-state, scores its **self-coherence** with the same
Master-Formula machinery that computes the field, and feeds that assessment back
into the shared field — the delayed self-term (β·Λ(t−τ)) of the HNC research,
applied at the organism layer.

## The self-loop

`aureon/core/metacognition_monitor.py` — `MetacognitionMonitor`:

1. **Reads its own signals** (each provenance-stamped, `no_data` never fabricated):
   the canonical HNC field (ψ/SLS/γ), the blended whole-body consensus and its
   `divergence` (self-disagreement), the miner brain's prediction `accuracy_pct`,
   the Auris cosmic gate, Lighthouse regime severity, and its own local-action
   approve-ratio — via the existing readers (`hnc_field`, `bus_trace`,
   `saas/cognitive:brain_surface`). No new signal I/O.
2. **Scores itself** — assembles one `SubsystemReading` per signal and runs them
   through its own `LambdaEngine` (isolated history at `state/metacognition_lambda.json`,
   the self-term store). `assess()` returns a `SelfAssessment`: `self_coherence`
   (Γ), `self_life_score` (SLS), `psi`, `divergence`, per-signal breakdown, and a
   top-level `truth_status`. This is **read-only** — it never publishes.
3. **Loops back** — `reflect()` does `assess()` then
   `publish_subfield("metacognition_monitor", state)`, so the monitor's reading
   re-enters `blend_field` as one more contributor: a delayed self-term on the
   whole-body field. This is the same closed loop `queen_metacognition` already
   runs; the monitor generalizes it to the whole cross-process signal set.

Stable by the Master Formula's own design: the echo is `tanh`-bounded, the blend
is an average, and the monitor's *inputs* are the other signals while its *output*
is its own sub-field — so there is no direct self-read amplification.

## Where it runs

- **Live**: `organism_daemon.breathe()` calls `get_metacognition_monitor().reflect()`
  every breath (guarded), so the self-assessment runs continuously and feeds back.
- **Read-only surface**: `GET /api/metacognition` returns `assess()` (never
  `reflect` — no publish from a GET) + provenance. Auto-metered + auth-gated.
- **Console page**: `frontend/src/shell/pages/MetacognitionPage.tsx` (nav route
  `/cognition/metacognition`) polls `/api/metacognition` and builds a client-side
  time series so you can watch the self-assessment *breathe* — self-coherence (Γ),
  awareness (ψ), and divergence sparklines, plus the per-signal breakdown with each
  signal's `truth_status`. A dormant monitor shows the honest `no_data` state.

## SaaS compliance

Every SaaS surface now carries a `provenance` block + honest top-level
`truth_status` (`gateway.py:_stamp` reusing `cognitive.provenance_block`).
`scripts/validation/audit_saas_compliance.py` asserts the contract — every
surface stamped, catalog counts honest, `charge-fee` 403 by default, provenance
reflects the real policy, no fabricated values in `aureon/saas/` — and writes
`docs/research/audits/saas_compliance_audit.{json,md}`.

## The live multi-daemon benchmark

`scripts/validation/benchmark_live_multidaemon.py` boots the three supervisord
daemons as **separate OS processes** (`hnc_live_daemon`, `organism_daemon`,
`operator_server`), lets them breathe for a bounded window, and verifies from the
outside that the organism senses itself across the boundary. Critical checks
(offline-robust): `daemon_boot`, `consensus_breathing`, **`metacognition_selfloop`**
(the `metacognition_monitor` sub-field appears in the shared trace — the loop
closed across processes), `operator_pulse`, `saas_compliance`. Network-dependent
source readings are informational (offline Layer-1 sources degrade honestly).
Writes `docs/research/benchmarks/live_multidaemon_benchmark.{json,md}`.

A recorded run: **5/5 critical + 3/4 informational** — the self-loop closed in a
real multi-process boot, with `metacognition_monitor` breathing alongside
`consciousness_module` and `dr_auris_throne`.

## Verify

```bash
AUREON_LLM_OFFLINE=1 pytest tests/test_metacognition_monitor.py tests/test_saas_compliance.py -q
AUREON_LLM_OFFLINE=1 python -m scripts.validation.audit_saas_compliance         # compliant, exit 0
AUREON_LLM_OFFLINE=1 python -m scripts.validation.audit_organism_unification    # 22/22 incl. metacognition_selfloop
AUREON_LLM_OFFLINE=1 python -m scripts.validation.benchmark_live_multidaemon    # boots 3 daemons, self-loop proven
```

## 📚 Related
- [`ORGANISM_UNIFICATION.md`](ORGANISM_UNIFICATION.md) — how every signal became connected + crosses processes
- [`COGNITIVE_SAAS.md`](COGNITIVE_SAAS.md) — the substrate as verified read APIs
- `aureon/core/aureon_lambda_engine.py` — the Master Formula + the β·Λ(t−τ) self-term this mirrors
