# IFS Full Board Coverage Validation

Generated: 2026-07-10T23:54:07+01:00
Operator: Aureon
Mode: IFS only

## Result

- IFS_FULL_BOARD_COVERAGE_VALIDATION_PASSED
- Validation passed: true
- IFS applications total: 20
- Submitted monitor-only: 4
- Active not submitted: 16
- Direct submit-ready routes: 0
- New browser submissions available: 0
- Route family counts: {"SUBMITTED_MONITOR": 4, "P1_NEAREST_DEADLINE": 4, "P2_NEXT_DEADLINE": 3, "LIVE_DRAFT_UK_SWISS": 1, "REMAINING_EVIDENCE_GATED": 7, "REPAYABLE_FINANCE_HELD_OUTSIDE_GRANT_QUEUE": 1}

## Source Refs

- current_grant_board: applications/IFS_CURRENT_GRANT_BOARD_20260710_235400.json
- current_action_register: applications/IFS_CURRENT_ACTION_REGISTER_20260710_235356.json
- submitted_track_signin_gate: applications/IFS_SUBMITTED_TRACK_SIGNIN_GATE_20260710_143214.json
- p1_stop_go_audit: applications/IFS_P1_STOP_GO_AUDIT_20260710_143920.json
- p2_stop_go_audit: applications/IFS_P2_STOP_GO_AUDIT_20260710_144429.json
- uk_swiss_stop_go_audit: applications/IFS_UK_SWISS_STOP_GO_AUDIT_20260710_145126.json
- remaining_stop_go_audit: applications/IFS_REMAINING_STOP_GO_AUDIT_20260710_145545.json
- repayable_finance_hold_audit: applications/IFS_REPAYABLE_FINANCE_HOLD_AUDIT_20260710_145906.json
- official_ifs_refresh: applications/IFS_OFFICIAL_CURRENT_REFRESH_20260710_232050.json
- company_compliance_readback: applications/IFS_COMPANY_COMPLIANCE_READBACK_20260710_143531.json

## Scan Results

- Secret scan hits: {}
- Internal-language scan hits: {}

## Controls

- Validation only; no IFS portal field was changed.
- No IFS application was submitted.
- No email, contact form, partner invite, upload, award terms or Project Impact action was performed.
- All active IFS route families are covered by current stop/go or hold audits.
