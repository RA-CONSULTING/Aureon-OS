# Aureon Grant Operator 24/7 Plan

Generated: 2026-07-09
Operator: Aureon
Account: gaxlec@gmail.com
Entity: R&A Consulting and Brokerage Services Ltd / Gary Leckey / Aureon Institute

## Operating Mode

Aureon will run as the grant operating system:

- Gather all Gary Leckey and Aureon work from local folders, repo snapshots, grant packs, Drive files, Gmail evidence, and public profiles where accessible.
- Normalize the work into one evidence corpus with source paths, dates, topics, grant fit, and confidence.
- Reconcile every application record to one of: `SUBMITTED`, `SUBMITTED_ENQUIRY`, `PORTAL_DRAFT_STAGED`, `LOCAL_DRAFT_PACK_BUILT`, `GATED_PROVIDER_CONTROL`, `NOT_FIT`, or `READY_TO_APPLY`.
- Search current official funder opportunities, with Innovate UK IFS as the first live sweep.
- Match current opportunities to Aureon work packages and produce funder-specific packs.
- Submit or stage applications where technically possible and authorized; preserve receipts, screenshots, emails, and local JSON records.
- If CAPTCHA, MFA, account control, or missing provider scope stops one route, log the exact state and immediately move to the next grant route.
- Never store plaintext passwords, private keys, bank details, tax files, or tokens in grant packs.

## Continuous Automation

Created active Codex automation:

- Automation ID: `aureon-grant-operator-continuous-funding-monitor`
- Schedule: every 6 hours
- Workspace: `C:\Users\user\aureon-trading`
- Mode: local grant ledger reconciliation, evidence discovery, opportunity search, application pack generation, portal staging/submission where possible, receipt logging.

## Current Application State

| Application | Status | Action |
| --- | --- | --- |
| IFS Next Wave 10209601 | `SUBMITTED` | Monitor IFS and Gmail for decision or feedback due by 1 Oct 2026. Do not reopen unless deliberate resubmission is needed. |
| InterTradeIreland Innovation Boost enquiry | `SUBMITTED_ENQUIRY` | Monitor email/funder response; convert response to full application pack. |
| AIRR Compute AI Open Access | `SUBMITTED` | Monitor AIRRPortal and Gmail for peer-review assignments, decision, or follow-up. |
| Future Leaders Fellowships Round 11, business and non-academic | `LIVE_PORTAL_APPLICATION_STARTED` | IFS application `10209992` is live under `gaxlec@gmail.com`; complete subsidy, finances, terms, and final review after finance validation. |
| Invest NI IFAS | `STAGED_BLOCKED_BY_CAPTCHA` | Keep enquiry pack; use CAPTCHA/manual provider route if needed, then record receipt. |
| EIC Accelerator Step 1 | `LOCAL_DRAFT_PACK_BUILT` | Close evidence gaps, then move to EU portal when login/account path is usable. |
| QUB Honorary Research Fellow | `DRAFT` | Use as partnership/host path for academic grants requiring affiliation. |

## Evidence Sources Already Found

### Local

- `C:\Users\user\aureon-trading`
- `C:\Users\user\Aureon_Work_Hub_20260705`
- `C:\Users\user\outputs`
- `C:\Users\user\Downloads`
- `C:\Users\user\OneDrive`
- `C:\Users\user\AureonResearch`
- `C:\Users\user\AureonObsidianVault`
- `C:\Users\user\project-rainbow`
- `C:\Users\user\Desktop\Kings_Accounting_Suite`
- `C:\Users\user\.aureon_grant_private` for encrypted credentials only

### Drive

- `Aureon Grant War Room - 2026-07-04` spreadsheet and folder
- `AUREON_GRANT_OPERATING_LOG_REFRESHED_20260705.md`
- `RA_Grant_War_Room_Package.pdf` and `.md`
- `Future_Leaders_Fellowship_Round11_Application.pdf`
- `MASTER_WORK_INDEX_20260705.md`
- `AUREON_WHITE_PAPER_RESEARCH_HUB.md`
- `aureon_complete_codex.md`
- `aureon_performance_validation_report.md`
- `Academia.edu - Analytics Export - 349634148-1775247579.csv`
- `Harmonic_Solar_System_Survey_Leckey.docx`
- `SCEMDA_HNC_LSC_Academic_White_Paper.pdf`
- `NI696693_aa_2026-07-01.pdf`, `NI696693_aa_2026-07-03.pdf`, and XHTML company account exports

## First Live IFS Sweep

Official IFS search showed 19 competitions open or closing soon on 2026-07-09.

High-priority matches:

| IFS competition | Deadline | Aureon fit | Initial route |
| --- | --- | --- | --- |
| Next Wave: Breakthrough Wave 1 | 11 Aug 2026 | Already submitted | Monitor. |
| Future Leaders Fellowships: Round 11, business and non-academic | 4 Nov 2026 | Strong if framed around Gary as future leader and Aureon R&D programme | Build/refresh business-host application pack; check host/supporting organisation requirements. |
| Scaling performance of quantum computing hardware: CR&D | 18 Sep 2026 | Conditional fit for HNC/QGITA/validation tooling; collaboration required | Partner search and concept note. |
| Consumer Led Flexibility for the Clean Energy Superpower Mission | 26 Aug 2026 | Possible fit for energy/LSSP/EPAS work if framed as pre-commercial clean energy software or control system | Scope check and partner/lead route. |
| Innovation Loans Expression of Interest | No deadline | Possible fit for close-to-market Aureon platform, not grant cash | Loan suitability review before applying. |
| UK-Switzerland CR&D Round 3 | 3 Sep 2026 | Conditional fit if Swiss implementation and research partners can be found | Partner-required; create outreach pack. |
| Clean maritime / zero emission vessel competitions | 15 Jul to 16 Sep 2026 | Possible for EPAS/energy systems only with maritime collaborator | Partner-required; triage quickly due near deadlines. |

Lower-priority or likely not fit:

- ADOPT farming/growing/forestry route: unlikely fit unless an agriculture partner/use case exists.
- CKAF public sector knowledge assets: not eligible unless a public sector research body leads.
- ACTASAP Pilot Phase 1: academic institution lead only.
- AKT 6: academic/RTO/Catapult lead and business with four or more FTEs required.
- Contracts for Innovation SEN: possible only if Aureon evidence tooling can credibly support SEN identification procurement needs; needs strict scope and ethics review.

## Immediate Next Work

1. Build `AUREON_UNIFIED_WORK_CORPUS_20260709.json` from local and Drive evidence.
2. Update `opportunities.json` with the 19 official current IFS competitions and fit rankings.
3. Promote the best routes into `applications.json` as either `READY_TO_APPLY`, `PARTNER_REQUIRED`, or `NOT_FIT`.
4. For each `READY_TO_APPLY` route, create a funder-specific application pack and portal checklist.
5. Recheck Gmail/IFS for submitted receipts and funder responses.
6. Continue every 6 hours through the active automation.
