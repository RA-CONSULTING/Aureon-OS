# IFS Drive P1 Targeted Evidence Readback

- Generated: 2026-07-10T12:58:03+01:00
- Operator: Aureon
- Mode: IFS_ONLY
- Result: DRIVE_P1_TARGETED_READBACK_NO_CONFIRMED_UNLOCK_EVIDENCE
- Drive searches reviewed: 12
- Drive results observed: 19
- Confirmed unlock evidence: 0
- Direct IFS submissions unlocked: 0
- Sensitive content copied: false
- Portal changed: false
- External submission performed: false

## Search Findings

### AKT6

- Route: AKT6
- Results observed: 0
- Classification: NO_DRIVE_MATCH
- Unlock evidence found: false
- Finding: No Drive result for AKT6.

### KTP

- Route: AKT6
- Results observed: 3
- Classification: PLANNING_AND_DRAFT_PACKS_ONLY
- Unlock evidence found: false
- Finding: Drive returned prior Aureon grant operating logs and the academic validation sprint PDF pack. These are planning/outreach materials, not an eligible knowledge-base lead commitment, TTO confirmation, four-FTE evidence, or signed role evidence.

### four FTE

- Route: AKT6
- Results observed: 1
- Classification: PRIVATE_FINANCE_FALSE_POSITIVE_EXCLUDED
- Unlock evidence found: false
- Finding: Drive returned a Future Leaders application PDF containing private finance/bank-detail material. It was not copied into the grant ledger and is not four-FTE evidence for AKT6.

### QUB KTP

- Route: AKT6
- Results observed: 0
- Classification: NO_DRIVE_MATCH
- Unlock evidence found: false
- Finding: No Drive result for QUB KTP.

### Ulster KTP

- Route: AKT6
- Results observed: 2
- Classification: PLANNING_LOGS_ONLY
- Unlock evidence found: false
- Finding: Drive returned prior Aureon grant operating logs only. No Ulster lead/TTO commitment or AKT6 role evidence was found.

### CMDC7

- Route: CMDC7
- Results observed: 0
- Classification: NO_DRIVE_MATCH
- Unlock evidence found: false
- Finding: No Drive result for CMDC7.

### Clean Maritime

- Route: CMDC7
- Results observed: 1
- Classification: IRRELEVANT_FALSE_POSITIVE
- Unlock evidence found: false
- Finding: Drive returned an unrelated ecommerce strategy markdown file. No maritime lead, vessel, site, permit, safety, budget, or partner commitment evidence was found.

### Belfast Harbour

- Route: CMDC7
- Results observed: 2
- Classification: PRIVATE_FINANCE_FALSE_POSITIVE_EXCLUDED
- Unlock evidence found: false
- Finding: Drive returned private bank-statement false positives. Their contents were not copied into the grant ledger and do not evidence Belfast Harbour partner commitment.

### Navantia

- Route: CMDC7
- Results observed: 0
- Classification: NO_DRIVE_MATCH
- Unlock evidence found: false
- Finding: No Drive result for Navantia.

### Artemis

- Route: CMDC7
- Results observed: 0
- Classification: NO_DRIVE_MATCH
- Unlock evidence found: false
- Finding: No Drive result for Artemis.

### maritime lead

- Route: CMDC7
- Results observed: 5
- Classification: IRRELEVANT_FALSE_POSITIVES
- Unlock evidence found: false
- Finding: Drive returned unrelated documentation, research manuscript and lead-list files. No maritime project lead, asset/site, safety, permit, budget, or commitment evidence was found.

### vessel permit

- Route: CMDC7
- Results observed: 5
- Classification: IRRELEVANT_FALSE_POSITIVES
- Unlock evidence found: false
- Finding: Drive returned unrelated workflow/readme files. No vessel or permit evidence was found.

## Route Impacts

- APP-IFS-AKT6-2473-20260709: No Drive evidence confirmed an eligible knowledge-base lead, TTO/authorised lead contact, business four-FTE evidence, work package budget, or signed role commitment.
- APP-IFS-CMDC7-PREDEPLOYMENT-2415-20260709: No Drive evidence confirmed a maritime lead, vessel/port/shipyard asset, trial site, safety case, permits, insurance basis, budget, or deployment plan.
- APP-IFS-CMDC7-FEASIBILITY-2416-20260709: No Drive evidence confirmed a maritime feasibility partner, asset context, scope, budget, work package, or partner commitment.
- APP-IFS-CMDC7-DEPLOYMENT-2414-20260709: No Drive evidence confirmed a deployment partner, deployment asset/site, permissions, safety case, partner budget, or deployment schedule.

## Controls

- Google Drive was searched read-only through the connector.
- Private finance/bank-statement false positives were excluded from artifact content.
- No Google Drive file was created, modified, moved, shared, downloaded as raw private finance evidence, or uploaded.
- No IFS portal page was changed and no external action was performed.
- No route was marked submit-ready from planning logs, outreach drafts, private finance false positives, or unrelated matches.
