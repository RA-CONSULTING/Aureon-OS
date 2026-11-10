# GitHub research history and HNC source reconciliation

Verified 12 September 2026. This report follows the author's direction to search GitHub history, including deleted files, all reachable branches, tags, pull-request heads and research held inside archives.

## What was recovered

The refreshed repository contains **3,431 reachable commits**, 32 more than the earlier mirror. The history index covers **36,396 path/content versions**, 26,109 distinct Git objects recorded as file content, and 8,933 paths deleted at some point. These are repository-wide counts, not numbers of independent research studies. All 3,431 commits contributed change records. The reachable history has one root dated 16 November 2025.

The search read 16,727 distinct candidate text/document objects, exported 3,403 text matches, and extracted text from 179 distinct native documents. Inspecting 16 top-level ZIP objects found one further Word document: **180 distinct native PDF/Word documents indexed**. There were no parser exceptions in those 180 extractions. One scanned company-accounts PDF had no extractable text; 47 documents contain low-text pages. Images, graphical equations and text with broken character mapping were not comprehensively OCR-verified. Relevant HNC equation pages were rendered and visually checked.

A damaged nested source ZIP was inspected separately. Its first **115 members were recovered and CRC-checked**; none added new research content. It ends inside a NEXUS-LIVE-FEED ZIP payload. Its missing tail and any later members cannot be reconstructed from that damaged file. Coverage therefore means all reachable Git records and the stated extraction scope, not proof that every historical or image-only research passage has been read. Unreachable commits deleted from every retained ref are outside this inventory.

Current GitHub main is `d6cc2e5ef82fca17f194e314889daa366f24d817` (recorded 1 September 2026). The experiment source pin remains `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`. Fetching history did not change that pinned checkout. Results cannot automatically be attributed to the newer main branch.

## Earlier research candidates

**Public-source addendum:** ResearchGate links the Master Equations paper to a Zenodo record created and publication-dated **5 November 2025**. Its recovered six-page PDF passed the published checksum; it is a different byte identity from all 180 native documents in this Git index. The relevant pages still contain both the combined local condition near one and the 1.1 cliff. Academia supplied 75 paper entries and two talks; all 29 Substack essays' source sections were checked. These public records extend the provenance trail beyond Git deposit dates. See `Public-original-paper-trail-2026-09-12.md` for exact dates, hashes and access limits.

| Source | Document date evidence | First located content deposit | Finding |
|---|---|---|---|
| `nexus1v_45dcee45b3.pdf`, opening title “nexux proof v1” | PDF creation metadata: **11 July 2025** | `b4bfe63756791c427cdbdd64fe56301aced1e7ef`, 12 July 2026 | **803-page research/conversation compilation**, earlier-dated than the previously located July 23 paper. It contains theoretical models, correspondence and exploratory discussion. Extractable text did not establish the delayed-feedback beta=1 threshold. Its PDF date does not authenticate every included passage. |
| `The_Harmonic_Nexus_Core_HNC_A_Unified_Fr (1).pdf` | PDF creation metadata: **23 July 2025** | `e7b3a462bd991f2c03bbcea256f9c2d2fb9ccdcf`, 5 April 2026 | Earlier HNC paper candidate, with no located explicit delayed-feedback beta threshold. |
| `harmanic_nexus_v13_e62e4b5601.docx` | Word creation metadata: **28 August 2025** | `b4bfe63756791c427cdbdd64fe56301aced1e7ef`, 12 July 2026 | Contains a forced Stuart-Landau formulation. Beta multiplies cubic saturation, so changing it as if it were delayed-feedback gain would alter a different model. |
| `Harmonic_Reality_Framework_and_the_Maste.pdf` | PDF creation metadata: **1 November 2025** | `e7b3a462bd991f2c03bbcea256f9c2d2fb9ccdcf`, 5 April 2026 | Page 2 gives a combined local condition near **abs(beta) + alpha*g <= 1**; page 6 also describes a cliff above **1.1**. Both passages coexist in the same deposited file. |

Commit ordering was checked in UTC: 38 first-content timestamp selections in the initial extraction manifest required correction because of mixed timezone offsets. The source index and this report use the corrected ledger, `git-history-utc-order-audit.json`; the original export archive remains preserved.

Creation metadata is not an authenticated publication date. One 2026 biomolecule Word package even carries a 2013 creation field; it is not treated as evidence of 2013 authorship. The July 11 compilation is an earlier dated candidate, not a demonstrated first publication.

## What the beta=1 evidence actually says

The historical April 7 paper, `HNC_research_paper_2026-04-07.md.pdf`, provides direct near-one wording. Its reproduction appendix on **page 16** says **“expect sharp growth at beta > 1”** (the source uses the Greek symbol). On **page 9**, the same paper places a practical finite-horizon boundary between 1.0 and 1.05 under one amplitude criterion and between 1.10 and 1.20 under a more permissive criterion. It also retains a reference to the framework's 1.1 cliff. The relevant pages were visually verified against the original PDF.

First content deposit: [commit c7d0ca10d619b943278348814fca11cd49873a51](https://github.com/RA-CONSULTING/Aureon-OS/commit/c7d0ca10d619b943278348814fca11cd49873a51), recorded 7 April 2026. This establishes an archival statement about growth above one. It does **not** demonstrate an exact, universal critical beta or establish the chronology of the author's reported reprint error.

The February 6 first version of `docs/HNC_UNIFIED_WHITE_PAPER.md` already contains 1.1. The April 3 Grand Unified Word content also contains it; that content was initially committed at the repository root and moved into `docs/research/whitepapers` on April 5. First-content dates and first dates at today's path must remain separate.

The correction therefore has three distinct supports: the author's present instruction identifies beta=1 as the intended reference; historical text contains both near-one and 1.1 wording; the September 12 numerical follow-up resolves increasingly late escape near one. **The original reprint chronology remains unverified.** Original documents are preserved, and the correction is a dated erratum.

## Consequences for the experiment brief

The completed 4,194,304-step HNC follow-up supports a finite-horizon transition close to one on its tested grid. It cannot turn an archival contradiction into a proven general theorem. The larger 128-GPU campaign is still pending its full horizon and final audit.

All four replacement acoustics geometry jobs completed. Their receipt/source audit passed; the 0.10 m coffer residual is 3.76e-12 and the opening residual is 2.44e-10. Corrected Galerkin versus fine-grid coffer frequencies differ by at most **0.326% for the first eight modes**, and **1.096% across all 26**. Eigenvectors were not retained for independent residual recomputation. This strengthens the amended numerical calculation; the old protocol remains INCONCLUSIVE and distinctive tuning is not established.

The complete family brief retains QGITA, Tandem, LiDAR, AURIS, capability/Stage 1, illumination, Doorbell, acoustics, V3, Gamma/conscience/weights/MCP, Math Angel/L(t), observational/Schumann/EPAS and repository coverage, with negative and missing results explicit.

## Evidence files

- `git-history-coverage-20260912.json`: repository/ref and change coverage.
- `git-research-source-index.json`: all 180 native-document identities, paths, creation metadata and extraction limitations. This local inventory includes non-research administrative documents discovered during the broad scan.
- `git-historical-document-evidence.json`: extracted matching passages from the 179 direct Git documents.
- `git-history-nested-summary.json` and `git-history-nested-recovery.json`: archive inspection and damaged-file recovery limits.
- `git-history-hnc-provenance.json`: selected HNC source identities.
- `acoustics-geometry-audit-6498032.json`: completed geometry receipt/source audit.

The bulk history archive is retained locally with SHA-256 `e5a1e94b900c90b951eb6c01c7d4dfd097f93ea5df460ced35c9c60df5eb1818`. It has not been published. These records establish source provenance and computational outcomes, not independent physical confirmation.
