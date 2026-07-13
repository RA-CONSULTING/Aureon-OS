# Aureon SaaS System Inventory

- Generated: `2026-05-15T17:48:45.024188+00:00`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`
- Status: `inventory_ready_with_blockers`

## Summary

- `surface_count`: `870`
- `frontend_surface_count`: `676`
- `supabase_function_count`: `101`
- `legacy_dashboard_count`: `26`
- `generated_accounting_html_count`: `20`
- `orphaned_frontend_count`: `648`
- `security_blocker_count`: `2`
- `uncalled_supabase_function_count`: `29`
- `missing_supabase_function_call_count`: `4`

## Counts

- `by_kind`:
```json
{
  "accounting_generated_html": 20,
  "frontend_component": 395,
  "frontend_config": 5,
  "frontend_core": 105,
  "frontend_hook": 73,
  "frontend_integration": 2,
  "frontend_lib": 29,
  "frontend_page": 2,
  "frontend_service": 8,
  "frontend_source": 57,
  "legacy_template": 6,
  "local_dashboard_server": 20,
  "public_asset": 41,
  "supabase_function": 101,
  "vault_ui_server": 2,
  "vault_ui_static": 4
}
```
- `by_domain`:
```json
{
  "accounting": 78,
  "cognition": 75,
  "operator": 190,
  "research": 48,
  "saas_security": 88,
  "trading": 377,
  "vault_memory": 14
}
```
- `by_wiring_status`:
```json
{
  "generated_output": 20,
  "legacy": 6,
  "orphaned": 648,
  "partial": 94,
  "security_blocker": 2,
  "unknown": 2,
  "wired": 98
}
```
- `by_safety_class`:
```json
{
  "admin_or_tenant_boundary": 3,
  "credential_or_auth_boundary": 184,
  "live_trading_boundary": 47,
  "manual_filing_boundary": 10,
  "observation": 593,
  "payment_or_kyc_boundary": 33
}
```
- `by_owner_subsystem`:
```json
{
  "accounting_saas_surface": 6,
  "cognition_saas_surface": 8,
  "frontend_react_vite": 676,
  "kings_accounting_suite": 20,
  "legacy_queen_dashboards": 6,
  "local_command_center": 20,
  "operator_saas_surface": 4,
  "research_saas_surface": 10,
  "saas_security_saas_surface": 5,
  "supabase_edge_functions": 101,
  "trading_saas_surface": 7,
  "vault_memory_saas_surface": 1,
  "vault_ui": 6
}
```

## Canonical Shell Targets

| Screen | Surface count | Canonical candidates |
| --- | ---: | --- |
| `overview` | 85 | `supabase/functions/backend-health-check/index.ts`, `supabase/functions/update-kyc-status/index.ts`, `frontend/src/components/AdminKYCDashboard.tsx`, `frontend/src/components/AlpacaStatusPanel.tsx`, `frontend/src/components/AureonDashboard.tsx` |
| `trading` | 397 | `frontend/src/components/ExchangeCredentialsManager.tsx`, `frontend/src/components/generated/AureonWorkOrderExecutionConsole.tsx`, `frontend/src/components/ui/badge.tsx`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/card.tsx` |
| `accounting` | 63 | `supabase/functions/gas-tank-topup/index.ts`, `supabase/functions/ingest-decision-fusion/index.ts`, `supabase/functions/ingest-ftcp-detector/index.ts`, `supabase/functions/ingest-qgita-signal/index.ts`, `frontend/src/components/CapitalStatusPanel.tsx` |
| `research` | 109 | `frontend/src/App.tsx`, `frontend/src/main.tsx`, `supabase/functions/analyze-solar-correlations/index.ts`, `supabase/functions/celestial-alignments/index.ts`, `supabase/functions/ingest-ticker-snapshot/index.ts` |
| `vault` | 27 | `supabase/functions/ingest-elephant-memory/index.ts`, `supabase/functions/ingest-rainbow-bridge/index.ts`, `frontend/src/components/AnalysisModePanel.tsx`, `frontend/src/components/HNCImperialDetection.tsx`, `frontend/src/components/LongFormNarrativeEngine.tsx` |
| `cognition` | 101 | `frontend/src/components/generated/AureonCodingAgentSkillBaseConsole.tsx`, `frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx`, `frontend/src/components/generated/AureonWorkOrderExecutionConsole.tsx`, `frontend/src/services/aureonAutonomousFrontend.ts`, `supabase/functions/create-aureon-session/index.ts` |
| `saas_security` | 110 | `frontend/src/components/ExchangeCredentialsManager.tsx`, `frontend/src/components/ui/label.tsx`, `frontend/src/integrations/supabase/client.ts`, `frontend/src/services/aureonAutonomousFrontend.ts`, `supabase/functions/analyze-space-weather-correlation/index.ts` |
| `self_improvement` | 6 | `frontend/src/components/EvidenceAuditPanel.tsx`, `frontend/src/components/MonteCarloGrowthCurve.tsx`, `frontend/src/components/warroom/TradingReadinessCheck.tsx`, `frontend/public/aureon_autonomous_capability_switchboard.json`, `frontend/public/aureon_exchange_data_capability_matrix.json` |
| `admin` | 38 | `frontend/src/components/ExchangeCredentialsManager.tsx`, `supabase/functions/get-binance-credentials/index.ts`, `supabase/functions/store-binance-credentials/index.ts`, `supabase/functions/update-bot-credentials/index.ts`, `supabase/functions/update-kyc-status/index.ts` |

## Gaps

- Security blockers: `2`
- Orphaned frontend surfaces: `648`
- Uncalled Supabase functions: `29`
- Missing Supabase functions called by frontend: `4`

## Surface Checklist

| Status | Kind | Domain | Safety | Path | Next step |
| --- | --- | --- | --- | --- | --- |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/filing_handoff/00000000/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/filing_handoff/00000000/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl_2.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl_2.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl_3.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl_4.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/draft_computation_readable_not_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/draft_computation_readable_not_ixbrl_2.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/accounts_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/accounts_readable_for_ixbrl_2.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/draft_accounts_readable_not_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/draft_accounts_readable_not_ixbrl_2.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/statutory/00000000/2024-05-01_to_2025-04-30/accounts_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/statutory/00000000/2024-05-01_to_2025-04-30/computation_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/accounts_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `live_trading_boundary` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/computation_readable_for_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `payment_or_kyc_boundary` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/draft_accounts_readable_not_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `generated_output` | `accounting_generated_html` | `accounting` | `manual_filing_boundary` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/draft_computation_readable_not_ixbrl.html` | Expose as accounting evidence/document link, not source UI code. |
| `partial` | `local_dashboard_server` | `trading` | `live_trading_boundary` | `aureon/bots/orca_command_center.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `observation` | `aureon/bots/orca_launcher.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `operator` | `observation` | `aureon/command_centers/__init__.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/aureon_atn_command_center.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `live_trading_boundary` | `aureon/command_centers/aureon_command_center.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/aureon_command_center_enhanced.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `operator` | `observation` | `aureon/command_centers/aureon_command_center_lite.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_command_center_ui.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `observation` | `aureon/command_centers/aureon_queen_realtime_command_center.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/aureon_strategic_war_planner.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `operator` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_system_hub.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_system_hub_cli.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `operator` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_system_hub_dashboard.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `operator` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_system_hub_mycelium.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/aureon_war_band.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `observation` | `aureon/command_centers/aureon_war_band_enhanced.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `credential_or_auth_boundary` | `aureon/command_centers/aureon_warzone_dashboard.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/war_room.py` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `trading` | `observation` | `aureon/command_centers/war_strategy.py` | Inventory for migration into the unified observation shell. |
| `unknown` | `vault_ui_server` | `cognition` | `observation` | `aureon/vault/ui/__init__.py` | Review manually during SaaS unification planning. |
| `unknown` | `vault_ui_server` | `vault_memory` | `observation` | `aureon/vault/ui/server.py` | Review manually during SaaS unification planning. |
| `partial` | `vault_ui_static` | `cognition` | `admin_or_tenant_boundary` | `aureon/vault/ui/static/bridge.html` | Inventory for migration into the unified observation shell. |
| `partial` | `vault_ui_static` | `cognition` | `observation` | `aureon/vault/ui/static/bridge_invite.html` | Inventory for migration into the unified observation shell. |
| `partial` | `vault_ui_static` | `cognition` | `observation` | `aureon/vault/ui/static/index.html` | Inventory for migration into the unified observation shell. |
| `partial` | `vault_ui_static` | `vault_memory` | `observation` | `aureon/vault/ui/static/sw.js` | Inventory for migration into the unified observation shell. |
| `partial` | `local_dashboard_server` | `cognition` | `observation` | `aureon/wisdom/aureon_samuel_agent.py` | Inventory for migration into the unified observation shell. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/components.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_config` | `operator` | `observation` | `frontend/eslint.config.js` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `observation` | `frontend/index.html` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `payment_or_kyc_boundary` | `frontend/package-lock.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_config` | `trading` | `live_trading_boundary` | `frontend/package.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_config` | `operator` | `observation` | `frontend/postcss.config.js` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `observation` | `frontend/public/aureon_asset_waveform_models.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `saas_security` | `payment_or_kyc_boundary` | `frontend/public/aureon_autonomous_capability_switchboard.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_capital_tradable_asset_registry.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `payment_or_kyc_boundary` | `frontend/public/aureon_coding_agent_skill_base.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_cognitive_trade_evidence.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `live_trading_boundary` | `frontend/public/aureon_data_ocean_status.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `live_trading_boundary` | `frontend/public/aureon_exchange_data_capability_matrix.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `payment_or_kyc_boundary` | `frontend/public/aureon_exchange_monitoring_checklist.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `live_trading_boundary` | `frontend/public/aureon_frontend_work_order_execution.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `live_trading_boundary` | `frontend/public/aureon_global_financial_coverage_map.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `payment_or_kyc_boundary` | `frontend/public/aureon_harmonic_affect_state.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_hnc_cognitive_proof.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_hnc_operating_cycle.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `credential_or_auth_boundary` | `frontend/public/aureon_hnc_packet_security_comparison.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `credential_or_auth_boundary` | `frontend/public/aureon_hnc_symbolic_route_seal.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `live_trading_boundary` | `frontend/public/aureon_kraken_tradable_asset_registry.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_live_cognition_benchmark.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `credential_or_auth_boundary` | `frontend/public/aureon_live_waveform_recorder.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `live_trading_boundary` | `frontend/public/aureon_operational_ui_spec.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `vault_memory` | `credential_or_auth_boundary` | `frontend/public/aureon_repo_singularity_vault.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_scanner_fusion_matrix.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `live_trading_boundary` | `frontend/public/aureon_trading_intelligence_checklist.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_unified_exchange_execution_results.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `credential_or_auth_boundary` | `frontend/public/aureon_unified_exchange_order_intents.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `live_trading_boundary` | `frontend/public/aureon_unified_shadow_trade_report.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `payment_or_kyc_boundary` | `frontend/public/aureon_wake_up_manifest.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/aureon_world_financial_ecosystem_intelligence.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/public/kraken_spot_fast_profit_positions.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/src/App.css` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_source` | `cognition` | `live_trading_boundary` | `frontend/src/App.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/APIKeyManager.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ActiveTradePositions.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `payment_or_kyc_boundary` | `frontend/src/components/AdminKYCDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `payment_or_kyc_boundary` | `frontend/src/components/AdminPaymentVerification.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AkashicFrequencyVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/AlpacaStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/AnalysisModePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AncientNumericalCodex.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/AngelOracleReader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AnomalyAlertsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/AppLayout.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AssetInventoryPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/AssetPriceListPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AuraNarrativeRenderer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AuraRingVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AureonChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `credential_or_auth_boundary` | `frontend/src/components/AureonDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AureonLiveDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/AureonProcessTree.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AureonReportCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/AurisAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/AurisEngine.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/AurisNodesVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/AurisSymbolicCompiler.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `payment_or_kyc_boundary` | `frontend/src/components/AuthForm.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/AutoTradingScheduler.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AutomatedHuntControl.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/AutonomousTradingGuide.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/AutonomousTradingPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/BackendHealthMonitor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/BacktestingInterface.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/BinanceConnectionStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/BinanceCredentialsAdmin.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/BinanceCredentialsSettings.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/BinancePortfolioWidget.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/BrainStatePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `credential_or_auth_boundary` | `frontend/src/components/CapitalStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/CasimirVacuumField.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/CelestialAlignments.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ChartContainer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ChatPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/CircleOfFifthsVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/CodexHarmonia.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/CoherenceForecaster.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/CoherenceHeatmap.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/CoherenceTrajectoryChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/ConsciousnessCoherenceTracker.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/ConsciousnessHistoryChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/CosmicPhaseIndicator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/CredentialManager.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/CymaticsFieldVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/DataSourceIndicator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/DataStreamMonitorPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/DataValidationStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/DecisionVerificationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/DimensionalDialler.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/DrivingForcesChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EarthLiveAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EarthLiveUILayout.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EarthResonanceDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/EckoushicCascadeVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EmotionBadge.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EmotionSparkline.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/EnhancedAngelOracleReader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/EvidenceAuditPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/ExchangeCredentialsManager.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `operator` | `credential_or_auth_boundary` | `frontend/src/components/ExchangeDataVerificationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ExchangeStatusSummary.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/FTCPTimeline.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/FeatureCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/Features.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/FieldDataLoader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/FieldPullMetricsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/FloatingAIButton.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/FormationEquationDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `credential_or_auth_boundary` | `frontend/src/components/FrequencyAIInterpreter.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/FrequencyHarmonizationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/FullPortfolioDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/GaryLeckeyFormation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/GlyphTradingCorrelationChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/GuardianDimensions.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/HNCImperialDetection.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HNCProbabilityMatrixPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/HNCScoreCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicDataIntegrityPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicFieldVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HarmonicKeyboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/HarmonicNexusAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/HarmonicNexusCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicNexusMonitor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HarmonicNexusPhaseField3D.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/HarmonicNexusTheory.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/HarmonicRealityFramework.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicSpectrogram.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicSurgeField.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HarmonicTheoryFoundation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HarmonicTierDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/Header.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HealthAlertSettings.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/Hero.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/HistoricalCoherenceChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/HiveStatePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/HocusPatternPipelineVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/IdentityBinder.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/IgnitionButton.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/IntegralAQALVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/IntegratedReadingV2.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/KellyCriterionCalculator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `credential_or_auth_boundary` | `frontend/src/components/KrakenStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/LatencyHook.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/LatticeFieldVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/LatticeMap.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/LighthouseMetricsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/Live6DWaveformVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/LiveAnalysisStream.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/LiveDataDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `credential_or_auth_boundary` | `frontend/src/components/LiveDataPuller.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `live_trading_boundary` | `frontend/src/components/LiveEmotionalReader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/LivePnLTable.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/LivePriceTicker.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/LiveTerminalStats.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/LiveTradingStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/LiveTradingTestPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/LiveValidationDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/LiveValidationProtocol.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/LongFormNarrativeEngine.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/MandalaCodexProcessor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MarginSentimentPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MarketMetricsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MarketOverview.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MasterEquationEducational.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MasterEquationTree.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/MetricCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/MonitoringPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/MonteCarloGrowthCurve.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/MultiSymbolForecastComparison.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/NanoParticleVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/NavLink.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/Navbar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `credential_or_auth_boundary` | `frontend/src/components/NewsCrossRef.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `credential_or_auth_boundary` | `frontend/src/components/NewsHealth.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/NexusLiveDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/NexusLiveDashboardComplete.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/NexusWebSocket.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/NoaaSpaceWeatherDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/OMSQueueMonitor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/OmegaFieldVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PAWControlPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PAWTelemetryDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `payment_or_kyc_boundary` | `frontend/src/components/PaymentGate.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PeaceHarmonicField.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PerformanceMetricsDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PlatypusCoherencePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PortfolioSummaryPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PredictionAccuracyPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PredictiveWindowsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PriceAlerts.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PrimeDNAHelix.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PrimeDNAHelixCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/PrimeLockActivation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PrimeSealPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/PrimeSentinelSeal.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PrimeSurgeControls.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PrimelinesIdentityCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/PrimelinesProtocolStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/PrismRevealVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ProbabilityReconstructionPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ProjectRainbow.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QGITAAutoTradingControl.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QGITAConfigPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QGITADebugPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QGITAOMSIntegrationStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QuantumAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QuantumField3DProjection.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumField6DVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumFieldMatrix.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumFieldVisualizer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumMandalaMesh.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/QuantumPhaseLock.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QuantumQuackersPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/QuantumTelescopeDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/QuantumTelescopePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/QuantumTradingConsole.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/QueenHiveControl.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/QuickTrade.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `credential_or_auth_boundary` | `frontend/src/components/RealBinanceBalances.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/RecentTrades.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/RegionOverlay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/RegionsTimelinePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ReportCard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/ResearchGallery.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/ResearchValidation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ResonanceSpiral.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/RiskManagementDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/SandboxRunner.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SchedulerHistoryCharts.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannDataLoaders.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SchumannLattice.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeComplete.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/SchumannLatticePatch.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeRenderer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeTimeline.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SchumannLatticeWithRegions.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/SchumannResonanceMonitor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/SchumannSpectrograph.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SentinelSealSpectrogram.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SettingsDrawer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SignalHistory.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SimulationDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SimulationEngine.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SimulationVerificationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SmartAlertBanner.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SmokeTestPhasePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SolarChainInterface.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SolarCoherenceCorrelationChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SolarFlareCorrelation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SolarResonanceAtlas.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SolarWeatherDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SongOfSpheresControls.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SourceReadingPage.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SpaceWeatherCorrelationAnalyzer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/SporeConcentrationChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/StargateNetworkAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/StargatePatternAnalysis.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `admin_or_tenant_boundary` | `frontend/src/components/StargateStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/StargateVisualization.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/StatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/SymbolicCompilerPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `credential_or_auth_boundary` | `frontend/src/components/SystemHealthPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/SystemRegistryPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/SystemsGrid.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/SystemsIntegrationDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TLIDDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/TWAPMonitor.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/TarotReader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TechnologyRoadmap.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TemporalAlignmentTracker.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/TemporalLadderDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/TemporalUnityConsole.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/TemporalUnityOrchestrator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TradeAnalyzer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TradeNotification.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/TradeValidationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TradingAnalytics.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/TradingConfig.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/TradingConfigPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `admin_or_tenant_boundary` | `frontend/src/components/TradingConsole.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/TradingDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/TradingSettingsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/UnifiedFieldTimeline.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/UnifiedOrcaCommandDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/UnifiedTandemCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/UnityEventTracker.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/UnityNexusCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/UserDataVerificationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/UtilitiesPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `observation` | `frontend/src/components/ValidationEquationsDiagram.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ValidationTracePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/VisualizationPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `live_trading_boundary` | `frontend/src/components/WarRoomDashboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/Watchlist.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/analytics/CoherenceTrendChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/analytics/LHEFrequencyChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/analytics/OptimalEntryStats.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/analytics/SignalDistributionChart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/auth/APIKeySecurityGuide.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/auth/ConsentCheckboxes.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/auth/PasswordStrengthIndicator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/auth/SecurityBadges.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/AmbientSoundscape.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/CinematicCamera.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/CinematicHUD.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/CinematicObservatory.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/CinematicScene.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/CoherenceAurora.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/CosmicEnvironment.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/EventSpotlight.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/ExchangeGateways.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/HUDConsciousnessPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/HUDMetricsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/HUDNarrator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/HUDQueenVoice.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/HUDTopBar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/HUDTradeStream.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/cinema/HiveConstellation.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/MarketNebula.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/MetricRings.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/src/components/cinema/NarratorEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/QueenCore.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/cinema/TradeBeamSystem.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/earth/LatticeWaveformPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/earth/PrimeSealPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/earth/SchumannSpectrogramPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/earth/TimelineMarkersPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/earth/ValidationMeterPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `research` | `observation` | `frontend/src/components/earth/index.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/generated/AureonCodingAgentSkillBaseConsole.tsx` | Keep as canonical reachable UI. |
| `wired` | `frontend_component` | `cognition` | `credential_or_auth_boundary` | `frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx` | Keep as canonical reachable UI. |
| `wired` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/generated/AureonWorkOrderExecutionConsole.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/ArbitrageScannerPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/ExchangeLearningPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/MarketRegimeIndicator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/panels/NotificationSettingsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/PortfolioRebalancerPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/PositionHeatPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/panels/TrailingStopPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/tabs/AnalyticsTabContent.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/tabs/QuantumTabContent.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/tabs/SystemsTabContent.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/components/tabs/index.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `operator` | `observation` | `frontend/src/components/theme-provider.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/accordion.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/alert-dialog.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ui/alert.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/aspect-ratio.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/avatar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ui/badge.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/breadcrumb.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ui/button.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/calendar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/card.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/carousel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/chart.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/checkbox.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/collapsible.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/command.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/context-menu.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/dialog.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/drawer.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/dropdown-menu.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/form.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/hover-card.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/input-otp.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/input.tsx` | Keep as canonical reachable UI. |
| `wired` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/ui/label.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/menubar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/ui/navigation-menu.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/pagination.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/popover.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/progress.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/radio-group.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/resizable.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/scroll-area.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/select.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/separator.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/ui/sheet.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/ui/sidebar.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/skeleton.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/slider.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/sonner.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/switch.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/table.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/tabs.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/textarea.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ui/toast.tsx` | Keep as canonical reachable UI. |
| `wired` | `frontend_component` | `operator` | `observation` | `frontend/src/components/ui/toaster.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_component` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/components/ui/toggle-group.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/ui/toggle.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_component` | `trading` | `observation` | `frontend/src/components/ui/tooltip.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/components/ui/use-toast.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/ActivePositionsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/AurisNodesOrbit.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `accounting` | `observation` | `frontend/src/components/warroom/AurisNodesPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/BattleMap.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/CommandCenter.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/warroom/CredentialStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/DuckCommandoIntel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/warroom/EcosystemStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/ExchangeBalances.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `saas_security` | `observation` | `frontend/src/components/warroom/FullEcosystemStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `payment_or_kyc_boundary` | `frontend/src/components/warroom/GasTankDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/HarmonicWaveform6DStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/HistoricalTimeline.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/KillConfirmationBanner.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `research` | `credential_or_auth_boundary` | `frontend/src/components/warroom/LaunchButton.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/LiveStrikeStream.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `live_trading_boundary` | `frontend/src/components/warroom/LiveTradeStream.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/MetricsHQ.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/MultiExchangePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/PrimeSealStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/PrismFrequencyPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/PrismStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/ProbabilityFusionPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/ProbabilityMatrixDisplay.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/ProjectionHorizon.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `cognition` | `observation` | `frontend/src/components/warroom/QuantumStatePanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/SniperLeaderboard.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `operator` | `observation` | `frontend/src/components/warroom/StrikeFeed.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/TemporalLadderStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/TradeControlsHeader.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/warroom/TradingModeToggle.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/warroom/TradingReadinessCheck.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `observation` | `frontend/src/components/warroom/TradingStatusPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `vault_memory` | `observation` | `frontend/src/components/warroom/UnifiedBusStatus.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_component` | `trading` | `credential_or_auth_boundary` | `frontend/src/components/warroom/UserAssetsPanel.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/contexts/AppContext.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/adaptiveFilterThresholds.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/adaptiveLearningEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/akashicFrequencyMapper.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/akashicMapperBridge.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/aqtsOrchestrator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `manual_filing_boundary` | `frontend/src/core/aurisNodes.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `manual_filing_boundary` | `frontend/src/core/aurisSymbolicTaxonomy.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/automatedSimulationEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/autonomyHubBridge.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/backgroundServices.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/binanceWebSocket.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/capitalPool.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/coinAPIAnomalyDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/config.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/crossExchangeArbitrageScanner.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/dataIngestion.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_core` | `operator` | `live_trading_boundary` | `frontend/src/core/dataStreamMonitor.ts` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/decisionAccuracyTracker.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/decisionExplainer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/decisionFusion.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/detection/coinAPIAnomalyDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/detection/index.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/dimensionalDialler.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/dimensionalDriftCorrector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `manual_filing_boundary` | `frontend/src/core/duckCommandos.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/earthAureonBridge.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/earthLiveDataIntegration.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/eckoushicCascade.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `credential_or_auth_boundary` | `frontend/src/core/ecosystemConfig.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/ecosystemConnector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/ecosystemEnhancements.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/elephantMemory.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/elephantMemoryDB.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/enhanced6DProbabilityMatrix.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `vault_memory` | `observation` | `frontend/src/core/enhancementLayer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/exchangeLearningTracker.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/executionEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/fibonacciLattice.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/forceValidatedTrade.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/ftcpDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/fullEcosystemConnector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/gaiaLatticeEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `payment_or_kyc_boundary` | `frontend/src/core/globalSystemsManager.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `credential_or_auth_boundary` | `frontend/src/core/harmonicNexus.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `saas_security` | `observation` | `frontend/src/core/harmonicNexusCore.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/hiveController.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/hncImperialDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/hncProbabilityMatrix.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/hocusPatternPipeline.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/imperialPredictability.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/instrumentedSupabase.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/integralAQAL.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/krakenWebSocket.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/lightPathTracer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/lighthouseConsensus.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/lotSizeValidator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/marketDataValidator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/marketPulse.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/masterEquation.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `credential_or_auth_boundary` | `frontend/src/core/multiExchangeClient.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_core` | `trading` | `credential_or_auth_boundary` | `frontend/src/core/networkMonitor.ts` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/nexusLiveFeedBridge.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/notificationManager.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/omegaEquation.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/opportunityScanner.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/performanceTracker.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/platypusCoherenceEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/portfolioRebalancer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/positionHeatTracker.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `credential_or_auth_boundary` | `frontend/src/core/positionManager.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `credential_or_auth_boundary` | `frontend/src/core/predictionAccuracyTracker.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `vault_memory` | `observation` | `frontend/src/core/primeSealComputer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `saas_security` | `observation` | `frontend/src/core/primelinesIdentity.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/prism.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/qgitaCoherence.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/qgitaEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/qgitaSignalGenerator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/quackersEvents.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/quantumTelescope.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/queenHive.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/queenHiveBrowser.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/rainbowBridge.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/riskManagement.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/sixDimensionalHarmonicEngine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/smartOrderRouter.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/smokeTestPhaseValidator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/stargateFrequencyHarmonizer.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/stargateGrid.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/stargateLattice.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `live_trading_boundary` | `frontend/src/core/startupHarvester.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/synchronicityDecoder.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `cognition` | `observation` | `frontend/src/core/systemsIntegration.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/temporalAnchor.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/core/temporalLadder.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/temporalProbabilityEcho.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `research` | `observation` | `frontend/src/core/thePrism.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/tickerCacheManager.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/tradeLogger.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/trailingStopManager.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `vault_memory` | `observation` | `frontend/src/core/unifiedBus.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `payment_or_kyc_boundary` | `frontend/src/core/unifiedExchangeClient.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `live_trading_boundary` | `frontend/src/core/unifiedOrchestrator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `trading` | `observation` | `frontend/src/core/unifiedStateAggregator.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `accounting` | `observation` | `frontend/src/core/unityDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_core` | `operator` | `observation` | `frontend/src/core/zeroPointFieldDetector.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `trading` | `observation` | `frontend/src/data/binance-pairs.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `saas_security` | `observation` | `frontend/src/engine/finite-engine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `saas_security` | `observation` | `frontend/src/engine/types.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/use-mobile.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/use-toast.ts` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useActiveSymbols.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useAllTickers.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useAssetPriceList.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useAureonLiveData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `payment_or_kyc_boundary` | `frontend/src/hooks/useAureonSession.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `credential_or_auth_boundary` | `frontend/src/hooks/useAutomatedHunt.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `live_trading_boundary` | `frontend/src/hooks/useAutonomousTrading.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useAvailableAssets.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useBackendHealth.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `credential_or_auth_boundary` | `frontend/src/hooks/useBinanceBalances.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `credential_or_auth_boundary` | `frontend/src/hooks/useBinanceCredentials.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useBinanceMarginData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useBinanceMarketData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `credential_or_auth_boundary` | `frontend/src/hooks/useBinanceWebSocket.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useBiometricSensors.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useBrainState.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useCelestialData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useConsciousnessHistory.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useConsciousnessStream.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useDataStreamMonitor.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `credential_or_auth_boundary` | `frontend/src/hooks/useDecisionVerification.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `research` | `observation` | `frontend/src/hooks/useEarthLiveData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useEcosystemData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useEmotionStream.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useExchangeDataVerification.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useFieldGlyphResonance.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useFieldPullMetrics.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useFrequencyHarmonization.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `payment_or_kyc_boundary` | `frontend/src/hooks/useGasTank.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `credential_or_auth_boundary` | `frontend/src/hooks/useGlobalState.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useGlyphTradingCorrelation.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `security_blocker` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useHarmonicAuth.ts` | Replace demo auto-login with explicit session/MFA/policy gate before SaaS production. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useHealthAlerts.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useHiResClock.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useHistoricalData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `cognition` | `observation` | `frontend/src/hooks/useHiveState.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useKrakenRealtime.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useMarketScanner.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `credential_or_auth_boundary` | `frontend/src/hooks/useMultiExchangeBalances.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useMultiSymbolWatchlist.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useOMSQueue.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/usePositionMonitor.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `observation` | `frontend/src/hooks/usePredictiveWindows.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/usePriceAlerts.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/usePrimeSeal.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/usePrimelinesProtocol.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useProjections.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useQGITAAutoTrading.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useQGITAConfig.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `observation` | `frontend/src/hooks/useQGITAMetrics.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useQuantumTelescope.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useQuantumWarRoom.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useQueenHive.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useSchumannData.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `observation` | `frontend/src/hooks/useSchumannResonance.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useSentinelConfig.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useSmokeTestStartup.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `accounting` | `observation` | `frontend/src/hooks/useStargateNetwork.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useStargateNetworkHistory.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useStargatePatterns.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useStrikeFeed.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useSystemsIntegration.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useTemporalAlignment.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `observation` | `frontend/src/hooks/useTerminalMetrics.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useTerminalSync.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `operator` | `observation` | `frontend/src/hooks/useTickerStream.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useTradeValidation.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useUserBalances.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/hooks/useUserDataVerification.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useWarMetrics.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_hook` | `trading` | `observation` | `frontend/src/hooks/useWarRoom.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `research` | `observation` | `frontend/src/index.css` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_integration` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/integrations/supabase/client.ts` | Keep as canonical reachable UI. |
| `wired` | `frontend_integration` | `trading` | `payment_or_kyc_boundary` | `frontend/src/integrations/supabase/types.ts` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/HighResClock.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/aura-engine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `trading` | `observation` | `frontend/src/lib/aureon-intervals-utils.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `trading` | `observation` | `frontend/src/lib/aureon-intervals.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `research` | `observation` | `frontend/src/lib/aureon-smoothing.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `cognition` | `observation` | `frontend/src/lib/aureon-utils.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/auris-codex.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `research` | `observation` | `frontend/src/lib/auris-engine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/auris-harmonic-engine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/auris-runtime-config.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/auris-stream-exporter.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `trading` | `observation` | `frontend/src/lib/countries-data.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `research` | `observation` | `frontend/src/lib/earth-data-loader.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/earth-streams.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/earth-validation.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `security_blocker` | `frontend_lib` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/lib/harmonic-nexus-auth.ts` | Replace demo auto-login with explicit session/MFA/policy gate before SaaS production. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/intentCompiler.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/lattice-id-seal.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/mood.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `research` | `observation` | `frontend/src/lib/newsSources.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `saas_security` | `observation` | `frontend/src/lib/nexus-models.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/paw-api-driver-complete.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `trading` | `observation` | `frontend/src/lib/schumann-country-mapping.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/solar-harmonics.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/song-of-spheres.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `trading` | `credential_or_auth_boundary` | `frontend/src/lib/tarot-engine.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/tonnetz.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_lib` | `accounting` | `observation` | `frontend/src/lib/tri-timeline-blender.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_lib` | `operator` | `observation` | `frontend/src/lib/utils.ts` | Keep as canonical reachable UI. |
| `wired` | `frontend_source` | `operator` | `observation` | `frontend/src/main.tsx` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_page` | `trading` | `credential_or_auth_boundary` | `frontend/src/pages/Systems.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_page` | `trading` | `credential_or_auth_boundary` | `frontend/src/pages/WarRoom.tsx` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `wired` | `frontend_service` | `saas_security` | `payment_or_kyc_boundary` | `frontend/src/services/aureonAutonomousFrontend.ts` | Keep as canonical reachable UI. |
| `orphaned` | `frontend_service` | `saas_security` | `credential_or_auth_boundary` | `frontend/src/services/aureonChatService.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `cognition` | `manual_filing_boundary` | `frontend/src/services/aureonService.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `cognition` | `observation` | `frontend/src/services/ecosystemContextBuilder.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `trading` | `credential_or_auth_boundary` | `frontend/src/services/geminiService.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `cognition` | `observation` | `frontend/src/services/lighthouseService.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `trading` | `credential_or_auth_boundary` | `frontend/src/services/tradingService.browser.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_service` | `trading` | `observation` | `frontend/src/services/websocketService.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `observation` | `frontend/src/state/newsEmotionStore.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `cognition` | `observation` | `frontend/src/types.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `saas_security` | `observation` | `frontend/src/types/hnc.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/types/paw-types.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/types/region.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/utils/number.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `observation` | `frontend/src/utils/time.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/src/vite-env.d.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `accounting` | `credential_or_auth_boundary` | `frontend/src/workers/sources/aurisSandbox.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `research` | `credential_or_auth_boundary` | `frontend/src/workers/sources/aurisUtils.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `research` | `credential_or_auth_boundary` | `frontend/src/workers/sources/aurisWebhook.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_config` | `trading` | `observation` | `frontend/tailwind.config.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/tsconfig.app.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/tsconfig.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_source` | `operator` | `observation` | `frontend/tsconfig.node.json` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `orphaned` | `frontend_config` | `operator` | `observation` | `frontend/vite.config.ts` | Decide whether to migrate into the unified shell, expose through navigation, or archive. |
| `partial` | `public_asset` | `saas_security` | `credential_or_auth_boundary` | `public/angel-oracle-cards-complete.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `saas_security` | `credential_or_auth_boundary` | `public/angel-oracle-cards.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/auris_codex.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `saas_security` | `observation` | `public/auris_codex_expanded.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `operator` | `observation` | `public/auris_emotions.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/auris_symbols.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `credential_or_auth_boundary` | `public/aztec-star-glyphs.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `operator` | `credential_or_auth_boundary` | `public/celtic-ogham-feda.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/consciousness_state.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/dashboard.html` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `credential_or_auth_boundary` | `public/earth-live-data/aureon_manifest.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/earth-live-data/auris_codex.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/earth-live-data/field_resonance_mapper.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `saas_security` | `observation` | `public/earth-live-data/manifest.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `operator` | `observation` | `public/earth-live-data/timeline_clip.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `credential_or_auth_boundary` | `public/egyptian-hieroglyphs.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/elder-futhark-complete.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `credential_or_auth_boundary` | `public/elder-futhark-runes.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `saas_security` | `credential_or_auth_boundary` | `public/elder-futhark-second-aett.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `credential_or_auth_boundary` | `public/elder-futhark-third-aett.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `observation` | `public/emotional_codex.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `observation` | `public/emotional_frequency_codex.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/emotional_frequency_codex_complete.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/emotional_spectrum_tree.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/emotional_spectrum_tree_complete.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/experiment_manifest.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/geometric_glyph.html` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/geometric_glyph_animated.html` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/hive_state.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/japanese-star-symbols.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/manifest.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/mogollon-star-symbols.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `credential_or_auth_boundary` | `public/ruleset-chakras.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `vault_memory` | `credential_or_auth_boundary` | `public/ruleset.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `operator` | `credential_or_auth_boundary` | `public/sacred-site-planetary-nodes.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `observation` | `public/symbolic_compiler_layer.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `credential_or_auth_boundary` | `public/tarot-major-arcana-complete.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `accounting` | `live_trading_boundary` | `public/tarot-major-arcana.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `research` | `live_trading_boundary` | `public/tarot_deck.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `cognition` | `observation` | `public/taste_molecular_codex.json` | Inventory for migration into the unified observation shell. |
| `partial` | `public_asset` | `trading` | `observation` | `public/test_cop_energy_ui.html` | Inventory for migration into the unified observation shell. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ai-commentary/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `payment_or_kyc_boundary` | `supabase/functions/analyze-lighthouse-event/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `research` | `credential_or_auth_boundary` | `supabase/functions/analyze-solar-correlations/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/analyze-space-weather-correlation/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/analyze-stargate-patterns/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `cognition` | `credential_or_auth_boundary` | `supabase/functions/aureon-chat/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/auto-trading-scheduler/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/automated-hunt-loop/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/backend-health-check/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/backfill-trades/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/binance-algo-twap/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `research` | `credential_or_auth_boundary` | `supabase/functions/celestial-alignments/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/confirm-trade/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `payment_or_kyc_boundary` | `supabase/functions/create-aureon-session/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/emergency-stop/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/execute-trade-alpaca/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/execute-trade-capital/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/execute-trade-kraken/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/execute-trade-user-alpaca/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/execute-trade-user-capital/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `live_trading_boundary` | `supabase/functions/execute-trade/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-all-tickers/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-binance-margin-data/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-binance-market-data/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/fetch-binance-portfolio/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-binance-symbols/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-historical-data/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-kraken-market-data/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/fetch-noaa-space-weather/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-open-positions/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-positions-pnl/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/fetch-schumann-data/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/fetch-trades/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/fetch-usgs-seismic-data/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `live_trading_boundary` | `supabase/functions/force-validated-trade/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/forecast-coherence/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `payment_or_kyc_boundary` | `supabase/functions/gas-tank-check-balance/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `accounting` | `payment_or_kyc_boundary` | `supabase/functions/gas-tank-deduct-fee/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `accounting` | `payment_or_kyc_boundary` | `supabase/functions/gas-tank-topup/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/get-alpaca-balances/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `live_trading_boundary` | `supabase/functions/get-binance-balances/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/get-binance-credentials/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/get-capital-balances/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/get-kraken-balances/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/get-user-balances/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/get-user-market-data/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-10-9-1-packet/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-6d-harmonic/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-adaptive-learning/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-akashic-attunement/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-akashic-mapper/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-auris-state/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-brain-state/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-calibration-trade/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-decision-fusion/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-dimensional-dialler/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-eckoushic-cascade/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `cognition` | `credential_or_auth_boundary` | `supabase/functions/ingest-ecosystem-snapshot/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-elephant-memory/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-exchange-learning/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `accounting` | `credential_or_auth_boundary` | `supabase/functions/ingest-ftcp-detector/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-hnc-detection/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-integral-aqal/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-kelly-computation/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-master-equation/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-omega-equation/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-performance-tracker/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-planetary-modulation/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-prism-state/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-probability-matrix/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `accounting` | `credential_or_auth_boundary` | `supabase/functions/ingest-qgita-signal/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `vault_memory` | `credential_or_auth_boundary` | `supabase/functions/ingest-rainbow-bridge/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-risk-manager/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-smart-router/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-stargate-harmonizer/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-stargate-network/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-telescope-state/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-temporal-anchor/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-terminal-state/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `research` | `credential_or_auth_boundary` | `supabase/functions/ingest-ticker-snapshot/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/ingest-trades/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/ingest-unity-event/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `accounting` | `credential_or_auth_boundary` | `supabase/functions/ingest-zero-point-field/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/interpret-frequency/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/monitor-positions/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/oms-leaky-bucket/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/poll-trade-confirmations/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `research` | `credential_or_auth_boundary` | `supabase/functions/primelines-protocol-gateway/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `cognition` | `credential_or_auth_boundary` | `supabase/functions/queen-hive-orchestrator/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/send-health-alert/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `partial` | `supabase_function` | `trading` | `payment_or_kyc_boundary` | `supabase/functions/send-signup-notification/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/store-binance-credentials/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/sync-exchange-assets/index.ts` | Verify auth and data contract from frontend caller. |
| `partial` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/sync-harmonic-nexus/index.ts` | Decide whether this backend function needs a unified frontend panel or should be archived. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/test-exchange-connection/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `trading` | `credential_or_auth_boundary` | `supabase/functions/unified-field-analysis/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/update-bot-credentials/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `payment_or_kyc_boundary` | `supabase/functions/update-kyc-status/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `payment_or_kyc_boundary` | `supabase/functions/update-user-credentials/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `credential_or_auth_boundary` | `supabase/functions/verify-exchange-connectivity/index.ts` | Verify auth and data contract from frontend caller. |
| `wired` | `supabase_function` | `saas_security` | `payment_or_kyc_boundary` | `supabase/functions/verify-payment/index.ts` | Verify auth and data contract from frontend caller. |
| `legacy` | `legacy_template` | `trading` | `observation` | `templates/aureon_face.html` | Inventory for migration into the unified observation shell. |
| `legacy` | `legacy_template` | `trading` | `payment_or_kyc_boundary` | `templates/queen_bot_intelligence.html` | Inventory for migration into the unified observation shell. |
| `legacy` | `legacy_template` | `trading` | `observation` | `templates/queen_dashboard.html` | Inventory for migration into the unified observation shell. |
| `legacy` | `legacy_template` | `trading` | `credential_or_auth_boundary` | `templates/queen_dashboard_enhanced.html` | Inventory for migration into the unified observation shell. |
| `legacy` | `legacy_template` | `trading` | `observation` | `templates/queen_live_panel.html` | Inventory for migration into the unified observation shell. |
| `legacy` | `legacy_template` | `trading` | `observation` | `templates/queen_sero_dashboard.html` | Inventory for migration into the unified observation shell. |

## Notes

- Inventory is read-only and does not call live trading, payment, filing, or external attack paths.
- Generated accounting HTML is treated as review/output material, not source UI.
- The unified frontend should migrate important orphaned and legacy surfaces before anything is removed.
