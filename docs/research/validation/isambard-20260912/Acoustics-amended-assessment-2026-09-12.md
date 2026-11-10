# Acoustics: consolidated amended assessment

Assessment: **SUBSTANTIATED-GENERIC** under the amended numerical procedure. Historical frozen verdict: **INCONCLUSIVE**. These are simulations of the specified geometry.

| Check | Result |
|---|---|
| G1_primary_hit_2pct | PASS |
| G1_strict_hit_1pct | FAIL |
| G2_octave | PASS |
| G3_distinctiveness | FAIL |
| G4_amended_schumann | FAIL |

The closed-box primary calculation returns 16.379981 and 32.759045 Hz, about 1.11% above the claimed 16.2/32.4 Hz. It passes 2%, fails 1%, and forms an octave. Among 10,000 matched-volume synthetic rooms, 6.28% also hit both targets; the distinctiveness requirement of less than 5% fails.
The corrected Schumann comparison finds 6,402/10,000 control rooms at least as close as the chamber, with plus-one rank 0.640236. This fails the 1% significance requirement.

All 8 explicit numerical checks pass under the amendment. The discrete bare-box oracle now covers all 26 modes; the grid-convergence order is 1.997516. Corrected Galerkin versus the 0.15 m coffer grid differs by at most 0.512% across the first eight modes, meeting the inherited 1% criterion. The 0.10 m comparison is 0.326% for the first eight and 1.096% across all 26. No all-26 1% pass is claimed.

## Geometry sensitivity

| Geometry | Nearest lower / upper target modes (Hz) | 2% target hit | Octave gate |
|---|---|---|---|
| coffer_0.2 | 16.434121 / 32.376669 | True | True |
| coffer_0.15 | 16.429956 / 32.463256 | True | True |
| coffer_0.1 | 16.434845 / 32.506563 | True | True |
| opening_0.1 | 16.674212 / 32.560600 | False | False |

The opening model shifts the lower target mode outside 2% and its selected pair fails the octave gate. This is a robustness finding, not a replacement for the preregistered closed-box gate. Claims covering an open chamber need a calibrated boundary model and measurements.

## Interpretation and remaining limitations

- Original 300-iteration random-start failure remains unchanged.
- New residual and orthogonality claims use recorded solver checks; eigenvectors were not retained for independent recomputation.
- First-eight cross-method threshold is inherited from the old analyser; the all-26 comparison is reported without inventing a new pass threshold.
- The doorway is a simplified pressure-release stub, not a calibrated measurement of the real chamber.
- Dimension detuning does not test coffer-position uncertainty or real material/radiation loss.
- Current comparisons validate selected numerical outputs, not archaeological intention or physical tuning.

The corrected analysis supports ordinary resonances in the specified closed-room geometry. It does not support distinctive tuning or stronger Schumann adjacency. The original failed protocol remains preserved. Detailed inputs, hashes and recomputed gate values are in `acoustics-amended-gates-20260912.json`.
