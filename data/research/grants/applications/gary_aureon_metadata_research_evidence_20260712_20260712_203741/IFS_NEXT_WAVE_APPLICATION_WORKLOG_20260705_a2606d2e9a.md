# IFS Next Wave Application Worklog

Prepared: 2026-07-05T17:15:39+01:00

Application: `10209601`

Portal URL: https://apply-for-innovation-funding.service.gov.uk/application/10209601

Competition: Next Wave: Breakthrough Wave 1

Deadline shown by portal: 11:00am Tuesday 11 August 2026

## Status

The application has been created and is 100% complete in the Innovation Funding Service portal. It has not been finally submitted.

## Completed In Portal

- Application details:
  - Title: Aureon Evidence Studio for Createch AI Workflows
  - Start date: 1 January 2027
  - Duration: 12 months
- Research category:
  - Industrial research
- Application team:
  - Lead organisation: R&A CONSULTING AND BROKERAGE SERVICES LTD
  - Company number: NI696693
  - Lead applicant: gary leckey, gaxlec@gmail.com
- Project summary.
- Public description.
- Scope.
- Subsidy basis:
  - Northern Ireland registered enterprise: Yes.
  - Funding directed outside agriculture, fisheries and aquaculture: Yes.
  - Does not affect trade in goods or Northern Ireland electricity market: No.
  - Services route selected.
  - Subsidy basis determined by portal: Subsidy Control Act 2022.
- Questions 1 to 17:
  - All marked complete using the Aureon operator copy pack.
- Project finances:
  - Total eligible costs: GBP250,000.
  - Funding level: 70%.
  - Funding sought: GBP175,000.
  - Company contribution: GBP75,000.
  - Other public funding: GBP0.
  - Project location postcode: BT12 4HX.
  - Organisation size: Micro or small.
  - Turnover entered from 2026 Companies House iXBRL accounts: GBP100,497.
  - Full-time employees entered from 2026 Companies House iXBRL accounts: 1.
- Finances overview.
- Project Impact survey:
  - Submitted successfully in Chrome after the in-app Salesforce flow controls failed.
  - Portal confirmation: "Project impact answers submitted".
  - IFS now marks Project Impact complete.
- Award terms and conditions:
  - Accepted in portal at 11:28pm on 5 July 2026.

## Current Handoff

The IFS application is complete and the review-and-submit page is open:

`https://apply-for-innovation-funding.service.gov.uk/application/10209601/review-and-submit`

The visible final button is `Submit application`. It has not been pressed.

Final submission requires exact action-time confirmation because it transmits the completed application to Innovate UK.

## Project Impact Route Resolved

IFS opened the external Innovate UK Salesforce route:

`https://innovateuk.my.site.com/IMCommunity/s/?CompanyNumber=NI696693&OrganisationId=116134&IFSApplicationNumber=10209601&CompetitionId=2517&PreApproval=true`

The survey loaded and showed the Project Impact introduction, but the Salesforce flow controls were inert in the in-app browser. Tested routes:

- Exact survey URL retry after the first Salesforce validation error.
- Visible DOM click on `Continue`.
- Coordinate click on the visible `Continue` button.
- Keyboard activation with Enter.
- Double click.
- Forced Playwright click.
- Application-questions accordion direct route.

Chrome was then used as the browser surface. Chrome advanced the Salesforce flow. Numeric inputs only committed after sending a `keyup` event, because the Salesforce component updates Flow state from `keyup`, not from ordinary value fill. Final Project Impact answers submitted:

- FTE employees: 1.
- FTE freelancers: 0.
- Innovation FTE employees: 1.
- Expected additional FTE from support: 3.0.
- Operating profit/loss rounded: GBP76,000.
- Innovation expenditure rounded: GBP25,000.
- Turnover from innovative products/services: 100%.
- Expected additional turnover over five years: GBP500,000.
- Active R&D projects: 1.
- Catapult engagement: No.
- Innovate UK Business Connect engagement: No.
- Business Connect positive outcomes: Not engaged with Innovate UK Business Connect.
- Creative UK engagement: No.
- New products/services/processes expected: Yes within 2 years.
- Market readiness: MRL9 - Product/service defined.
- Technology readiness: TRL 5 - Technology validated in relevant environment.

No plaintext password was stored in `.env`, `.env1.txt`, or this worklog.

## Aureon Operator Output

The Aureon repo is now the operating layer for this application.

- Operator module: `C:\Users\user\aureon-trading\aureon\grants\operator.py`
- Copy pack: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_10209601_COPY_PACK_20260705.md`
- JSON pack: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_10209601_COPY_PACK_20260705.json`
- Q14 project plan PDF: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_Q14_PROJECT_PLAN_APPENDIX_20260705.pdf`
- Q15 risk register PDF: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_Q15_RISK_REGISTER_APPENDIX_20260705.pdf`

Aureon operator run:

- Run ID: `aureon-grant-operator-20260705-230323`
- Application ledger ID: `APP-IFS-NEXT-WAVE-10209601`
- Draft finance staged: GBP250,000 total eligible costs, GBP175,000 provisional grant request, GBP75,000 provisional company contribution.
- Existing Chief Grant Officer tracker repaired and run: 19 opportunities, 17 open opportunities, 3 active applications.

## Remaining Action

- Final Innovate UK application submission only.
- Current page: `https://apply-for-innovation-funding.service.gov.uk/application/10209601/review-and-submit`
- Visible final button: `Submit application`.
- Exact action-time confirmation is required before pressing final submit.

## Constraints To Preserve

- Keep the project framed as Createch evidence tooling for advertising and marketing workflows.
- Do not turn the submission into unsupported trading, defence, physics, or consciousness claims.
- Do not attach private financial records, credentials, local runtime state, customer material, or raw Git bundles.
- Do not submit the final application without final review and exact action-time confirmation.

## 2026-07-06 Continuation

Aureon operator updates:

- `aureon.grants.operator --sync-next-wave` run at 2026-07-06T06:19:34+01:00.
- `aureon.grants.operator --autopilot-status` run at 2026-07-06T06:19:44+01:00.
- Application status corrected to `READY_FOR_FINAL_SUBMISSION`.
- Pipeline corrected to count `READY_FOR_FINAL_SUBMISSION` as active.
- Current GBP pipeline value: GBP175,000.
- Non-GBP active request: AIRR Compute GPU-hours request.

Generated Aureon files:

- `C:\Users\user\aureon-trading\data\research\grants\autopilot_status.json`
- `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_FINAL_SUBMISSION_BRIEF_20260706.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\SELF_UPDATE_IFS_NEXT_WAVE_READY_20260706.eml`
- `C:\Users\user\aureon-trading\data\research\grants\drive_sync_20260706.json`

Drive export:

- Uploaded to `Aureon Grant War Room - 2026-07-04`.
- Folder URL: https://drive.google.com/drive/folders/1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr
- Uploaded files:
  - `AUREON_GRANT_OPERATOR_REPO_STATE_20260706_062033.tar.gz`
  - `AUREON_GRANT_WORKING_PACK_20260706_062033.tar.gz`
  - `AUREON_DRIVE_EXPORT_MANIFEST_20260706_062033.json`
- Google Drive UI verification showed all three filenames and `3 uploads complete`.

Invest NI IFAS continuation:

- Chrome form populated with name, email confirmation, telephone, postcode, and enquiry text.
- CAPTCHA remains present.
- Submit was not clicked.
- Aureon autopilot status regenerated at 2026-07-06T06:27:52+01:00 and now marks Invest NI as `STAGED_BLOCKED_BY_CAPTCHA`.

EIC Accelerator continuation:

- EIC Step 1 draft package generated from the staged Aureon project text.
- Official EIC source check confirmed Step 1 requires a short 12-page form, a pitch deck of up to 10 slides, and a video pitch of up to 3 minutes.
- Rendered PDF verified visually after rebuilding the first draft to fix paragraph wrapping.
- Registered in Aureon applications ledger as `APP-EIC-ACCELERATOR-STEP1-20260706`.
- Drive upload verified for:
  - `EIC_ACCELERATOR_STEP1_SHORT_PROPOSAL_DRAFT_20260706.pdf`
  - `AUREON_EIC_STEP1_DRAFT_PACK_20260706_063435.tar.gz`
