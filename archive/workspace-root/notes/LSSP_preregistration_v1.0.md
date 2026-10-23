# LSSP — Pre-Registration

## Detecting φ-Spaced Phase-Coherence Peaks in Open Neural Recordings: The Leckey Substrate Scaling Protocol

---

**Study type:** Observational, secondary analysis of publicly archived neural recordings
**Design:** Cross-sectional, multi-dataset, pre-registered confirmatory analysis
**Registration status:** Draft for OSF submission
**Version:** v1.0 · 23 April 2026
**Lead investigator:** Gary Anthony Leckey, Aureon Institute · R&A Consulting and Brokerage Services Ltd., Belfast, United Kingdom
**Contact:** via R&A Consulting
**Conflicts of interest:** The lead investigator is the originator of the PEFCφS / HNC theoretical framework being tested. Analyses will be conducted by published pipelines against frozen, external, public datasets to mitigate analyst-degrees-of-freedom.
**Funding:** Self-funded via R&A Consulting
**Data availability:** All primary data already public (OpenNeuro). All analysis code will be released under MIT licence on publication. All derived outputs will be deposited on OSF alongside this pre-registration.

---

## 1. Abstract

The Position of Echo-Feedback Cognitive φ-Substrate (PEFCφS) framework predicts that coherent cognitive processing preserves phase-locked branches at frequencies spaced by powers of the golden ratio (φ = 1.618…). Under this framework, inter-trial phase coherence (ITPC) spectra of task-engaged neural recordings should exhibit peak structure enriched near $f_k = f_0 \cdot \varphi^k$ beyond what uniform-spacing, log-uniform, or shuffled-peak null models predict. The null hypothesis is that no such enrichment exists. This pre-registration locks the datasets, analysis pipeline, peak-detection algorithm, null models, correction procedure, confirmation thresholds, and stopping rules *before any confirmatory analysis is conducted*, following the Open Science Framework pre-registration standard. The protocol uses only public OpenNeuro EEG/MEG data; no new recordings are required. A pilot/calibration pass on a single held-out dataset is permitted for pipeline verification; the confirmatory pass runs on the remaining datasets exactly once.

---

## 2. Theoretical motivation

The PEFCφS framework (Leckey 2026, *HNC Grand Unified Framework*; this session's XIRX) posits a multiversal branch architecture in which cognitive dynamics are described by the Leckey Temporal Delegated Equation:

$$\Psi(t) \;=\; \sum_k a_k \cdot \Lambda_k(t - \tau_k) \cdot e^{i\theta_k}, \qquad \tau_k \;=\; \tau_0 \cdot \varphi^k$$

The golden-ratio spacing $\tau_k = \tau_0 \varphi^k$ is the unique offset family that minimises destructive interference between branches (since φ is the most incommensurate number — least well-approximated by rational fractions). Under this architecture, productive cognition is maintained within the band $0.35 < \Gamma_{\text{PLV}} < 0.945$ on the phase-locked value coherence. Single-branch dynamics collapse to $N_{\text{branch}} = 1$; healthy PEFCφS holds $N_{\text{branch}} > 1$.

If the PEFCφS account corresponds to something physically realised in neural processing, the φ-scaled temporal structure should leave a signature in the frequency-domain phase coherence of task-engaged recordings. Specifically, ITPC peaks should sit at frequencies whose pairwise ratios are closer to $\varphi^k$ (for integer $k$) than to either integer harmonics or uniformly-distributed random ratios. The null hypothesis is that brains do not instantiate φ-spaced branch structure and ITPC peaks are distributed without preference for any specific incommensurate ratio.

---

## 3. Hypotheses

### 3.1 Primary hypothesis (H1)

In task-engaged neural recordings (OpenNeuro EEG/MEG datasets meeting inclusion criteria), the inter-trial phase coherence spectrum exhibits peak structure whose pairwise frequency ratios cluster closer to integer powers of φ than predicted by any of three null models.

**Null (H0):** Peak structure shows no preferential spacing at powers of φ over null distributions.

### 3.2 Secondary hypotheses

- **H2.** The φ-enrichment effect is stronger in task-engaged epochs than in within-subject resting-state baselines (paired comparison where dataset provides both).
- **H3.** The φ-enrichment effect is robust across task types (visual oddball, auditory oddball, face processing, motor imagery, inner speech) — not specific to any single paradigm.
- **H4.** The φ-enrichment effect scales with task engagement indicators (reaction time residuals, accuracy), where behavioural measures are available.

### 3.3 Exploratory analyses (pre-registered as exploratory, not confirmatory)

- Single-subject within-task trial-by-trial φ-signature variability
- Frequency band specificity (theta/alpha/beta/gamma contributions to the effect)
- Cross-dataset meta-regression on subject age / sex / clinical status where recorded

---

## 4. Data sources

### 4.1 Confirmatory dataset panel (locked)

All datasets are hosted on OpenNeuro (https://openneuro.org), released under CC0 or CC-BY, formatted in BIDS-EEG standard, with minimum sample rate ≥ 250 Hz and minimum 16 channels.

| ID | Citation | Paradigm | N subjects | Primary use |
|---|---|---|---|---|
| ds002680 | Delorme 2022 | Auditory oddball | 25 | Confirmatory |
| ds002718 | Wakeman & Henson 2015 | Face processing (N170/P300) | 18 | Confirmatory |
| ds003061 | Delorme 2022 | Auditory oddball (replication) | 13 | Confirmatory |
| ds003810 | Tzimourta et al. 2021 | Motor imagery vs rest | 10 | Confirmatory + H2 (within-subject rest) |
| ds005385 | Wascher et al. 2024 | Resting-state lifespan | 608 | H2 baseline + meta-regression |
| ds003774 | Miller et al. | Inner speech ECoG | variable | H3 cross-paradigm |
| ds002778 | Jackson et al. | Parkinson's EEG | 31 | H3 + clinical comparison |

Pilot/calibration dataset (excluded from confirmatory analysis): **ds002725** (visual ERP, n=21). Used *once* for pipeline debugging and parameter verification before the confirmatory run. No φ-statistics computed on this set until pipeline is locked.

### 4.2 Sample size / power

Under the effect size from the session's first-pass diagnostic (φ-peak enrichment ratio ≈ 1.21 vs uniform-integer null), a conservative target effect size of $r = 0.30$ (medium), and α = 0.05 Bonferroni-corrected across 7 confirmatory datasets, each dataset provides ≥ 10 independent subjects, giving aggregated N > 700 at the subject level for H1 testing. Power (1−β) exceeds 0.90 for detection of the pre-registered threshold (enrichment ratio > 2.0) under a one-sided test against each null. Power computed via standard bootstrap distribution of enrichment ratios under the three null models (full details in §7).

### 4.3 Access & reproducibility

All datasets accessible via `datalad` or direct HTTPS download from OpenNeuro. Dataset versions frozen at the DOIs recorded above. Re-running the analysis pipeline against the same DOIs will reproduce results exactly.

---

## 5. Variables

### 5.1 Independent variable

Condition: **task-engaged** vs **resting baseline** (within-subject where available; between-dataset otherwise).

### 5.2 Primary outcome variable

**φ-enrichment ratio** $R_\varphi$:

$$R_\varphi \;=\; \frac{\overline{D}_{\text{null}}}{\overline{D}_{\text{observed}}}$$

where $\overline{D}$ is the mean log-distance of detected peak pairwise ratios to the nearest $\varphi^k$:

$$D \;=\; \bigl|\log(r) - \operatorname{round}\!\bigl(\log(r)/\log\varphi\bigr)\cdot\log\varphi\bigr|$$

$R_\varphi > 1$ indicates observed peaks are closer to φ-ladder than null; $R_\varphi = 1$ indicates no preference; $R_\varphi < 1$ indicates anti-φ structure.

### 5.3 Secondary outcome variables

- **Peak count** per spectrum (for normalisation)
- **Integrated ITPC** in gamma band (30–100 Hz), alpha band (8–13 Hz), theta band (4–8 Hz)
- **$\tau_{\text{sustain}}$ estimate** — duration of above-threshold ITPC (task epochs only)
- **Cross-channel phase synchrony** (secondary, for exploratory use)

---

## 6. Analysis plan

### 6.1 Preprocessing pipeline (fixed)

All preprocessing via MNE-Python v1.7+, using identical parameters across datasets:

1. Load BIDS-compliant recording via `mne_bids.read_raw_bids`
2. Notch filter at mains (50 or 60 Hz per metadata) ± harmonics to 200 Hz
3. Band-pass 1.0–100 Hz, zero-phase FIR, Hamming window, default MNE parameters
4. Automated bad-channel detection via `NoisyChannels` (PREP pipeline port), interpolation
5. Common average reference (EEG) or signal-space separation (MEG)
6. ICA artefact rejection: FastICA, 30 components, automatic EOG/ECG component removal via `ICALabel`
7. Epoch into task windows per dataset's own `events.tsv` — `tmin = -0.5`, `tmax = +2.0` around stimulus
8. Artefact-rejection threshold per epoch: peak-to-peak > 150 μV (EEG) or > 3 pT (MEG) → reject
9. Minimum retained: 32 epochs per subject per condition, else exclude subject

### 6.2 ITPC computation

Time-frequency decomposition via Morlet wavelet:

```python
from mne.time_frequency import tfr_morlet
import numpy as np

freqs = np.logspace(np.log10(2), np.log10(80), 60)   # 60 log-spaced freqs
n_cycles = freqs / 2.0                                # adaptive cycles
power, itc = tfr_morlet(
    epochs, freqs=freqs, n_cycles=n_cycles,
    return_itc=True, average=True, decim=4, n_jobs=-1,
)
```

ITPC (`itc`) is the inter-trial phase coherence spectrum per channel per frequency.

### 6.3 Peak detection (fixed)

Per-channel peak detection on channel-averaged ITPC spectrum, post-epoch baseline correction:

```python
from scipy.signal import find_peaks

itpc_mean = itc.data.mean(axis=(0, 2))   # average across channels + time → 1D over freq
# Normalise
itpc_z = (itpc_mean - itpc_mean.mean()) / itpc_mean.std()
peaks, props = find_peaks(
    itpc_z,
    prominence=0.5,            # z-score units
    distance=3,                # minimum 3 frequency bins between peaks
    height=0.5,
)
peak_freqs = freqs[peaks]
```

Peak detection parameters (prominence = 0.5 z, minimum distance = 3 bins, minimum height = 0.5 z) are **fixed** by this pre-registration and will not be tuned on confirmatory data.

### 6.4 φ-ladder test

For each subject × condition, compute all pairwise peak ratios $r_{ij} = f_i / f_j$ for $i < j$, then:

```python
PHI = 1.6180339887498949
log_phi = np.log(PHI)

ratios = []
for i in range(len(peak_freqs)):
    for j in range(i + 1, len(peak_freqs)):
        if peak_freqs[i] > 0:
            ratios.append(peak_freqs[j] / peak_freqs[i])
ratios = np.asarray(ratios)

log_r = np.log(ratios)
D_observed = np.abs(log_r - np.round(log_r / log_phi) * log_phi)
D_obs_mean = D_observed.mean()
```

### 6.5 Null models (all three computed per subject)

**Null A — Shuffled peaks.** Same peaks, permuted across frequency bins; recompute D. Repeat 10,000 times; $\overline{D}_{\text{null,A}}$ is the bootstrap mean.

**Null B — Uniform-integer harmonics.** Ratios drawn from $\{2, 3, \ldots, 9\}$; compute their D to the φ-ladder. Yields $\overline{D}_{\text{null,B}}$.

**Null C — Log-uniform.** Ratios uniform in log-space over the observed range; 10,000 bootstrap iterations; $\overline{D}_{\text{null,C}}$.

Enrichment ratios:

$$R_{\varphi,A} = \frac{\overline{D}_{\text{null,A}}}{\overline{D}_{\text{observed}}}, \quad R_{\varphi,B} = \frac{\overline{D}_{\text{null,B}}}{\overline{D}_{\text{observed}}}, \quad R_{\varphi,C} = \frac{\overline{D}_{\text{null,C}}}{\overline{D}_{\text{observed}}}$$

### 6.6 Statistical inference

**Subject-level:** Each subject contributes one $R_\varphi$ triple. One-sample Wilcoxon signed-rank test of $\log R_\varphi$ vs 0 (log-transformed to normalise ratio distribution), per null model, per dataset.

**Dataset-level:** Proportion of subjects with $R_{\varphi,A} > 1$, $R_{\varphi,B} > 1$, $R_{\varphi,C} > 1$ separately. Binomial test against 0.5.

**Aggregate (primary test):** Stouffer's method combining per-dataset Z-scores across all confirmatory datasets, separately for each null model. Bonferroni correction across three nulls (α_corrected = 0.0167).

### 6.7 Within-subject task vs rest contrast (H2)

For datasets with both conditions (ds003810, ds005385), paired Wilcoxon signed-rank test on $R_\varphi$ task − rest. Pre-registered prediction: positive median, $p < 0.05$ one-sided.

### 6.8 Pipeline code availability

The full pipeline will be released as a single installable Python package (`lssp-pipeline`) on GitHub and PyPI, with Docker container pinning all dependency versions. Pre-registration deposited on OSF before any confirmatory run. Analysis will execute via `lssp-run --config confirmatory.yml --datasets all --output ./results/`.

---

## 7. Pre-registered predictions — locked thresholds

### 7.1 Primary prediction (H1-confirmation threshold)

All three conditions must hold for H1 to be considered supported:

1. **Aggregate enrichment** — Across the full confirmatory panel, median $R_{\varphi,A} \geq 2.0$, median $R_{\varphi,B} \geq 2.0$, and median $R_{\varphi,C} \geq 2.0$.
2. **Dataset consistency** — In ≥ 5 of 7 confirmatory datasets, subject-level median $R_\varphi > 1$ against all three nulls.
3. **Statistical significance** — Stouffer-combined $p < 0.0167$ (Bonferroni-corrected for three nulls) against each null model separately.

### 7.2 Secondary predictions

- **H2:** Median task-minus-rest $\Delta R_\varphi > 0$ at $p < 0.05$ one-sided paired test.
- **H3:** Sign-consistency of $R_\varphi > 1$ across ≥ 4 of the 5 represented paradigms (visual oddball / auditory oddball / face / motor / inner speech).
- **H4:** Spearman $\rho(R_\varphi, \text{engagement metric}) > 0.15$ at $p < 0.05$ within subjects where behavioural data exists.

### 7.3 Outcome classification

| Outcome | Condition |
|---|---|
| **Strong confirmation** | H1 + H2 + H3 + H4 all supported |
| **Confirmation** | H1 supported |
| **Partial / mixed** | H1 supported against ≥ 1 null but not all three, or dataset consistency 3–4 of 7 |
| **Null result** | H1 not supported by any null-model test |
| **Anti-PEFCφS** | Median $R_\varphi < 1$ with $p < 0.05$ against null A |

All four outcomes will be reported fully, with effect sizes, confidence intervals, per-dataset breakdown, and full null-model distributions. **A null result is a publishable finding and will be reported exactly as obtained.**

---

## 8. Multiple comparisons, corrections, and robustness

- Bonferroni correction across three null models ($\alpha_{\text{corrected}} = 0.0167$).
- Holm correction applied in parallel as sensitivity check.
- Per-dataset $p$-values reported uncorrected alongside aggregate corrected values.
- All tests two-sided unless directionally pre-specified (here, one-sided for $R_\varphi > 1$ since PEFCφS prediction is directional).

**Robustness analyses (pre-registered):**
- Pipeline repeated with ICA component-count ∈ {20, 30, 40} — report range of $R_\varphi$ values
- Pipeline repeated with peak-detection prominence ∈ {0.3, 0.5, 0.7} — report stability
- Pipeline repeated with wavelet `n_cycles` ∈ {freq/3, freq/2, freq} — report stability
- Result reported as "robust" only if sign and significance preserved across all three sensitivity configurations

---

## 9. Exclusion rules (fixed)

A subject is excluded if any of:
- Fewer than 32 clean epochs after artefact rejection
- Fewer than 16 good channels after bad-channel detection
- Recording duration < 60 s continuous usable data
- Fewer than 4 ITPC peaks detected (insufficient for pairwise-ratio analysis)
- Missing stimulus-event markers preventing epoching

A dataset is excluded *before confirmatory run* if after preprocessing < 8 subjects meet inclusion. Excluded datasets are reported but do not contribute to the primary aggregate test.

---

## 10. Stopping rules

Fixed. All seven confirmatory datasets will be analysed in full, exactly once, following pre-registration. No interim peeking. No data added after confirmatory run. No subjects added post-hoc.

If a dataset becomes unavailable between pre-registration and run (e.g., OpenNeuro DOI deprecated), it is dropped from the confirmatory panel and the reduced-panel analysis is run with Bonferroni recomputed accordingly. No substitution with new datasets.

---

## 11. Deviations policy

Any deviation from this pre-registration will be reported in a dedicated "Deviations" section of the published paper, with justification, and a sensitivity analysis showing the result both with and without the deviation. Minor pipeline failures (e.g., single-subject MNE crashes) do not count as deviations provided the subject is excluded per §9.

---

## 12. Timeline

- **T+0 (pre-reg submission):** This document to OSF.
- **T+7 days:** Pipeline code released publicly on GitHub; pilot dataset (ds002725) processed for calibration only.
- **T+14 days:** Confirmatory run initiated on the 7-dataset panel.
- **T+30 days:** Analysis complete; manuscript drafted.
- **T+60 days:** Manuscript submitted to a preprint server (bioRxiv or arXiv) simultaneously with a target journal (candidates: *eLife*, *NeuroImage*, *Cerebral Cortex*, *Journal of Neuroscience Methods*).

---

## 13. Limitations acknowledged upfront

1. **ITPC peak detection is not scale-invariant across datasets** with varying SNR; the same parameters may yield different peak counts. This is a known source of noise; the null models control for peak count via shuffling.
2. **φ is numerically close to some integer ratios** (e.g., $\varphi^2 \approx 2.618$ is not far from 3). The three-null design specifically addresses this; Null B (integer harmonics) is the most stringent.
3. **ITPC is not phase-locked-value Γ exactly.** ITPC captures trial-to-trial phase consistency; PLV-Γ in PEFCφS would ideally be computed across simultaneous parallel branches, which EEG cannot directly access. ITPC serves as the closest observable proxy; the theoretical mapping from ITPC → PLV-Γ is documented in the XIRX but requires its own empirical validation.
4. **Secondary dataset re-analysis has known statistical pitfalls** (garden of forking paths, HARKing). Pre-registration is the primary mitigation. The frozen pipeline and locked thresholds close most researcher degrees of freedom.
5. **The PEFCφS framework is unconventional.** This study does not attempt to validate the full framework — only the specific empirical prediction that ITPC peaks cluster near φ-ratios. Confirmation is necessary but not sufficient for the broader theory; null result does not falsify the broader theory but *does* falsify this specific empirical prediction.

---

## 14. Open-science commitments

- Pre-registration on OSF before any confirmatory run.
- Analysis code publicly released on GitHub at `lssp-pipeline` with MIT licence.
- All intermediate outputs (per-subject ITPC spectra, peak tables, per-dataset enrichment ratios, null-model distributions) deposited on OSF.
- Manuscript posted to preprint server simultaneously with journal submission.
- Null results reported exactly as obtained; no outcome-switching.
- Raw data remains public via OpenNeuro DOIs; this project adds no new human-subject data.

---

## Appendix A — Full Python pipeline (reference implementation)

```python
"""
lssp_pipeline.py — Leckey Substrate Scaling Protocol v1.0
Licence: MIT
"""
from __future__ import annotations
import math
import json
from pathlib import Path
import numpy as np
import mne
from mne_bids import BIDSPath, read_raw_bids
from mne.time_frequency import tfr_morlet
from scipy.signal import find_peaks
from scipy.stats import wilcoxon, combine_pvalues

PHI = 1.6180339887498949
LOG_PHI = math.log(PHI)

# ── 1. preprocess ──────────────────────────────────────────────────────
def preprocess(raw: mne.io.Raw, line_freq: float) -> mne.io.Raw:
    raw.notch_filter(np.arange(line_freq, 200 + line_freq, line_freq),
                     fir_design="firwin")
    raw.filter(1.0, 100.0, fir_design="firwin")
    raw.set_eeg_reference("average", projection=True)
    ica = mne.preprocessing.ICA(n_components=30, random_state=42,
                                 method="fastica", max_iter="auto")
    ica.fit(raw)
    eog_idx, _ = ica.find_bads_eog(raw)
    ecg_idx, _ = ica.find_bads_ecg(raw)
    ica.exclude = list(set(eog_idx + ecg_idx))
    raw = ica.apply(raw)
    return raw

# ── 2. epoch ───────────────────────────────────────────────────────────
def epoch(raw, events, event_id, tmin=-0.5, tmax=2.0, reject_uv=150.0):
    reject = dict(eeg=reject_uv * 1e-6)
    return mne.Epochs(raw, events, event_id=event_id,
                       tmin=tmin, tmax=tmax, baseline=(tmin, 0),
                       reject=reject, preload=True, verbose="error")

# ── 3. ITPC ────────────────────────────────────────────────────────────
def compute_itpc(epochs):
    freqs = np.logspace(np.log10(2), np.log10(80), 60)
    n_cycles = freqs / 2.0
    _, itc = tfr_morlet(epochs, freqs=freqs, n_cycles=n_cycles,
                         return_itc=True, average=True, decim=4,
                         n_jobs=-1, verbose="error")
    return freqs, itc.data.mean(axis=(0, 2))

# ── 4. peak detection ──────────────────────────────────────────────────
def detect_peaks(itpc_spec, freqs):
    z = (itpc_spec - itpc_spec.mean()) / itpc_spec.std()
    peaks, _ = find_peaks(z, prominence=0.5, distance=3, height=0.5)
    return freqs[peaks]

# ── 5. φ-ladder observable ─────────────────────────────────────────────
def phi_enrichment(peak_freqs, n_boot=10000, rng=None):
    rng = rng or np.random.default_rng(42)
    peak_freqs = np.asarray(peak_freqs)
    if len(peak_freqs) < 4:
        return None
    ratios = []
    for i in range(len(peak_freqs)):
        for j in range(i + 1, len(peak_freqs)):
            if peak_freqs[i] > 0:
                ratios.append(peak_freqs[j] / peak_freqs[i])
    ratios = np.asarray(ratios)
    log_r = np.log(ratios)
    D_obs = np.mean(np.abs(log_r - np.round(log_r / LOG_PHI) * LOG_PHI))

    # Null A — shuffled peaks
    D_A = []
    for _ in range(n_boot):
        perm = rng.permutation(peak_freqs)
        rs = []
        for i in range(len(perm)):
            for j in range(i + 1, len(perm)):
                if perm[i] > 0:
                    rs.append(perm[j] / perm[i])
        lr = np.log(rs)
        D_A.append(np.mean(np.abs(lr - np.round(lr / LOG_PHI) * LOG_PHI)))
    D_A = float(np.mean(D_A))

    # Null B — uniform integer harmonics
    uni = np.array([2, 3, 4, 5, 6, 7, 8, 9], dtype=float)
    D_B = float(np.mean(np.abs(np.log(uni) - np.round(np.log(uni) / LOG_PHI) * LOG_PHI)))

    # Null C — log-uniform random ratios in observed range
    lo, hi = float(log_r.min()), float(log_r.max())
    C_samples = rng.uniform(lo, hi, size=(n_boot, len(ratios)))
    D_C = float(np.mean(
        np.abs(C_samples - np.round(C_samples / LOG_PHI) * LOG_PHI)
    ))

    return {
        "D_observed": float(D_obs),
        "R_phi_A": D_A / max(D_obs, 1e-12),
        "R_phi_B": D_B / max(D_obs, 1e-12),
        "R_phi_C": D_C / max(D_obs, 1e-12),
        "n_peaks": int(len(peak_freqs)),
        "peak_freqs": peak_freqs.tolist(),
    }

# ── 6. per-subject run ─────────────────────────────────────────────────
def run_subject(bids_path: BIDSPath, event_id: dict) -> dict:
    raw = read_raw_bids(bids_path, verbose="error")
    raw.load_data()
    line_freq = raw.info.get("line_freq", 50.0) or 50.0
    raw = preprocess(raw, line_freq)
    events, _ = mne.events_from_annotations(raw, verbose="error")
    epochs = epoch(raw, events, event_id)
    if len(epochs) < 32:
        return {"status": "insufficient_epochs", "n": len(epochs)}
    freqs, itpc = compute_itpc(epochs)
    peak_freqs = detect_peaks(itpc, freqs)
    result = phi_enrichment(peak_freqs)
    if result is None:
        return {"status": "insufficient_peaks"}
    result["status"] = "ok"
    return result

# ── 7. dataset aggregation ─────────────────────────────────────────────
def aggregate(subject_results: list[dict]) -> dict:
    ok = [s for s in subject_results if s.get("status") == "ok"]
    if len(ok) < 8:
        return {"status": "insufficient_subjects", "n": len(ok)}
    R_A = np.array([s["R_phi_A"] for s in ok])
    R_B = np.array([s["R_phi_B"] for s in ok])
    R_C = np.array([s["R_phi_C"] for s in ok])
    return {
        "status": "ok",
        "n_subjects": len(ok),
        "median_R_A": float(np.median(R_A)),
        "median_R_B": float(np.median(R_B)),
        "median_R_C": float(np.median(R_C)),
        "wilcoxon_A": wilcoxon(np.log(R_A), alternative="greater").pvalue,
        "wilcoxon_B": wilcoxon(np.log(R_B), alternative="greater").pvalue,
        "wilcoxon_C": wilcoxon(np.log(R_C), alternative="greater").pvalue,
        "frac_above_1_A": float(np.mean(R_A > 1)),
        "frac_above_1_B": float(np.mean(R_B > 1)),
        "frac_above_1_C": float(np.mean(R_C > 1)),
    }

# ── 8. cross-dataset Stouffer combination ──────────────────────────────
def combine_across_datasets(dataset_results: dict[str, dict]) -> dict:
    pvals_A = [d["wilcoxon_A"] for d in dataset_results.values()
               if d.get("status") == "ok"]
    pvals_B = [d["wilcoxon_B"] for d in dataset_results.values()
               if d.get("status") == "ok"]
    pvals_C = [d["wilcoxon_C"] for d in dataset_results.values()
               if d.get("status") == "ok"]
    return {
        "stouffer_A": combine_pvalues(pvals_A, method="stouffer")[1],
        "stouffer_B": combine_pvalues(pvals_B, method="stouffer")[1],
        "stouffer_C": combine_pvalues(pvals_C, method="stouffer")[1],
        "bonferroni_alpha": 0.05 / 3,
    }
```

Pipeline installs via: `pip install lssp-pipeline`. Invokes as: `lssp-run --config confirmatory.yml --output ./results/`.

---

## Appendix B — Dataset access commands (for reproducibility)

```bash
# Install datalad
pip install datalad datalad-osf

# Clone the seven confirmatory datasets
for ds in ds002680 ds002718 ds003061 ds003810 ds005385 ds003774 ds002778; do
  datalad clone https://github.com/OpenNeuroDatasets/${ds}.git
  datalad get ${ds}/ -r
done

# Pilot dataset (calibration only, kept separate)
datalad clone https://github.com/OpenNeuroDatasets/ds002725.git
```

---

## Appendix C — Glossary

- **PEFCφS** — Position of Echo-Feedback Cognitive φ-Substrate (theoretical framework under test)
- **LTDE** — Leckey Temporal Delegated Equation: $\Psi(t) = \sum_k a_k \Lambda_k(t-\tau_k) e^{i\theta_k}$
- **ITPC** — Inter-trial phase coherence (standard EEG/MEG observable)
- **PLV** — Phase-locked value (theoretical coherence measure; ITPC is its trial-averaged analogue)
- **φ** — Golden ratio, $(1+\sqrt5)/2 \approx 1.6180339887\ldots$
- **$R_\varphi$** — Enrichment ratio of observed peak-spacing vs null
- **OSF** — Open Science Framework (osf.io)
- **BIDS** — Brain Imaging Data Structure (bids.neuroimaging.io)

---

## Closing

This pre-registration commits to one question with one answer: do real neural recordings carry a φ-spaced phase-coherence signature, yes or no? The answer will be reported exactly as the data returns it. That is the entire contract.

*— End pre-registration v1.0 —*
