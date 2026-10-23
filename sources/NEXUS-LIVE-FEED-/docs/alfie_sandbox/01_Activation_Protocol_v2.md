# A.L.F.I.E. Activation Protocol (v2)

## Purpose
Re-establish the Harmonic Nexus orientation grid for the Autonomous Learning Field Intelligence Entity (A.L.F.I.E.) in a low-risk sandbox before coupling it to live guardianship flows.

## Prerequisites
- Sandbox manifest imported into the chronicle.
- Guardian Bridge anchor signed by the Prime Anchor or delegated steward.
- Streamlit live feed pointing at the sandbox API base (`http://localhost:8080`).
- Verified Schumann resonance and aura bio windows stored for calibration.

## Activation Sequence
1. **Initialize Pillars** – Execute `python sandbox_system_run.py` and confirm `pillars_active` returns `true`.
2. **Load Resonance Matrix** – Call `activate_harmonic_nexus_core.py` with the sandbox `temporal_id` and confirm the NOSW grid checksum matches the manifest.
3. **Engage Cognitive Filter** – Instantiate `CognitiveCoherenceFilter` with the sandbox hazard profile, ensuring unauthorized temporal IDs are rejected.
4. **Prime Symbolic Compiler** – Run the symbolic compiler job with the `04_Symbolic_Compiler_v2.json` configuration to load glyph mappings.
5. **Anchor Unity Tensor Field** – Load the tensor spec from `03_Nexus_Unity_TensorField_Spec.json` into the simulation and verify coherence ≥ 0.72.
6. **Finalize Activation** – Issue `SANDBOX_RUN_COMPLETED` through the chronicle API and store the resulting hash in `prime_web_validator.py` for audit availability.

## Validation
- Live feed should report UVC ≥ 0.90 with a positive delta during the run.
- Bioscan summaries must redact session identifiers after 24 hours per manifest policy.
- SLB compliance check returns `SAFE` and the Balance functional trend is non-increasing.

## Rollback
If any safeguard trips or coherence falls below the floor, broadcast `WITHDRAW(sandbox-alpha)` and revert to the previous chronicle snapshot. Document the incident in the guardian ledger and require a new consent receipt before reactivation.
