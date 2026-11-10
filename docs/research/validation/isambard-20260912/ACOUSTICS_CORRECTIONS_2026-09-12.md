# Acoustics corrections — 12 September 2026

This is a versioned engineering follow-up to the King's Chamber acoustic experiment. The historical frozen verdict remains INCONCLUSIVE. All results concern simulated room geometry under stated acoustic assumptions.

## Corrections implemented and tested

1. The Galerkin basis normalization added NumPy boolean arrays, which combined truth values instead of counting nonzero mode indices. Integer counts now give the correct normalization for mixed modes. An independent numerical integration check gives a maximum Gram-matrix error of 4.0e-15.
2. The analytic mode generator accepted a frequency cutoff but did not apply it. The cutoff is now enforced for the spectral basis and controls.
3. The earlier validation compared only the modes below 60 Hz although 26 modes were reported. All 26 historical bare-box modes were rechecked against the discrete operator formula. Their frequency errors remain below 5.2e-12. The finest grid's residual is 1.08e-7: above the 1e-8 target but below the declared 1e-3 acceptance bound.
4. The random-start solver check is replaced in this explicit post-hoc amendment by an ARPACK solve of the assembled matrix with no analytic initial eigenvectors. Three fixed seeds each recovered all 26 modes: maximum relative eigenvalue error 1.19e-13 and maximum relative residual 1.20e-12. This addresses the convergence failure in the follow-up; it does not retroactively pass the old 300-iteration protocol.
5. The Schumann calculation compared chamber mode distances with one minimum per control room. The amended comparison uses one minimum per room in the same frequency band. **6,402/10,000 control rooms (64.02%) were at least as close as the chamber**; the plus-one calibrated rank value is 0.640236. The earlier Mann-Whitney value must not be treated as a valid comparison of matching quantities.

The corrected synthetic controls still find 6.28% of rooms hitting both claimed frequencies within 2%, and 3.15% within 1%. The bare chamber's approximately 1.11% deviation still passes the 2% condition and fails the 1% condition. These repairs do not establish distinctive tuning.

## Coffer and opening calculations

Corrected Galerkin runs used 355, 1,100 and 2,166 modes at cutoffs of 200, 300 and 380 Hz. The fundamental at 380 Hz cutoff is 16.441915 Hz. Increasing the cutoff from 300 to 380 Hz changes the first eight frequencies by at most 0.0496%, and all 26 by at most 0.3617%; this is finite-basis convergence evidence, not an exact solution.

The historical coffer FD solves had first-eight relative residuals as high as 0.20–0.30, exceeding the 1e-3 acceptance limit. Their small frequency differences against Galerkin did not validate those solves. Replacement geometry array **6498032** completed all four tasks: coffer grids at 0.20, 0.15 and 0.10 m, plus the 0.10 m opening model. The source/receipt audit passed for physical jobs 6498033, 6498034, 6498035 and 6498032. All 26 returned modes meet the declared residual bound. The 0.10 m coffer maximum relative residual is 3.76e-12; the opening maximum is 2.44e-10. Both finer jobs finished within their original 30-minute limits.

The converged 0.10 m coffer fundamental is **16.434845 Hz**. Corrected Galerkin versus that FD grid differs by at most **0.326% for the first eight modes** and **1.096% across all 26**. Changing the coffer grid from 0.15 to 0.10 m changes the first eight modes by at most 0.194% and all 26 by 1.113%. The opening model introduces a 2.034959 Hz mode; it must not be aligned with the rigid-coffer spectrum simply by comparing the same array indices.

The receipt audit checked source hashes, job identities, finite and sorted modes, and residual-array consistency. Eigenvectors were not retained, so it did not independently recompute the reported residuals or orthogonality. The new calculations strengthen numerical convergence evidence within these simplified geometries.

## Evidence

- Preflight `6497961`: PASS.
- Seven calculation tasks in array `6497982`: completed; source manifest and all returned result identities checked.
- Audits: `acoustics-repair-audit-6497982.json` and `acoustics-geometry-audit-6498032.json`.
- Archive: `acoustics-repair-6497982.tar.gz`, SHA-256 `8cf756dbdf59e6d66a51816226e59d2b08585b05c96c904f5539f6709a927679`.
- Original solver SHA-256: `47adeef1ed42b1458ed3cfc576c560216608013ac6826f5a4f38a183b673567d`.
- Corrected solver SHA-256: `669df70a688175d31e2ca3b6c39ba023fc6e3963fcef6fe604dd0bec4fef07f3`.
- Method documentation: [SciPy eigsh](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html).

The consolidated gate report is complete. All eight explicit numerical checks pass under the post-hoc amendment, giving **SUBSTANTIATED-GENERIC** for the specified closed-room geometry. G1 at 2% and G2 pass; strict G1 at 1%, G3 distinctiveness and corrected G4 Schumann comparison fail. The opening model shifts the nearest lower target mode to 16.674212 Hz, 2.927% above 16.2 Hz, and its selected pair fails the octave gate. Geometry robustness therefore limits extension of the closed-room result.

The original frozen verdict remains INCONCLUSIVE. Dimension detuning does not establish coffer-position robustness. Detailed values and input hashes are in `acoustics-amended-gates-20260912.json` and `Acoustics-amended-assessment-2026-09-12.md`.
