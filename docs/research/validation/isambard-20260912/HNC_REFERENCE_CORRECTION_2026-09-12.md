# HNC reference correction and horizon evidence

Date: 12 September 2026. Status: author-directed correction with an open archival-source question. Claim class: computational simulation for the numerical results below.

## Corrected reference

Gary Leckey identifies **beta = 1** as the intended reference for the delayed-feedback HNC model and **1.1 as a reprint error**. Future experiments addressing that model must identify beta=1 as the author-corrected reference. Historical comparisons against 1.1 remain part of the record and must not be relabelled as measurements at 1.

This correction does not declare a universal stability theorem. A reference parameter, a finite-time numerical transition and an asymptotic stability boundary are different statements. The transition can depend on the equation, gain, delay, averaging window, initial conditions, forcing and classification rule.

Do not apply this correction indiscriminately to every symbol beta. In the August 2025 `Harmonic_Nexus_Theory_Part_2_Validation.pdf`, beta is a cubic saturation coefficient in a different equation. Local linear conditions involving beta and alpha times gain also must not be replaced with a bare global threshold.

## Documentary provenance

The public-source check recovered the PDF attached to [Zenodo record 17527831](https://zenodo.org/records/17527831), which ResearchGate cites for the Master Equations paper. The record was created on **5 November 2025** and gives that publication date; its current metadata was updated in July 2026. The six-page PDF passes the repository checksum and has SHA-256 `dad45d3d999adc865a47b3eb2a737b6c9b618be833262f8914eb32a5f806d268`. It differs from the 180 indexed Git-native document hashes. Rendered pages 2 and 6 retain the combined local condition near one and the 1.1 cliff respectively. Current file identity is verified; an independent archived capture proving the exact file bytes present in November 2025 has not been obtained. This strengthens the public provenance without resolving the reprint chronology. The 77 Academia records and 29 Substack source sections are indexed in `Public-original-paper-trail-2026-09-12.md`.

The full-history search recovered an earlier candidate: the 803-page `nexus1v_45dcee45b3.pdf` compilation, with PDF creation metadata of **11 July 2025**, first deposited in Git on 12 July 2026 at `b4bfe63756791c427cdbdd64fe56301aced1e7ef`. Metadata does not authenticate the date of every included passage. Its extractable text did not establish the delayed-feedback beta=1 threshold. The previously located `The_Harmonic_Nexus_Core_HNC_A_Unified_Framework.pdf` has creation metadata of 23 July 2025 and first content deposit on 5 April 2026. August 2025 Word material uses beta as cubic saturation in a different model.

The history now covers 3,431 reachable commits and 36,396 path/content versions, with 180 distinct native documents indexed after archive inspection. Images and broken text mapping were not comprehensively OCR-verified; one nested source archive is truncated. These limits are recorded in `GitHub-research-history-2026-09-12.md`.

Direct archival near-one wording was recovered in `HNC_research_paper_2026-04-07.md.pdf`, first deposited at `c7d0ca10d619b943278348814fca11cd49873a51` on 7 April 2026. Page 16 says to expect sharp growth at beta>1. Page 9 describes finite-horizon boundaries at 1.0–1.05 or 1.10–1.20 depending on the amplitude criterion, while retaining the 1.1 reference. Both pages were visually verified. The November 2025 metadata-dated Master Formula PDF likewise contains a combined local condition near abs(beta)+alpha*g<=1 on page 2 and a 1.1 cliff statement on page 6. The combined local condition is not a bare universal beta threshold.

The following deposited later versions contain 1.1:

| File | Recorded provenance |
|---|---|
| `docs/research/whitepapers/HNC_Grand_Unified_Framework_Leckey_2026.docx` | Same content first deposited under a root-level filename on 3 April 2026 at `4d31fe078b80d455dab8bc0ad7d25bb1602bd12e`; SHA-256 `de4c29869fc5f533139ccd071c844575672be98d9403be71b5b7d2e85c52eae8` |
| `Antarctic research/HNC_White_Paper_v3.docx` and `HNC_White_Paper_v3-1.docx` | Identical bytes; Word creation metadata 29 April 2026; first Git addition 22 May 2026; SHA-256 `77bd1f9364271d0f7feddd7542a0ea54df3caea71b854b711a2269d9ad2149a4` |

An archival statement about growth above one has now been recovered, but the **original reprint chronology and an earlier unambiguous exact beta=1 reference remain unverified**. The author's current instruction supplies the correction authority; the historical wording and numerical follow-up are recorded separately. Existing source documents are preserved; this is a dated erratum, not a backdated replacement.

## Completed horizon experiment

The campaign covers gains 0.5, 1.5 and 4; delays 10, 50 and 100; and averaging windows 1, 10, 50 and 100: 36 parameter cells. Each cell contains 121 alpha values and 203 beta values, for 884,268 trajectories in total. The fine beta grid is 0.95 through 1.05 in steps of 0.0005, with separate 0.85 and 1.1 controls.

The recorded stable class requires no escape above the 1e12 numerical threshold, at least one valid Lyapunov block, and a finite-time Lyapunov estimate no greater than 1e-4 per step. There are 83,329 bounded trajectories with no valid Lyapunov blocks at each checkpoint; they are excluded from this class.

| Steps | Stable at beta=1 / tested | Total escaped | New escapes since prior checkpoint | Median first downward 50% crossing |
|---:|---:|---:|---:|---:|
| 65,536 | 4,314 / 4,356 | 264,959 | — | 1.005232 |
| 262,144 | 4,356 / 4,356 | 401,072 | 136,113 | 1.002116 |
| 1,048,576 | 4,356 / 4,356 | 431,913 | 30,841 | 1.000306 |
| 4,194,304 | 4,356 / 4,356 | 439,572 | 7,659 | 1.000250 |

Crossings are interpolated only within the fine grid, and all downward crossings are retained because some curves are nonmonotonic. Medians summarize the 36 cells; they are not pooled confidence intervals. At the final horizon, crossings range from 1.000250 to 1.000256. This is approximately the midpoint of the first grid interval above 1, so the result has reached the resolution limit of the current beta grid. It is not evidence for a precisely resolved critical value of 1.00025.

The results support testing progressively longer horizons on a finer grid around 1. They do not prove asymptotic stability or the physical interpretation of HNC.

## Reproducibility and audit

- Original horizon run: job `6497215`. Extension: job `6497438`, completed in 27m09s using nine nodes and 36 GPUs.
- Final audit: `6497683`, PASS across 144 receipts and 288 result/checkpoint file hashes, source/configuration hashes, receipt chains and array consistency.
- Physical GPU UUIDs establish 36 distinct GPUs across nine hosts for each extended checkpoint. UUIDs were not recorded by the older run and are not retroactively claimed.
- Configuration SHA-256: `f43b0d9c725c421f59e130cb5ef33bae23969e8f13d563d5f68168cfa55bbe65`.
- Mathematical harness SHA-256: `bb0e231ec1a39abc5b1096413fab6cbd3c68ce2934b7e4ba82fbfb2566b6fe9d`.
- Audit program SHA-256: `b07f282782ed5cc7f918a3c7fce212b9e9661d953119e9c372d2d716fe778172`.
- Report: `hnc-four-million-step-audit-6497683.json`. Remote run root: `/projects/u6vs/hnc-organism/expansion-20260912/million-6497438`.
- Result/source archive excluding large checkpoint tensors: `hnc-million-6497438-results.tar.gz`, SHA-256 `909a22227ce6ad84a25b4d3419ac58122b4f4a028063add39c534a18c7c65ca7`.

The audit verifies artifact integrity and recorded identities. It does not independently recompute checkpoint tensor semantics or establish independent scientific replication. The current campaign uses versioned source snapshots and preserves the earlier source pin `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d` for documentary provenance.

## Completed fine-grid extension

Production 6498143 and audit 6498144 completed after the campaign above. The expanded 128-cell grid tests 6,303,616 trajectories at beta spacing 0.000005 through 16,777,216 steps. All 15,488 beta=1 cases meet the finite-time stable rule; no beta=1.1 control does. The median first downward 50% crossing moves from 1.000423625 at 1,048,576 steps to 1.000015067 at the final horizon, with final cell range 1.000002542–1.000077614. The last million-step segment adds 13,284 escapes.

Audit 6498144 passed 2,176 receipts and 4,352 result/checkpoint hashes; reanalysis 6500155 rehashed result grids and receipt chains and matched final totals. The final horizon still has 13,293 bounded trajectories without valid Lyapunov blocks, excluded from the stable class. These expanded results support the reference near one but do not prove an exact universal boundary. See `HNC-fine-grid-results-2026-09-12.md` for full outcomes, nonmonotonicity, cost and limits.
