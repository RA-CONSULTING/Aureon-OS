# Tandem repairs and duration expansion — 12 September 2026

The corrected experiment passed its preflight and four-GPU resource pilot.
The full seven-stage study and its audit are submitted. At **2026-09-12T17:04:56.749751+00:00**,
production **6506509 was PENDING for resources**, audit **6506656 was PENDING
on its dependency**, and there were **0 full result receipts**.
There is no new full-study detection conclusion yet.

The connected HNC/legacy account remains the research context: people and
practitioners, durable records, Maeshowe, light, two-channel twig readings,
calendar cycles and later interpretation. This Tandem study tests one explicit
simulation of selection and an echo from other trajectories. It does not resolve
which historical mark or passage is selected when light reaches the base, nor
establish spoken readings across daily, annual or nineteen-year cycles. The
[connected legacy review](Legacy-system-connected-review-2026-09-12.md) retains
those connections and the missing observation requirements.

## What the earlier results actually establish

The earlier detector redesign tested 331,776 synthetic trials and 117,504 held-out
nulls. Its original correlation score detected 28.69% of target cases. The best
tested learned score reached 56.62%, with 0.74% false positives; its weakest
eta=.05/SNR=0 corner reached only 2.31%. None met the declared 80% target-power
requirement. The archived verdict label “SYNTHETIC_SIGNATURE_NOT_IDENTIFIABLE”
is preserved, but those finite detector failures do not establish mathematical
nonidentifiability. The old source and outcomes are not relabelled or replaced.

## Source corrections and controlled comparisons

The pinned repository implementation uses beta **.90**. This is an explicit older
default, distinct from the **1.1 reprint error** identified by the author. The new
reference uses the author's **1.0** correction while preserving .90 as a control.
No global replacement of different models' beta parameters is made.

Three additional implementation issues were found. The echo mixture included
the selected trajectory although the registered protocol describes non-observed
trajectories. Noise was centred and normalized to exact unit RMS over each whole
record, creating an exact-energy constraint. Five input frequencies were above
the original 500 Hz Nyquist limit. The stages isolate these changes sequentially:

| Stage | Beta | Noise and echo | Sampling | Duration |
|---|---:|---|---:|---:|
| Legacy control | .90 | Exact record RMS; selected branch included | 1,000 Hz | 2.048 s |
| Population noise | .90 | Stationary Gaussian noise; selected included | 1,000 Hz | 2.048 s |
| Corrected reference | 1.0 | Gaussian noise; selected included | 1,000 Hz | 2.048 s |
| Nonselected echo | 1.0 | Gaussian noise; selected removed, others renormalized | 1,000 Hz | 2.048 s |
| Sampling correction | 1.0 | Corrected choices | 2,000 Hz | 2.048 s |
| Longer record | 1.0 | Corrected choices | 2,000 Hz | 8.192 s |
| Longest record | 1.0 | Corrected choices | 2,000 Hz | 32.768 s |

The 528, 639, 741, 852 and 963 Hz inputs alias to signed frequencies −472, −361,
−259, −148 and −37 Hz at the old rate. Doubling the rate resolves the stated
input harmonics; it does not prove a band-limited nonlinear output or numerical
convergence. Physical delay/window lengths and coloured-noise correlation times
are preserved when sampling changes. White per-sample SNR stays fixed, adding
an independent-measurement assumption. Longer records also extend the observer's
selection interval and recurrence evolution; these are not merely repeated
measurements of a fixed short waveform. Noise and echo scales follow the selected
trajectory's test-half RMS, as in the source. [NIST on sampling and aliasing](https://tf.nist.gov/phase/Properties/ten.htm).

## What the new diagnostics can and cannot show

The original correlation score remains. A new conditional likelihood score uses
the exact simulated baseline, echo and phase templates, noise family and scale.
It compares the best nonnegative echo fit with the best phase-mixture fit over
strengths 0 to .20. These privileged inputs are not available from an ordinary
physical sensor; the test is a conditional diagnostic, not a validated field detector.

A separate exact-energy diagnostic tests the old noise-normalization artifact.
It is deliberately given the exact simulated components and discrete strength
grid. Its performance cannot be promoted as evidence for physical echo detection.

For stationary Gaussian noise, the specified information calculation uses exact
finite-record whitening and the distance to the closest allowed phase null.
Its ideal simple-versus-simple power is an upper bound only for a detector that
controls false positives uniformly at every conditional null mean. It is not
a bound for a rule that controls only an average-mixture false-positive rate.
The old exact-RMS distribution is not Gaussian and gets no Gaussian bound.

For example, with Gaussian white noise, the old-length test half has 1,024 samples.
At eta=.05 and SNR=0, even the ideal simple-delay-null power at a 1.5% false-positive
rate is **28.43%**. Reaching 80% requires a whitened mean separation of at least
3.0117, compared with 1.6 in that example. This calculation motivates testing
duration; it is not a result of the new full study or a bound on the original
exact-RMS noise.

## Completed verification and resource decision

**Preflight 6506231: COMPLETED, exit 0, 18 seconds.** Twelve grouped checks passed:
all twelve fields of 256 historical trials in each of shards 0 and 31 reproduced
exactly; whitening matched dense covariance inverses; Gaussian normalization,
likelihood calculations, sampling aliases and every amended stage passed.

**Pilot 6506293: COMPLETED, exit 0, 51 seconds.** All 28 stage/cell files contain
14,336 records, with four distinct GPU identities, finite values and exactly zero
selected-branch contribution in corrected stages. Maximum recorded GPU memory
was about 18.53 GiB.
The measured slowest cell took 34.43 seconds
of experiment work. Full projection: **11.62 minutes**;
with the declared 50% margin and ten minutes: **27.43 minutes**.
Storage projection is a conservative 2.97 GB;
the filesystem reported sufficient free space, without claiming a separate quota check.

**Local pilot audit passed at 2026-09-12T16:53:54.358467+00:00.** All file hashes, trial IDs,
factor labels and stored scalar shapes were checked. A separate scalar Kalman
calculation recalculated 56 saved channel records; the maximum likelihood-score
difference was 5.33e-15. This sample check
does not regenerate every latent trajectory. The 18,248,963-byte pilot archive has
SHA-256 `a28adcac2bed9a3cff7f8972f6288446b5c1dce0591f14d616e19960e1e4d7a2`.

Full production uses **eight nodes / 32 GPUs**, with **2,322,432 records** across
32 parameter cells and seven stages. The hard limit is tightened to **45 minutes**,
a maximum **six physical node-hours**, within the original three-hour ceiling.
The overlapping first 512 production identities in pilot cells 0,15,16,31 are
excluded from inference in every stage. This leaves **2,308,096 eligible records**.

Allocation information was refreshed at 2026-09-12T16:55:30.276733+00:00 using 533
visible September allocation records. Conservative full-node usage was
152.18 hours, plus 110.10
hours reserved for active jobs' remaining ceilings. Against the previously verified
4,992.53 September opening balance, this leaves a provisional **4724.26**
after those amounts and the new six-hour ceiling. This is not an exact current
billed or spendable balance. The web session expired and renewed portal sign-in
is pending; invisible jobs, other clusters and unobserved credit changes are not covered.

## Completion requirements

The queued audit must verify all 224 full receipts and arrays, all 32 GPU owners,
the exact source manifests, all pilot/full duplicate blocks, all scalar factor
identities, all Gaussian bound values and 448 saved channel records using the
independent whitening implementation. All three noise models must be represented.
It then recomputes thresholds using calibration nulls only and evaluates false
positives, target power, the weakest corner, all strength/noise/operator/SNR strata,
and correct-versus-shifted discrimination.

Uncertainty uses 20,000 paired configuration-cell bootstrap draws, and Holm
correction covers six successive-stage power comparisons. Intervals are conditional
on the fixed parameter panel and fitted calibration thresholds; they do not include
threshold refitting or independent sampling of physical systems. A deliberate
calibration-leakage test and a perfect-power/excessive-false-alarm test passed locally.

Full raw arrays will remain outside Git. Frozen source packs, dated reports,
manifests and audit receipts are staged separately. No completed full result,
independent human replication, physical observation or historical decoding is claimed.

Source pin: `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`.
Original harness SHA: `5ff9000846bdeaf65a2c93f14463200442fe9cdadced1e4db3c6b6f7709567d2`.
New experiment manifest: `ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e`.
Full launcher manifest: `6287bf2b722dd793220e747b3a39682faa88b86faf27abef701cc2bb39f936c4`.
Audit manifest: `6478d963bfef6ffa948ee57dff391385f64e71fa478376c185b03e764101ae24`.
