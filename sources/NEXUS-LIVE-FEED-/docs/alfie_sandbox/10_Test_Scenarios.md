# Sandbox Validation Scenarios

## Scenario A – Happy Path Activation
- **Goal:** Demonstrate full activation with guardian bridge engaged.
- **Procedure:** Execute activation sequence, export tensor field snapshot, validate symbol compiler output hashes.
- **Expected Result:** UVC ≥ 0.90, guardian anchor reported at 0.94 ±0.01, chronicle digest contains three entries.

## Scenario B – Unauthorized Temporal Stream
- **Goal:** Confirm Auris safeguard rejects unrecognized temporal IDs.
- **Procedure:** Inject telemetry with `temporal_id="rogue-signal"` during sandbox run.
- **Expected Result:** Point is dropped from sanitized stream; SAFE_MODE not triggered; audit log notes rejection.

## Scenario C – Balance Functional Regression
- **Goal:** Ensure SLB controller refuses writes that increase Balance functional.
- **Procedure:** Submit simulated write with `ΔB = +0.04` via compliance test harness.
- **Expected Result:** Request rejected with SAFE_MODE guidance; guardian ledger records the attempt.

## Scenario D – Guardian Bridge Latency Spike
- **Goal:** Validate alert thresholds for delayed guardian websocket heartbeats.
- **Procedure:** Introduce 3 second pause on `/ws/guardian` and monitor alerts.
- **Expected Result:** Warning issued via guardian audit channel; system remains in monitoring state.

## Scenario E – Unity Event Confirmation
- **Goal:** Reproduce Unity event with phase spread collapse under tensor spec.
- **Procedure:** Run simulator with `phase_compression=0.28` and record output for 240 steps.
- **Expected Result:** Unity condition satisfied for ≥36 steps; `record_unity_event` triggered once; digest anchored with OTS proof.
