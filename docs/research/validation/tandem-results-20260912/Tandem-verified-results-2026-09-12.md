# Tandem repair results — 12 September 2026

**The seven-stage study completed and passed both remote and local verification.**
A diagnostic given exact simulated signal and noise information detects the
declared target cases much more reliably in longer records: **89.87% at 2.048 s,
96.17% at 8.192 s, and 98.52% at 32.768 s**, with about **1% false alarms**.
The original correlation score remains below its 80% requirement at every stage.
These are conditional simulation results; an operational detector with unknown
baseline, noise and templates has not been validated.

The old forced noise normalization created a usable artificial constraint. The
diagnostic built specifically to detect that constraint scored **100%** on the
legacy target and specified weak-corner cases. Removing exact-record normalization
reduced its target detection to **21.15%** and the specified weak corner to **1.16%**.
That perfect legacy result is an artifact diagnostic, not physical echo evidence.

## Complete results and denominators

Target cases mean injected echo strength eta≥.05 and SNR≥0 dB. The specified
weak corner is eta=.05/SNR=0; lower-strength/noisier cases also exist and remain
substantially harder. Each stage has **329,728 eligible records**: **116,648
calibration nulls**, **116,592 held-out nulls** and **96,488 positives**. Of those
positives, **31,014** are target cases and **3,446** occupy the specified weak corner.

| Stage | Original score: target | Likelihood diagnostic: target | Likelihood false alarms | Likelihood: specified weak corner | Exact-energy diagnostic: target |
|---|---:|---:|---:|---:|---:|
| Legacy .90 control | 27.05% | 87.97% | 0.996% | 33.40% | 100.00% |
| Gaussian noise, .90 | 27.19% | 88.16% | 1.008% | 34.21% | 21.15% |
| Beta 1.0 reference | 24.04% | 85.84% | 1.097% | 30.35% | 19.09% |
| Nonselected echo | 20.47% | 84.30% | 1.050% | 25.77% | 18.57% |
| 2,000 Hz, 2.048 s | 21.47% | 89.87% | 1.070% | 45.12% | 19.56% |
| 2,000 Hz, 8.192 s | 18.96% | 96.17% | 1.008% | 78.12% | 28.96% |
| 2,000 Hz, 32.768 s | 19.01% | 98.52% | 1.003% | 93.79% | 38.34% |

The likelihood diagnostic meets the **pooled** ≤1.5% false-positive / ≥80% target
power gate at every stage, including the legacy control. It also satisfies the
registered correct-versus-shifted-template requirement. This demonstrates that
the earlier tested D0–D4 failures were not a proof of mathematical nonidentifiability.
The new likelihood score has additional privileged phase-template/noise knowledge,
so its gain must not be represented as an otherwise identical practical detector
comparison with the old learned method.

At the longest duration, likelihood target detection is **30,554 / 31,014 = 98.52%**,
with a configuration-cell bootstrap interval **[97.47%, 99.38%]**.
The specified weak corner is **3,232 / 3,446 = 93.79%**, interval
**[90.49%, 96.67%]**. Held-out false positives are
**1,170 / 116,592 = 1.003%**, interval **[0.903%, 1.115%]**.

Performance is not uniform. Across **all positive strengths/SNRs**, longest-record
detection is **65,150 / 96,488 = 67.52%**. At eta=.002/SNR=−10, detection across
the nine noise/operator strata is only **0.52%–2.87%**. The weakest parameter cell's
target detection is **86.73%**, and the minimum cell rate at the specified weak
corner is **67.59%**. Although all 36 broad noise/operator/SNR strata have empirical
false-positive rates ≤1.5% in the longest arm, a parameter cell reaches **1.99%**
and a smaller null-truth subgroup reaches **3.65%**. The pooled gate does not
establish uniform false-positive control.

The original score detects only **19.01%** of longest-arm target cases and
**0 / 3,446** in the specified weak corner. Simply collecting longer records does
not repair that score. The last-arm correct-versus-shifted-template win rate is
78.04% across positives, a separate metric from its detection performance.

## What each correction changed

The source's .90 default remains an old-model control. The author's **1.0 reference**
is tested explicitly; the distinct 1.1 reprint control elsewhere is not substituted
for it. Beta correction and removal of the selected trajectory each make this
particular conditional detection problem harder. They remain correct source/design
choices rather than values selected to improve the score.

| Successive change | Target-power change, percentage points | Paired 95% interval |
|---|---:|---:|
| Legacy .90 control → Gaussian noise, .90 | +0.19 | [+0.11, +0.27] |
| Gaussian noise, .90 → Beta 1.0 reference | -2.32 | [-3.20, -1.49] |
| Beta 1.0 reference → Nonselected echo | -1.53 | [-1.98, -1.16] |
| Nonselected echo → 2,000 Hz, 2.048 s | +5.56 | [+4.95, +6.16] |
| 2,000 Hz, 2.048 s → 2,000 Hz, 8.192 s | +6.30 | [+5.57, +7.06] |
| 2,000 Hz, 8.192 s → 2,000 Hz, 32.768 s | +2.35 | [+1.72, +3.08] |

All six predeclared paired configuration-cell sign-flip comparisons have
Holm-adjusted p≈**0.000300** under 20,000 draws. Their scientific magnitudes differ:
the noise change is only +0.19 percentage points; sampling and duration produce
larger improvements. Bootstrap intervals resample whole parameter cells and hold
the fitted calibration thresholds fixed. They do not include threshold refitting
or independently sampled physical systems. The zero-width empirical interval for
the exact-energy control's 100% result is not a universal-certainty statement.

The old mixture gave the selected trajectory an average **20.52%** weight in
the .90 control and **18.23%** in the short beta=1.0 arm. Corrected arms set that
contribution to exactly zero and renormalize the other fifteen trajectories.
Original outputs and the selected-included controls remain preserved.

The sampling correction resolves the five specified input harmonics above the
old Nyquist limit, while preserving physical delays and coloured-noise correlation
times. It also adds independent white-noise measurements at fixed per-sample SNR
and defines a related discrete recurrence. It is not a proof of whole-output
band-limiting or continuous-time convergence. Longer records extend both observer
selection and recurrence evolution, while retaining the original relative RMS
scaling. [NIST on sampling](https://tf.nist.gov/phase/Properties/ten.htm).

## Information calculation and remaining scientific limits

In the longest Gaussian arm, the mean ideal simple-delay-null power is **99.81%**
for target cases; the mean nearest-phase-null value is **98.44%**. At the specified
weak corner those means are **98.35%** and **93.53%**. These calculations help expose
the cost of confusing an echo with a phase mixture. They use exact simulated
baseline, templates, noise family and scale. The phase calculation is an upper
bound only for a rule controlling false positives uniformly at every conditional
null mean; this campaign's pooled empirical gate does not establish that property.
Empirical detection rates and conditional ideal powers need not be ordered exactly.
No Gaussian bound is applied to the original exact-RMS noise distribution.

The full legacy/HNC account remains connected: practitioners, durable records,
light, two-channel twig readings, calendar timing and later readers. This study
provides a repaired computational link for one selected/unselected-trajectory
construction. It does not establish physical timeline branches, a field sensor,
or which passage is selected by light at Maeshowe over day/year/nineteen-year
cycles. See the [connected legacy review](Legacy-system-connected-review-2026-09-12.md)
and the [frozen source/launch account](Tandem-repairs-and-expansion-2026-09-12.md).
The exact light-to-mark-to-passage binding and independent observations remain
evidence requirements. A broader detection study must next estimate the baseline,
noise and templates from allowed data, retain phase-mixture controls, and test
new source-appropriate measurements. No Stage 2 or physical validation is claimed.

## Verification, provenance and compute

**6506231 preflight: 18 s; 6506293 pilot: 51 s; 6506509 production: 656 s;
6506656 audit: 29 s. All COMPLETED, exit 0.** Production used eight nodes and
32 distinct GPUs. Counting each whole allocated node conservatively, these jobs
used **1.485 physical node-hours**, including preflight, pilot and audit. This is
not a refreshed portal billing figure. The web session still awaits renewed
sign-in; terminal access and scheduler records were checked directly.

All **2,322,432** full records are retained. The **14,336** duplicated pilot
identities reproduce bit-for-bit and are excluded from inference, leaving
**2,308,096 eligible records**. The remote audit rehashed all **224** result receipts
and arrays, verified source identity and all GPU owners, checked all scalar factor
and Gaussian-bound values, and independently recomputed **448 saved channel
records** using a separate scalar Kalman implementation. Those saved channels are
the first two records of each cell/stage (eta 0/.002 at SNR −10); all three noise
families occur, but this is not full waveform regeneration at every strength.
Maximum likelihood-score discrepancy in this sample check: **5.95×10⁻¹⁴**.

**Local verification PASS at 2026-09-12T17:21:35.217042+00:00.** All **451** archive members
were verified; **11,844** rate/count cells and all thresholds
were independently recomputed. The complete frozen statistical analysis and
uncertainty calculations were reproduced; maximum numeric difference
**1.78e-15**. This is an author-run software/numerical audit,
not independent human scientific replication.

Raw archive: **486,760,874 bytes**, SHA-256
`0cd7385e58799e65dd1f10a5c5ab675748861ee5749fcec6a43980cf344a8de5`.
Analysis SHA-256: `2bf8f74703ce27d0c05167ff4348f4a4aea5d10591a6e0268194439c4426ccbd`.
Audit SHA-256: `7dfc325e552ac53e8ae6993cb1662144b3b1106d34745264e19b17293040d044`.
Frozen experiment manifest: `ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e`.
Documentary source pin: `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`.
Raw per-trial arrays remain outside Git; source, controls, hashes, receipts and
reports are preserved. Earlier pending-state reports remain dated historical
snapshots. No commit or publication is part of this work.
