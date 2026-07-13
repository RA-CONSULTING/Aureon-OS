# Aureon Coding Capability Unblocker

- status: coding_capabilities_need_gate_repairs
- gates: 8/9 ready
- converted coding blockers: 1
- manual authority holds: 0
- work orders: 7

## Gates
- scope_defaulting_gate: ready - If the prompt is incomplete, choose safe defaults and write assumptions into evidence.
- local_forge_gate: ready - Route build/app/media requests through aureon_capability_forge before declaring blocked.
- safe_code_authoring_gate: ready - Create proposals and apply only scoped repo patches through safe local routes.
- adaptive_skill_acquisition_gate: ready - When a skill is missing, create a domain worker, run tests, and publish a quality report.
- dependency_install_gate: ready - Use project-local venv/npm only; record installs and rerun verification.
- open_source_research_gate: ready - Search sources, capture source packets, review license/security, then build Aureon's own implementation.
- test_and_run_gate: ready - Run focused tests/build/smoke after each generated artifact or repo patch.
- quality_handover_gate: needs_repair - Run complex stress certification and hold handover until fake passes are zero.
- manual_authority_boundary_gate: manual_hold_ready - Never convert trading, payment, filing, credential, or destructive OS authority into coding autonomy.

## Work Orders
- unblock_missing_domain_worker_1: P80 via adaptive_skill_acquisition_gate
- unblock_unknown_attention_2: P60 via safe_code_authoring_gate
- unblock_unknown_attention_3: P60 via safe_code_authoring_gate
- unblock_unknown_attention_4: P60 via safe_code_authoring_gate
- unblock_unknown_attention_5: P60 via safe_code_authoring_gate
- unblock_unknown_attention_6: P60 via safe_code_authoring_gate
- unblock_unknown_attention_7: P60 via safe_code_authoring_gate
