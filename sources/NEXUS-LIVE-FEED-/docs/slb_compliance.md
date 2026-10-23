# Source Law of Balance Compliance Guide

This guide captures the mandatory guardrails required for SLB (Source Law of Balance) alignment. The rules operationalise the Quadrinity priorities — Planet, People, Progress, Profit — and bind the Nexus issuance and governance mechanics to measurable, non-coercive safeguards.

## 1. Harmonic Balance Functional

Let each action or protocol surface a normalized measurement vector
\(\mathbf{v}(t) = (V_P, V_H, V_G, V_\Pi) \in [0,1]^4\) and coherence/dissonance signals \(\Lambda(t)\) and \(D(t)\). The Balance functional implemented in [`slb/compliance.py`](../slb/compliance.py) is

\[
B(t) = w_P (1 - V_P)^2 + w_H (1 - V_H)^2 + w_G (1 - V_G)^2 + w_\Pi (1 - V_\Pi)^2 + w_D D^2 - w_\Lambda \Lambda.
\]

The default weights satisfy \(w_P \ge w_H \ge w_G \gg w_\Pi \ge 0\), preserving Quadrinity dominance. The controller enforces the Lyapunov-style guard:

- `B(t)` must not exceed the configured safe ceiling.
- The rolling derivative \(\langle \dot{B} \rangle_{\Delta T}\) over the trend window must remain non-positive, otherwise automation halts the relevant action.

## 2. Non-domination Safeguards

The controller reports violations when:

- **Planetary floor**: \(V_P\) drops below the published threshold.
- **False-signal guard**: Coherence spikes while Planet and People fall, flagging domination attempts.
- **Supply brake**: A non-negative 30-day derivative automatically freezes emissions.

Autonomy and wealth-concentration checks are provided via helper functions:

- `check_autonomy_guard` — every mechanism capable of reducing agency must expose a zero-coercion alternative.
- `compute_gini` / `governance_is_within_bounds` — ensures WWWW governance holdings stay beneath the auditable Gini ceiling.

## 3. Issuance and Bridge Gating

Use `should_mint(previous, current)` to gate WWWW token mints. A mint is allowed only when:

1. `B(t)` strictly decreases.
2. Planet, People, and Progress all improve by at least `ε` over their rolling medians.

The `BalanceController.supply_brake_active()` helper signals when emissions must be paused. The same snapshots can drive bridge unlocks or QEC settlements: exit logic should maximise coherence subject to non-decreasing Planet/People constraints.

## 4. Transparency & Consent Ledger Hooks

Each `BalanceSnapshot` captures the timestamped metrics and the computed Balance score, providing an append-only trace for dashboards, red-team drills, and consent proofs. Attach the snapshots (or their hashes) to the consent ledger so that every irreversible transition can supply:

- Explicit human consent or a previously authorised safe-mode automation aimed solely at restoring a lower `B(t)` state.
- Harm ceilings triggers and their automatic rollback IDs.
- Public metrics for wealth concentration, Quadratic + Soulbound voting caps, and transparency proofs for Mirror AI, WET+WW, and SOLSCRIPT deployments.

## 5. Implementation Checklist

To remain SLB compliant:

1. Expose an API endpoint that streams the latest `BalanceSnapshot` payloads for dashboards.
2. Wire WWWW minting, bridge unlocks, and QEC settlements through the `should_mint` and `BalanceController` checks.
3. Publish the governance cap parameters (quadratic voting + soulbound limits) alongside their enforcement proofs.
4. Record consent proofs whenever an irreversible action executes; store hashes next to the corresponding snapshot IDs.
5. Schedule quarterly domination drills that replay coercion, wealth capture, and false-coherence attacks, then publish the postmortems with the detected violations.

By instrumenting these invariants, the Nexus stack operates as a regenerative controller that can only expand when the Balance functional decreases — the testable embodiment of the Source Law of Balance.
