# Aureon Autonomous Capability Switchboard

- Generated: `2026-05-22T18:17:38.089511+00:00`
- Status: `switchboard_ready_with_blockers`
- Repo: `C:\Users\user\aureon-trading`

## Summary

- `capability_count`: `9`
- `autonomous_capability_count`: `9`
- `blocked_capability_count`: `5`
- `presentation_intent_count`: `15`
- `blocker_count`: `8`
- `frontend_work_order_count`: `564`
- `ready_adapter_count`: `461`
- `security_blocker_count`: `2`
- `runtime_feed_status`: `offline`
- `action_mode`: `safe_observation`
- `trading_action_allowed`: `False`
- `canonical_screen_count`: `7`

## Capability Modes

| Status | Domain | Authority | Capability | Next action |
| --- | --- | --- | --- | --- |
| `ready` | `operator` | `autonomous_reasoning_and_contract_creation` | Conversation And Goal Router | Use this route for operator dialogue and self-questioning before selecting a deeper capability. |
| `ready_with_backlog` | `frontend` | `generate_read_only_ui_contracts` | Frontend Design And Layout Orchestrator | Convert high-priority ready work orders into read-only adapters and visual smoke tests. |
| `blocked_missing_manifest` | `self_improvement` | `proposal_patch_test_retest` | App Generation And Local Tool Builder | Keep generated code behind audit, benchmark, patch, retest, and explicit apply records. |
| `ready_for_prompt_contract` | `presentation` | `prompt_contract_and_asset_request` | Image And Visual Asset Generation | Use generated visuals for explanation and interface clarity, never as hidden evidence. |
| `blocked_missing_manifest` | `research` | `read_research_ingest_summarise` | Research, Search, And Vault Memory | Keep research outputs source-linked and visible in the vault/research tab. |
| `blocked_missing_manifest` | `accounting` | `generate_manual_filing_support_documents` | Accounting Accounts And Evidence Builder | Refresh the accounting registry and show every missing evidence item before final-ready claims. |
| `runtime_feed_offline` | `trading` | `observe_plan_and_delegate_to_existing_trading_gates` | Trading Cognition And Dynamic Positioning | Bring the local runtime feed online and clear guard blockers before live action. |
| `blocked_security_review` | `saas_security` | `authorized_local_or_owned_scope_test_fix_retest` | HNC SaaS Security And Authorized Test Lab | Show blockers clearly and only test owned/local/staging surfaces. |
| `blocked_missing_manifest` | `self_improvement` | `safe_loop_with_apply_handoff` | Continuous Audit, Benchmark, Fix, Retest Loop | Keep observer running and use blockers as the next improvement queue. |

## Presentation Intents

| Priority | Status | Display | Target | Intent |
| ---: | --- | --- | --- | --- |
| 100 | `blocked_security_review` | `dashboard_panel` | `trading` | Wire Orca Command Center into Trading |
| 100 | `ready_for_frontend_adapter` | `dashboard_panel` | `trading` | Wire Aureon Atn Command Center into Trading |
| 100 | `ready_for_frontend_adapter` | `dashboard_panel` | `trading` | Wire Aureon Command Center Enhanced into Trading |
| 100 | `blocked_security_review` | `dashboard_panel` | `self_improvement` | Wire Aureon Command Center into Self-Improvement |
| 100 | `ready_for_frontend_adapter` | `dashboard_panel` | `self_improvement` | Wire Aureon Queen Realtime Command Center into Self-Improvement |
| 100 | `ready_for_frontend_adapter` | `dashboard_panel` | `self_improvement` | Wire Aureon War Band Enhanced into Self-Improvement |
| 100 | `blocked_security_review` | `dashboard_panel` | `saas_security` | Wire Adminkycdashboard into SaaS Security |
| 100 | `blocked_security_review` | `dashboard_panel` | `saas_security` | Wire Adminpaymentverification into SaaS Security |
| 100 | `blocked_security_review` | `dashboard_panel` | `saas_security` | Wire Apikeysecurityguide into SaaS Security |
| 100 | `blocked_security_review` | `dashboard_panel` | `saas_security` | Wire Authform into SaaS Security |
| 100 | `blocked_security_review` | `dashboard_panel` | `overview` | Wire Gastankdisplay into Overview |
| 100 | `blocked_security_review` | `dashboard_panel` | `overview` | Wire Warroomdashboard into Overview |
| 98 | `ready_to_queue_adapters` | `generated_app_surface` | `self_improvement` | Build read-only adapters from older dashboard systems |
| 95 | `blocked_waiting_for_runtime_feed` | `dashboard_panel` | `overview` | Show runtime feed as offline until real data arrives |
| 94 | `blocked_security_review` | `release_gate` | `saas_security` | Surface security blockers before interactive controls |

## HNC Control Contract

```json
{
  "anti_hallucination_gates": [
    "source_evidence_required",
    "manifest_freshness_checked",
    "data_contract_declared",
    "no_fake_state_or_hidden_totals",
    "confidence_and_blockers_visible",
    "safe_authority_boundary_checked",
    "result_retest_or_visual_smoke_required"
  ],
  "authority_matrix": {
    "accounting_documents": "autonomous_generation_manual_filing_only",
    "app_generation": "autonomous_patch_allowed_only_with_tests_and_scope",
    "conversation": "autonomous_allowed_with_evidence",
    "frontend_design": "autonomous_allowed_read_only_or_tested_patch",
    "image_generation": "autonomous_prompt_contract_generated_asset_must_be_labelled",
    "saas_security_tests": "owned_or_local_authorized_scope_only",
    "search_and_research": "autonomous_allowed_read_only",
    "secrets": "metadata_status_only_never_reveal_values",
    "trading_orders": "delegated_to_existing_live_trading_gates_only"
  },
  "decision_ladder": [
    "perceive_current_goal_or_blind_spot",
    "recall_vault_and_manifest_evidence",
    "classify_domain_and_select_capability",
    "run_hnc_anti_drift_gates",
    "create_contract_or_presentation_intent",
    "render_or_execute_only_within_authority",
    "verify_with_tests_or_source_reconciliation",
    "publish_status_back_to_frontend_vault_and_thoughtbus"
  ],
  "drift_controls": [
    "No frontend panel may show trusted data without source_path and freshness.",
    "Generated media and generated reports must be labelled as generated.",
    "Low confidence or missing evidence must become a visible blocker.",
    "Unsafe side effects must become manual or gated actions, not hidden autonomy."
  ]
}
```

## Safety Contract

- `llm_can_select_capability`: `True`
- `llm_can_create_presentation_intents`: `True`
- `llm_can_queue_work_orders`: `True`
- `llm_can_generate_frontend_or_app_code_after_tests`: `True`
- `llm_can_request_labelled_generated_visuals`: `True`
- `llm_can_publish_thoughtbus_status`: `True`
- `runtime_can_place_live_orders_via_existing_gates`: `False`
- `llm_can_place_direct_live_orders`: `False`
- `llm_can_file_hmrc_or_companies_house`: `False`
- `llm_can_make_payments`: `False`
- `llm_can_attack_third_party_targets`: `False`
- `secret_values_hidden`: `True`
- `unsafe_actions_become_blockers`: `True`

## Blockers

- `medium` `runtime_feed.offline`: Real-time feed is offline; show audit/manifest state only. Next: Start the local read-only runtime status endpoint.
- `high` `saas_inventory.security_blockers`: 2 SaaS security blockers remain. Next: Route through HNC SaaS Security and authorized local retests.
- `medium` `frontend_evolution.blocked_work_orders`: 26 frontend evolution work orders are blocked. Next: Resolve blocker status or create safe read-only status adapters.
- `medium` `capability.app_generation`: App Generation And Local Tool Builder is blocked_missing_manifest. Next: Keep generated code behind audit, benchmark, patch, retest, and explicit apply records.
- `medium` `capability.research_search_and_vault`: Research, Search, And Vault Memory is blocked_missing_manifest. Next: Keep research outputs source-linked and visible in the vault/research tab.
- `medium` `capability.accounting_document_brain`: Accounting Accounts And Evidence Builder is blocked_missing_manifest. Next: Refresh the accounting registry and show every missing evidence item before final-ready claims.
- `medium` `capability.saas_security_cognition`: HNC SaaS Security And Authorized Test Lab is blocked_security_review. Next: Show blockers clearly and only test owned/local/staging surfaces.
- `medium` `capability.continuous_self_enhancement`: Continuous Audit, Benchmark, Fix, Retest Loop is blocked_missing_manifest. Next: Keep observer running and use blockers as the next improvement queue.
