# The φ Celestial Observatory — every sky lane, one engine

*The capstone. One instrument that operates every sky-facing φ sensor through the
same unchanged phenolic engine and reports one consolidated picture.*

## What it is

`aureon/bio/celestial_observatory.py` doesn't add a new sensor — it **operates all of
them at once**. Each lane is an existing governed scorer (`score_signal`:
consent/provenance → controls → Operator/conscience veto → Test A / Test B →
separability at `ALPHA`); the observatory runs them and tabulates exactly what the
pre-registered test returned for each, neutrally. The φ engine is never modified.

## The lanes

| Lane | Domain | Source |
|------|--------|--------|
| Hydrogen Balmer | starlight (emission) | `sky_signal_adapter` catalog |
| Solar Fraunhofer | sunlight (absorption) | `sky_signal_adapter` catalog |
| Airglow | nightglow (self-emission) | `sky_signal_adapter` catalog |
| Diffuse night sky | diffuse background (anchor) | `sky_signal_adapter` |
| NASA stellar Wien | host-star colour | `sky_map` stellar sources (pooled) |
| Schumann modes | ionosphere (ELF) | `cosmic_scan` |
| Planetary tones | orbital (Cosmic Octave) | `cosmic_scan` |
| Space weather | solar (Kp/ap/F10.7) | `cosmic_scan` |
| DE440 coherence | planetary coherence | `coherence_scan` |
| Stargate lattice | Earth grid (ancient sites) | `sacred_lattice_scan` |
| Maeshowe solstice | chamber (solstice) | `sacred_lattice_scan` |
| Metatron geometry | φ-geometry (13-sphere) | `sacred_lattice_scan` |
| Master Formula Λ(t) | HNC substrate (6 modes) | `harmonic_core_scan` |
| Celtic Ogham | tree-tones (φ-scaled) | `harmonic_core_scan` |
| Ghost Dance | ancestral (Solfeggio) | `harmonic_core_scan` |
| Counter-frequency | φ/Fibonacci canon | `counter_frequency_scan` |
| All-sky map | RA/Dec convergence | `sky_map` (summary) |
| Sacred-lattice map | Earth grid convergence | `sky_map` (summary) |

## The boundary (load-bearing)

`OBSERVATORY_BOUNDARY`: statistical structure in derived signals only, across every
lane, through one unchanged φ engine — **NOT** a claim about the nature, composition,
or behaviour of any celestial object, and no efficacy claim. Each verdict is exactly
what the pre-registered test returned.

## The consolidated picture (whatever the tests return)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Lane | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Hydrogen Balmer | 7 | 0.907 | 0.575 | False |
| Solar Fraunhofer | 21 | 0.186 | 0.402 | False |
| Airglow | 10 | 0.877 | 0.655 | False |
| Diffuse night sky | 0 | — | — | False (anchor) |
| NASA stellar Wien | 1000 | 0.003 | 0.003 | **True** |
| Schumann modes | 7 | 1.000 | 0.847 | False |
| Planetary tones | 6 | 1.000 | 0.488 | False |
| Space weather | 14 | 0.003 | 0.355 | False |
| DE440 coherence | 23 | 0.940 | 0.704 | False |
| Stargate lattice | 12 | 0.907 | 0.252 | False |
| Maeshowe solstice | 18 | 1.000 | 0.682 | False |
| Metatron geometry | 12 | 0.815 | 0.225 | False |
| Master Formula Λ(t) | 6 | 1.000 | 0.384 | False |
| Celtic Ogham | 15 | 0.841 | 0.715 | False |
| Ghost Dance | 9 | 1.000 | 0.709 | False |
| Counter-frequency | 16 | 0.324 | 0.066 | False |

**16/16 lanes valid**; the all-sky map reports **4 converged cells of 63 scored** and the sacred-lattice Earth-grid map **0 of 9 scored**.
Every number is the engine's own verdict — the observatory makes no claim beyond
tabulating them.

![observatory](../research/figures/celestial_observatory.png)

## Closing the loop — the observatory feeds cognition

`emit_observatory(report)` publishes the consolidated picture as a
**`bio.observatory.run`** Thought on the ThoughtBus (plus a `celestial_observatory`
bus-trace), mirroring the human-proxy / phenolic-bridge emission idiom — so Aureon's
metacognition monitor and the Queen can sense the whole-sky reading. Emission is
best-effort: a throwing bus never crashes an observation. This makes the observatory a
live sensor of the organism, not just a report.

## The durable evidence artifact

`write_observatory_report(report, out_md, out_json=None)` serializes the consolidated
picture to a **markdown + JSON** record — every number copied verbatim from
`report.to_dict()`, nothing recomputed, the honest boundary printed in full. The body
carries no wall-clock timestamp, so two runs at the same `seed`/`nulls` produce
byte-identical files: the artifact is diff-stable and reproducible. The committed
snapshot lives at [OBSERVATORY_EVIDENCE.md](OBSERVATORY_EVIDENCE.md) (regenerate with the
`--report` command below); the full machine-readable record is `observatory_evidence.json`.

## Run it

```bash
python -m aureon.bio.celestial_observatory --render observatory.png
python -m aureon.bio.celestial_observatory --emit          # publish to cognition
python -m aureon.bio.celestial_observatory \
    --report docs/reports/OBSERVATORY_EVIDENCE.md \
    --report-json docs/reports/observatory_evidence.json   # durable evidence artifact
```

Benchmarked as Tier-A invariants **b20 "φ Celestial Observatory"** and
**b21 "Observatory → cognition"** (plus **b22 "Sacred lattice"**, **b23 "Harmonic core"**,
**b24 "Counter-frequency"**, and **b25 "Observatory evidence report"**) in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A 25/25). Fully offline; lanes whose
data is absent degrade to a skipped reading so it runs anywhere. See
[SENSOR_SUITE.md](SENSOR_SUITE.md) for the per-lane catalog.
