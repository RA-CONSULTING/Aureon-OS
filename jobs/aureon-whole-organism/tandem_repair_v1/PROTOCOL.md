# Tandem observation-model repair and duration expansion v1

Fixed 12 September 2026 before viewing this campaign's new-seed outcomes.
This is computational simulation of explicit candidate 10→9→1 relationships.
No physical time series is included. The whole legacy/HNC account remains in
scope; a synthetic echo does not establish historical or physical branching.

## Source and preserved controls

The registered 2026-08-26 harness SHA-256 is
5ff9000846bdeaf65a2c93f14463200442fe9cdadced1e4db3c6b6f7709567d2.
The pinned repository implementation SHA is
6ce8483dbda2d696b383de79a1bead0e17cc859e53c132181f971cc615233696,
commit f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d. Its beta .90 is an
explicit older repository default, not the user's 1.1 reprint error. Beta 1.0
is the corrected reference requested by the user; .90 remains a control.
The source PDF is SHA 7c16f5bdf7a08169b231c23928bcbc61d8851c47edfec743361bd0e02f32e43c.
The source code/PDF and old redesign code/receipts are preserved byte-for-byte.

The first 256 archived trials in each of original shards 0 and 31 must reproduce
all twelve registered fields exactly under the original seed, batch size 64,
original normalization and original container. These are historical machinery
checks only, not a new full replication of all 32 old streams.

## Specific issues and sequential comparison

1. Legacy control: beta .90, Fs=1000 Hz, 2048 samples, original per-record
   mean removal/RMS normalization, selected branch included in the echo mixture.
2. Population noise: retain .90 and the original model; replace noise-record
   centering/normalization with stationary Gaussian processes of unit population
   variance. White, AR(.9), and independent .65×AR(.97)+.35×AR(.45) noise are
   retained; the mixture is divided by sqrt(.65²+.35²).
3. Beta 1.0: change only the recurrence beta from the previous stage.
4. Nonselected echo: set the selected branch's mixture weight to zero and
   renormalize the other fifteen weights. The original protocol calls for
   non-observed trajectories, but the old implementation included the selected
   trajectory. Record its contribution before and after the correction.
5. Sampling 2000 Hz: preserve total duration 2.048 s with 4096 samples. Scale
   physical tau, observer window, branch-delay offsets and shifted-control offset
   in milliseconds. For colored noise use rho_new=rho_old^(1000/Fs) to preserve
   physical correlation times. White per-sample SNR remains fixed: this adds an
   independent-measurement assumption, not only interpolation.
6. Duration 8.192 s: 16384 samples at 2000 Hz with all corrected choices.
7. Duration 32.768 s: 65536 samples at 2000 Hz with all corrected choices.

The 18-frequency input contains 528, 639, 741, 852 and 963 Hz, above the old
500-Hz Nyquist limit. Their signed aliases at Fs=1000 are -472, -361, -259,
-148 and -37 Hz. Fs=2000 resolves the specified input harmonics. The nonlinear
recurrence can generate higher harmonics; no whole-output bandlimit or numerical
convergence claim is made. Changing sample rate defines a related discrete model
and does not itself establish a continuous-time limit. NIST discussion:
https://tf.nist.gov/phase/Properties/ten.htm

The old exact record-RMS noise has a constrained support. A deliberately
privileged diagnostic measures how closely subtracting candidate echo or phase
templates returns residual energy to that exact sphere. It uses exact simulated
baseline, noise scale and the declared discrete eta grid, not a physical sensor.
This is a diagnostic for an observation-model artifact and is not promoted as
a detector. The stationary-noise stage removes this exact-norm constraint.

## Detector and conditional information calculations

Retain the original discriminant corr(true)−abs(corr(shifted)) as D0. Add a
conditional generalized likelihood ratio using the exact simulated noiseless
baseline, true echo/phase templates, noise family and noise scale. These are
privileged inputs; the earlier D0–D4 also use exact latent simulation components.
No operational unknown-template or unknown-baseline detector is validated here.

Use the second half of each record. Whiten Gaussian residual r and templates E/P
with the known stationary covariance: identity for white, exact AR innovations
for AR(1), and exact finite-record Kalman innovations for the two-component
mixture. Native C++ computes the recurrence without periodic padding; verify W C
Wᵀ=I and quadratic products against independent dense covariance solves. Compile
with FP contraction disabled, hash source and shared library, record compiler.

For either template Q, maximize 2η〈Q,r〉−η²〈Q,Q〉 over 0≤η≤.20; the optimum
is clip(〈Q,r〉/〈Q,Q〉,0,.20). Score is max_echo minus max_phase, with eta=0
included in the null. This is a specified composite GLRT, not a uniformly most
powerful detector. The fixed-RMS lane deliberately uses a misspecified Gaussian
score as a control; Gaussian information bounds are not valid there.

For stationary Gaussian noise, set d_delay=η||W E||. The ideal simple-null
power at false-positive alpha=.015 is Φ(d_delay−Φ⁻¹(.985)). For the composite
null select its closest phase mean νP, with ν=clip(η〈WE,WP〉/||WP||²,0,.20),
and use d_phase=||W(ηE−νP)||. Its simple-versus-simple Neyman–Pearson power is
an upper bound for a detector required to maintain alpha uniformly at every
conditional phase-null mean. It is not a bound for a rule controlling only an
average mixture FPR, nor an unconditional physical information bound.

In the old-length white-Gaussian setting at eta=.05/SNR=0, the test half has
1024 samples, d=1.6 and even the simple-null oracle power is .2843082.
An 80% power target requires d≥3.0117116. This mathematical fact does not use
new experiment outcomes. The fixed-RMS original noise is not Gaussian, so this
bound applies to the corresponding Gaussian-noise setting, not that constrained
original distribution.

## Frozen design, inference and launch gates

All 32 original gain/tau/window cells; seven stages; 10368 trials per cell/stage:
**2,322,432 new trials**. Retain 16 phase trajectories, three selection operators,
three truth models, eight eta values and four SNR levels. The longest arm has
16 times the original physical duration and 32 times its recurrence steps.
Do not duplicate tasks merely to consume resources.

New batch size 512 is fixed for useful GPU occupancy. Block seed is the first
eight SHA-256 bytes (big endian, reduced modulo 2^63−1) of
`2912092600|shard|offset`. Same-length stages share phases/random draws; different
record lengths change noise draw layout and are not asserted to have identical
noise prefixes. Every stage/cell/offset ID is unique. Pilot uses 512 trials in
cells 0,15,16,31 for all seven stages. Those same identities overlap the first
production blocks and are development data; exclude the first 512 trials of
these four cells from confirmatory inference in every stage. Retain them in
complete accounting and report the reduced evaluation denominators.

Calibration/evaluation null labels follow the original crossed split. H1 with
eta>0 is positive; every other truth/eta combination is null, including phase
mixtures at all amplitudes. No learned model is trained. Set per-method p99
thresholds by stage/noise/operator/SNR from eligible calibration nulls only.
Report held-out overall and stratum FPR, target power eta≥.05/SNR≥0, weakest
eta=.05/SNR=0 corner, every eta/SNR/noise/operator curve, and correct-versus-
shifted discrimination. Retain the <=1.5% FPR and >=80% target-power requirements;
do not rename detector gate failure as mathematical nonidentifiability.

Report Gaussian conditional bounds by the same strata and all uncertainty.
Use 20000 paired configuration-cell bootstrap draws, seed 49120926, for six
successive-stage GLRT power/FPR contrasts; uncertainty is conditional on the
tested parameter panel. Holm correction over six two-sided cell sign-flip
power comparisons. Do not treat millions of correlated parameterized trials
as millions of independently sampled physical systems. No Stage 2 is launched.

Preflight ceiling: one GPU on one node, 15 minutes. Pilot: one node/four GPUs,
30 minutes. Full requires successful preflight, all 28 pilot receipts with
source/array identity checks, four distinct GPUs, finite arrays, selected-branch
exclusion exactly zero in corrected stages, and pilot-derived runtime/storage
projection. Full uses eight nodes/32 GPUs, three-hour hard ceiling (24 node-hours)
only if projected runtime×1.5+10 minutes fits. Refresh allocation information
before launching that wave. No automatic rerun after observation timeout.

Retain every failure and raw result hash. Independent review must recompute
scores on saved channels and all metrics before any completion claim. The
original HNC long run remains separate and unchanged.
