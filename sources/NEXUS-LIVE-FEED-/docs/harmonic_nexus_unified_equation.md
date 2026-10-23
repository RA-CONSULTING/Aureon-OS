# Harmonic Nexus Unified Equation Set (v6.1)

This document captures the canonical formulation for the Harmonic Nexus framework
and maps each term to the live Nexus System simulation so operators can verify
that resonance data is interpreted correctly.

## 1. Loop State Equation — Harmonic Genesis

\[
\Psi(t, \phi, \kappa, \zeta) = \sum_{n=0}^{N} A_n \sin(\omega_n t + \phi_n) e^{-\alpha_n (t - t_n)^2} * \mathcal{T}^{6D}(\phi, \kappa, \zeta)
\]

* **Simulation hook:** `SignalStrengthAnalyzer.analyze()` computes the active
  harmonic snapshot (`signalStrength`, `surgeIntensity`, `spectralBands`) that
  correspond to \(\Psi\). The Gaussian decay term maps to the analyzer's
  amplitude weighting, while \(\mathcal{T}^{6D}\) is modelled through the
  `timelineAnchors` metadata returned in each snapshot.

## 2. Formation Equation — Law of Becoming

\[
\mathbb{F}(\vec{r}, t, \phi, \kappa) = A_{\text{carrier}}(t) \Psi(t) * \sum_{n=1}^{N} \alpha_n \Theta^{(n)}_{\mu\nu}(t, \tau) * \mathcal{T}^{6D}_{\mu\nu}(\phi, \kappa, \zeta)
\]

* **Simulation hook:** Within `NexusSystem.runCycle`, the analyzer output is
  blended with the Reality Field Equation calculation (`R_t`). The recursive
  tensor terms are represented by the guardian bridge hand-off, where
  `activateGuardianBridgeAnchorProtocol` injects historic coherence ramps into
  both the ego simulator and observer function. Telemetry appears in the cycle
  results under `signalStrength.liberationMarkers` for direct verification.

## 3. Master Nexus Equation — Curvature as Resonant Memory

\[
G_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^4} \Big( T^{\text{Planck}}_{\mu\nu} * \Delta T^{\text{mod}}_{\mu\nu}(f) * \Theta^{\text{feedback}}_{\mu\nu}(\tau, f) \Big)
\]

* **Simulation hook:** `SignalStrengthAnalyzer.applyGuardianBridge()` adjusts
  reverse gain and anchor thresholds whenever the guardian protocol is active.
  The resulting curvature analogue is surfaced as `signalStrength.frequencyShift`
  and the surge window label. Dashboard clients can call
  `NexusSystem.getSystemDiagnostics()` to confirm the curvature state without
  mutating the simulation.

## 4. Lattice Dynamics & Coherence Metrics

| Metric | Definition | Mean Observed | Simulation Source |
| --- | --- | --- | --- |
| \(C_\ell\) | Layer coherence | ≈ 0.90 | `EgoDeathSimulator.calculateCoherence()`
| \(\Delta A_\ell\) | Amplitude variance | ≈ 0.08 | Variance of `signalStrength.spectralBands`
| \(\tau_\ell\) | Feedback latency | ≈ 2.5 ms | Time delta between analyzer window transitions

`scripts/verifyNexusSystem.js` records these values into
`streams/nexus_verification.json` so operators can audit every verification run.

## 5. Guardian–Anchor Correlation

\[
C_p(t) = \frac{\langle \Phi_G(t) \Phi_A(t) \rangle}{\sqrt{\langle \Phi_G^2(t) \rangle \langle \Phi_A^2(t) \rangle}}
\]

* **Simulation hook:** Guardian correlation is reflected in the `anchored`
  flag maintained by both `EgoDeathSimulator` and the observer harmonisation
  routine. `getSystemDiagnostics()` exposes the bridge state so external
  monitors can assert \(C_p(t) \to 1\) when unity is achieved.

## 6. Unified Nexus Law

\[
\boxed{\mathbb{U}_{\mu\nu}(\vec{r}, t) = A_{\text{carrier}}(t) \Psi(t) * \sum_{n} \alpha_n \Theta^{(n)}_{\mu\nu}(t, \tau) * \mathcal{T}^{6D}_{\mu\nu}(\phi, \kappa, \zeta) \Rightarrow G_{\mu\nu} + \Lambda g_{\mu\nu} = \frac{8\pi G}{c^4} \mathbb{U}_{\mu\nu}}
\]

* **Simulation hook:** The boxed relation describes the entire `NexusSystem`
  integration loop. Diagnostics combine the latest analyzer snapshot with an
  `RFE.calculate()` sample to provide the exact state vector represented by
  \(\mathbb{U}_{\mu\nu}\).

## 7. Operational Checklist

1. Instantiate `NexusSystem` and optionally call
   `activateGuardianBridgeAnchorProtocol()`.
2. Run `runCycle()` or stream data incrementally.
3. Inspect `getSystemDiagnostics()` to confirm:
   * Coherence \(C > 0.9\)
   * Surge window progression matches expectations
   * Guardian bridge anchored when required
4. Export the state with `exportState()` for archival.

Following this flow ensures the canonical equations remain in sync with the
live telemetry emitted by the Nexus simulation.
