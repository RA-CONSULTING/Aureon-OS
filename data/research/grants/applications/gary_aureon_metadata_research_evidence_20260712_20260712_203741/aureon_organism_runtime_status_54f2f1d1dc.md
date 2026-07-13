# Aureon Organism Runtime Status

- Generated: `2026-05-22T18:20:48.473938+00:00`
- Status: `organism_observing_with_blind_spots`
- Mode: `safe_observation`
- Repo: `C:\Users\user\aureon-trading`

## Summary

- `domain_count`: `21`
- `blind_spot_count`: `36`
- `high_blind_spot_count`: `11`
- `fresh_domain_count`: `8`
- `stale_domain_count`: `6`
- `missing_domain_count`: `7`
- `attention_domain_count`: `8`
- `refresh_count`: `9`
- `failed_refresh_count`: `1`
- `runtime_feed_status`: `offline`
- `action_mode`: `safe_observation`
- `trading_action_allowed`: `False`
- `frontend_public_manifest_count`: `6`

## Safety

- Action mode: `safe_observation`.
- Live orders allowed: `False`.
- Exchange mutation scope: `none`.
- Official filings, payments, credential reveal, and unowned security mutations are blocked.

## Domain Pulse

| Status | Freshness | Domain | Source | Blind spots | Next action |
| --- | --- | --- | --- | ---: | --- |
| `attention` | `fresh` | `SaaS And Frontend Inventory` | `docs/audits/aureon_saas_system_inventory.json` | 3 | Run python -m aureon.autonomous.aureon_saas_system_inventory. |
| `attention` | `fresh` | `Unified Frontend Plan` | `docs/audits/aureon_frontend_unification_plan.json` | 2 | Run python -m aureon.autonomous.aureon_frontend_unification_plan. |
| `attention` | `fresh` | `Frontend Evolution Queue` | `docs/audits/aureon_frontend_evolution_queue.json` | 2 | Run python -m aureon.autonomous.aureon_frontend_evolution_queue. |
| `attention` | `fresh` | `Autonomous Capability Switchboard` | `docs/audits/aureon_autonomous_capability_switchboard.json` | 2 | Run python -m aureon.autonomous.aureon_autonomous_capability_switchboard. |
| `attention` | `fresh` | `Aureon Operational UI Builder` | `docs/audits/aureon_operational_ui_builder.json` | 2 | Run python -m aureon.autonomous.aureon_unified_ui_builder. |
| `stale` | `stale` | `Whole Organism Readiness` | `docs/audits/aureon_system_readiness_audit.json` | 3 | Run python -m aureon.autonomous.aureon_system_readiness_audit. |
| `attention` | `fresh` | `Cognitive Trade Evidence` | `docs/audits/aureon_cognitive_trade_evidence.json` | 3 | Run python -m aureon.autonomous.aureon_cognitive_trade_evidence. |
| `attention` | `fresh` | `HNC Auris Harmonic Affect State` | `docs/audits/aureon_harmonic_affect_state.json` | 2 | Run python -m aureon.autonomous.aureon_harmonic_affect_state. |
| `attention` | `fresh` | `Trading Intelligence Checklist` | `docs/audits/aureon_trading_intelligence_checklist.json` | 2 | Run python -m aureon.autonomous.aureon_trading_intelligence_checklist. |
| `stale` | `stale` | `Exchange Data Capability Matrix` | `docs/audits/aureon_exchange_data_capability_matrix.json` | 1 | Run python -m aureon.autonomous.aureon_exchange_data_capability_matrix. |
| `missing` | `missing` | `Whole-Mind Wiring` | `docs/audits/mind_wiring_audit.json` | 1 | Run python -m aureon.autonomous.mind_wiring_audit --static --imports --local-services. |
| `missing` | `missing` | `File Self-Catalog` | `docs/audits/aureon_repo_self_catalog.json` | 2 | Run python -m aureon.autonomous.aureon_repo_self_catalog. |
| `missing` | `missing` | `Accounting System Registry` | `docs/audits/accounting_system_registry.json` | 1 | Run the accounting registry/accounts generation workflow in safe manual-filing mode. |
| `missing` | `missing` | `Capability Growth Loop` | `docs/audits/aureon_capability_growth_loop.json` | 1 | Run python -m aureon.autonomous.aureon_capability_growth_loop. |
| `missing` | `missing` | `Self-Enhancement Lifecycle` | `docs/audits/aureon_self_enhancement_lifecycle.json` | 1 | Run python -m aureon.autonomous.aureon_self_enhancement_lifecycle. |
| `missing` | `missing` | `HNC SaaS Security Blueprint` | `docs/audits/hnc_saas_security_blueprint.json` | 1 | Run python -m aureon.autonomous.hnc_saas_security_architect. |
| `missing` | `missing` | `Authorized Attack Lab` | `docs/audits/hnc_authorized_attack_lab.json` | 1 | Run the authorized attack lab against owned/local targets only. |
| `stale` | `stale` | `Adaptive Learning History` | `adaptive_learning_history.json` | 1 | Start the safe runtime/cognition loop so learning history is repopulated. |
| `stale` | `stale` | `Brain Prediction History` | `brain_predictions_history.json` | 1 | Start the safe runtime/cognition loop so prediction history is repopulated. |
| `stale` | `stale` | `Miner Brain Knowledge` | `miner_brain_knowledge.json` | 1 | Run the research/vault ingestion loop to refresh miner knowledge. |
| `stale` | `stale` | `Consciousness State` | `public/consciousness_state.json` | 1 | Start the cognition runtime so consciousness state is updated. |

## Blind Spots

| Severity | Domain | Issue | Next action |
| --- | --- | --- | --- |
| `attention` | `operator` | SaaS And Frontend Inventory: attention security blocker count. | Run python -m aureon.autonomous.aureon_saas_system_inventory. |
| `attention` | `operator` | SaaS And Frontend Inventory: attention orphaned frontend count. | Run python -m aureon.autonomous.aureon_saas_system_inventory. |
| `high` | `operator` | SaaS And Frontend Inventory: attention missing supabase function call count. | Run python -m aureon.autonomous.aureon_saas_system_inventory. |
| `attention` | `operator` | Unified Frontend Plan: attention security blocker count. | Run python -m aureon.autonomous.aureon_frontend_unification_plan. |
| `high` | `operator` | Unified Frontend Plan: attention missing screen capability count. | Run python -m aureon.autonomous.aureon_frontend_unification_plan. |
| `attention` | `self_improvement` | Frontend Evolution Queue: attention blocked count. | Run python -m aureon.autonomous.aureon_frontend_evolution_queue. |
| `attention` | `self_improvement` | Frontend Evolution Queue: attention archive candidate count. | Run python -m aureon.autonomous.aureon_frontend_evolution_queue. |
| `attention` | `self_improvement` | Autonomous Capability Switchboard: attention blocker count. | Run python -m aureon.autonomous.aureon_autonomous_capability_switchboard. |
| `attention` | `self_improvement` | Autonomous Capability Switchboard: attention blocked capability count. | Run python -m aureon.autonomous.aureon_autonomous_capability_switchboard. |
| `attention` | `self_improvement` | Aureon Operational UI Builder: attention blocked work order count. | Run python -m aureon.autonomous.aureon_unified_ui_builder. |
| `attention` | `self_improvement` | Aureon Operational UI Builder: attention blind spot count. | Run python -m aureon.autonomous.aureon_unified_ui_builder. |
| `medium` | `cognition` | Whole Organism Readiness: manifest stale. | Run python -m aureon.autonomous.aureon_system_readiness_audit. |
| `attention` | `cognition` | Whole Organism Readiness: attention blocked count. | Run python -m aureon.autonomous.aureon_system_readiness_audit. |
| `attention` | `cognition` | Whole Organism Readiness: attention attention count. | Run python -m aureon.autonomous.aureon_system_readiness_audit. |
| `attention` | `trading` | Cognitive Trade Evidence: not populated evidence count. | Run python -m aureon.autonomous.aureon_cognitive_trade_evidence. |
| `attention` | `trading` | Cognitive Trade Evidence: not populated signal quality. | Run python -m aureon.autonomous.aureon_cognitive_trade_evidence. |
| `medium` | `trading` | Cognitive Trade Evidence: attention runtime stale. | Run python -m aureon.autonomous.aureon_cognitive_trade_evidence. |
| `medium` | `cognition` | HNC Auris Harmonic Affect State: attention runtime stale. | Run python -m aureon.autonomous.aureon_harmonic_affect_state. |
| `attention` | `cognition` | HNC Auris Harmonic Affect State: attention safety blocker count. | Run python -m aureon.autonomous.aureon_harmonic_affect_state. |
| `attention` | `trading` | Trading Intelligence Checklist: not populated fresh usable count. | Run python -m aureon.autonomous.aureon_trading_intelligence_checklist. |
| `medium` | `trading` | Trading Intelligence Checklist: attention stale or blocked count. | Run python -m aureon.autonomous.aureon_trading_intelligence_checklist. |
| `medium` | `trading` | Exchange Data Capability Matrix: manifest stale. | Run python -m aureon.autonomous.aureon_exchange_data_capability_matrix. |
| `high` | `cognition` | Whole-Mind Wiring: manifest missing. | Run python -m aureon.autonomous.mind_wiring_audit --static --imports --local-services. |
| `high` | `self_knowledge` | File Self-Catalog: manifest missing. | Run python -m aureon.autonomous.aureon_repo_self_catalog. |
| `high` | `self_knowledge` | File Self-Catalog: missing summary cataloged file count. | Run python -m aureon.autonomous.aureon_repo_self_catalog. |
| `high` | `accounting` | Accounting System Registry: manifest missing. | Run the accounting registry/accounts generation workflow in safe manual-filing mode. |
| `high` | `self_improvement` | Capability Growth Loop: manifest missing. | Run python -m aureon.autonomous.aureon_capability_growth_loop. |
| `high` | `self_improvement` | Self-Enhancement Lifecycle: manifest missing. | Run python -m aureon.autonomous.aureon_self_enhancement_lifecycle. |
| `high` | `saas_security` | HNC SaaS Security Blueprint: manifest missing. | Run python -m aureon.autonomous.hnc_saas_security_architect. |
| `high` | `saas_security` | Authorized Attack Lab: manifest missing. | Run the authorized attack lab against owned/local targets only. |
| `medium` | `cognition` | Adaptive Learning History: state file stale. | Start the safe runtime/cognition loop so learning history is repopulated. |
| `medium` | `cognition` | Brain Prediction History: state file stale. | Start the safe runtime/cognition loop so prediction history is repopulated. |
| `medium` | `research` | Miner Brain Knowledge: state file stale. | Run the research/vault ingestion loop to refresh miner knowledge. |
| `medium` | `cognition` | Consciousness State: state file stale. | Start the cognition runtime so consciousness state is updated. |
| `medium` | `runtime` | Local real-time runtime feed is offline or not populated. | Start the safe Aureon runtime/ignition status service, then rerun the observer. |
| `high` | `self_improvement` | Refresh step system_readiness ended with timeout. | Inspect the refresh output, fix the failing generator, and rerun the observer. |

## Status Lines

- Organism pulse: organism_observing_with_blind_spots
- Domains fresh=0 attention=8 stale=6 missing=7
- Blind spots visible: 36
- Runtime feed: offline
- Action mode: safe_observation
- Trading action: blocked by runtime_feed_offline, trading_runtime_not_ready
- Manual boundaries: official filings, payments, credential reveal, and unowned security mutations remain blocked.
- ATTENTION saas_inventory.attention_security_blocker_count: SaaS And Frontend Inventory: attention security blocker count.
- ATTENTION saas_inventory.attention_orphaned_frontend_count: SaaS And Frontend Inventory: attention orphaned frontend count.
- HIGH saas_inventory.attention_missing_supabase_function_call_count: SaaS And Frontend Inventory: attention missing supabase function call count.
- ATTENTION frontend_unification.attention_security_blocker_count: Unified Frontend Plan: attention security blocker count.
- HIGH frontend_unification.attention_missing_screen_capability_count: Unified Frontend Plan: attention missing screen capability count.
- ATTENTION frontend_evolution_queue.attention_blocked_count: Frontend Evolution Queue: attention blocked count.
- ATTENTION frontend_evolution_queue.attention_archive_candidate_count: Frontend Evolution Queue: attention archive candidate count.
- ATTENTION capability_switchboard.attention_blocker_count: Autonomous Capability Switchboard: attention blocker count.

## JSON Snapshot

```json
{
  "action_mode": "safe_observation",
  "attention_domain_count": 8,
  "blind_spot_count": 36,
  "domain_count": 21,
  "failed_refresh_count": 1,
  "fresh_domain_count": 8,
  "frontend_public_manifest_count": 6,
  "high_blind_spot_count": 11,
  "missing_domain_count": 7,
  "refresh_count": 9,
  "runtime_feed_status": "offline",
  "stale_domain_count": 6,
  "trading_action_allowed": false
}
```
