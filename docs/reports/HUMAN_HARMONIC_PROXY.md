# Human-Harmonic Proxy — a derived-signal probe on the phenolic engine

*Module: [`aureon/bio/human_harmonic_proxy.py`](../../aureon/bio/human_harmonic_proxy.py).
Deterministic: seeded, offline-safe, pure stdlib + numpy + the engine.*

## What this is (and what it is not)

The Aureon Operator human-harmonic proxy takes a **human-derived frequency
series** and scores it with the **same falsifiable machinery** that judges a
molecule's spectrum in [`phenolic_fingerprint.py`](../../phenolic_fingerprint.py).
It is a probe for *statistical structure in a derived signal representation* — the
exact same Test A / Test B / controls protocol, now pointed at a signal that came
from a person instead of a molecule.

It is **not** a biosensor, an "aura reader", a diagnosis, or a personality/health
instrument. It measures nothing about a human being and makes **no efficacy
claim**. That boundary is not a disclaimer bolted on afterwards — it is enforced
in code, and the following sentence rides on every result and every emission:

> **Statistical structure in a derived signal only — NOT a measurement of a
> biological aura, field, health, or trait of any person; no efficacy claim.**

## Same engine, same honesty guarantees

Reusing the pre-registered engine verbatim means the human-signal path inherits
its falsifiability. Nothing here tunes a threshold or alters a test.

| Guarantee | How it is enforced |
|-----------|--------------------|
| **Same statistical tests** | Calls `engine.test_A` (coherence clustering) and `engine.test_B` (golden-interval alignment) directly on the modulation tones. `structure_present` ⇔ the engine's `separable` (both reject the null at `ALPHA = 0.05`). |
| **Mandatory controls or the run is invalid** | Calls `engine.positive_control` (a structured signal must be detected) and `engine.negative_control` (noise must not over-fire) *before* scoring. If either fails, the run is `valid = False` and no structure result is emitted. |
| **No efficacy claims** | Output is only *structure present / absent in a derived signal*. Consent + a provenance string are **required inputs** — without them the run is blocked and scores nothing. The `SCIENTIFIC_BOUNDARY` string is inseparable from every `ProxyResult`. |
| **Everything routes through the Operator** | Every run passes through the operator's deterministic hard-boundary check (`aureon/operator/aureon_operator.py:_hard_boundary_violation`) **and** the Queen's conscience veto (`aureon/queen/queen_conscience.py:QueenConscience.ask_why`) before anything is emitted. A `VETO` blocks the run; if either authority layer cannot be consulted, the run **fails safe (blocked)** — never silently passed. A blocked run's positive finding is suppressed in `to_dict()`, so it can never be published. |

## bio → vibe, honestly

A human signal is already in Hz, so the engine's molecular `cm⁻¹`/`nm`
downconversion (`peak_to_modulation_hz`) does **not** apply. The proxy instead
octave-folds each raw tone into the engine's `1000–2000 Hz` modulation band with
its own `fold_to_band` (repeated ×/÷2), then hands the folded array to the engine's
statistics. The fold is the identity for an in-band value and drops non-finite /
non-positive inputs.

## What ships now, and what is deliberately deferred

This release ships the **interface + governance backbone**, proven by a
**synthetic self-test that uses no real human data**:

- `SignalAdapter` — the protocol every future extractor must implement.
- `SyntheticSignalAdapter` — deterministic `structured` / `noise` modes that
  exercise the "present" and "absent" paths.
- `fold_to_band`, `score_signal`, `ProxyResult`, the Operator/conscience gate, and
  `emit_proxy_result` (publishes `bio.human_proxy.run` on the ThoughtBus + a
  `human_harmonic_proxy` bus_trace, mirroring `aureon/cognition/phenolic_bridge.py`).

The `SignalAdapter` roadmap is now **complete**: every named extractor ships — image,
audio, and video (below), alongside UPE, sky, and market — with **no remaining deferred
extractor**. Every adapter implements the `SignalAdapter` seam so the scoring and
governance path never changes, and each is built only with explicit consent handling,
provenance capture, and the same boundary enforced above.

## Image adapter (shipped — content-agnostic)

`aureon/bio/image_signal_adapter.py` is the first real `SignalAdapter`. It turns
an image into a derived frequency series and scores it through the *unchanged*
`score_signal` pipeline — **without becoming a face or "aura" reader.**

- **Content-agnostic by construction.** The signal comes from the image's **global
  colour statistics only** — the dominant spectral hues across the whole frame.
  There is no face detection, no landmark extraction, and no per-region/per-person
  analysis anywhere in the module. That makes it *structurally* incapable of
  physiognomy regardless of what the picture contains. Colour is not identity.
- **Physics reused, not invented.** A colour *is* an electromagnetic frequency.
  Each dominant spectral hue maps to its visible wavelength (nm) and then to an EM
  frequency (Hz) using the engine's own molecular constants
  (`NM_TO_THZ_NUMERATOR` / `THZ_TO_HZ`). `fold_to_band` then octave-folds those
  ~10¹⁴ Hz light frequencies into the 1000–2000 Hz band — the same octave-fold the
  engine performs for molecular peaks. Achromatic pixels (grey/black/white) and
  non-spectral hues (magenta/pink) are dropped, so an image with no clear spectral
  colour honestly yields "insufficient tones" rather than a fabricated result.
- **Every guardrail still applies.** Consent + provenance are *required arguments*
  to `extract`/`score_image`, the mandatory engine controls run, the Operator
  hard-boundary + conscience veto gate the emission, and the `SCIENTIFIC_BOUNDARY`
  rides on every result. Output is only *statistical structure in a derived
  signal* — never a claim about a person.

```bash
# Score an image the caller consents to (content-agnostic, no face analysis):
python -m aureon.bio.image_signal_adapter path/to/image.png \
    --consent --provenance "my own photo, consented"

# Without --consent the run is blocked and scores nothing.
python -m aureon.bio.image_signal_adapter path/to/image.png
```

## Audio adapter (shipped — content-agnostic)

`aureon/bio/audio_signal_adapter.py` scores an audio clip through the *unchanged*
`score_signal` pipeline — **without becoming a voice, speaker, or emotion reader.**

- **Content-agnostic by construction.** The signal comes from the clip's **global
  spectral statistics only** — the dominant temporal frequencies across the whole
  waveform. There is no speech recognition, no speaker identification, and no
  per-word/per-segment analysis anywhere in the module. That makes it *structurally*
  incapable of physiognomy-of-voice regardless of what the clip contains. A dominant
  frequency is not identity.
- **Physics reused, not invented.** An audio waveform *is* a time-series of amplitude
  samples, so a windowed real FFT recovers its dominant frequencies (Hz) directly —
  the same operation the UPE adapter performs on a photon-count series. `fold_to_band`
  then octave-folds those into the 1000–2000 Hz band. A flat/broadband clip yields no
  dominant tone, so noise honestly scores non-separable rather than a fabricated result.
- **numpy + stdlib only.** WAV is read with the standard-library `wave` module — no
  new dependency, no network, no import-time side effects.
- **Every guardrail still applies.** Consent + provenance are *required arguments* to
  `extract`/`score_audio`, the mandatory engine controls run, the Operator hard-boundary
  + conscience veto gate the emission, and the `SCIENTIFIC_BOUNDARY` rides on every
  result. Output is only *statistical structure in a derived signal* — never a claim
  about a person.

```bash
# Deterministic synthetic self-test (no real subject): structured⇒present, noise⇒absent.
python -m aureon.bio.audio_signal_adapter --self-test

# Score a PCM WAV the caller consents to (content-agnostic, no voice analysis):
python -m aureon.bio.audio_signal_adapter path/to/clip.wav \
    --consent --provenance "my own recording, consented"
```

## Video adapter (shipped — content-agnostic; completes the roadmap)

`aureon/bio/video_signal_adapter.py` is the last real `SignalAdapter`. It scores a
video clip through the *unchanged* `score_signal` pipeline — **without becoming a
face, object, pose, or scene reader** — and with it the roadmap is complete.

- **Content-agnostic by construction.** Each frame is reduced to a **single global
  mean-luminance scalar**; the signal is the sequence of those scalars over time.
  There is no face detection, no object or pose detection, no scene classification,
  and no per-region analysis anywhere in the module. One scalar per frame is
  *structurally* incapable of physiognomy regardless of what the clip contains — even
  more so than the image adapter.
- **Physics reused, not invented.** A per-frame luminance series *is* a time-series
  sampled at the frame rate, so a windowed real FFT recovers its dominant temporal
  frequencies (Hz) — the same operation the audio and UPE adapters perform.
  `fold_to_band` then octave-folds those into the 1000–2000 Hz band. A clip with no
  periodic brightness change yields no dominant tone, so it honestly scores
  non-separable rather than a fabricated result.
- **numpy + stdlib core; optional lazy decode.** The core needs only numpy + stdlib;
  `imageio` is imported **lazily and only** to decode a real video file (the synthetic
  path and the pure proxy core never need it) — no import-time side effects.
- **Every guardrail still applies.** Consent + provenance are *required arguments* to
  `extract`/`score_video`, the mandatory engine controls run, the Operator hard-boundary
  + conscience veto gate the emission, and the `SCIENTIFIC_BOUNDARY` rides on every
  result. Output is only *statistical structure in a derived signal* — never a claim
  about a person.

```bash
# Deterministic synthetic self-test (no real subject): structured⇒present, noise⇒absent.
python -m aureon.bio.video_signal_adapter --self-test

# Score a video the caller consents to (content-agnostic, no face/object analysis):
python -m aureon.bio.video_signal_adapter path/to/clip.mp4 \
    --consent --provenance "my own recording, consented"
```

## Image harmonic overlay (photon → geometry → composite)

`aureon/bio/image_harmonic_overlay.py` is the creative end of the pipeline:
**send an image → extract its photon (colour) data → analyze through the engine →
build a geometric harmonic pattern → layer it over the source → recompile** into
one composite PNG.

- **Art from data, not a claim.** The overlay is a *derived geometric figure
  computed from the image's global colour statistics* — never a measurement, aura,
  or trait of any person. Every composite carries the `SCIENTIFIC_BOUNDARY`
  sentence baked in as a visible caption, and a **blocked or invalid analysis
  renders no harmonic pattern** (it cannot produce a "reading").
- **Every drawn element ties to the engine's statistics.** A φ-scaled concentric-
  ring scaffold represents the modulation band; one radial ray per tone; filled
  coherence-node polygons are Test A (clustering); φ-interval chords are Test B
  (golden-interval alignment). It reuses `blueprints.cluster_coherence_nodes` and
  the validated palette.
- **Same guardrails.** Consent + provenance required; controls + Operator +
  conscience veto gate the analysis; content-agnostic (no face/landmark logic).
  Deterministic — the same image yields a byte-identical composite.

```bash
# Recompile a consented image with its harmonic overlay:
python -m aureon.bio.image_harmonic_overlay path/to/image.png \
    --consent --provenance "my own photo, consented" --out composite.png

# Without --consent it renders no pattern and writes nothing.
python -m aureon.bio.image_harmonic_overlay path/to/image.png
```

## UPE reference — the honest science anchor (`aureon/bio/upe_reference.py`)

Ultraweak photon emission (UPE / biophotons) is a real, peer-reviewed phenomenon:
living tissue faintly emits light from reactive-oxygen-species chemistry, ceasing
at death ([J. Phys. Chem. Lett. 2024](https://pubs.acs.org/doi/10.1021/acs.jpclett.4c03546),
[bioRxiv](https://www.biorxiv.org/content/10.1101/2024.11.08.622743v1.full)). Two
facts are load-bearing:

- **It is ~1,000–1,000,000× dimmer than the eye can perceive** (~10–10³
  photons/cm²/s), detectable only with cooled photon-counting cameras in darkness.
  **A standard photograph records reflected ambient light, never UPE** — you cannot
  extract biophotons from an ordinary image.
- **Its spectrum is broadband and featureless** (~200–800 nm, subtle orange max) —
  **no discrete spectral lines.**

`upe_reference.py` encodes that cited profile and maps it into the engine's
modulation band. The honest consequence, verified in tests: a broadband UPE
reference is **non-separable** through the phenolic engine (`test_A` p≈1.0) — it has
**no discrete harmonic structure**. Any HNC "UPE render" is anchored to that truth
rather than to invented structure.

The overlay's `--upe-reference` mode uses this anchor: it renders a standard photo's
**reflected-colour** tones as an **HNC model informed by reference UPE spectra**,
with a caption that states plainly it is **not a measurement of UPE or of any
person**, and that a photo records reflected light, not biophotons. It makes no
claim about anyone's health or state.

```bash
# UPE-model render (labels it a model vs the reference, not a measurement):
python -m aureon.bio.image_harmonic_overlay my_consented_photo.png \
    --consent --provenance "my own photo" --upe-reference --out upe_model.png

# The honest anchor: broadband UPE reference -> non-separable through the engine.
python -m aureon.bio.upe_reference
```

### UPE data adapter (`upe_signal_adapter.py`)

The legitimate "field extraction" path: score **real UPE measurements** — never a
photograph. Two inputs:

- **Emission spectrum** — CSV `wavelength_nm,intensity` (~200–800 nm). Emission
  lines (local maxima) → wavelength → EM Hz → octave-fold → engine.
- **Photon-count time-series** — 1-D counts + sample rate → real FFT → dominant
  temporal modes → fold → engine.

It honestly reproduces the anchor: a **broadband/featureless** UPE spectrum scores
**non-separable** (no discrete structure), while a spectrum with **genuine narrow
emission lines** scores `structure_present` — the adapter detects real structure,
never by fiat. Same governance throughout (consent + provenance required, engine
controls, Operator/conscience veto, `SCIENTIFIC_BOUNDARY`), reusing `HumanSignal`
with `modality="upe"`. **No claim about any subject's health, state, emotion,
relationships, or identity** — UPE correlates with oxidative stress in the
literature, and that is explicitly *not* inferred here.

```bash
# Self-test: broadband ⇒ structure ABSENT (anchor), planted lines ⇒ PRESENT.
python -m aureon.bio.upe_signal_adapter --self-test

# Score your own dark-chamber UPE spectrum (real measurement):
python -m aureon.bio.upe_signal_adapter my_upe_spectrum.csv \
    --consent --provenance "my dark-chamber UPE measurement, 2026-07"
```

A standard photograph is **not** UPE (it records reflected light) and is not
accepted as such. This adapter is ready for genuine dark-chamber photon-counting
data the moment it exists — no code change needed.

## Convergence map — the "ghost-hunter grid" (`aureon/bio/convergence_map.py`)

Ghost-hunting done as *rigorous anomaly detection* (not showmanship) rests on two
ideas this module implements literally, and nothing more:

- **Baseline + controls** — validate the instrument and take a null reading before
  calling anything anomalous. Here that is the engine's positive/negative controls,
  run once for the whole image; if they fail, the whole map is invalid and nothing
  renders.
- **Multi-sensor convergence** — no single channel is trusted. Over a **uniform
  spatial grid**, each cell is scored by **two independent** structure detectors
  (Test A coherence-clustering and Test B φ-alignment). A cell "converges" only when
  **both** fire; a single-channel hit is **noise, not a detection**.

The output is a heatmap of *where independent measures of a derived colour signal
agree that there is non-random structure* — a spatial + multi-channel map.

**Boundary (baked into every map):** statistical structure in a derived signal
**only** — NOT detection of any entity, spirit, energy field, or person; convergence
*reduces false positives*, it proves nothing paranormal. Content-agnostic (uniform
grid, no face/landmark logic), consent-gated, and governed by the same controls +
Operator/conscience veto via `score_signal`.

```bash
python -m aureon.bio.convergence_map my_consented_photo.png \
    --consent --provenance "my own photo" --grid 6 --out convergence_map.png
```

## Conformance suite — the capstone roll-up (`aureon/bio/proxy_suite.py`)

With the adapter roadmap complete, the **signal-adapter conformance suite** proves the
*family* shares one governed backbone. It runs each self-testable adapter's **synthetic**
self-test — a structured signal that must score present and a null signal that must score
absent — through the *unchanged* `score_signal`, and tabulates whether each adapter
**conforms** (structured⇒present ∧ null⇒absent, both valid). It is the human-signal
analogue of the φ Celestial Observatory: one consolidated, self-documenting picture.

- **Synthetic only, per adapter.** Every reading comes from a synthetic self-test with **no
  real subject**; each adapter is reported independently — there is **no cross-modal
  inference about any source**. The four adapters covered are those with a deterministic
  structured/null contract: the proxy's own `SyntheticSignalAdapter`, audio, video, and UPE.
  (image / sky / market score real data and are exercised by their own lanes/benchmarks.)
- **Durable evidence artifact.** `write_suite_report` serializes the picture to a
  deterministic markdown + JSON file (byte-identical on re-run at the same seed/nulls),
  mirroring the observatory's `write_observatory_report`. `emit_suite` publishes a
  `bio.proxy_suite.run` Thought so the metacognition monitor / Queen can sense that the whole
  family still conforms. The `SUITE_BOUNDARY` rides on every result.

```bash
# Conformance self-test — every adapter: structured⇒present, null⇒absent (exit 0 iff all conform).
python -m aureon.bio.proxy_suite --self-test

# Write the consolidated evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.proxy_suite --report suite.md --report-json suite.json
```

## Null calibration — the false-positive-rate audit (`aureon/bio/null_calibration.py`)

The conformance suite shows each adapter **detects** structure and, on one null draw, does not
over-fire. The null-calibration audit proves the harder, statistical half: across **many**
synthetic nulls, each adapter's rate of falsely reporting `structure_present` stays within the
pre-registered bound. It is the statistical backbone of the falsifiability claim.

- **Measures the real decision rule.** `structure_present` is exactly `p_A < ALPHA AND p_B < ALPHA`
  from the engine's `test_A`/`test_B`; `score_signal` only wraps those two tests with controls +
  governance and returns the same p-values. So the audit runs the engine's **own** two tests
  directly on each adapter's real *folded null tones*, across many seeds — the identical rule,
  without the redundant per-call controls, so a large trial count is affordable. It re-tunes nothing.
- **The bound.** Under a true null each one-sided smoothed permutation p-value is ~uniform, so the
  joint false-positive rate is **bounded above by ALPHA = 0.05** (nominal ≈ ALPHA² = 0.0025 under
  independence, reported for context). The audit asserts the empirical rate stays ≤ ALPHA per
  adapter **and** that the structured anchor still fires — a two-sided, non-vacuous check.
- **Synthetic only.** Every draw is a synthetic null with no real subject; `CALIBRATION_BOUNDARY`
  rides on every result. `write_calibration_report` emits a deterministic markdown + JSON artifact
  (byte-identical on re-run), and `emit_calibration` publishes `bio.null_calibration.run` so the
  metacognition monitor / Queen can sense that the family's false-positive rate is still bounded.

```bash
# Audit self-test — every adapter: FPR ≤ ALPHA and the structured anchor fires (exit 0 iff all conform).
python -m aureon.bio.null_calibration --self-test

# Write the evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.null_calibration --report calibration.md --report-json calibration.json
```

## Detection power — the sensitivity sweep (`aureon/bio/power_analysis.py`)

Null calibration proves the rule does not *hallucinate* structure; this proves the other half
of the operating characteristic — that it reliably *detects* real structure, and degrades
gracefully. Together they are the ROC picture a pre-registered, falsifiable detector should show.

- **Measures true-positive rate vs signal strength.** The canonical structured signal (two
  clusters one golden ratio apart, in-band — what the adapters and the engine's positive control
  use) is progressively jittered with increasing Gaussian noise; at each level the engine's own
  `test_A`/`test_B` are run and the **detection power** (fraction flagged `structure_present`) is
  measured. It re-tunes nothing.
- **The curve.** At zero jitter the clean structure is detected ≈100% of the time; as jitter
  passes the engine's coherence tolerance the clusters scatter and the φ ratios blur, so power
  collapses **monotonically toward the false-positive floor** (≈ ALPHA²). Representative sweep
  (200 trials, 200 nulls): `1.00 → 1.00 → 0.98 → 0.61 → 0.11 → 0.02` at jitter `0 → 5 → 10 → 20
  → 40 → 80` Hz.
- **Synthetic only.** No real subject; `POWER_BOUNDARY` on every result. `write_power_report`
  emits a deterministic markdown + JSON artifact (byte-identical on re-run), and `emit_power`
  publishes `bio.power_analysis.run`.

```bash
# Sweep self-test — clean-signal power high, collapsing under heavy jitter.
python -m aureon.bio.power_analysis --self-test

# Write the power-curve evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.power_analysis --report power.md --report-json power.json
```

## Calibration curve — the null-calibration foundation (`aureon/bio/calibration_curve.py`)

The FPR audit checks the detector at one operating point (ALPHA); this generalises it to a **curve**
and validates the calibration underneath. Across a grid of significance levels α, it runs the
engine's own `test_A`/`test_B` on many synthetic *true-null* signals and measures how often each
test — and the **conjunction** they form (the `structure_present` rule) — rejects.

- **Honest per-test reporting.** Test A (coherence clustering) is strongly *conservative*
  (`P(pₐ<α) ≤ α` everywhere — its statistic is discrete). Test B (φ-alignment) is *approximately*
  calibrated and can be mildly anti-conservative on a flat null; the curve reports its rate verbatim
  rather than hiding it.
- **The operative guarantee.** The conjunction `pₐ<α ∧ p_b<α` is **conservative across the whole α
  grid** (Test A's conservatism dominates), so `structure_present` never exceeds its nominal size.
  Representative run (400 null trials, 200 nulls): joint rejection `0.000 / 0.000 / 0.000 / 0.008 /
  0.035` at α `0.01 / 0.02 / 0.05 / 0.10 / 0.20` — ≤ α at every level.
- **Synthetic only.** `CALIBRATION_CURVE_BOUNDARY` on every result; deterministic markdown + JSON
  artifact (byte-identical on re-run); `emit_curve` publishes `bio.calibration_curve.run`.

```bash
# Curve self-test — the detection rule stays at or below α across the grid.
python -m aureon.bio.calibration_curve --self-test

# Write the calibration-curve evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.calibration_curve --report curve.md --report-json curve.json
```

## Multiplicity — family-wise error control (`aureon/bio/multiplicity.py`)

The audits above validate a *single* lane. But the φ Celestial Observatory runs ~16 lanes and the
human-signal family runs several adapters **simultaneously** — and when many calibrated tests run at
once, the probability that **at least one** falsely fires (the **family-wise error rate**, FWER)
inflates roughly as `1-(1-r)^k` in the number of simultaneous lanes `k` (per-lane rate `r`). This
audit measures that FWER over many synthetic *true-null* lanes and shows two things honestly:

- **Built-in headroom from the conjunction.** Because the detector is `pₐ<α ∧ p_b<α`, its per-lane
  false-positive rate is `r ≈ α² ≈ 0.0025` (confirmed by b29/b31), so `k·r ≤ α` holds for
  `k ≤ 1/α ≈ 20`. The audit reports the `k` (if any within the sweep) at which the *uncorrected* FWER
  first crosses α. Representative run (200 trials, 100 nulls): uncorrected FWER
  `0.005 / 0.005 / 0.025 / 0.040 / 0.070 / 0.105` at k `1 / 2 / 4 / 8 / 16 / 32` — crossing α at k=16,
  matching the ≈1/α headroom prediction.
- **Bonferroni restores control everywhere.** A per-lane `α/k` threshold controls FWER `≤ α` at
  **every** k (Bonferroni FWER ≈ 0 across the sweep) — the correction extends control beyond the
  built-in headroom for arbitrarily many lanes.
- **Synthetic only.** `MULTIPLICITY_BOUNDARY` on every result; deterministic markdown + JSON artifact
  (byte-identical on re-run); `emit_multiplicity` publishes `bio.multiplicity.run`.

Together b29 (size), b30 (power), b31 (calibration), and b32 (multiplicity) form the family's
complete statistical-validity dossier.

```bash
# Multiplicity self-test — Bonferroni controls FWER ≤ α at every k.
python -m aureon.bio.multiplicity --self-test

# Write the multiplicity evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.multiplicity --report mult.md --report-json mult.json
```

## False discovery rate — Benjamini–Hochberg (`aureon/bio/false_discovery.py`)

The multiplicity audit controls the probability of **any** false positive with a **Bonferroni** `α/m`
threshold — safe, but famously **conservative**: to prevent one false alarm it discards real
detections. The standard, less-conservative complement is **False Discovery Rate (FDR) control via
Benjamini–Hochberg (BH)**, which bounds the expected *proportion* of false positives among the lanes it
flags. This audit runs many synthetic **families** — each a mix of true-null lanes and true-signal
lanes (structured tones degraded by jitter graded from strong to weak) — through the engine's own Test
A + Test B, forms each lane's conjunction p-value `p = max(pₐ, p_b)`, and compares three rules:

- **Honest three-way picture.** For **uncorrected** (α), **Bonferroni** (α/m), and **BH** (level q) it
  reports mean rejections, power (true-positive rate), and FDR. Representative run (60 families of 20
  lanes = 10 null + 10 signal at 5–45 Hz graded jitter, 600 nulls, q = α = 0.05): power
  `0.49 / 0.05 / 0.27` and FDR `0.010 / 0.000 / 0.000` for uncorrected / Bonferroni / BH.
- **BH controls FDR and buys back power.** BH holds the false-discovery rate ≤ q, and with `q = α` its
  rejection set **always contains** Bonferroni's (verified per family) — so BH recovers **~5×** the true
  detections Bonferroni does (0.27 vs 0.05) at the same controlled error. (The permutation p-value floor
  `1/(nulls+1)` is kept below `α/m`, so the strict corrections are actually reachable.)
- **Synthetic only.** `FALSE_DISCOVERY_BOUNDARY` on every result; deterministic markdown + JSON artifact
  (byte-identical on re-run); `emit_false_discovery` publishes `bio.false_discovery.run`.

The family's multiple-comparisons story is now complete across both error-control regimes — **FWER
(b32, Bonferroni)** and **FDR (b33, Benjamini–Hochberg)** — on top of size (b29), power (b30), and
calibration (b31).

```bash
# FDR self-test — BH controls FDR ≤ q and rejects a superset of Bonferroni.
python -m aureon.bio.false_discovery --self-test

# Write the false-discovery evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.false_discovery --report fdr.md --report-json fdr.json
```

## Authenticity — real vs synthetic (the Ditto/Gucci paradox) (`aureon/bio/authenticity_discriminator.py`)

A real plant and a fake plant made to imitate it can look identical to the eye — but a genuine natural
system carries a specific **harmonic + geometric makeup** an imitation lacks. This is the immune layer's
**counterfeit detector** (benchmark **b37**), and it reuses the b36 membrane's sealing idea in its keyed
form. It classifies a signal *claimed* to be real along two structural axes — the engine's own
independent kernels, nothing invented — plus a keyed origin seal:

- **Harmonic makeup** → `test_A` (coherence clustering); **geometric makeup** → `test_B` (φ-interval
  alignment); `structure_present ⇔ p_A < α AND p_B < α`.
- **The axes are independent.** A *coarse mimic* (uniform in-band draw) reproduces neither. A
  *harmonic-only* signal (tight clusters at non-φ centers) passes Test A but fails Test B; a
  *geometric-only* signal (φ-spaced singletons, no within-cluster coherence) does the reverse.
- **The clone paradox, resolved.** A **perfect structural clone** reproduces every measurable feature —
  it passes *both* structural tests. Structure alone cannot catch it. A **keyed HMAC provenance seal**
  can: the genuine article carries an origin token a cloner cannot forge without the secret key, so
  `authentic = structure AND provenance` blocks the clone (`clone_blocked_by_provenance`). The honest
  limit is stated plainly — **a clone that also steals the key is authentic by every test.**
- **Honest scope + key hygiene.** Synthetic only, *not* a claim about any person and *not* a security
  proof. The real production key comes from `AUREON_AUTHENTICITY_KEY` (never committed); a fixed,
  documented **non-secret** test key is the default so self-tests are deterministic and artifacts are
  byte-identical. `emit_authenticity` publishes `bio.authenticity.run`.

```bash
# Authenticity self-test — genuine detected, surface imitations blocked,
# perfect clone structurally passes but blocked by provenance, separation > 0.
python -m aureon.bio.authenticity_discriminator --self-test

# Write the authenticity evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.authenticity_discriminator --report auth.md --report-json auth.json
```

## Immune memory — recall and the secondary response (`aureon/bio/immune_memory.py`)

The immune layer's memory organ (benchmark **b38**): once the swarm (b35) confirms a neutralization, the
threat's content signature is committed to a bounded, self-tolerant memory, so a repeat parasite is
recognized instantly and answered by a cheap, escalated **secondary response** instead of the full quorum
re-verification.

- **Work-units, not wall-clock.** A novel threat costs the full quorum (`PRIMARY_COST =
  swarm_defense.DEFAULT_N_DEFENDERS`); a recognized repeat costs `1` — a measurable speedup that keeps the
  artifact byte-identical.
- **Specificity + self-tolerance.** A remembered parasite does not recall a different one; a benign / self
  signal (severity 0) is never remembered — no autoimmunity. Bounded, deterministic FIFO eviction.
- **Reuse + wiring.** Imports `swarm_defense.ThreatReport` (no third copy), reuses the `mcp_membrane`
  signature idiom and the `conversation_memory` atomic `state/` persistence; `install_immune_memory`
  closes the guard→swarm→memory loop the effector only described. Not ML, not prevention — a *mutated*
  signature is correctly seen as new. Emits `bio.immune_memory.run`.

```bash
# Immune-memory self-test — repeats recognized, novel/self missed, speedup > 1, self not remembered.
python -m aureon.bio.immune_memory --self-test

# Write the immune-memory evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.immune_memory --report mem.md --report-json mem.json
```

## Immune regulation — the homeostatic brake (`aureon/bio/immune_regulation.py`)

The immune layer's brake (benchmark **b39**): memory accelerates responses, so regulation counterbalances
or the layer harms the host (autoimmunity, cytokine storm). A deterministic tick-based governor enforces:

- **Self-tolerance** — a benign / self signal (severity 0) is *never* mounted against (self_attack_rate 0).
- **Refractory cooldown** — repeated identical alarms are suppressed within a cooldown window (damps a
  false-alarm storm), while a genuine *novel* threat always passes (novelty is never suppressed).
- **Bounded inflammation** — concurrent active responses are capped; a flood is *deferred*, not run away;
  inflammation resolves to **homeostasis** when alarms quiet.

Cost is measured in event-ticks, not wall-clock. Reuses `swarm_defense.ThreatReport` +
`immune_memory.signature_of`; `install_immune_regulation` closes the swarm→cooldown loop. Emits
`bio.immune_regulation.run`.

```bash
# Immune-regulation self-test — self never attacked, false alarms damped, genuine pass, homeostasis.
python -m aureon.bio.immune_regulation --self-test

# Write the immune-regulation evidence artifact (deterministic markdown + JSON).
python -m aureon.bio.immune_regulation --report reg.md --report-json reg.json
```

## Run it

```bash
# Synthetic self-test — controls valid, structured⇒present, noise⇒absent,
# unconsented⇒blocked, boundary on every result.
python -m aureon.bio.human_harmonic_proxy

# Tests
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
  pytest tests/bio/test_human_harmonic_proxy.py -q
```

The self-test is the end-to-end proof: the same engine, the same controls
enforced, the consent gate and Operator veto active, and the scientific-boundary
statement inseparable from every result.
