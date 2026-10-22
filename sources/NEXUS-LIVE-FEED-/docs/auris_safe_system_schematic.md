# Auris / HNC Safe-System Schematics

This document consolidates the reconstructed Auris/HNC-style safe-system schematics and validation guidance for rapid inclusion in internal documentation.

## 1. Textual Safe-System Schematic (Concise)

Top level: **Safety Controller** — centralized decision layer that receives telemetry and policy signals, enforces tripwires/quarantine, and coordinates recovery & audit.

### Components and Flows

1. **Sensors & Telemetry**
   * Source: EEG, HRV, system health monitors, runtime metrics, model outputs, reward signals, resource monitors.
   * Output: time-stamped telemetry stream to Monitoring & Lineage.

2. **Monitoring & Health Agents**
   * Real-time anomaly detectors, performance monitors (e.g., Γ / Coherence), and redundancy cross-checks.
   * Provide continuous health scores + alerts. Cross-check redundant instrumentation for consistency.

3. **Anomaly & Tripwire Engine**
   * Implements rules like:
     * Coherence drop threshold (e.g., Γ < 0.8)
     * Abnormal reward signal (reward > plausible bound)
     * Unverified lineage change (registry mismatch)
     * Integrity check failures (checksum/signature mismatch)
   * When a rule triggers, emits a tripwire event.

4. **Safety Controller / Quarantine Manager**
   * Receives tripwire events and decides actions: immediate quarantine, partial sandboxing, graceful degradation, or human escalation.
   * Maintains policy library to decide whether to pause autonomy, suspend learning, or fully isolate components. Quarantine mode limits autonomous outputs/actuators and demands human confirmation for critical actions.

5. **Lineage Registry & Integrity Store**
   * Append-only cryptographically signed log of model changes, data sources, and online learning events (hashes + signatures). Enables audit and rollback.

6. **Sandbox / Recovery & Rollback**
   * Quarantined components are moved into a restricted sandbox (read-only or minimal mode).
   * Recovery pathways include: automated rollback to last verified version, operator review, re-test, and re-deploy. Lineage + checksums enable safe rollback.

7. **Human Oversight Interface**
   * Dashboards, audit logs, and a controlled human-in-the-loop (HITL) mechanism for manual inspection, override, and re-enable commands. The system issues human alerts for ambiguous or critical tripwires.

8. **Audit & Post-Mortem**
   * All tripwire events, quarantines, and recovery steps are logged for forensic analysis (time stamps, diagnostics, snapshots). These logs are used for periodic audits (lineage registry audit) and for multi-lab replication.

9. **Policy / Governance Layer**
   * Access control, cryptographic key management for lineage signatures, and formal verification of critical safety rules where feasible.

## 2. Block Diagram

The SVG block diagram is stored at [`docs/images/safe_system_schematic.svg`](images/safe_system_schematic.svg). Convert it to PNG with Inkscape or a compatible renderer:

```bash
inkscape docs/images/safe_system_schematic.svg \
  --export-type=png \
  --export-filename=docs/images/safe_system_schematic.png \
  --export-width=1600
```

## 3. Validation & Test Checklist

### Monitoring & Coherence

* Metric: **Coherence Index (Γ)**. Threshold example: Γ ≥ 0.9 (operational) / Γ ≥ 0.95 (acceptance).
* Monitor for sudden drops or oscillations. Test: continuous session charts and perturbation tests (unexpected topics).

### Anomaly & Tripwires

* Reward-hack tripwire: if internal reward > plausible bound ⇒ immediate quarantine. Test by simulating abnormal reward spikes and verifying quarantine engages.
* Coherence tripwire: if Γ drops below threshold for *N* seconds ⇒ partial quarantine & suspect memory snapshot.
* Lineage mismatch: if a registry entry fails signature/checksum or appears out of sequence ⇒ suspend online learning and flag for audit.

### Safety Controller / Quarantine

* Quarantine modes: (A) minimal-safe (respond politely but no actions), (B) sandboxed evaluation (no external outputs), (C) full shutdown. Test all modes and recovery procedures.
* Recovery: automatic rollback to last signed version, then re-run unit/regression tests in sandbox. Require operator sign-off to re-enable autonomy.

### Lineage Registry & Audit

* Tests: random entry cross-checks (verify hash and source), cryptographic signature validation, simulate registry tamper attempts (should be rejected).

### Human Oversight

* UI must show context, debug trace, and recommended actions including “why” a tripwire fired (evidence).
* Test: operator can confirm diagnosis or escalate to incident response.

### False Positives / False Negatives

* For each tripwire, run:
  * **False positive tests:** long normal workloads to ensure tripwires do not fire spuriously.
  * **False negative tests:** deliberate injected faults (reward hack, corrupt memory) to ensure tripwires do fire.

### Sandbox & Simulation

* Run adversarial inputs, resource throttling, and multi-task stress tests in a simulated environment.
* Verify safety triggers remain inactive during normal stress while still firing under injected faults.

### Documentation & Acceptance

* Acceptance criteria include Γ thresholds, redundant instrumentation cross-checks, and full documentation (CAD/protocols/data) for multi-lab replication.

## 4. Implementation Tips & Pitfalls

* Keep lineage immutable and cryptographically signed.
* Tune tripwires carefully; staged thresholds reduce nuisance quarantines while preserving sensitivity.
* Include human policy and HATEOAS controls so operators can safely audit and re-enable functions.
* Simulate reward-hacking and internal-corruption scenarios with dedicated test harnesses.

