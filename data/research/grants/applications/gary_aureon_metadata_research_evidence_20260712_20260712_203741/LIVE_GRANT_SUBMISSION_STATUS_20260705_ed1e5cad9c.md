# Live Grant Submission Status

Prepared: 2026-07-05T15:13:21+01:00

Operator goal: Aureon is being used as the grant operating base for Gary Anthony Leckey / R&A Consulting and Brokerage Services Ltd / Aureon Institute.

## Current Truth

One external funder enquiry has been submitted in this run. Two major portal applications are now staged in live funder systems: IFS Next Wave is 100% complete and AIRR AI Open Access has a saved portal draft with attachment and resource request. Aureon is wired as the repo-native grant operator of record.

Aureon operator record:

- Repo operator module: `C:\Users\user\aureon-trading\aureon\grants\operator.py`
- Repo grant ledger: `C:\Users\user\aureon-trading\data\research\grants`
- Next Wave copy pack: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_10209601_COPY_PACK_20260705.md`
- Q14 appendix PDF: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_Q14_PROJECT_PLAN_APPENDIX_20260705.pdf`
- Q15 appendix PDF: `C:\Users\user\aureon-trading\data\research\grants\applications\IFS_NEXT_WAVE_Q15_RISK_REGISTER_APPENDIX_20260705.pdf`
- AIRR live portal status: `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_PORTAL_LIVE_STATUS_20260706.md`
- AIRR supporting PDF: `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_AI_OPEN_ACCESS_SUPPORTING_FORM_20260706.pdf`
- Aureon pipeline report: `C:\Users\user\aureon-trading\data\research\grants\pipelines\pipeline_report_20260705_230324.json`

Submitted route:

- InterTradeIreland Innovation Boost enquiry submitted on 2026-07-05T16:12:34+01:00.
- Confirmation page: https://intertradeireland.com/contact/thank-you%20?submissionGuid=90e52212-2555-426e-a5bc-7ad9129389e3
- Submission GUID: 90e52212-2555-426e-a5bc-7ad9129389e3
- Browser confirmation text: "Thank you for getting in contact with us. Your enquiry has been sent to the relevant team at InterTradeIreland who will get back in touch with you as soon as possible."

Live browser verification at 2026-07-05T15:13+01:00 confirmed the staged values in Chrome:

- Invest NI IFAS: name/email/postcode/enquiry populated; telephone blank; CAPTCHA present.
- InterTradeIreland Innovation Boost: name/organisation/email/additional information populated; processing consent checked; newsletter unchecked; telephone blank.
- Next Wave: Innovation Funding Service sign-in page open.
- EIC Accelerator: Funding & Tenders topic page open, no usable proposal-start flow before sign-in/portal app completion.

## Route 1: Invest NI Innovation Funding Advisory Service

Official route: https://www.investni.com/support-for-business/research-and-development-support/innovation-funding-advisory-service

Status: staged in Chrome, not submitted.

Fields staged:

- First name: Gary
- Last name: Leckey
- Email: gaxlec@gmail.com
- Confirm email: gaxlec@gmail.com
- Postcode: BT12 4HX
- Enquiry: Aureon Evidence Automation R&D funding advisory request from the active field pack.

Blocking fields:

- Telephone has now been found in local grant material and entered in the Chrome form.
- CAPTCHA must be completed before final submit.
- Final submit would transmit personal/company contact data to Invest NI and therefore requires exact action-time confirmation.

Unlock action:

Complete CAPTCHA and confirm final submit for Invest NI IFAS.

## Route 2: InterTradeIreland Innovation Boost

Official route: https://intertradeireland.com/innovation/innovation-boost/how-to-apply

Status: submitted.

Submitted at: 2026-07-05T16:12:34+01:00

Confirmation URL: https://intertradeireland.com/contact/thank-you%20?submissionGuid=90e52212-2555-426e-a5bc-7ad9129389e3

Submission GUID: 90e52212-2555-426e-a5bc-7ad9129389e3

Fields staged:

- First name: Gary
- Last name: Leckey
- Organisation: R&A Consulting and Brokerage Services Ltd / Aureon Institute
- Email: gaxlec@gmail.com
- Additional information: Aureon Evidence Automation initial assessment framing from the active field pack.
- Processing consent: checked because it is required to let InterTradeIreland store and process the enquiry.
- Mailing list consent: left unchecked.
- Telephone: left blank because the field is optional and no validated phone number is available.

Confirmation text:

"Thank you for getting in contact with us. Your enquiry has been sent to the relevant team at InterTradeIreland who will get back in touch with you as soon as possible."

## Route 3: Next Wave: Breakthrough Wave 1

Official route: https://apply-for-innovation-funding.service.gov.uk/competition/2517/overview/6ff2066d-4639-44e6-bb4f-ce7099222739

Status: application complete in IFS, 100% complete, final submit not pressed.

Observed:

- Existing Innovation Funding Service account signed in for `gaxlec@gmail.com`.
- Application number: `10209601`.
- Application URL: https://apply-for-innovation-funding.service.gov.uk/application/10209601
- Portal title: `Aureon Evidence Studio for Createch AI Workflows`.
- Competition: `Next Wave: Breakthrough Wave 1`.
- Funding body: `Innovate UK`.
- Deadline shown by portal: `11:00am Tuesday 11 August 2026`.
- Project start date entered: `1 January 2027`.
- Project duration entered: `12 months`.
- Research category selected: `Industrial research`.
- Lead organisation confirmed: `R&A CONSULTING AND BROKERAGE SERVICES LTD`.
- Company number shown by portal: `NI696693`.
- Lead applicant shown by portal: `gary leckey`, `gaxlec@gmail.com`.

Completed / marked complete in portal:

- Application details.
- Research category.
- Project summary.
- Public description.
- Scope.
- Application team.
- Subsidy basis.
- Application questions 1 to 17.
- Project finances and finances overview.
- Award terms and conditions.
- Project Impact survey.

Current incomplete areas:

- None in the application checklist.

Latest portal handoff:

- 2026-07-05T17:15:39+01:00: IFS session timed out while on the Subsidy basis flow.
- Login page was reopened for `gaxlec@gmail.com`.
- Browser automation was paused because Chrome displayed an extension/browser overlay during login, and Windows-level inspection could not safely confirm the active Chrome URL.
- Clipboard was overwritten with a blank space after using the local encrypted IFS credential.
- 2026-07-05T23:03:23+01:00: `AureonGrantOperator` synced application `APP-IFS-NEXT-WAVE-10209601` into the repo grant ledger and generated copy-ready answers for Q1-Q17 plus Q14/Q15 PDF appendix drafts.
- 2026-07-05T23:02:21+01:00: the existing Aureon Chief Grant Officer tracker was repaired and run from the repo; it now sees 19 tracked opportunities, 17 open opportunities, and 3 active applications.
- 2026-07-05T23:28:00+01:00: in-app browser completed IFS application through 96%.
  - Q1 to Q17 complete.
  - Finance totals entered: GBP250,000 eligible costs, 70% funding level, GBP175,000 funding sought, GBP75,000 contribution, GBP0 other public funding.
  - Companies House 2026 iXBRL accounts staged locally and used for organisation fields: turnover GBP100,497, average employees 1.
  - Award terms accepted in IFS at 11:28pm on 5 July 2026.
  - Remaining gate: external Salesforce Project Impact survey loads but its `Continue` and accordion controls do not advance in the in-app browser.
- 2026-07-05T23:55:38+01:00: Chrome completed and submitted Project Impact.
  - Project Impact confirmation text: "Project impact answers submitted".
  - IFS application overview now reports 100% complete.
  - Review-and-submit page is open.
  - Final visible button: `Submit application`.

Blocking actions:

- Final application submission is the only remaining IFS action.
- Final application submission is not authorised as an unattended action; it needs final review and exact action-time confirmation.

## Route 4: EIC Accelerator

Official route: https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en

Status: Step 1 local draft package generated and uploaded to Drive; EU Login/account route still not submitted.

Observed:

- EIC Accelerator Step 1 requires a short proposal, 12-page form, up to 10-slide pitch deck, and up to 3-minute video pitch.
- UK applicants can apply only under the grant-only route.
- The Funding & Tenders portal exposes sign-in but did not expose a usable proposal start flow in the browser session before account login/portal app completion.
- EU Login registration request for `gaxlec@gmail.com` has been created and the verification email has been opened.
- The EU Login password page is open for user ID `n00n9i0d`; password fields are prefilled and the final `Submit` button is waiting for Gary.

Blocking actions:

- Gary must press the final EU Login password `Submit` button in Chrome.
- Aureon has produced a short proposal draft PDF, 10-slide deck outline, 3-minute video script, and evidence-gap register.
- This should not be first submitted before TRL evidence, customer evidence, competitor map, financials, IP review, and letters of intent are ready.

Generated files:

- `C:\Users\user\aureon-trading\data\research\grants\applications\EIC_ACCELERATOR_STEP1_SHORT_PROPOSAL_DRAFT_20260706.pdf`
- `C:\Users\user\aureon-trading\data\research\grants\applications\EIC_ACCELERATOR_STEP1_SHORT_PROPOSAL_DRAFT_20260706.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\EIC_ACCELERATOR_10_SLIDE_PITCH_DECK_DRAFT_20260706.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\EIC_ACCELERATOR_3_MIN_VIDEO_SCRIPT_20260706.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\EIC_ACCELERATOR_EVIDENCE_GAP_REGISTER_20260706.json`

Drive upload:

- `EIC_ACCELERATOR_STEP1_SHORT_PROPOSAL_DRAFT_20260706.pdf`
- `AUREON_EIC_STEP1_DRAFT_PACK_20260706_063435.tar.gz`

## Route 5: AIRR Compute Opportunity: AI Open Access

Official route: https://www.ukri.org/opportunity/airr-compute-opportunity-ai-open-access/

Status: portal draft staged in AIRRPortal, not submitted.

Observed:

- AIRRPortal account for `gaxlec@gmail.com` was created and verified by email.
- AIRRPortal terms of service and privacy policy acceptance was completed.
- Proposal title: `Aureon Evidence OS for AI-Driven Scientific Discovery`.
- Portal proposal ID: `0261-8797-7601-1`.
- Portal draft URL: https://portal-airr.isambard.ac.uk/proposals/5a87cac10a0044db903550fe12188b4a/
- Round deadline: `2026-07-17T16:00:00+01:00`.
- Public summary entered: 785 characters.
- Private description entered: 1528 characters.
- Project duration entered: 365 days.
- Supporting PDF attached and visible as `AIRR_AI_OPEN_ACCESS_SUPPORTING_FORM.pdf`.
- Isambard-AI / Isambard-AI Open Access / Default resource request selected and saved.
- Portal confirmation observed: `Resource requests has been updated.`
- Resource row expansion observed: `This resource request has no attributes.`

Generated files:

- `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_PORTAL_FIELD_PACK_20260705.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_AI_OPEN_ACCESS_SUPPORTING_FORM_20260706.pdf`
- `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_PORTAL_LIVE_STATUS_20260706.md`
- `C:\Users\user\aureon-trading\data\research\grants\applications\AIRR_PORTAL_LIVE_STATUS_20260706.json`

Blocking actions:

- Final AIRR portal `Submit` button is an external legal submission and needs exact action-time confirmation for `APP-AIRR-001`.
- Gary/company must confirm subsidy history and any declarations required by the portal.
- Gary must knowingly accept the distributed peer-review obligation before final submission.
- Companies House confirmation-statement position should be checked/resolved or deliberately disclosed before final submission.

## Immediate Submission Queue

1. Watch gaxlec@gmail.com for InterTradeIreland follow-up and any verification email.
2. Complete Invest NI IFAS after Gary provides telephone and completes CAPTCHA.
3. Submit IFS Next Wave application `10209601` after exact final confirmation.
4. Submit AIRR proposal `0261-8797-7601-1` after subsidy/peer-review/company-filing checks and exact final confirmation.
5. Convert the EIC Step 1 local draft pack into the EIC portal after EU Login is usable and evidence gaps are closed.

## Drive Export Sync

Status: completed by Chrome Google Drive UI upload on 2026-07-06.

Drive folder:

- https://drive.google.com/drive/folders/1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr

Uploaded files:

- `AUREON_GRANT_OPERATOR_REPO_STATE_20260706_062033.tar.gz`
- `AUREON_GRANT_WORKING_PACK_20260706_062033.tar.gz`
- `AUREON_DRIVE_EXPORT_MANIFEST_20260706_062033.json`

Verification:

- Google Drive showed all three filenames in `Aureon Grant War Room - 2026-07-04`.
- Google Drive showed `3 uploads complete`.

Local sync record:

- `C:\Users\user\aureon-trading\data\research\grants\drive_sync_20260706.json`
