# IFS UK-Switzerland Finance Complete And Project Impact Block

Generated: 2026-07-11T12:57:08+01:00
Operator: Aureon
Mode: IFS only

## Result

- IFS_UK_SWISS_FINANCE_COMPLETE_PROJECT_IMPACT_PROVIDER_PERSISTENCE_BLOCK_NO_FINAL_SUBMISSION
- Portal application: 10210100
- Finance sections changed and live-read back: true
- Project Impact submitted: false
- Award terms accepted: false
- Final application submitted: false

## Finance Readback

- Your project costs: Complete
- Your project location: Complete
- Your organisation: Complete
- Your funding: Complete
- Finances summary: Complete
- Total costs: GBP 250,000
- Funding level: 70.00%
- Funding sought: GBP 175,000
- Contribution to project: GBP 75,000
- Other public sector funding: GBP 0

## Project Impact Provider Block

- The survey accepted visible Q1 entry during coordinate input, but review returned Q1 blank.
- Final survey Submit was not pressed because provider readback did not persist Q1.
- Existing No values for Catapult and Innovate UK Business Connect were visible on the review page.

## IFS Review Readback

- Project details: Complete
- Application questions 1-17: Complete
- Finances summary: Complete
- Project impact: Incomplete
- Award terms and conditions: Incomplete
- Submit application: Disabled

## Screenshots

- ifs_internal_server_error: `applications/rendered/ifs_uk_swiss_project_costs_save_error_20260711_1245.png`
- project_impact_q1_provider_issue: `applications/rendered/ifs_uk_swiss_project_impact_q1_blank_provider_20260711_1250.png`
- ifs_review_finance_complete: `applications/rendered/ifs_uk_swiss_finance_complete_review_project_impact_block_20260711_1252.png`

## Remaining Gates

- Project Impact provider persistence must be resolved before pressing Project Impact Submit.
- Award terms and conditions remain incomplete and were not accepted.
- Final IFS Submit application button remains disabled.
- Swiss implementation partner and research institute or valid waiver evidence still need confirmed external evidence before the application can be made fully robust.

## Controls

- Finance values were entered from the Aureon open-source-backed cost model and live-read back from IFS.
- A first project-cost save returned an IFS Internal Server Error, unique error ID 8e989f7ab1a86765a99d1807d00aba78, but labour and overheads persisted.
- The other-cost description was shortened and the second save completed, producing the expected GBP250,000 finance summary.
- Project Impact Submit, award terms acceptance and final application submission were not pressed.
- No email, partner invite, upload, purchase, account creation, password storage or unrelated browser action was performed.
