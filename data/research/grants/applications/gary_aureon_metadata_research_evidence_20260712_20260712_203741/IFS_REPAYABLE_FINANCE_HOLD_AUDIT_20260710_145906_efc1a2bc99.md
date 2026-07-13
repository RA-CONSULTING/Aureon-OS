# IFS Repayable Finance Hold Audit

Generated: 2026-07-10T14:59:06+01:00
Operator: Aureon
Mode: IFS only

## Result

- IFS_REPAYABLE_FINANCE_HOLD_AUDIT_ROUTE_HELD_OUTSIDE_GRANT_QUEUE
- Repayable finance routes reviewed: 1
- Grant routes created: 0
- Direct submit-ready routes: 0
- New browser submissions available: 0
- Route held outside grant queue: true

## Decision

- Application: APP-IFS-INNOVATION-LOANS-EOI-2505-20260709
- Deadline: open-no-submission-deadline
- Status: INNOVATION_LOANS_REPAYABLE_FINANCE_CAPACITY_AND_ACTION_APPROVAL_REQUIRED
- Go decision: HOLD_OUTSIDE_GRANT_QUEUE_REPAYABLE_FINANCE
- Why not now: Innovation Loans is repayable finance, not grant funding. It needs explicit loan-route approval, repayment-capacity evidence and cash-flow support before it can be treated as a deliberate finance application.
- Next operator action: Keep outside the grant-submit queue. Only revisit if the operator deliberately approves repayable finance and supplies repayment-capacity and cash-flow evidence.
- Missing evidence:
  - repayable finance approval
  - repayment capacity evidence
  - cash-flow forecast
  - specific action-time approval for loan route

## Source Refs

- current_grant_board: applications/IFS_CURRENT_GRANT_BOARD_20260710_145627.json
- current_action_register: applications/IFS_CURRENT_ACTION_REGISTER_20260710_145622.json
- official_ifs_refresh: applications/IFS_OFFICIAL_CURRENT_REFRESH_20260710_143047.json
- drive_remaining_targeted_evidence_readback: applications/IFS_DRIVE_REMAINING_TARGETED_EVIDENCE_READBACK_20260710_131430.json
- remaining_submission_unlock_control_packet: applications/IFS_REMAINING_SUBMISSION_UNLOCK_CONTROL_PACKET_20260710_133509.json
- master_submission_readiness_ledger: applications/IFS_MASTER_SUBMISSION_READINESS_LEDGER_20260710_133816.json
- route_gate_evidence_search: applications/IFS_ROUTE_GATE_EVIDENCE_SEARCH_20260710_135633.json
- formal_attachment_guard: applications/IFS_FORMAL_ATTACHMENT_GUARD_20260710_142728.json
- company_compliance_readback: applications/IFS_COMPANY_COMPLIANCE_READBACK_20260710_143531.json

## Controls

- No IFS portal field was changed.
- No loan or grant application was submitted.
- No external email or contact route was submitted.
- No upload, partner invite, award terms acceptance or Project Impact action was performed.
- No repayment-capacity, cash-flow, affordability or loan approval claim was invented.
