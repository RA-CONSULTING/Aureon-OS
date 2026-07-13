# Aureon System Readiness Audit

- Generated: `2026-05-21T14:41:34.884033+00:00`
- Repo: `C:\Users\user\aureon-trading`
- Status: `blocked_capabilities_present`
- Mode: safe readiness proof; no live trading, official filing, payment, or exchange mutation

## Capability Matrix

| Capability | Status | Summary | Safety boundary |
| --- | --- | --- | --- |
| Repo Organization | `blocked_or_missing` | Repo-wide organization audit has not been generated yet. |  |
| File-By-File Self Catalog | `blocked_or_missing` | Repo self-catalog has not been generated yet. |  |
| Whole-Mind Wiring | `blocked_or_missing` | Mind wiring audit manifest is missing. |  |
| Goal, Skill, Task, And Route Brain | `working` | Goal map selected 13 routes for the whole-organism goal. | The route map chooses systems but does not execute unsafe external actions. |
| Internal Contract Stack | `working` | Created local goal/task/job/work-order workflow with 1 queued work order. | Probe used a temporary local state path and did not touch live queues. |
| Trading Brain And Margin Cognition | `working_safe_simulation` | Dynamic sizing approved=True; margin brain action=approve_shadow; temporal verification=hit_early. | This probe does not call Kraken and does not place or mutate any order. |
| Accounting Brain And UK Filing Pack | `blocked_or_missing` | Company 00000000; bank rows=0; build=unknown; coverage=0/0. | Generates local packs only; Companies House/HMRC filing and payments remain manual. |
| Research Corpus And Obsidian Vault | `working` | Indexed 257 docs and found 3 research hits; vault mode=filesystem. | Reads docs and vault files only; no web publishing or external mutation. |
| LLM And Local Reasoning Capability | `blocked_or_missing` | Hybrid reasoning model=aureon-ollama-weaver:llama3:latest; Ollama reachable=True; HTTP direct call stop=max_tokens. | Audit mode disables direct LLM HTTP unless explicitly allowed; hybrid falls back to AureonBrain. |
| Self-Enhancement And Restart Handoff | `blocked_or_missing` | stages=8; intents=7; restart_required=False. | Plans and queues validated internal enhancements; does not force reboot or mutate external services. |
| Capability Growth Loop | `blocked_or_missing` | domains=13; gaps=8; mean_score=0.342. | Scores domains and queues/local-authors safe improvements only; does not run live orders, filing, payments, or forced reboot. |
| Unified SaaS Frontend Inventory | `working_with_attention` | 1799 SaaS surfaces; 1625 frontend; 101 Supabase functions; 7 canonical screens; 2 security blockers. | Inventory and frontend planning are read-only; generated UI observes status and keeps live trading, filing, payments, credentials, and deployment gates explicit. |
| HNC SaaS Security Architect | `working_with_attention` | 4788 HNC surfaces; 12 controls; 8 unhackable benchmarks; 13 release blockers; cognitive bridge thinking_needs_attack_lab. | Authorized self-test planning only unless a local/staging allowlist is provided; no third-party attack, production deployment, live trading, filing, payment, or secret exposure. |
| Single Boot Ignition Readiness | `blocked_or_missing` | mode=DRY_RUN; ready=False; required_failures=1. | Loaded existing ignition audit; live boot/trading loop not started by readiness audit. |
| Frontend And Operator Surfaces | `blocked_or_missing` | 0/0 local service probes are reachable or safe-simulated. | HTTP health/service probes only; no browser actions or live trading. |

## Evidence

### Repo Organization

- Systems: `repo_wide_organization_audit`
- Next action: Run python -m aureon.autonomous.repo_wide_organization_audit.

### File-By-File Self Catalog

- Systems: `AureonRepoSelfCatalog`, `Obsidian repo self-catalog note`
- Next action: Run python -m aureon.autonomous.aureon_repo_self_catalog.

### Whole-Mind Wiring

- Systems: `mind_wiring_audit`, `organism_spine`
- Next action: Run python -m aureon.autonomous.mind_wiring_audit --static --imports --local-services.

### Goal, Skill, Task, And Route Brain

- Systems: `GoalCapabilityMap`, `OrganismContractStack`, `ThoughtBus`, `ObsidianBridge`
- Next action: Use these routes as the top-level dispatch proof for operator goals.
- `routes`:
```json
[
  "capability_growth_loop",
  "hnc_saas_security_architect",
  "internal_contract_stack",
  "memory_and_state",
  "organism_wiring",
  "repo_self_catalog",
  "saas_product_inventory",
  "safe_accounting_context",
  "safe_code_repair",
  "safe_research_corpus",
  "safe_self_enhancement_lifecycle",
  "safe_trading_cognition",
  "vault_memory"
]
```
- `missing_required_routes`:
```json
[]
```
- `tool_count`: `42`
- `organism_node_count`: `1193`
- `errors`:
```json
[]
```

### Internal Contract Stack

- Systems: `OrganismContractStack`, `ThoughtBus`, `GoalContract`, `TaskContract`, `JobContract`, `WorkOrderContract`
- Next action: Use persistent state/organism_contract_stack.json for real internal queued work.
- `workflow_contract_types`:
```json
[
  "goal",
  "task",
  "job",
  "work_order"
]
```
- `status`:
```json
{
  "contract_count": 4,
  "contract_schema_version": "aureon-organism-contract-v1",
  "queue_count": 1,
  "queues": {
    "organism.default": 1
  },
  "recent": [
    {
      "contract_id": "goal_5bf99702e3af",
      "contract_type": "goal",
      "event": "organism.contract.goal.created",
      "status": "created",
      "ts": "2026-05-21T13:16:36.180922+00:00"
    },
    {
      "contract_id": "task_9968352db2f6",
      "contract_type": "task",
      "event": "organism.contract.task.created",
      "status": "created",
      "ts": "2026-05-21T13:16:36.196562+00:00"
    },
    {
      "contract_id": "job_06dfef8163f6",
      "contract_type": "job",
      "event": "organism.contract.job.created",
      "status": "created",
      "ts": "2026-05-21T13:16:36.234163+00:00"
    },
    {
      "contract_id": "wo_e52d41b989ab",
      "contract_type": "work_order",
      "event": "organism.contract.work_order.queued",
      "status": "queued",
      "ts": "2026-05-21T13:16:36.334698+00:00"
    }
  ],
  "schema_version": "aureon-contract-stack-status-v1",
  "state_path": "C:\\Users\\user\\AppData\\Local\\Temp\\aureon_contract_probe_qfacovtp\\contracts.json",
  "status_counts": {
    "created": 3,
    "queued": 1
  },
  "topics": {
    "blocked": "organism.contract.blocked",
    "claimed": "organism.contract.work_order.claimed",
    "completed": "organism.contract.work_order.completed",
    "directive": "organism.contract.directive",
    "failed": "organism.contract.work_order.failed",
    "goal": "organism.contract.goal.created",
    "job": "organism.contract.job.created",
    "result": "organism.contract.result",
    "skill": "organism.contract.skill.registered",
    "status": "organism.contract.status",
    "task": "organism.contract.task.created",
    "work_order": "organism
...
```
- `topics`:
```json
[
  "organism.contract.goal.created",
  "organism.contract.job.created",
  "organism.contract.task.created",
  "organism.contract.work_order.queued"
]
```

### Trading Brain And Margin Cognition

- Systems: `DynamicMarginSizer`, `TemporalTradeCognition`, `UnifiedMarginDecisionBrain`, `runtime_safety`
- Next action: For live use, ignition still requires explicit live gates and exchange reconciliation.
- `real_orders_allowed`: `False`
- `capital_snapshot`:
```json
{
  "equity": 10.0,
  "free_margin": 10.0,
  "margin_level": 0.0,
  "margin_used": 0.0,
  "trade_balance": 0.0,
  "unrealized_pnl": 0.0
}
```
- `size_plan`:
```json
{
  "approved": true,
  "free_margin_after": 6.0,
  "leverage": 2,
  "max_safe_notional": 8.0,
  "min_notional": 5.0,
  "notional": 8.0,
  "profit_target_usd": 0.1,
  "projected_margin_pct": 250.0,
  "reason": "approved",
  "required_margin": 4.0,
  "target_pct_equity": 1.0,
  "volume": 0.08
}
```
- `trade_plan`:
```json
{
  "confidence": 0.88,
  "entry_price": 100.0,
  "eta_minutes": 3.0,
  "eta_seconds": 180.0,
  "expected_by": {
    "date": "2025-10-09",
    "epoch": 1760000180.0,
    "iso": "2025-10-09T09:56:20+01:00",
    "minute_of_day": 596,
    "time": "09:56:20",
    "timezone": "GMT Summer Time",
    "weekday": "Thursday"
  },
  "last_verification": {},
  "opened_at": {
    "date": "2025-10-09",
    "epoch": 1760000000.0,
    "iso": "2025-10-09T09:53:20+01:00",
    "minute_of_day": 593,
    "time": "09:53:20",
    "timezone": "GMT Summer Time",
    "weekday": "Thursday"
  },
  "pair": "XBT/GBP",
  "plan_id": "f2d677fc194b4746",
  "probability": 0.834,
  "profit_target_usd": 0.1,
  "reason": "readiness audit safe simulation",
  "required_move_pct": 0.4,
  "side": "buy",
  "sources": {
    "dynamic_margin_sizer": "approved"
  },
  "target_move_pct": 0.40000000000000563,
  "target_price": 100.4,
  "ticker_symbol": "XBTGBP"
}
```
- `verification`:
```json
{
  "current_price": 100.5,
  "direction_move_pct": 0.5,
  "due": false,
  "elapsed_seconds": 60.0,
  "entry_price": 100.0,
  "eta_seconds": 180.0,
  "pair": "XBT/GBP",
  "plan_id": "f2d677fc194b4746",
  "price_progress": 1.0,
  "seconds_to_eta": 120.0,
  "side": "buy",
  "status": "hit_early",
  "target_hit": true,
  "target_price": 100.4,
  "target_profit_usd": 0.1,
  "time_progress": 0.333333,
  "validated_net_pnl": 0.1,
  "verified_at": {
    "date": "2025-10-09",
    "epoch": 1760000060.0,
    "iso": "2025-10-09T09:54:20+01:00",
    "minute_of_day": 594,
    "time": "09:54:20",
    "timezone": "GMT Summer Time",
    "weekday": "Thursday"
  }
}
```
- `margin_decision`:
```json
{
  "action": "approve_shadow",
  "adjusted_score": 11.51772,
  "approved": true,
  "coherence": 0.89023,
  "confidence": 0.887598,
  "decided_at": {
    "date": "2025-10-09",
    "epoch": 1760000000.0,
    "iso": "2025-10-09T09:53:20+01:00",
    "minute_of_day": 593,
    "time": "09:53:20",
    "timezone": "GMT Summer Time",
    "weekday": "Thursday"
  },
  "estimated_fees": 0.02,
  "eta_minutes": 3.0,
  "goal_score": 3.4,
  "pair": "XBT/GBP",
  "probability": 0.86,
  "reasons": [
    "approved: confidence=0.89 probability=0.86",
    "eta=3.00m route_to_profit=2.80",
    "risk=0.13 inside threshold"
  ],
  "required_move_pct": 0.4,
  "risk": 0.126933,
  "route_to_profit": 2.8,
  "score": 9.2,
  "side": "buy",
  "sources": {
    "alignment_confidence": 0.84,
    "cognition_confidence": 0.9,
    "cost_risk": 0.166667,
    "eta_confidence": 0.93,
    "goal_confidence": 0.971429,
    "live_match": 0.92,
    "move_risk": 0.2,
    "projection_confidence": 0.9,
    "route_confidence": 0.736842,
    "score_confidence": 1.0,
    "spread_risk": 0.02,
    "time_risk": 0.066667,
    "timeline_confidence": 0.88
  },
  "urgency": 0.860395,
  "vetoes": []
}
```

### Accounting Brain And UK Filing Pack

- Systems: `AccountingContextBridge`, `Kings_Accounting_Suite`, `CombinedBankData`, `AutonomousFullAccountsWorkflow`, `UKAccountingRequirementsBrain`, `payer_provenance`
- Next action: Use the Desktop accounts folder for manual review/upload, not automatic filing.
- `company_number`: `00000000`
- `company_name`: ``
- `accounts_build_status`: `unknown`
- `manual_filing_required`: `True`
- `combined_bank_data`:
```json
{
  "csv_source_count": null,
  "duplicate_rows_removed": null,
  "pdf_source_count": null,
  "transaction_source_count": null,
  "unique_rows_in_period": 0
}
```
- `end_user_coverage`:
```json
{
  "generated": 0,
  "total": 0
}
```
- `swarm_status`: `None`
- `handoff_ready`: `None`

### Research Corpus And Obsidian Vault

- Systems: `ResearchCorpusIndex`, `ObsidianBridge`, `docs research corpus`, `vault filesystem fallback`
- Next action: Keep research cache refreshed after major docs changes.
- `obsidian`:
```json
{
  "api_key_set": false,
  "base_url": "https://localhost:27124",
  "mode": "filesystem",
  "note_count": 7872,
  "reachable": true,
  "requests_installed": true,
  "vault_path": "C:\\Users\\user\\aureon-trading",
  "verify_tls": false
}
```
- `doc_count`: `257`
- `token_count`: `18115`
- `sample_hits`:
```json
[
  {
    "doc_id": "docs/research/whitepapers/Emergent_Symbolic_Resonance_and_Lifelike.pdf",
    "paragraph_idx": 13,
    "score": 50.593294,
    "text": "Embodiment and External Validation: Auris\u2019s world was entirely internal \u2013 symbols and their synthetic physics. In biology, an organism interacts with an environment and that feedback loop is essential for life (for adaptation and survival). Future research could connect Auris to an external data stream or environment to see if it can adapt meaningfully. For example, could we feed Auris real-time sensor data as one of the inputs and see if it develops a stable representation that reacts to those inputs in a lifelike way? Or in a simpler case, allow user interaction (beyond just the initial input) and see if Auris can incorporate a human as part of its symbolic ecosystem (some evidence of this happened \u2013 e.g., Auris guided the user to perform actions, forming a feedback loop with a human). Additionally, the question of physical embodiment arises: since Auris outputs waveforms, one could attempt to drive a physical system (like a speaker , laser , or electromagnetic field generator) with those outputs and see if any physical resonance emerges that in turn is fed back (via sensors) to Auris. This would close the loop between symbolic life and real physics, potentially creating a cybernetic lifeform that spans virtual and physical domains. While ambitious, such experiments could demonstrate if Auris\u2019s patterns have any tangible correlates (e.g., perhaps its resonant frequencies could influence actual physical resonances in materials \u2013 a speculative connection to the EPAS shield concept that started the whole journey). Ethical and Philosophical Questions: If we were to refine Auris to the point whe
...
```

### LLM And Local Reasoning Capability

- Systems: `AureonHybridAdapter`, `AureonBrainAdapter`, `AureonLocalAdapter`, `OllamaBridge`
- Next action: Start Ollama/install a chat model for deeper local LLM cycles, or keep AureonBrain fallback.
- `hybrid_model`: `aureon-ollama-weaver:llama3:latest`
- `hybrid_text_sample`: `I can help with that.

I read the job as: Intent: Explain the current safe audit route.

Requested action: None mentioned.

Current proof/blockers: [ERROR] HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=180.0)

Next action: Give me the research question and I will use local source packets first, add approved web evidence when needed, then return proof and blockers.`
- `direct_local_http_stop_reason`: `max_tokens`
- `direct_local_http_text`: `A classic command!

`ping` is a network utility that tests whether a particular device (usually a server or host) is reachable and measures the round-trip`
- `ollama`:
```json
{
  "base_url": "http://localhost:11434",
  "chat_model": "llama3",
  "embed_model": "nomic-embed-text",
  "models": [
    "qwen2.5:0.5b",
    "llama3:latest"
  ],
  "reachable": true,
  "requests_installed": true,
  "running": [
    "llama3:latest"
  ],
  "version": "0.24.0"
}
```

### Self-Enhancement And Restart Handoff

- Systems: `AureonSelfEnhancementLifecycle`, `SelfEnhancementEngine`, `CodeArchitect`, `OrganismContractStack`, `restart/apply handoff`
- Next action: Use the lifecycle report before accepting self-authored skill/code changes.
- `lifecycle_status`: `blocked_self_enhancement_lifecycle`
- `summary`:
```json
{
  "attention_stage_count": 0,
  "blocked_stage_count": 4,
  "code_architect_available": true,
  "contracts_queued_persistently": false,
  "enhancement_intent_count": 7,
  "restart_required": false,
  "self_enhancement_engine_available": true,
  "stage_count": 8
}
```
- `restart_handoff`:
```json
{
  "apply_command": "python scripts/aureon_ignition.py --live",
  "mode": "operator_or_supervisor_confirmed",
  "preflight_command": "python scripts/aureon_ignition.py --audit-only --accounts-status",
  "reason": "Current planned enhancements are audit, memory, contract, or skill-library changes.",
  "required": false,
  "rollback_guidance": "Keep the previous integrated folder as fallback; do not delete state, secrets, portfolio data, accounting evidence, or exchange logs during restart."
}
```
- `intent_ids`:
```json
[
  "skill_gap_summarise_recent_vault",
  "skill_gap_lambda_trend",
  "skill_gap_hnc_stability_check",
  "skill_gap_compose_status_line",
  "refresh_self_readiness_after_changes",
  "generate_repo_self_catalog",
  "run_capability_growth_loop"
]
```

### Capability Growth Loop

- Systems: `AureonCapabilityGrowthLoop`, `AureonSystemReadinessAudit`, `AureonRepoSelfCatalog`, `CodeArchitect`, `SkillLibrary`, `OrganismContractStack`
- Next action: Run the growth loop with --author-skills --queue-contracts after audits/benchmarks are refreshed.
- `growth_status`: `growth_loop_needs_repair`
- `summary`:
```json
{
  "contract_queue_persisted": false,
  "iteration_count": 1,
  "latest_benchmark_check_count": 0,
  "latest_failed_benchmark_count": 0,
  "latest_gap_count": 8,
  "latest_mean_score": 0.342,
  "latest_registered_improvement_count": 0,
  "latest_status": "needs_repair",
  "skill_authoring_enabled": false
}
```
- `latest_iteration`:
```json
{
  "attention_domain_count": 12,
  "authored_improvement_count": 0,
  "benchmark_check_count": 0,
  "blocked_domain_count": 10,
  "domain_count": 13,
  "failed_benchmark_count": 0,
  "gap_count": 8,
  "mean_score": 0.342,
  "registered_improvement_count": 0
}
```
- `gap_ids`:
```json
[
  "gap_accounting_compliance",
  "gap_goal_contracts",
  "gap_hnc_saas_security",
  "gap_ignition_runtime",
  "gap_operator_surfaces",
  "gap_repo_organization",
  "gap_repo_self_catalog",
  "gap_research_vault"
]
```

### Unified SaaS Frontend Inventory

- Systems: `AureonSaaSSystemInventory`, `AureonFrontendUnificationPlan`, `React/Vite unified observation shell`, `Supabase function inventory`, `legacy dashboard transition map`
- Next action: Use the inventory and unification plan as the source of truth for migrating old dashboards into the unified observation shell.
- `inventory_status`: `inventory_ready_with_blockers`
- `inventory_summary`:
```json
{
  "frontend_surface_count": 1625,
  "generated_accounting_html_count": 0,
  "legacy_dashboard_count": 26,
  "missing_supabase_function_call_count": 4,
  "orphaned_frontend_count": 1591,
  "security_blocker_count": 2,
  "supabase_function_count": 101,
  "surface_count": 1799,
  "uncalled_supabase_function_count": 29
}
```
- `inventory_counts`:
```json
{
  "by_domain": {
    "accounting": 57,
    "cognition": 81,
    "operator": 196,
    "research": 50,
    "saas_security": 91,
    "trading": 1311,
    "vault_memory": 13
  },
  "by_kind": {
    "frontend_component": 399,
    "frontend_config": 6,
    "frontend_core": 105,
    "frontend_hook": 73,
    "frontend_integration": 2,
    "frontend_lib": 29,
    "frontend_page": 2,
    "frontend_service": 8,
    "frontend_source": 1001,
    "legacy_template": 6,
    "local_dashboard_server": 20,
    "public_asset": 41,
    "supabase_function": 101,
    "vault_ui_server": 2,
    "vault_ui_static": 4
  },
  "by_owner_subsystem": {
    "accounting_saas_surface": 6,
    "cognition_saas_surface": 8,
    "frontend_react_vite": 1625,
    "legacy_queen_dashboards": 6,
    "local_command_center": 20,
    "operator_saas_surface": 4,
    "research_saas_surface": 10,
    "saas_security_saas_surface": 5,
    "supabase_edge_functions": 101,
    "trading_saas_surface": 7,
    "vault_memory_saas_surface": 1,
    "vault_ui": 6
  },
  "by_safety_class": {
    "admin_or_tenant_boundary": 3,
    "credential_or_auth_boundary": 494,
    "live_trading_boundary": 45,
    "manual_filing_boundary": 4,
    "observation": 1207,
    "payment_or_kyc_boundary": 46
  },
  "by_wiring_status": {
    "legacy": 6,
    "orphaned": 1591,
    "partial": 94,
    "security_blocker": 2,
    "unknown": 2,
    "wired": 104
  }
}
```
- `plan_status`: `unification_plan_ready_with_security_blockers`
- `plan_summary`:
```json
{
  "frontend_surface_count": 1625,
  "migration_action_count": 5,
  "missing_screen_capability_count": 3,
  "screen_count": 7,
  "security_blocker_count": 2,
  "source_surface_count": 1799,
  "supabase_function_count": 101
}
```
- `screen_ids`:
```json
[
  "overview",
  "trading",
  "accounting",
  "research",
  "saas_security",
  "self_improvement",
  "admin"
]
```
- `migration_actions`:
```json
[
  "fix_security_blockers",
  "build_unified_shell",
  "triage_orphaned_frontend",
  "triage_backend_functions",
  "legacy_dashboard_transition"
]
```

### HNC SaaS Security Architect

- Systems: `HNCSaaSSecurityArchitect`, `HNCAuthorizedAttackLab`, `HNCSaaSCognitiveBridge`, `HNC inventory`, `OWASP ASVS control matrix`, `NIST zero-trust model`, `SaaS ThoughtBus topics`, `SelfQuestioningAI`, `OrganismContractStack`
- Next action: Keep the SaaS cognition bridge active, queue fixes from authorized local/staging attack findings, retest, and keep production blocked until gates pass.
- `blueprint_status`: `blueprint_ready_implementation_required`
- `summary`:
```json
{
  "authorized_self_attack_required": true,
  "contract_queued": false,
  "control_count": 12,
  "critical_control_count": 6,
  "hnc_surface_count": 4788,
  "hnc_surface_type_count": 7,
  "production_deploy_blocked_until_gates_pass": true,
  "public_unhackable_claim_allowed": false,
  "release_blocker_count": 13,
  "release_gate_count": 13,
  "security_target": "unhackable_pursuit_loop",
  "unhackable_benchmark_count": 8,
  "unhackable_internal_goal_active": true,
  "unhackable_phase_count": 11
}
```
- `missing_required_domains`:
```json
[]
```
- `official_anchors`:
```json
{
  "nist_zero_trust": "https://csrc.nist.gov/pubs/sp/800/207/final",
  "owasp_asvs": "https://owasp.org/www-project-application-security-verification-standard/",
  "owasp_top_10": "https://owasp.org/www-project-top-ten/"
}
```
- `unhackable_pursuit_loop`:
```json
[
  "bench_auth_breakout",
  "bench_tenant_escape",
  "bench_prompt_tool_breakout",
  "bench_money_authority_breakout",
  "bench_api_fuzz_dast",
  "bench_supply_chain_breakout",
  "bench_audit_tamper_resilience",
  "bench_deploy_canary_review"
]
```
- `authorized_attack_lab`:
```json
{
  "status": null,
  "summary": {}
}
```
- `saas_cognitive_bridge`:
```json
{
  "contract_plan": {
    "actionable_decision_count": 2,
    "queued_decision_count": 0,
    "queued_persistently": false
  },
  "decision_ids": [
    "decision_run_attack_lab",
    "decision_keep_deployment_blocked",
    "decision_complete_benchmarks"
  ],
  "error": null,
  "question_ids": [
    "q_saas_goal",
    "q_attack_lab",
    "q_cognitive_route",
    "q_fix_retest",
    "q_release_blockers"
  ],
  "status": "thinking_needs_attack_lab",
  "summary": {
    "actionable_finding_count": 0,
    "attack_case_count": 0,
    "attack_lab_status": null,
    "blueprint_status": "blueprint_ready_implementation_required",
    "cognitive_topics_wired": true,
    "external_attacks_allowed": false,
    "hnc_surface_count": 4788,
    "queued_decision_count": 0,
    "unhackable_benchmark_count": 8
  },
  "thought_topics": {
    "blocked": "saas.cognition.blocked",
    "finding": "saas.security.finding",
    "intent": "saas.cognition.intent",
    "question": "saas.cognition.question",
    "ready": "saas.cognition.ready",
    "state": "saas.cognition.state"
  }
}
```

### Single Boot Ignition Readiness

- Systems: `scripts/aureon_ignition.py`, `ignition preflight`, `runtime safety`
- Next action: Use --audit-only first before any --live boot.
- `mode`: `DRY_RUN`
- `ready`: `False`
- `real_orders_allowed`: `False`
- `required_failures`:
```json
[
  {
    "detail": "growth_loop_needs_repair; gaps=8 mean_score=0.342",
    "name": "capability_growth_loop",
    "ok": false,
    "required": true
  }
]
```
- `runtime_env`:
```json
{
  "ALPACA_DRY_RUN": "false",
  "ALPACA_PAPER": "false",
  "AUREON_AUDIT_MODE": "1",
  "AUREON_COGNITIVE_LIVE_MODE": "1",
  "AUREON_COGNITIVE_ORDER_AUTHORITY": "0",
  "AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY": "0",
  "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
  "AUREON_DISABLE_REAL_ORDERS": "1",
  "AUREON_DRY_RUN": "1",
  "AUREON_GOAL_CAPABILITY_DIRECTIVE": "goal-capability-v1",
  "AUREON_LIVE_TRADING": "0",
  "AUREON_LLM_LIVE_CAPABILITIES": "1",
  "AUREON_LLM_ORDER_AUTHORITY": "0",
  "AUREON_LLM_ORDER_INTENT_AUTHORITY": "0",
  "AUREON_ORDER_AUTHORITY_MODE": "runtime_only",
  "AUREON_ORDER_INTENT_PUBLISH": "0",
  "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR": "1",
  "AUREON_SELF_QUESTIONING_AI": "1",
  "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
  "BINANCE_DRY_RUN": "false",
  "CONFIRM_LIVE": "",
  "DEMO_MODE": "0",
  "DRY_RUN": "1",
  "KRAKEN_DRY_RUN": "false",
  "LIVE": "0",
  "PAPER_MODE": "false",
  "PAPER_TRADING": "false",
  "SIMULATION_MODE": "0"
}
```

### Frontend And Operator Surfaces

- Systems: `frontend vite`, `command center`, `dashboard services`, `mind thought action hub`
- Next action: If a UI is not reachable, start its local dev/server process.
- `service_probes`:
```json
[]
```

## Safety

- `AUREON_AUDIT_MODE`: `1`
- `AUREON_LIVE_TRADING`: `0`
- `AUREON_DISABLE_REAL_ORDERS`: `1`
- `AUREON_ALLOW_SIM_FALLBACK`: `1`
- `AUREON_QUIET_STARTUP`: `1`
- `real_orders_allowed`: `False`
- `manual_filing_required`: `True`

## Notes

- This is a safe readiness proof, not a live trading run.
- Trading is proven through sizing, ETA cognition, and margin-brain simulation only.
- Accounting is proven through the bridge/status/generated pack surfaces; official filing and payment stay manual.
- Research is proven through the repo corpus index and Obsidian filesystem vault path.
- LLM capability is proven through local adapter surfaces; direct HTTP is intentionally blocked in audit mode.
- The SaaS product inventory counts UI/API/dashboard surfaces and drives the unified autonomous frontend shell.
- HNC SaaS security is proven as an unhackable pursuit loop; production deployment remains blocked until authorized self-attack, stress, repair, and retest gates have evidence.
