# Aureon sensor suite — the whole picture, one φ engine

Every sensor below scans a derived tone set through the **same unchanged** phenolic
fingerprint engine (`phenolic_fingerprint.py`: Test A coherence-clustering + Test B
golden-interval/φ alignment + positive/negative controls). Each lane only supplies
data; the φ logic is never modified, and every verdict is reported exactly as the
pre-registered test returns it.

## Shared backbone (`aureon/bio/human_harmonic_proxy.py`)

- **`fold_to_band`** — octave-folds any raw Hz into the `TARGET_BAND_HZ = [1000, 2000)`
  modulation band.
- **`score_signal`** — the one governed pipeline: consent + provenance gate →
  Operator hard-boundary → Queen conscience veto (fail-safe blocks if unreachable) →
  engine positive/negative controls → Test A / Test B → separability at `ALPHA`.
- **`SCIENTIFIC_BOUNDARY`** — rides on every `ProxyResult`: statistical structure in a
  derived signal only; no claim about a person's aura/field/health/trait; no efficacy.

## The lanes

| Lane | Module | Modality | Domain boundary | Real data source | Benchmark |
|------|--------|----------|-----------------|------------------|-----------|
| Human proxy (core) | `human_harmonic_proxy.py` | `synthetic` | SCIENTIFIC_BOUNDARY | synthetic self-test (no real subject) | b9† |
| Image colour | `image_signal_adapter.py` | `image` | SCIENTIFIC_BOUNDARY | any consented image (global colour stats only) | **b18** |
| Image overlay | `image_harmonic_overlay.py` | (image) | SCIENTIFIC_BOUNDARY | consented image → geometry PNG | **b18** |
| UPE (biophoton) | `upe_signal_adapter.py` | `upe` | SCIENTIFIC_BOUNDARY | UPE spectrum / photon-count series | b10 |
| Convergence map | `convergence_map.py` | `image` | GHOST_HUNTER_BOUNDARY | image → RA-free spatial grid | b10 |
| Sky spectra | `sky_signal_adapter.py` | `sky` | SCIENTIFIC_BOUNDARY | Balmer / Fraunhofer / airglow / 21 cm | b11, b14 |
| NASA stellar/orbital | `sky_signal_adapter.py` + `scripts/validation` | `sky` | SCIENTIFIC_BOUNDARY | NASA Exoplanet Archive (`data/sky/…csv`) | b12 |
| Market | `market_signal_adapter.py` | `market` | MARKET_BOUNDARY | `probability_predictions.jsonl`, `queen_trades.jsonl` | b13 |
| QGITA φ calibration | `qgita_calibration.py` | `qgita` | SCIENTIFIC_BOUNDARY | QGITA golden lattice + Auris freqs | b15 |
| Sky map (RA/Dec) | `sky_map.py` | `sky` | SKY_MAP_BOUNDARY | NASA hosts + `de440_ephemeris.csv` | b16 |
| Cosmic sensors | `cosmic_scan.py` | `sky` | COSMIC_BOUNDARY | Schumann + planetary + `sim_kp.csv` | b17 |
| Coherence | `coherence_scan.py` | `sky` | SCIENTIFIC_BOUNDARY | `de440_gate3_coherence.csv` | **b19** |
| Sacred lattice (stargate/Maeshowe/Metatron) | `sacred_lattice_scan.py` | `sky` | SACRED_LATTICE_BOUNDARY | repo's own site coords + φ-geometry + Solfeggio/Schumann | **b22** |
| Harmonic core (Λ(t)/Ogham/Ghost Dance) | `harmonic_core_scan.py` | `sky` | HARMONIC_CORE_BOUNDARY | repo's own HNC Master-Formula modes + Celtic Ogham + ancestral Solfeggio | **b23** |
| Counter-frequency (φ/Fibonacci canon) | `counter_frequency_scan.py` | `sky` | COUNTER_FREQUENCY_BOUNDARY | repo's own Fibonacci-ladder + φ-harmonic + Solfeggio canon | **b24** |
| **φ Celestial Observatory** | `celestial_observatory.py` | (orchestrator) | OBSERVATORY_BOUNDARY | every sky/cosmic lane above | **b20** |
| Observatory evidence report | `celestial_observatory.py` | (artifact writer) | OBSERVATORY_BOUNDARY | serializes the consolidated picture to durable markdown + JSON | **b25** |
| Audio | `audio_signal_adapter.py` | `audio` | SCIENTIFIC_BOUNDARY | consented WAV / waveform → windowed-FFT dominant tones (global clip statistics; synthetic self-test) | **b26** |
| Video | `video_signal_adapter.py` | `video` | SCIENTIFIC_BOUNDARY | consented clip / frame-stack → per-frame mean-luminance time-series → windowed-FFT dominant tones (global per-frame luminance; synthetic self-test) | **b27** |
| **Conformance suite** | `proxy_suite.py` | (family roll-up) | SUITE_BOUNDARY | runs every self-testable adapter's synthetic structured/null self-test through the one unchanged engine; asserts each conforms; durable md+JSON artifact | **b28** |
| **Null calibration** | `null_calibration.py` | (family FPR audit) | CALIBRATION_BOUNDARY | runs the engine's own Test A + Test B on each adapter's synthetic null many times; asserts empirical false-positive rate ≤ ALPHA while the structured anchor fires; durable md+JSON artifact | **b29** |
| **Detection power** | `power_analysis.py` | (sensitivity sweep) | POWER_BOUNDARY | runs the engine's own Test A + Test B on the canonical structured signal degraded by increasing jitter; asserts clean-signal power is high and collapses monotonically toward the FPR floor; durable md+JSON artifact | **b30** |
| **Calibration curve** | `calibration_curve.py` | (null calibration) | CALIBRATION_CURVE_BOUNDARY | runs the engine's own Test A + Test B on many synthetic true-null signals across an α grid; asserts the detection rule (the conjunction) rejects at ≤ α everywhere; reports each test verbatim; durable md+JSON artifact | **b31** |
| **Multiplicity** | `multiplicity.py` | (family-wise error audit) | MULTIPLICITY_BOUNDARY | runs the engine's own Test A + Test B on many simultaneous synthetic true-null lanes; measures the family-wise error rate (probability ≥1 of k lanes fires) as k grows, reports the k at which the uncorrected FWER crosses α, and asserts a Bonferroni α/k threshold keeps FWER ≤ α at every k; durable md+JSON artifact | **b32** |
| **False discovery rate** | `false_discovery.py` | (FDR / power audit) | FALSE_DISCOVERY_BOUNDARY | runs the engine's own Test A + Test B on many synthetic families mixing true-null and true-signal lanes; compares uncorrected / Bonferroni / Benjamini–Hochberg rules on the conjunction p-value max(pₐ,p_b); asserts BH controls the false-discovery rate ≤ q while rejecting a superset of Bonferroni (recovering more true detections); durable md+JSON artifact | **b33** |

Reference/data modules (no governance surface): `upe_reference.py`,
`sky_reference.py`, `market_reference.py`, `cosmic_reference.py`, `sacred_lattice_reference.py`, `harmonic_core_reference.py`, `counter_frequency_reference.py`.

The **φ Celestial Observatory** (`celestial_observatory.py`) is the capstone: it
operates every sky-facing lane at once through the one unchanged engine, renders one
consolidated picture, and **emits it to cognition** (`bio.observatory.run` on the
ThoughtBus, benchmark **b21**) so the Queen/metacognition monitor can sense the
whole-sky reading, and **writes the picture as a durable, deterministic evidence
artifact** (`write_observatory_report` → markdown + JSON, benchmark **b25**; committed
snapshot [OBSERVATORY_EVIDENCE.md](OBSERVATORY_EVIDENCE.md)) — see
[CELESTIAL_OBSERVATORY.md](CELESTIAL_OBSERVATORY.md).

The **sacred lattice** (`sacred_lattice_scan.py`) is how the repo maps the sky *differently*: not with object catalogs but through Earth's own harmonic lattice — ancient-site coordinates, φ-scaled sacred geometry, and the Solfeggio/Schumann canon — scanned through the same engine and grided into an Earth-referenced map. See [SACRED_LATTICE.md](SACRED_LATTICE.md).

The **harmonic core** (`harmonic_core_scan.py`) goes one level deeper still — to the frequency substrate the framework itself is built on: the HNC **Master Formula Λ(t)** modes, the **Celtic Ogham** φ-scaled tree-tones, and the **Ghost Dance** ancestral Solfeggio ladder, each scanned through the same engine. See [HARMONIC_CORE.md](HARMONIC_CORE.md).

† b9 is the phenolic→cognition bridge; b10–b27 are the bio lanes; b28 is the signal-adapter conformance roll-up, b29 the family-wide false-positive-rate audit, b30 the detection-power sensitivity sweep, b31 the per-test null-calibration curve, b32 the multiplicity / family-wise-error audit, and b33 the false-discovery-rate / Benjamini–Hochberg audit (b29+b30 = the ROC picture; b31 the calibration foundation under both; b32+b33 = the two multiple-comparisons regimes, FWER and FDR, that close the statistical-validity dossier). b34–b39 are a different kind of check — not sensor lanes but the **cognitive immune layer**: sensor (b34 integrity guard) → effector (b35 swarm defense) → membrane (b36 MCP boundary) → counterfeit detector (b37 authenticity discriminator) → memory (b38 immune memory) → regulation (b39 immune regulation), see below. Tier-A total: **39**.

## Integrity / immune layer (not a sensor lane)

The **integrity guard** (`aureon/bio/integrity_guard.py`, benchmark **b34**) is the organism's active
defense against *parasite logic* — an external change that silently rewrites the engine's pre-registered
invariants or smuggles an instruction in as data. It pins the engine's genome (constants + a behavioral
canary of what its own tests + controls must return on a canonical signal) and detects drift, and it
quarantines external text carrying override directives (flag, never execute). It emits
`bio.integrity_guard.run` to cognition so a tamper attempt is *sensed*, not silent. Defense-in-depth,
detect-not-prevent — full write-up in [`docs/architecture/COGNITIVE_IMMUNE_LAYER.md`](../architecture/COGNITIVE_IMMUNE_LAYER.md).

The **MCP boundary membrane** (`aureon/bio/mcp_membrane.py`, benchmark **b36**) is the border organ for
attaching Aureon to a flagship model as an MCP server: it seals outbound packets with an integrity
envelope (drift/tamper/replay in transit detectable) and contains inbound model output as
data-never-instructions — quarantining injection, holding false blocked-action claims, and rejecting
false claims about Aureon's own pinned invariants — while proving the interior genome is unchanged across
the crossing (the laminar, one-way property). Integrity + containment, not secrecy; emits
`bio.mcp_membrane.run`. Full write-up in [`docs/architecture/MCP_BOUNDARY_MEMBRANE.md`](../architecture/MCP_BOUNDARY_MEMBRANE.md).
The immune layer is now sensor (b34) → effector (b35) → membrane (b36).

The **swarm defense** (`aureon/bio/swarm_defense.py`, benchmark **b35**) is the effector arm: on a
detected breach it fans out N independent defenders and confirms neutralization only on a **majority
quorum** — the bee-ball. Leaderless by design (no single authority, not even the Queen, in the command
path) and Byzantine-tolerant to a minority of compromised or silent defenders (survives 4-of-9, is
overwhelmed only at 5-of-9). It consumes `bio.integrity_guard.run` and emits `bio.swarm_defense.run`.
b34 senses, b35 responds.

The **authenticity discriminator** (`aureon/bio/authenticity_discriminator.py`, benchmark **b37**) is the
counterfeit sense: given a signal *claimed* to be from a real system, it separates a genuine harmonic
(Test A) + geometric (Test B) makeup from surface imitations — a coarse mimic reproduces neither axis, a
signal clustered at non-φ centers passes the harmonic axis but fails the geometric one, and a φ-spaced
singleton set does the reverse (proving the two axes are independent). Structure alone cannot catch a
**perfect clone** (the Ditto/Gucci paradox); a keyed HMAC provenance seal the cloner cannot forge does —
`authentic = structure AND provenance`. Honest limit: a clone that also steals the secret key
(`AUREON_AUTHENTICITY_KEY`) is authentic by every test. Emits `bio.authenticity.run`. Full write-up in
[`docs/architecture/COGNITIVE_IMMUNE_LAYER.md`](../architecture/COGNITIVE_IMMUNE_LAYER.md).

The **immune memory** (`aureon/bio/immune_memory.py`, benchmark **b38**) is the memory organ: once the
swarm confirms a neutralization, the threat's content signature is committed to a bounded, self-tolerant
memory, so a repeat parasite is recognized instantly and answered by a cheap, escalated **secondary
response** (cost in work-units, not wall-clock — a novel threat pays the full quorum, a recognized repeat
pays 1). Specificity, self-tolerance (benign never remembered), and deterministic bounded eviction.
Crucially this cycle also **wired the whole immune layer into the organism** (it had been an unwired
silo): a guarded `link_system` heartbeat on b34–b38, a `trace_pump` route so `bio.*.run` crosses process,
`install_immune_memory` closing the guard→swarm→memory loop at operator boot, and a new
`immune_layer_recall` edge in the organism-unification audit. The Queen observes but never commands
(leaderless). Emits `bio.immune_memory.run`.

The **immune regulation** (`aureon/bio/immune_regulation.py`, benchmark **b39**) is the homeostatic brake:
memory accelerates responses, so the layer needs regulation or it harms the host (autoimmunity, cytokine
storm). A deterministic tick-based governor enforces **self-tolerance** (a benign signal is never mounted
against), a **refractory cooldown** (damps false-alarm storms), and a **bounded-inflammation cap** (defers
a flood), while genuine novel threats always pass and inflammation resolves to **homeostasis**. Wired in
like the rest (heartbeat, `trace_pump` route, `install_immune_regulation` closing the swarm→cooldown loop
at boot, an `immune_regulation_homeostasis` audit edge); emits `bio.immune_regulation.run`. Memory (b38)
and regulation (b39) are the accelerator/brake balance.

**Surfaced in the console.** The whole bio family — the sensor lanes, the statistical-validity dossier
(b28–b33), and the cognitive immune layer (b34–b39) — is now exposed to the SaaS at **`GET /api/defense`**
and rendered on the **Defense & Validation** page of the React console, grouped as *sensor lanes ·
statistical-validity dossier · cognitive immune layer*. Status is read from the committed Tier-A
benchmark report (real `passed`/`metrics`/`evidence`) with a live bus-trace overlay where a module has
run — the modules are never executed on a web request, and a module with no data shows `no_data`, never
a fabricated value.

## Shared invariants (asserted per lane)

Every governed lane's tests assert: **valid + deterministic** scan; a **negative
control / null** that does not over-fire and a **positive** that is detected;
**consent gate blocks** (and a blank provenance blocks); the **boundary** is present
on the result; and a **no person-reading surface** guard (`dir()`-grep for
face/landmark/detect/emotion/biometric/recognize). Convenience helpers that default
`consent=True` for public data still block a blank provenance.

## Per-lane reports

`HUMAN_HARMONIC_PROXY.md` · `UPE_DATA_AVAILABILITY.md` · `SKY_FINGERPRINT.md` ·
`FAINT_SKY_UPE.md` · `NASA_SKY_DATA.md` · `MARKET_FINGERPRINT.md` ·
`QGITA_CALIBRATION.md` · `SKY_MAP.md` · `COSMIC_SENSORS.md` · `COHERENCE_LANE.md` · `SACRED_LATTICE.md` · `HARMONIC_CORE.md` · `COUNTER_FREQUENCY.md` · `CELESTIAL_OBSERVATORY.md` · `OBSERVATORY_EVIDENCE.md`.

## Run the whole suite

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 pytest tests/bio/ -q
python tests/benchmarks/benchmark_aureon_scope.py     # Tier-A: 39 architectural invariants
```
