# Aureon Repo Self-Catalog

- Generated: `2026-05-13T19:41:25.603959+00:00`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`
- Status: `catalog_complete_with_attention_items`
- Safety: read-only; secret contents excluded; no live orders, filing, payment, or execution

## Summary

- `total_project_files_discovered`: 6890
- `cataloged_file_count`: 6890
- `excluded_infrastructure_root_count`: 75
- `secret_metadata_only_count`: 19
- `python_symbol_probe_count`: 2103
- `coverage_policy`: Every project file outside dependency/cache/virtualenv/git internals is labelled; excluded infrastructure roots are recorded explicitly.

## What Aureon Can Know About Itself

- Every catalogued project file has an owner subsystem, organism stage, domain, kind, role, safety flags, and next action.
- Python files include module names, top-level classes/functions/imports where safe to inspect.
- Secret and environment files are visible to the self-map as metadata only, not copied into memory.
- Vault/LLM context is provided as compact per-file `llm_context` strings in the JSON manifest.

## Subsystems

| Subsystem | Files |
| --- | ---: |
| `accounting_tax_and_business_data` | 1200 |
| `archive` | 916 |
| `autonomy` | 8 |
| `autonomy_and_self_management` | 1364 |
| `boot` | 22 |
| `boot_devops_and_deployment` | 284 |
| `cognition` | 44 |
| `cognitive_queen_brain` | 119 |
| `core` | 485 |
| `devops` | 32 |
| `interface` | 25 |
| `knowledge_and_documentation` | 684 |
| `legacy_root` | 27 |
| `llm_reasoning` | 12 |
| `operator_interface_and_api` | 946 |
| `runtime_state` | 178 |
| `trading` | 16 |
| `trading_and_market_risk` | 180 |
| `unknown` | 1 |
| `validation` | 2 |
| `validation_and_benchmarking` | 284 |
| `vault_memory` | 61 |

## File Kinds

| Kind | Files |
| --- | ---: |
| `archive_or_bundle` | 24 |
| `audit_manifest_or_index` | 41 |
| `configuration` | 20 |
| `data_or_business_evidence` | 170 |
| `dependency_or_deployment_config` | 16 |
| `documentation_or_report` | 1829 |
| `frontend_source` | 842 |
| `generated_output_or_cache` | 903 |
| `local_secret_or_environment_config` | 2 |
| `misc_project_file` | 235 |
| `python_source` | 2067 |
| `runtime_state_or_memory` | 152 |
| `structured_manifest_or_memory` | 166 |
| `test_or_benchmark` | 298 |
| `visual_asset` | 125 |

## Top-Level Directory Map

| Directory | Files | Dominant subsystem | Dominant kind |
| --- | ---: | --- | --- |
| `.claude` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `.clawdhub` | 1 | `devops` | `configuration` |
| `.do` | 1 | `boot` | `configuration` |
| `.dockerignore` | 1 | `devops` | `misc_project_file` |
| `.env` | 1 | `devops` | `local_secret_or_environment_config` |
| `.env.example` | 1 | `devops` | `misc_project_file` |
| `.env1.txt` | 1 | `knowledge_and_documentation` | `local_secret_or_environment_config` |
| `.github` | 4 | `knowledge_and_documentation` | `documentation_or_report` |
| `.gitignore` | 1 | `devops` | `misc_project_file` |
| `.obsidian` | 15 | `vault_memory` | `documentation_or_report` |
| `accounting` | 2 | `accounting_tax_and_business_data` | `data_or_business_evidence` |
| `adaptive_learning_history.json` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `antarctic_4d_panels.png` | 1 | `legacy_root` | `visual_asset` |
| `api` | 1 | `operator_interface_and_api` | `frontend_source` |
| `app.yaml` | 1 | `boot` | `configuration` |
| `archive` | 24 | `archive` | `archive_or_bundle` |
| `AUDIT_SUMMARY.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `aureon` | 932 | `core` | `python_source` |
| `AUREON Design System.zip` | 1 | `archive` | `archive_or_bundle` |
| `aureon_alpaca_scanner_bridge.py` | 1 | `trading` | `python_source` |
| `aureon_animal_momentum_scanners.py` | 1 | `legacy_root` | `python_source` |
| `aureon_baton_link.py` | 1 | `legacy_root` | `python_source` |
| `aureon_bot_intelligence_profiler.py` | 1 | `legacy_root` | `python_source` |
| `aureon_chirp_bus.py` | 1 | `legacy_root` | `python_source` |
| `aureon_elephant_learning.py` | 1 | `legacy_root` | `python_source` |
| `aureon_harmonic_seed.py` | 1 | `legacy_root` | `python_source` |
| `aureon_hft_harmonic_mycelium.py` | 1 | `legacy_root` | `python_source` |
| `aureon_launcher` | 7 | `boot` | `python_source` |
| `aureon_lighthouse.py` | 1 | `legacy_root` | `python_source` |
| `aureon_multi_exchange.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `aureon_mycelium.py` | 1 | `legacy_root` | `python_source` |
| `aureon_nexus.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `aureon_obsidian_filter.py` | 1 | `cognition` | `python_source` |
| `aureon_probability_nexus.py` | 1 | `legacy_root` | `python_source` |
| `AUREON_PRODUCTION_LIVE.cmd` | 1 | `unknown` | `misc_project_file` |
| `aureon_thought_bus.py` | 1 | `core` | `python_source` |
| `AUREON_WAKE_UP_FULL_AUTONOMOUS.cmd` | 1 | `autonomy` | `misc_project_file` |
| `AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` | 1 | `autonomy` | `misc_project_file` |
| `aureon_whale_behavior_predictor.py` | 1 | `legacy_root` | `python_source` |
| `autonomy` | 1293 | `autonomy_and_self_management` | `documentation_or_report` |
| `autonomy_feedback_loop.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `boot_result.txt` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `bot_army_catalog.json` | 1 | `legacy_root` | `structured_manifest_or_memory` |
| `bot_shape_snapshot.json` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `brain_predictions_history.json` | 1 | `cognition` | `runtime_state_or_memory` |
| `bussiness accounts` | 57 | `accounting_tax_and_business_data` | `data_or_business_evidence` |
| `CAPABILITIES.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `capital_diag.py` | 1 | `legacy_root` | `python_source` |
| `capital_hft_benchmark.json` | 1 | `validation` | `structured_manifest_or_memory` |
| `capital_hft_stress.py` | 1 | `validation` | `python_source` |
| `CLAUDE.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `cli` | 6 | `devops` | `python_source` |
| `conftest.py` | 1 | `legacy_root` | `python_source` |
| `data` | 71 | `runtime_state` | `structured_manifest_or_memory` |
| `DATA_FLOW.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `deploy` | 12 | `boot_devops_and_deployment` | `misc_project_file` |
| `docker-compose.autonomous.yml` | 1 | `boot` | `configuration` |
| `docker-compose.yml` | 1 | `boot` | `dependency_or_deployment_config` |
| `Dockerfile` | 1 | `boot` | `dependency_or_deployment_config` |
| `Dockerfile.ephemeris` | 1 | `legacy_root` | `misc_project_file` |
| `docs` | 381 | `knowledge_and_documentation` | `documentation_or_report` |
| `EPAS_Unified_Architecture_WhitePaper_Lec.docx` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `eslint.config.js` | 1 | `interface` | `frontend_source` |
| `frontend` | 717 | `operator_interface_and_api` | `frontend_source` |
| `functions` | 1 | `operator_interface_and_api` | `frontend_source` |
| `global_financial_state.json` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `harmonic_cache` | 2 | `runtime_state` | `runtime_state_or_memory` |
| `headless_watch.py` | 1 | `legacy_root` | `python_source` |
| `HNC_Grand_Unified_Framework_Leckey_2026.docx` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `imports` | 1184 | `archive` | `python_source` |
| `INDEX.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `integrations_audit.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `Kings_Accounting_Suite` | 1138 | `accounting_tax_and_business_data` | `generated_output_or_cache` |
| `kraken_fee_tracker_state.json` | 1 | `trading` | `runtime_state_or_memory` |
| `kraken_margin_army_results.json` | 1 | `trading` | `structured_manifest_or_memory` |
| `kraken_margin_army_state.json` | 1 | `trading` | `runtime_state_or_memory` |
| `lattice_simulation.png` | 1 | `legacy_root` | `visual_asset` |
| `LICENSE` | 1 | `legacy_root` | `misc_project_file` |
| `lighthouse_metrics.py` | 1 | `legacy_root` | `python_source` |
| `LIVE_PROOF.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `logs` | 35 | `runtime_state` | `runtime_state_or_memory` |
| `LSSP_Preregistration_Leckey_2026.pdf` | 1 | `knowledge_and_documentation` | `data_or_business_evidence` |
| `LSSP_preregistration_v1.0.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `lyra_resonance.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `margin_goal_proof.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `memory` | 1 | `vault_memory` | `structured_manifest_or_memory` |
| `miner_brain.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `miner_brain_knowledge.json` | 1 | `cognition` | `runtime_state_or_memory` |
| `mountain_climbing_state.json` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `multi_battlefront.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `multiverse_live.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `netlify` | 1 | `operator_interface_and_api` | `frontend_source` |
| `nexus_learning_state.json` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `organism-runtime-observer.err.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `organism-runtime-observer.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `packaging` | 2 | `boot_devops_and_deployment` | `python_source` |
| `PEFCphiS_Leckey_2026.pdf` | 1 | `knowledge_and_documentation` | `data_or_business_evidence` |
| `prime_sentinel_decree.py` | 1 | `legacy_root` | `python_source` |
| `probability_intelligence_matrix.py` | 1 | `legacy_root` | `python_source` |
| `probability_ultimate_intelligence.py` | 1 | `legacy_root` | `python_source` |
| `Procfile` | 1 | `boot` | `misc_project_file` |
| `production` | 15 | `devops` | `misc_project_file` |
| `public` | 59 | `operator_interface_and_api` | `structured_manifest_or_memory` |
| `qgita.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `queen_backups` | 20 | `cognition` | `misc_project_file` |
| `queen_elephant_memory.json` | 1 | `cognition` | `runtime_state_or_memory` |
| `queen_exchange_autonomy.json` | 1 | `cognition` | `structured_manifest_or_memory` |
| `queen_neuron_v2_weights.json` | 1 | `cognition` | `structured_manifest_or_memory` |
| `queen_warrior_path_state.json` | 1 | `cognition` | `runtime_state_or_memory` |
| `QUICK_START.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `README.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `real_portfolio_state.json` | 1 | `trading` | `runtime_state_or_memory` |
| `requirements.txt` | 1 | `knowledge_and_documentation` | `dependency_or_deployment_config` |
| `run_dj_resonance.py` | 1 | `legacy_root` | `python_source` |
| `run_hnc_live.py` | 1 | `legacy_root` | `python_source` |
| `run_integrated_cognitive_system.py` | 1 | `cognition` | `python_source` |
| `RUNNING.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `runtime.txt` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `scripts` | 270 | `boot_devops_and_deployment` | `python_source` |
| `seer_visions.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `server` | 7 | `operator_interface_and_api` | `frontend_source` |
| `skills` | 12 | `autonomy` | `documentation_or_report` |
| `state` | 46 | `runtime_state` | `runtime_state_or_memory` |
| `supabase` | 160 | `operator_interface_and_api` | `frontend_source` |
| `supervisord.conf` | 1 | `boot` | `configuration` |
| `SWOT_ANALYSIS.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `SYSTEM_OVERVIEW.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `templates` | 6 | `interface` | `frontend_source` |
| `tests` | 270 | `validation_and_benchmarking` | `test_or_benchmark` |
| `thoughts.jsonl` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `tools` | 5 | `devops` | `python_source` |
| `trade_audit.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `trade_logger.log` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `Untitled.canvas` | 1 | `legacy_root` | `misc_project_file` |
| `uploads` | 3 | `accounting_tax_and_business_data` | `data_or_business_evidence` |
| `use_cases.py` | 1 | `legacy_root` | `python_source` |
| `VERIFICATION AND VALIDATION` | 14 | `validation_and_benchmarking` | `data_or_business_evidence` |
| `watch_log.txt` | 1 | `knowledge_and_documentation` | `documentation_or_report` |
| `wisdom_data` | 12 | `cognition` | `structured_manifest_or_memory` |
| `ws_cache` | 1 | `runtime_state` | `runtime_state_or_memory` |
| `XIRX_session_codex.md` | 1 | `knowledge_and_documentation` | `documentation_or_report` |

## Directory-Level Infrastructure

- `.git`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `.pytest_cache`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `.venv`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/alignment/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/analytics/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/atn/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/autonomous/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/autonomous/vm_control/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/bots/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/bots_intelligence/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/bridges/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/code_architect/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/cognition/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/command_centers/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/conversion/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/core/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/data_feeds/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/decoders/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/exchanges/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/harmonic/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/inhouse_ai/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/integrations/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/integrations/obsidian/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/integrations/ollama/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/integrations/world_data/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/intelligence/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/miner/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/monitors/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/observer/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/portfolio/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/queen/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/s51/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/scanners/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/simulation/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/strategies/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/swarm_motion/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/trading/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/utils/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/vault/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/vault/ui/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/vault/voice/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `aureon/wisdom/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `frontend/node_modules`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/.pytest_cache`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/aureon_systems/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/aureon_systems/auris/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/cash_flow/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/core/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/ledger/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/show_tools/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/tests/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `Kings_Accounting_Suite/tools/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/diagnostics/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/python/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/reports/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/runners/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `scripts/validation/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `server/node_modules`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `skills/moltbook-registry/node_modules`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/benchmark/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/benchmarks/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/capability/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/cognition/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/harmonic/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/hyper/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/integrations/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/mega/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/observer/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/stress/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/ultimate/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.
- `tests/vault/__pycache__`: Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.

## File Label Samples

| File | Subsystem | Kind | Domain | Role |
| --- | --- | --- | --- | --- |
| `.claude/agents/dr-auris-throne.md` | `knowledge_and_documentation` | `documentation_or_report` | `vault_memory` | Knowledge/report document for auris throne. |
| `.clawdhub/lock.json` | `devops` | `configuration` | `devops` | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `.do/app.yaml` | `boot` | `configuration` | `devops` | Launchers, deployment files, ignition scripts, and operator entrypoints. |
| `.dockerignore` | `devops` | `misc_project_file` | `devops` | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `.env` | `devops` | `local_secret_or_environment_config` | `devops` | Local environment/secret surface; catalog records metadata only and never stores values. |
| `.env.example` | `devops` | `misc_project_file` | `devops` | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `.env1.txt` | `knowledge_and_documentation` | `local_secret_or_environment_config` | `vault_memory` | Local environment/secret surface; catalog records metadata only and never stores values. |
| `.github/copilot-instructions.md` | `knowledge_and_documentation` | `documentation_or_report` | `vault_memory` | Knowledge/report document for copilot instructions. |
| `.github/ISSUE_TEMPLATE/feature_request.md` | `knowledge_and_documentation` | `documentation_or_report` | `vault_memory` | Knowledge/report document for feature request. |
| `.github/workflows/build-windows-release.yml` | `boot_devops_and_deployment` | `configuration` | `frontend` | Launchers, deployment files, ignition scripts, and operator entrypoints. |
| `.github/workflows/main_ci.yml` | `boot_devops_and_deployment` | `configuration` | `devops` | Launchers, deployment files, ignition scripts, and operator entrypoints. |
| `.gitignore` | `devops` | `misc_project_file` | `devops` | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `.obsidian/app.json` | `vault_memory` | `structured_manifest_or_memory` | `cognition` | Structured manifest, registry, or memory surface used by vault_memory. |
| `.obsidian/appearance.json` | `vault_memory` | `structured_manifest_or_memory` | `cognition` | Structured manifest, registry, or memory surface used by vault_memory. |
| `.obsidian/Aureon Self Understanding/aureon_autonomous_capability_switchboard.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for autonomous capability switchboard. |
| `.obsidian/Aureon Self Understanding/aureon_frontend_evolution_queue.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for evolution frontend queue. |
| `.obsidian/Aureon Self Understanding/aureon_frontend_unification_plan.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for frontend plan unification. |
| `.obsidian/Aureon Self Understanding/aureon_organism_runtime_status.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for organism runtime status. |
| `.obsidian/Aureon Self Understanding/aureon_saas_system_inventory.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for inventory saas system. |
| `.obsidian/Aureon Self Understanding/capability_growth_loop.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for capability growth loop. |
| `.obsidian/Aureon Self Understanding/hnc_authorized_attack_lab.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for attack authorized hnc lab. |
| `.obsidian/Aureon Self Understanding/hnc_saas_cognitive_bridge.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for bridge cognitive hnc saas. |
| `.obsidian/Aureon Self Understanding/hnc_saas_security_blueprint.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for blueprint hnc saas security. |
| `.obsidian/Aureon Self Understanding/repo_self_catalog.md` | `vault_memory` | `documentation_or_report` | `cognition` | Knowledge/report document for catalog repo self. |
| `.obsidian/core-plugins.json` | `vault_memory` | `structured_manifest_or_memory` | `cognition` | Structured manifest, registry, or memory surface used by vault_memory. |
| `.obsidian/graph.json` | `vault_memory` | `structured_manifest_or_memory` | `cognition` | Structured manifest, registry, or memory surface used by vault_memory. |
| `.obsidian/workspace.json` | `vault_memory` | `structured_manifest_or_memory` | `cognition` | Structured manifest, registry, or memory surface used by vault_memory. |
| `accounting/full_accounts_index.md` | `accounting_tax_and_business_data` | `data_or_business_evidence` | `accounting` | Business, accounting, or structured data evidence used by accounting_tax_and_business_data. |
| `accounting/workflows/NI696693_2024-05-01_to_2025-04-30.md` | `accounting_tax_and_business_data` | `data_or_business_evidence` | `accounting` | Business, accounting, or structured data evidence used by accounting_tax_and_business_data. |
| `adaptive_learning_history.json` | `runtime_state` | `runtime_state_or_memory` | `vault_memory` | Runtime state or long-memory file preserved for recall/reconciliation by runtime_state. |
| `antarctic_4d_panels.png` | `legacy_root` | `visual_asset` | `legacy_root` | Loose root-level launch helpers, compatibility wrappers, visual assets, and historical top-level utilities retained for compatibility. |
| `api/rss.ts` | `operator_interface_and_api` | `frontend_source` | `frontend` | Frontend/operator interface asset for rss. |
| `app.yaml` | `boot` | `configuration` | `devops` | Launchers, deployment files, ignition scripts, and operator entrypoints. |
| `archive/Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/AUREON-QUANTUM-TRADING-SYSTEM-AQTS--main.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/aureoninstitute-uk-deploy.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/cost_basis_history.json.backup` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/crash_log.txt` | `knowledge_and_documentation` | `documentation_or_report` | `cognition` | Knowledge/report document for crash log. |
| `archive/earth-live-data-1 (10).zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/earth-live-data-1.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/earth-live-data-3 (7).zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/earth-live-data-3 (8).zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/FINAL_LOSS_PREVENTION_FIX.patch` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/Kimi_Agent_Aureon系统集成.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/kraken_margin_penny_trader.py.bak` | `archive` | `misc_project_file` | `trading` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/NEXUS-LIVE-FEED--main.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/nohup.out` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/orca_complete_kill_cycle.py.backup` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/orca_complete_kill_cycle.py.working` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/orca_live_trading.log.pre_test_20260218_222402` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/queen_eternal_state.json.bak` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/RAINBOW-main-extracted/.github/workflows/azure-webapps-node.yml` | `devops` | `configuration` | `cognition` | Git, Docker, linting, dependency, deployment, and local environment metadata. |
| `archive/RAINBOW-main-extracted/earth-live-data-3 (9).zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/RAINBOW-main-extracted/README.md` | `knowledge_and_documentation` | `documentation_or_report` | `cognition` | Knowledge/report document for readme. |
| `archive/RAINBOW-main.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/rate_limiter_v2.py.backup` | `archive` | `misc_project_file` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `archive/VERIFICATION AND VALIDATION-20250916T213737Z-1-001.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `AUDIT_SUMMARY.md` | `knowledge_and_documentation` | `documentation_or_report` | `vault_memory` | Knowledge/report document for audit summary. |
| `AUREON Design System.zip` | `archive` | `archive_or_bundle` | `cognition` | Historical imports, legacy snapshots, templates, design assets, and archived recovery materials. |
| `aureon/__init__.py` | `core` | `python_source` | `devops` | AUREON TRADING SYSTEM ===================== The Unified Quantum Trading System From Atom to Multiverse 🌌 Core Modules: - aureon_nexus: The central nervous system connecting all modules - aureon_omega: Complete Ω equation system - aureon_infinite: 10-9-1 Queen Hive model - aureon_multiverse: Atom to Multiverse ladder - aureon_piano: Multi-coin harmonic tra... |
| `aureon/_path_setup.py` | `core` | `python_source` | `devops` | Import this module early in entry-point scripts to ensure all aureon/ subdirectories are on sys.path. This keeps bare module-name imports working after the repository reorganisation. Usage (at the top of a runner script):: import aureon._path_setup # noqa: F401 |
| `aureon/alignment/__init__.py` | `cognition` | `python_source` | `cognition` | Aureon Pillar Alignment — The Six Singing as One ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ "When the many become one, the Lighthouse burns." — Aureon White Paper This package aligns the six pillars of the Aureon ecosystem into one harmonic voice. Each pillar speaks at its own Solfeggio frequency: Nexus 432 Hz — central... |
| `aureon/alignment/harmonic_resonance.py` | `cognition` | `python_source` | `cognition` | HarmonicResonance — the math of alignment ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Computes how "aligned" a set of pillar signals is. Alignment has four components, each in [0, 1]: 1. signal_consensus — fraction agreeing on direction (BUY/SELL/NEUTRAL) 2. harmonic_lock — how cleanly each frequency relates to the funda... |
| `aureon/alignment/pillar_alignment.py` | `cognition` | `python_source` | `cognition` | PillarAlignment — The Six Singing as One ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Runs all six Aureon pillar agents in parallel on a shared context, measures their harmonic alignment (signal consensus + frequency lock + phase coherence + mean Γ), and emits a unified alignment signal. Usage: from aureon.alignment impor... |
| `aureon/alignment/unified_directive.py` | `cognition` | `python_source` | `cognition` | UnifiedHarmonicDirective — The Master Directive ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ The final mile of alignment: assembles a single MasterDirective from every sovereign layer of the Aureon system: ┌──────────────────────────────────────────────────────────┐ │ UnifiedHarmonicDirective │ │ │ │ Pillars (6) + Love St... |
| `aureon/analytics/__init__.py` | `core` | `python_source` | `devops` | aureon.analytics — Analysis and forensics suite. Provides backtesting harnesses, whale-activity analysis, money-flow trackers, market profilers, and bot-census tools. Feeds aggregated insights into intelligence/ for model training and into strategies/ for strategy refinement and validation. |
| `aureon/analytics/analyze_actual_vs_expected_costs.py` | `core` | `python_source` | `devops` | Analyze actual vs expected trading costs to find the math error. This script retrieves recent trade fills from Alpaca and compares: 1. Expected profit (from pre-execution gate) 2. Actual costs (fees + slippage + price movement) 3. Net result (actual P&L) Goal: Find WHERE the $0.71 loss came from and FIX the cost model. |
| `aureon/analytics/analyze_portfolio_stats.py` | `core` | `python_source` | `trading` | Analyze full portfolio win rate (standalone CLI script). |
| `aureon/analytics/aureon_complete_profiler_integration.py` | `core` | `python_source` | `devops` | 🎯 AUREON COMPLETE PROFILER INTEGRATION 🎯 ========================================== PULLS TOGETHER ALL SYSTEMS: ├─ Bot Shape Scanner (detects bots with frequencies) ├─ Firm Intelligence Profiler (attributes to trading firms) ├─ Whale Profiler System (tracks full profiles) ├─ Moby Dick Whale Hunter (predicts next moves) └─ Sonar Scanner (real-time monitori... |
| `aureon/analytics/aureon_deep_money_flow_analyzer.py` | `core` | `python_source` | `devops` | AUREON DEEP MONEY FLOW ANALYZER =============================== Ultimate system that wires ALL intelligence together: - Historical manipulation events with dates/times - Bot activity correlated to money flows - Where the money went, who moved it - Short-term and long-term planetary effects - Queen + Enigma + Mycelium deep learning integration THE COMPLETE... |
| `aureon/analytics/aureon_historical_backtest.py` | `core` | `python_source` | `validation` | ╔══════════════════════════════════════════════════════════════════════════════════════╗ ║ ║ ║ 📊 AUREON HISTORICAL BACKTEST ENGINE 📊 ║ ║ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ║ ║ ║ ║ 1 YEAR GLOBAL CRYPTO MARKET BACKTEST ║ ║ ║ ║ DATA SOURCES: ║ ║ • Coinbase API (PUBLIC - no auth needed) ║ ║ • Binance API (PUBLIC - no auth needed) ║ ║ • LOCAL CA... |
| `aureon/analytics/aureon_historical_bot_census.py` | `core` | `python_source` | `devops` | 📜 AUREON HISTORICAL BOT CENSUS & EVOLUTION TRACKER 📜 ═══════════════════════════════════════════════════════════════════════════════ Scans the last 4 years of market history to identify, label, and TRACK the growth of algorithmic actors. Features: - Fetches 4 years of 1h candles (Klines) from Binance. - Performs FFT Spectral Analysis to find dominant cycl... |
| `aureon/analytics/aureon_historical_knowledge_ingest.py` | `core` | `python_source` | `vault_memory` | 📚🧠 AUREON HISTORICAL KNOWLEDGE INGESTION SYSTEM 🧠📚 ====================================================== "Using her learning systems to scan news wiki and coin base for all historical data" This module: 1. 🪙 SCANS COINBASE: Fetches 1 year of hourly data to find "Golden Hours" and "Market Rhythms". 2. 📰 SCANS WIKI/NEWS: Ingests historical market events (H... |
| `aureon/analytics/aureon_historical_manipulation_hunter.py` | `core` | `python_source` | `devops` | ╔══════════════════════════════════════════════════════════════════════════════════════╗ ║ ║ ║ 📜⚔️ AUREON HISTORICAL MANIPULATION HUNTER ⚔️📜 ║ ║ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ║ ║ ║ ║ TRACK COORDINATION ACROSS DECADES - HISTORY IS ON OUR SIDE ║ ║ ║ ║ "Those who cannot remember the past are condemned to repeat it" ║ ║ - George Santayan... |
| `aureon/analytics/aureon_lighthouse.py` | `core` | `python_source` | `devops` | ╔══════════════════════════════════════════════════════════════════════════════════════╗ ║ ║ ║ 🏮 AUREON LIGHTHOUSE - PATTERN DETECTOR 🏮 ║ ║ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ║ ║ ║ ║ Watches the evolving harmonic wave model for patterns & anomalies ║ ║ ║ ║ DETECTS: ║ ║ • Phase Resets (sudden frequency shifts) ║ ║ • Coherence Collapses (mark... |
| `aureon/analytics/aureon_live_whale_profiler.py` | `core` | `python_source` | `devops` | 🔴 AUREON LIVE WHALE PROFILER 🔴 ================================= LIVE INTEGRATION of all profiling systems: ├─ Reads Bot Shape Scanner detections ├─ Creates/updates whale profiles in real-time ├─ Tracks 24-hour activity ├─ Generates complete intelligence reports └─ Displays active whales with full attribution DISPLAYS: ┌───────────────────────────────────... |
| `aureon/analytics/aureon_moby_dick_whale_hunter.py` | `core` | `python_source` | `devops` | 🐋⚔️ AUREON MOBY DICK WHALE HUNTER ⚔️🐋 ========================================== CAPTAIN AHAB'S LEGENDARY WHALE HUNTING STRATEGIES Applied to Market Whales and Algorithmic Traders From Herman Melville's Moby-Dick (1851): "He piled upon the whale's white hump the sum of all the general rage and hate felt by his whole race from Adam down; and then, as if hi... |
| `aureon/analytics/aureon_rising_star_logic.py` | `core` | `python_source` | `devops` | 🌟 AUREON RISING STAR LOGIC - Multi-Intelligence Trade Selection ═══════════════════════════════════════════════════════════════════════════════ 4-STAGE FILTERING SYSTEM: Stage 1: SCAN - Map entire market using ALL intelligence systems - Quantum scoring (luck, inception, phantom, etc.) - Probability Ultimate Intelligence (95% accuracy) - Wave Scanner momen... |
| `aureon/analytics/aureon_russian_doll_analytics.py` | `core` | `python_source` | `devops` | Aureon Russian Doll Analytics - Fractal Measurement System =========================================================== Three-level nested analytics architecture: - QUEEN (Macro): Global market state, cross-exchange coherence - HIVE (System): Per-exchange, per-validator analytics - BEE (Micro): Individual symbol/trade-level measurements Data flows A→Z (top... |
| `aureon/analytics/aureon_whale_agent.py` | `core` | `python_source` | `autonomy` | Run all whale subsystem components (orderbook analyzer, pattern mapper, predictor). Usage: python aureon_whale_agent.py BTC/USD ETH/USD --interval 1.0 |
| ... | ... | ... | ... | 6810 more labels in JSON/CSV |

## Vault Memory

- `status`: `written`
- `note_path`: `C:\Users\user\aureon-trading-integrated-main-20260508\.obsidian\Aureon Self Understanding\repo_self_catalog.md`
- `topic`: `repo.self_catalog.ready`
- `llm_context_available`: `True`
- `compact_manifest_for_prompts`: `Use compact() or each label.llm_context; do not prompt with secret file contents.`

## Notes

- Read-only self-catalog: no execution, no trading, no official filing, no payment, and no external mutation.
- Secret-risk files are catalogued by path and metadata only; values are never copied into JSON, CSV, Markdown, vault notes, or LLM context.
- Runtime memories and large logs are labelled without requiring full content ingestion.
- Dependency, virtualenv, git, and cache roots are directory-level infrastructure, not organism decision logic.
- The JSON and CSV manifests are the file-by-file source of truth; the Markdown and vault note are compact human/LLM indexes.
