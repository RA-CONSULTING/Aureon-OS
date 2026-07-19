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

The first **real** adapter now ships (see below); remaining **video / audio**
extractors stay **future, gated, consent-required work**. Every adapter implements
the `SignalAdapter` seam so the scoring and governance path never changes — and
each is built only with explicit consent handling, provenance capture, and the
same boundary enforced above.

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
