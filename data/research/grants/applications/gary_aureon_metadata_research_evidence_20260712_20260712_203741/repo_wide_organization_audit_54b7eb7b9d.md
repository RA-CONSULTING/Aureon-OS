# Aureon Repo-Wide Organization Audit

- Generated: `2026-05-13T19:40:42.053424+00:00`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`
- Status: `organized_with_attention_items`
- Safety: read-only; no live trading, filing, payment, or external mutation

## Summary

- `total_discovered_files`: 6890
- `recorded_files`: 6890
- `unstaged_file_count`: 1
- `secret_risk_surface_count`: 19
- `runtime_state_file_count`: 153
- `generated_or_cache_file_count`: 923

## Organism Stages

| Stage | Files | Purpose |
| --- | ---: | --- |
| `00_boot_and_runtime_entrypoints` | 313 | Launchers, deployment files, ignition scripts, and operator entrypoints. |
| `01_core_contracts_and_bus` | 63 | Shared organism contracts, safety gates, ThoughtBus, spine, environment, and cognitive runtime glue. |
| `02_cognition_memory_and_models` | 233 | Queen, cognition, LLM, Obsidian, memory, BeingModel, world-sense, and internal reasoning surfaces. |
| `03_autonomy_goals_agents_and_contract_queues` | 1378 | Autonomous goals, self-questioning, agents, work-order queues, task routing, and action hubs. |
| `04_trading_market_execution_and_risk` | 196 | Market data, exchange adapters, trading decision engines, risk sizing, state reconciliation, and live gates. |
| `05_accounting_tax_compliance_and_raw_business_data` | 1200 | Accounting suite, bank feeds, uploads, ledgers, Companies House/HMRC support packs, VAT, CIS, and compliance data. |
| `06_frontend_apis_and_operator_interfaces` | 971 | Frontend UI, public assets, API/server endpoints, Supabase/Netlify surfaces, and command-center screens. |
| `06b_aureon_package_misc_and_compatibility_wrappers` | 425 | Aureon package files that are not in a narrower subsystem folder yet, including compatibility wrappers and package glue. |
| `07_tests_benchmarks_and_validation` | 286 | Unit tests, smoke tests, stress tests, benchmarks, external validation evidence, and verification documents. |
| `08_docs_audits_and_architecture_knowledge` | 643 | Human-readable docs, architecture maps, audits, whitepapers, and repo operating knowledge. |
| `09_runtime_state_logs_and_generated_outputs` | 179 | Runtime logs, generated caches, local state snapshots, and history files that must be preserved but controlled. |
| `10_devops_config_and_repo_metadata` | 36 | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `11_archives_imports_templates_and_legacy_snapshots` | 937 | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `12_root_compatibility_wrappers_and_visual_assets` | 29 | Loose root-level launch helpers, compatibility wrappers, visual assets, and historical top-level utilities retained for compatibility. |
| `99_unstaged_or_needs_owner` | 1 | Needs a named owner/stage before the repo can be considered fully organized. |

## Domains

| Domain | Files |
| --- | ---: |
| `accounting` | 1200 |
| `archive` | 937 |
| `autonomy` | 1378 |
| `boot` | 313 |
| `cognition` | 233 |
| `core` | 488 |
| `devops` | 36 |
| `interface` | 971 |
| `knowledge` | 643 |
| `legacy_root` | 29 |
| `runtime_state` | 179 |
| `trading` | 196 |
| `unknown` | 1 |
| `validation` | 286 |

## Contract Surfaces

| Surface | Status | Stage | Path |
| --- | --- | --- | --- |
| `boot_ignition` | `present` | `00_boot_and_runtime_entrypoints` | `scripts/aureon_ignition.py` |
| `organism_spine` | `present` | `01_core_contracts_and_bus` | `aureon/core/aureon_organism_spine.py` |
| `organism_contracts` | `present` | `01_core_contracts_and_bus` | `aureon/core/organism_contracts.py` |
| `thought_bus` | `present` | `01_core_contracts_and_bus` | `aureon/core/aureon_thought_bus.py` |
| `integrated_cognitive_system` | `present` | `01_core_contracts_and_bus` | `aureon/core/integrated_cognitive_system.py` |
| `mind_wiring_audit` | `present` | `03_autonomy_goals_agents_and_contract_queues` | `aureon/autonomous/mind_wiring_audit.py` |
| `goal_capability_map` | `present` | `03_autonomy_goals_agents_and_contract_queues` | `aureon/autonomous/aureon_goal_capability_map.py` |
| `self_questioning_ai` | `present` | `03_autonomy_goals_agents_and_contract_queues` | `aureon/autonomous/aureon_self_questioning_ai.py` |
| `accounting_bridge` | `present` | `02_cognition_memory_and_models` | `aureon/queen/accounting_context_bridge.py` |
| `accounting_system_registry` | `present` | `05_accounting_tax_compliance_and_raw_business_data` | `Kings_Accounting_Suite/tools/accounting_system_registry.py` |
| `accounting_full_workflow` | `present` | `05_accounting_tax_compliance_and_raw_business_data` | `Kings_Accounting_Suite/tools/end_user_accounting_automation.py` |
| `payer_provenance` | `present` | `05_accounting_tax_compliance_and_raw_business_data` | `Kings_Accounting_Suite/tools/accounting_payer_provenance.py` |
| `frontend_manifest` | `present` | `06_frontend_apis_and_operator_interfaces` | `frontend/package.json` |
| `repo_tests` | `present` | `directory` | `tests` |
| `audit_docs` | `present` | `directory` | `docs/audits` |

## Attention Items

- 1 files do not map to a known organism stage.
- 19 credential/secret-risk surfaces exist; audit recorded paths only and did not read values.
- 19 runtime/state files sit outside the runtime-state stage.
- 17 generated/cache outputs sit inside source stages.

## Unstaged Path Samples

- `AUREON_PRODUCTION_LIVE.cmd`

## Secret-Risk Surface Samples

- `.env`
- `.env1.txt`
- `aureon_launcher/credentials.py`
- `frontend/src/components/APIKeyManager.tsx`
- `frontend/src/components/auth/APIKeySecurityGuide.tsx`
- `frontend/src/components/auth/PasswordStrengthIndicator.tsx`
- `frontend/src/components/BinanceCredentialsAdmin.tsx`
- `frontend/src/components/BinanceCredentialsSettings.tsx`
- `frontend/src/components/CredentialManager.tsx`
- `frontend/src/components/ExchangeCredentialsManager.tsx`
- `frontend/src/components/warroom/CredentialStatusPanel.tsx`
- `frontend/src/hooks/useBinanceCredentials.ts`
- `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon_launcher/credentials.py`
- `scripts/diagnostics/diagnose_api_key.py`
- `scripts/traders/validateSecrets.ts`
- `supabase/functions/get-binance-credentials/index.ts`
- `supabase/functions/store-binance-credentials/index.ts`
- `supabase/functions/update-bot-credentials/index.ts`
- `supabase/functions/update-user-credentials/index.ts`

## Runtime State Outside Runtime Stage Samples

- `aureon/data_feeds/thoughts.jsonl`
- `brain_predictions_history.json`
- `docs/audits/aureon_harmonic_affect_state.json`
- `docs/research/research_history.json`
- `frontend/dist/aureon_harmonic_affect_state.json`
- `frontend/public/aureon_harmonic_affect_state.json`
- `frontend/vite-8081.log`
- `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/adaptive_learning_history.json`
- `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/brain_predictions_history.json`
- `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/docs/research/research_history.json`
- `Kings_Accounting_Suite/data/king_audit.jsonl`
- `Kings_Accounting_Suite/data/king_state.json`
- `kraken_fee_tracker_state.json`
- `kraken_margin_army_state.json`
- `public/consciousness_state.json`
- `public/hive_state.json`
- `queen_warrior_path_state.json`
- `real_portfolio_state.json`
- `tests/fixtures/test_thoughts.jsonl`

## Generated Output In Source Stage Samples

- `frontend/dist/assets/index-Ccs5pZ3J.css`
- `frontend/dist/assets/index-D70gORz6.js`
- `frontend/dist/aureon_autonomous_capability_switchboard.json`
- `frontend/dist/aureon_cognitive_trade_evidence.json`
- `frontend/dist/aureon_frontend_evolution_queue.json`
- `frontend/dist/aureon_frontend_unification_plan.json`
- `frontend/dist/aureon_frontend_work_order_execution.json`
- `frontend/dist/aureon_harmonic_affect_state.json`
- `frontend/dist/aureon_hnc_cognitive_proof.json`
- `frontend/dist/aureon_live_cognition_benchmark.json`
- `frontend/dist/aureon_operational_ui_spec.json`
- `frontend/dist/aureon_organism_runtime_status.json`
- `frontend/dist/aureon_saas_system_inventory.json`
- `frontend/dist/aureon_unified_exchange_execution_results.json`
- `frontend/dist/aureon_unified_shadow_trade_report.json`
- `frontend/dist/aureon_wake_up_manifest.json`
- `frontend/dist/index.html`

## Staging Checklist

- Keep `scripts/aureon_ignition.py` as the single live boot entrypoint and keep audit-only checks separate.
- Keep core contracts, ThoughtBus, runtime safety, and organism spine in `aureon/core`.
- Keep accounting/code-generated compliance packs under `Kings_Accounting_Suite` and business evidence under explicit raw-data roots.
- Keep runtime state, generated logs, and giant memory files in controlled state/output locations.
- Assign every remaining root-level helper or historical artifact to a stage, archive, or documented compatibility wrapper.
- Do not move `.env`, API keys, portfolio state, exchange state, accounting evidence, or generated filing packs automatically.

## Notes

- Read-only organization audit: no files are moved, deleted, submitted, paid, or traded.
- The audit stages code, data, generated outputs, state, docs, tests, and interfaces into a single organism map.
- Secret-risk files are identified by path/name only; values are not read into the report.
- The legacy 'bussiness accounts' data root is preserved and explicitly mapped as business/accounting evidence.
- Official filing, payments, and live exchange mutation remain outside this organization audit.
