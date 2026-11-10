# Tandem in Unity 10-9-1 Timeline-Branch Protocol

Status: staged experiment specification; no scientific or ontological verdict has been reached.

## Authoritative 10-9-1 mapping

This experiment uses Gary Leckey's clarification of 26 August 2026 as the
authoritative semantic mapping:

- **10 — Source / Harmonic Fish:** the finite vacuum of total harmonic
  potential. The numeral is an ontological label, not a forced count of ten
  frequencies.
- **9 — Possibility Sea / Phase Fish:** the multiversal plane of dynamically
  permitted phase configurations. A finite simulation samples this plane; it
  does not claim that the physical possibility space contains only nine states.
- **1 — Realised Now / Motion Fish:** the prime, presently realised trajectory
  in which delayed echoes of the possibility sea may reside.

The cycle is `10 -> 9 -> 1 -> 10`: Source generates permitted phase
possibilities; an explicit selection operator produces the realised Now; the
Now returns to Source as causal memory.

The repository did not contain literal Motion Fish, Phase Fish, or Harmonic
Fish modules when this protocol was prepared. They are author-defined theory
roles mapped here onto the pinned HNC substrate, phase-domain ensemble, and
realised recurrence. This prevents later software labels from being
misrepresented as an earlier derivation.

## Mathematical registration

The Source uses the deposited HNC substrate:

`S_10(t) = sum_i w_i sin(2*pi*f_i*t + phi_i)`

The finite computational sample of the possibility plane is:

`Omega_9(t) = {Lambda_j(t) : phi_j drawn from the registered phase measure}`

Each sampled possibility obeys the pinned HNC recurrence:

`Lambda_j(t) = S_j(t) + alpha*tanh(g*mean_Delta(Lambda_j)) + beta*Lambda_j(t-tau)`

The candidate realised Now is:

`N_1(t) = Lambda_selected(t) + eta*E_9(t) + measurement_noise(t)`

where `E_9(t)` is a registered, delayed and normalised composite of the
non-observed phase-domain trajectories. `eta=0` is the no-cross-domain null.

Because the research does not yet supply a unique selection equation, three
predeclared candidate operators are tested rather than silently choosing one:

1. source lock — greatest causal agreement with the Source;
2. echo coherence — greatest registered self-delay coherence;
3. minimum action — smallest normalised step-to-step motion.

An operator-specific result is not promoted to a universal law. Robustness
across operators is reported separately.

## Hypotheses

- **H0-delay:** the realised series is a conventional single-domain HNC delay
  recurrence plus measurement noise; `eta=0`.
- **H0-phase-mix:** the realised series contains an equally strong undelayed
  mixture of sampled phase-domain trajectories, testing whether ordinary phase
  superposition is mistaken for a delayed possibility-sea echo.
- **H0-shuffled:** apparent echo evidence is unchanged when the registered
  phase-echo template is shifted away from its declared delay structure.
- **H1-10-9-1:** the realised series contains a non-zero contribution from the
  registered possibility-sea echo template; `eta>0`.

Stage 1 is a synthetic identifiability and sensitivity calculation. It asks
whether the proposed H1 signature is measurable at all and calibrates false
positives under H0. It does not use a physical observation and cannot prove
that physical reality branches.

## Isambard Stage 1 design

- 32 independent GH200 shards.
- Two observer gains, four causal delays, and four observer windows.
- HNC FP64 recurrence with the pinned 18-frequency substrate.
- A finite 16-trajectory Monte Carlo sample of the 9-plane per trial.
- Three selection operators.
- White, AR(1), and two-timescale coloured-noise controls.
- Registered echo strengths from zero through 0.2 of realised-signal RMS.
- Signal-to-noise ratios from -10 dB through 20 dB.
- Calibration and held-out null trials are separated before thresholds are
  calculated.
- A time-shifted echo template is retained as a negative control.
- The phase-mixture null is simulated at every registered injection strength.

Reservation ceiling: 32 GPU-hours. Tasks release their allocation immediately
when complete; the ceiling is not a spending target.

## Predeclared gates

The aggregate may report `SYNTHETIC_SIGNATURE_IDENTIFIABLE` only if all of the
following hold:

1. held-out no-echo false-positive rate is at most 1.5%;
2. detection power is at least 80% for `eta >= 0.05` and `SNR >= 0 dB`;
3. the correctly delayed template outperforms the shifted template on the
   non-zero-echo trials;
4. all 32 immutable receipts are present, finite, hash-bound, and schema-valid.

Otherwise the verdict is `SYNTHETIC_SIGNATURE_NOT_IDENTIFIABLE` or
`INCOMPLETE`. No Stage 1 result may be labelled physical observation,
independent replication, or proof of timeline branches.

## Required Stage 2 before a physical claim

1. Freeze the Stage 1 detector, code hashes, selection operators, thresholds,
   exclusions, and analysis before inspecting physical outcomes.
2. Supply independently timestamped laboratory time series with sensor
   calibration, units, raw channels, sham runs, environmental controls and an
   immutable chain of custody.
3. Compare the frozen 10-9-1 detector against conventional delay equations,
   phase mixtures, autoregressive models and instrument artefacts on blind
   holdouts.
4. Retain negative results and all excluded observations with reasons.
5. Obtain an independent team rerun from the frozen package and immutable data.

Only a unique, preregistered physical prediction that survives these controls
and independent replication would materially support the literal branch claim.
