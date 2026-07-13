# Aureon Ignition Live Boot Audit

- Generated: `2026-05-22T08:22:08.203458`
- Command: `python scripts/aureon_ignition.py --live`
- Mode: `LIVE`
- Ready: `False`
- Real orders allowed by runtime: `True`
- Loaded env files: `C:\Users\user\aureon-trading\.env`
- Accounting status: `unknown`; manual filing required: `True`; bank sources: `0`; unique bank rows: `0`; accounting tools: `99`; ready: `False`; statutory outputs: `2`; raw files: `0`; swarm files: `0`; swarm consensus: `unknown`

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
| `cognitive_order_intent_authority` | `True` | `FAIL` | cognition may publish live order intents; exchange mutation remains runtime-gated |
| `import:runtime_safety` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\core\aureon_runtime_safety.py |
| `import:queen_layer` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\queen\queen_layer.py |
| `import:goal_capability_map` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\autonomous\aureon_goal_capability_map.py |
| `import:self_questioning_ai` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\autonomous\aureon_self_questioning_ai.py |
| `import:capability_growth_loop` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\autonomous\aureon_capability_growth_loop.py |
| `import:accounting_context_bridge` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\queen\accounting_context_bridge.py |
| `import:dynamic_margin_sizer` | `False` | `PASS` | C:\Users\user\aureon-trading\aureon\trading\dynamic_margin_sizer.py |
| `import:temporal_trade_cognition` | `False` | `PASS` | C:\Users\user\aureon-trading\aureon\trading\temporal_trade_cognition.py |
| `import:unified_margin_brain` | `False` | `PASS` | C:\Users\user\aureon-trading\aureon\trading\unified_margin_brain.py |
| `import:micro_profit_labyrinth` | `True` | `PASS` | C:\Users\user\aureon-trading\aureon\trading\micro_profit_labyrinth.py |
| `accounting_suite_path` | `True` | `PASS` | C:\Users\user\aureon-trading\Kings_Accounting_Suite |
| `package:reportlab` | `False` | `PASS` | C:\Users\user\aureon-trading\.venv\Lib\site-packages\reportlab\__init__.py |
| `package:pypdf` | `False` | `PASS` | C:\Users\user\aureon-trading\.venv\Lib\site-packages\pypdf\__init__.py |
| `package:openpyxl` | `False` | `PASS` | C:\Users\user\aureon-trading\.venv\Lib\site-packages\openpyxl\__init__.py |
| `accounting_context_status` | `False` | `PASS` | company=00000000 build=unknown overdue=0 manual_filing=True bank_sources=0 csv_sources=0 pdf_sources=0 unique_bank_rows=0 duplicates_removed=0 accounting_tools=99 ready=False statutory_outputs=2 raw_files=0 swarm_files=0 swarm_consensus=unknown end_user_confirmed=0 autonomous_workflow=unknown handoff=unknown evidence_requests=1 evidence_docs=0 llm_docs=0 llm_status=not_run end_user=unknown end_user_coverage=0/0 uk_requirements=5 uk_questions=8 vault_memory=unknown self_questioning=unknown |
| `accounting_system_registry` | `False` | `PASS` | modules=99 artifacts=5 domains=18 |
| `accounting_readiness` | `False` | `FAIL` | ready_for=final_ready_manual_upload_pack required_failures=13 bank_sources=0 statutory_outputs=2 |
| `accounting_statutory_pack` | `False` | `PASS` | generated_at= outputs=2 manual_filing_required=True |
| `accounting_raw_data_intake` | `False` | `FAIL` | files=0 transaction_sources=0 evidence_only=0 |
| `accounting_swarm_raw_data_wave_scan` | `False` | `FAIL` | files=0 duration=0 files_per_second=0 consensus=unknown score=n/a |
| `accounting_end_user_confirmation_feed` | `False` | `FAIL` | status=unknown confirmed=0 attention=0 |
| `accounting_uk_requirements_brain` | `False` | `PASS` | status=capability_ready_no_private_pack requirements=5 questions=8 unresolved=8 vat_over_threshold=review_required |
| `accounting_evidence_authoring` | `False` | `PASS` | status=capability_ready_no_private_pack requests=1 documents=0 petty_cash=0 llm_status=not_run llm_docs=0 internal_support_documents_only |
| `accounting_end_user_automation` | `False` | `FAIL` | status=unknown coverage=0/0 start_here=not found manual_filing_required=True |
| `accounting_artifact:full_run_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:full_run_summary` | `False` | `FAIL` | not found |
| `accounting_artifact:compliance_audit_json` | `False` | `FAIL` | not found |
| `accounting_artifact:period_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:statutory_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:raw_data_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:accounting_evidence_authoring_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:accounting_evidence_requests_csv` | `False` | `FAIL` | not found |
| `accounting_artifact:uk_accounting_requirements_brain_json` | `False` | `FAIL` | not found |
| `accounting_artifact:accountant_self_questions_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_accounting_automation_manifest` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_accounting_automation_start_here` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_confirmation_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:end_user_confirmation_json` | `False` | `FAIL` | not found |
| `accounting_artifact:internal_logic_chain_checklist_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:internal_logic_chain_checklist_json` | `False` | `FAIL` | not found |
| `accounting_artifact:swarm_raw_data_wave_scan_markdown` | `False` | `FAIL` | not found |
| `accounting_artifact:swarm_raw_data_wave_scan_json` | `False` | `FAIL` | not found |
| `goal_capability_map` | `True` | `PASS` | 42 tool/skill routes; 1196 organism nodes |
| `capability_growth_loop` | `True` | `FAIL` | growth_loop_needs_repair; gaps=8 mean_score=0.552 |

## Required Failures

- `cognitive_order_intent_authority`: cognition may publish live order intents; exchange mutation remains runtime-gated
- `capability_growth_loop`: growth_loop_needs_repair; gaps=8 mean_score=0.552
