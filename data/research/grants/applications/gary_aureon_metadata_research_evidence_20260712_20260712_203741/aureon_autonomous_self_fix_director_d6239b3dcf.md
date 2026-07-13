# Aureon Autonomous Self-Fix Director

- status: self_fix_blocked
- handover_ready: False
- codex_audit_state: autonomous_safe
- repairs selected: 3
- patches applied: 0
- snags: 1

## SWOT
### Strengths
- capability_forge: Capability forge exists and can create local artifacts. present=True
- complex_stress: Complex build stress certification exists. present=True
- coding_unblocker: Coding unblocker maps coding blockers into autonomous gates. present=True
- quality_gate: Artifact quality gate and public evidence are wired. present=True
- unique_artifacts: Generated build IDs prevent stale artifact reuse. present=True
### Weaknesses
- proposal_only_apply: SafeCodeControl records proposals but needs a guarded patch applier. present=True
- stress_repair_depth: Stress repairs must create work orders and apply safe fixes, not only rerun proof. present=True
- repo_integration_depth: Generated artifacts can pass while live repo integration remains shallow. present=True
### Opportunities
- guarded_patch_apply: Use allowlisted diffs with git apply checks and tests. present=True
- self_fix_backlog: Convert failed stress cases into repair jobs Aureon owns. present=True
- source_packets: Use local/GitHub/docs research as source packets before coding. present=True
### Threats
- authority_leakage: Live trading, payments, filings, secrets, and destructive OS actions must stay blocked. present=True
- fake_passes: Fake passes must block handover. present=False
- license_or_copy_risk: Open-source references need license notes and must not be copied blindly. present=True
- stale_evidence: Stale public evidence can make the cockpit look healthier than it is. present=True

## Repair Backlog
- P0 guarded_patch_applier: Add guarded repo patch applier
- P0 stress_repair_work_orders: Make complex stress failures become self-fix work orders
- P1 cockpit_self_fix_panel: Show Aureon Self-Fix SWOT in the coding cockpit
- P0 repair_case_sandbox_ten_second_video_preview: Repair failed stress case: sandbox_ten_second_video_preview
