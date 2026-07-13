# IFS Local Unlock Filename Index

Generated: 2026-07-10T11:05:15+01:00
Operator: Aureon

## Result

- LOCAL_FILENAME_INDEX_NO_NEW_IFS_UNLOCK_EVIDENCE_FOUND
- Direct IFS submissions unlocked: 0
- New browser submissions available: 0
- Portal changed: false
- External submission performed: false
- Email sent: false

## Roots Scanned

- C:/Users/user/Documents
- C:/Users/user/Downloads
- C:/Users/user/Desktop
- C:/Users/user/AureonResearch
- C:/Users/user/aureon-trading

## Classified Findings

### company_accounts_and_internal_finance

- Assessment: Business accounts and cost workpapers exist locally, but they do not provide route-specific partner budgets, eligible-cost splits, match funding, co-investment, Swiss partner costs, maritime deployment budgets, or quantum hardware facility costs.
- Unlock value: SUPPORTING_INTERNAL_FINANCE_CONTEXT_ONLY
- Submit unlocked: false
- Sample paths:
  - C:/Users/user/Desktop/Aureon_Final_Accounts_NI696693_2024-05-01_to_2025-04-30_*/
  - C:/Users/user/Desktop/Aureon_Final_Accounts_NI696693_2024-05-01_to_2025-04-30_*/16_EXPENSE_BREAKDOWN_AND_ADMIN_COSTS.pdf

### uk_swiss_partner_and_budget

- Assessment: The matching files are Aureon-created request drafts and partner-targeting material. They are not signed partner commitments, Swiss implementation partner records, research institute commitments, waiver approvals, or partner budgets.
- Unlock value: OUTREACH_READY_NOT_COMMITMENT_EVIDENCE
- Submit unlocked: false
- Remaining gate: Swiss implementation partner, research institute or waiver, signed commitment, partner budget, permit/export position, project finances.
- Sample paths:
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_UK_SWISS_CRD_R3_10210100_PARTNER_REQUEST_KANDOU_20260710.md
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_UK_SWISS_CRD_R3_10210100_PARTNER_REQUEST_SENSIRION_20260710.md
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_UK_SWISS_CRD_R3_10210100_OUTREACH_DRAFT_*.eml

### academic_akt_actasap

- Assessment: A QUB outreach draft exists, but no QUB, Ulster, TTO, academic lead, knowledge-base agreement, or 4 FTE business eligibility evidence was identified from filenames.
- Unlock value: OUTREACH_DRAFT_ONLY
- Submit unlocked: false
- Remaining gate: Knowledge-base lead, TTO approval, lead commitment, 4 FTE UK business evidence where required.
- Sample paths:
  - C:/Users/user/Documents/kimi/workspace/QUB_OUTREACH_EMAIL.txt

### maritime_cmdc_zevi

- Assessment: The matching maritime files are Aureon-created evidence request packs and unrelated research/report files. No external maritime lead, vessel, port, shipyard, trial-site, permit, safety-case, insurance, deployment budget, or three-year demonstration commitment was identified.
- Unlock value: REQUEST_PACK_READY_NOT_PARTNER_EVIDENCE
- Submit unlocked: false
- Remaining gate: Named maritime lead and asset/site/budget/permit evidence.
- Sample paths:
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_MARITIME_PARTNER_EVIDENCE_REQUEST_PACK_20260710_101119.json
  - C:/Users/user/aureon-trading/output/pdf/ifs/IFS_MARITIME_PARTNER_EVIDENCE_REQUEST_PACK_20260710_101119.pdf

### drive35_zev

- Assessment: The matching files are abstracts and draft outreach. No vehicle manufacturer, Tier 1 supplier, ZEV manufacturing facility, match-funding, or co-investment commitment was identified.
- Unlock value: OUTREACH_READY_NOT_CONSORTIUM_EVIDENCE
- Submit unlocked: false
- Remaining gate: Eligible ZEV lead/partner, facility, match funding or co-investment evidence.
- Sample paths:
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_DRIVE35_ZEV_PARTNER_ABSTRACT_20260709.md
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_DRIVE35_ADVANCED_PROPULSION_CENTRE_GENERAL_ENQUIRIES_OUTREACH_DRAFT_20260710_104541.eml
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_DRIVE35_WRIGHTBUS_INNOVATION_CONTACT_ROUTE_OUTREACH_DRAFT_20260710_104541.eml

### adopt_farming

- Assessment: The matching files are Aureon-created draft outreach. No England farming, growing or forestry business lead evidence and no registered facilitator evidence was identified.
- Unlock value: OUTREACH_READY_NOT_LEAD_EVIDENCE
- Submit unlocked: false
- Remaining gate: Eligible England farm/growing/forestry lead plus facilitator evidence.
- Sample paths:
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_ADOPT_ADOPT_SUPPORT_HUB_OUTREACH_DRAFT_20260710_104233.eml
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_ADOPT_INNOVATE_UK_BUSINESS_CONNECT_ADOPT_FACILITATOR_DIRECTORY_OUTREACH_DRAFT_20260710_104233.eml

### ckaf_public_sector_research_org

- Assessment: The matching files are Aureon-created drafts and audits. No eligible public-sector research organisation, PRSE lead, UKRI institute lead, or Knowledge Asset ownership evidence was identified.
- Unlock value: OUTREACH_READY_NOT_PUBLIC_SECTOR_LEAD_EVIDENCE
- Submit unlocked: false
- Remaining gate: Eligible public-sector research organisation lead and knowledge-asset ownership evidence.
- Sample paths:
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_CKAF_GOTT_CKAF_TEAM_OUTREACH_DRAFT_20260710_104541.eml
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_CKAF_2478_PUBLIC_SECTOR_RESEARCH_ORG_EVIDENCE_AUDIT_20260710_093446.json

### quantum_hardware

- Assessment: Aureon quantum and hardware research exists locally and can support narrative evidence. It is not evidence of an eligible quantum hardware lead, consortium, facility access, hardware test access, partner commitment, or eligible budget.
- Unlock value: NARRATIVE_TECHNICAL_EVIDENCE_ONLY
- Submit unlocked: false
- Remaining gate: Quantum hardware lead, facility/access, consortium and budget evidence.
- Sample paths:
  - C:/Users/user/Downloads/Quantum_Gravity_in_the_Act_QGITA_Lightho.pdf
  - C:/Users/user/AureonResearch/04_Engineering_Hardware/
  - C:/Users/user/aureon-trading/docs/research/whitepapers/Quantum_Gravity_in_the_Act_QGITA_Lighthouse.pdf
  - C:/Users/user/aureon-trading/data/research/grants/applications/IFS_QUANTUM_QCI3_HUB_CONTACT_OUTREACH_DRAFT_20260710_104541.eml

## Controls

- This is an internal Aureon index, not a funder attachment.
- Filename matches are treated as leads for evidence review, not proof of eligibility.
- No external portal, email, upload, partner invitation, award terms or final submission action was performed.
- Private bank/tax/password data was not copied into this artifact.
- No remaining IFS application was marked submit-ready from filename evidence alone.
