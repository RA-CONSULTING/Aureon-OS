# Aureon Ignition Live Boot Audit

- Generated: `2026-05-15T15:28:42.762491`
- Command: `python scripts/aureon_ignition.py --live`
- Mode: `LIVE`
- Ready: `False`
- Real orders allowed by runtime: `True`
- Loaded env files: `C:\Users\user\aureon-trading-integrated-main-20260508\.env`
- Accounting status: `completed`; manual filing required: `True`; bank sources: `36`; unique bank rows: `1052`; accounting tools: `99`; ready: `True`; statutory outputs: `64`; raw files: `60`; swarm files: `0`; swarm consensus: `unknown`

## Checks

| Check | Required | Status | Detail |
| --- | --- | --- | --- |
| `live_order_runtime` | `True` | `PASS` | real_orders_allowed=True |
| `audit_mode_off` | `True` | `PASS` | AUREON_AUDIT_MODE=0 |
| `dry_run_off` | `True` | `PASS` | DRY_RUN=0/AUREON_DRY_RUN=0 |
| `exchange_dry_run_off` | `True` | `PASS` | Kraken/Binance/Alpaca dry-run flags false |
| `confirm_live_set` | `True` | `PASS` | CONFIRM_LIVE=yes |
| `llm_live_capabilities_on` | `True` | `PASS` | LLM may reason with live state |
| `cognitive_live_mode_on` | `True` | `PASS` | cognitive systems may reason with live state |
| `llm_no_direct_order_authority` | `True` | `PASS` | LLM cannot directly place orders |
| `cognitive_no_direct_order_authority` | `True` | `PASS` | cognitive layer cannot bypass execution gates |
| `kraken_credentials_present` | `False` | `PASS` | KRAKEN_API_KEY=set, KRAKEN_API_SECRET=set; loaded_env=C:\Users\user\aureon-trading-integrated-main-20260508\.env |
| `binance_credentials_present` | `False` | `PASS` | BINANCE_API_KEY=set, BINANCE_API_SECRET=set; loaded_env=C:\Users\user\aureon-trading-integrated-main-20260508\.env |
| `alpaca_credentials_present` | `False` | `PASS` | ALPACA_API_KEY=set, ALPACA_SECRET_KEY=set; loaded_env=C:\Users\user\aureon-trading-integrated-main-20260508\.env |
| `capital_credentials_present` | `False` | `PASS` | CAPITAL_API_KEY=set, CAPITAL_IDENTIFIER=set, CAPITAL_PASSWORD=set; loaded_env=C:\Users\user\aureon-trading-integrated-main-20260508\.env |
| `import:runtime_safety` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\core\aureon_runtime_safety.py |
| `import:queen_layer` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\queen\queen_layer.py |
| `import:goal_capability_map` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\autonomous\aureon_goal_capability_map.py |
| `import:self_questioning_ai` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\autonomous\aureon_self_questioning_ai.py |
| `import:capability_growth_loop` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\autonomous\aureon_capability_growth_loop.py |
| `import:accounting_context_bridge` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\queen\accounting_context_bridge.py |
| `import:dynamic_margin_sizer` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\trading\dynamic_margin_sizer.py |
| `import:temporal_trade_cognition` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\trading\temporal_trade_cognition.py |
| `import:unified_margin_brain` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\trading\unified_margin_brain.py |
| `import:micro_profit_labyrinth` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\aureon\trading\micro_profit_labyrinth.py |
| `accounting_suite_path` | `True` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite |
| `package:reportlab` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\.venv\Lib\site-packages\reportlab\__init__.py |
| `package:pypdf` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\.venv\Lib\site-packages\pypdf\__init__.py |
| `package:openpyxl` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\.venv\Lib\site-packages\openpyxl\__init__.py |
| `accounting_context_status` | `False` | `PASS` | company=00000000 build=completed overdue=4 manual_filing=True bank_sources=36 csv_sources=4 pdf_sources=32 unique_bank_rows=1052 duplicates_removed=44 accounting_tools=99 ready=True statutory_outputs=64 raw_files=60 swarm_files=0 swarm_consensus=unknown end_user_confirmed=0 autonomous_workflow=unknown handoff=completed evidence_requests=362 evidence_docs=250 llm_docs=5 llm_status=completed end_user=unknown end_user_coverage=0/0 uk_requirements=8 uk_questions=67 vault_memory=unknown self_questioning=unknown |
| `accounting_system_registry` | `False` | `PASS` | modules=99 artifacts=1317 domains=18 |
| `accounting_readiness` | `False` | `PASS` | ready_for=final_ready_manual_upload_pack required_failures=0 bank_sources=36 statutory_outputs=64 |
| `accounting_statutory_pack` | `False` | `PASS` | generated_at=2026-05-13T20:27:34.137036+00:00 outputs=64 manual_filing_required=True |
| `accounting_raw_data_intake` | `False` | `PASS` | files=60 transaction_sources=36 evidence_only=24 |
| `accounting_swarm_raw_data_wave_scan` | `False` | `FAIL` | files=0 duration=0 files_per_second=0 consensus=unknown score=n/a |
| `accounting_end_user_confirmation_feed` | `False` | `FAIL` | status=unknown confirmed=0 attention=0 |
| `accounting_uk_requirements_brain` | `False` | `PASS` | status=final_ready_manual_upload_required requirements=8 questions=67 unresolved=2 vat_over_threshold=False |
| `accounting_evidence_authoring` | `False` | `PASS` | status=completed requests=362 documents=250 petty_cash=0 llm_status=completed llm_docs=5 internal_support_documents_only |
| `accounting_end_user_automation` | `False` | `FAIL` | status=unknown coverage=0/0 start_here=not found manual_filing_required=True |
| `accounting_artifact:full_run_manifest` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\company_compliance\00000000\full_company_accounts_run_manifest.json |
| `accounting_artifact:full_run_summary` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\company_compliance\00000000\full_company_accounts_run_summary.md |
| `accounting_artifact:compliance_audit_json` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\company_compliance\00000000\company_house_tax_audit.json |
| `accounting_artifact:period_manifest` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\gateway\2024-05-01_to_2025-04-30\period_pack_manifest.json |
| `accounting_artifact:statutory_manifest` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\statutory\00000000\2024-05-01_to_2025-04-30\statutory_filing_pack_manifest.json |
| `accounting_artifact:raw_data_manifest` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\company_raw_data\00000000\2024-05-01_to_2025-04-30\raw_data_manifest.json |
| `accounting_artifact:accounting_evidence_authoring_manifest` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\filing_handoff\00000000\2024-05-01_to_2025-04-30\07_review_workpapers\evidence_authoring\evidence_authoring_manifest.json |
| `accounting_artifact:accounting_evidence_requests_csv` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\filing_handoff\00000000\2024-05-01_to_2025-04-30\07_review_workpapers\evidence_authoring\evidence_requests.csv |
| `accounting_artifact:uk_accounting_requirements_brain_json` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\filing_handoff\00000000\2024-05-01_to_2025-04-30\07_review_workpapers\uk_accounting_requirements_brain.json |
| `accounting_artifact:accountant_self_questions_markdown` | `False` | `PASS` | C:\Users\user\aureon-trading-integrated-main-20260508\Kings_Accounting_Suite\output\filing_handoff\00000000\2024-05-01_to_2025-04-30\00_start_here\accountant_self_questions.md |
| `accounting_artifact:end_user_accounting_automation_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_accounting_automation_start_here` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_confirmation_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_confirmation_json` | `False` | `FAIL` | not found |
| `accounting_artifact:internal_logic_chain_checklist_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:internal_logic_chain_checklist_json` | `False` | `FAIL` | not found |
| `accounting_artifact:swarm_raw_data_wave_scan_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:swarm_raw_data_wave_scan_json` | `False` | `FAIL` | not found |
| `goal_capability_map` | `True` | `PASS` | 42 tool/skill routes; 1160 organism nodes |
| `capability_growth_loop` | `True` | `FAIL` | growth_loop_needs_repair; gaps=8 mean_score=0.737 |

## Required Failures

- `capability_growth_loop`: growth_loop_needs_repair; gaps=8 mean_score=0.737
