# Aureon Trading Intelligence Checklist

- Generated: 2026-05-22T18:20:47.022653+00:00
- Status: runtime_data_not_ready
- Runtime fresh: False
- Fresh usable: 0/14
- Decision fed: 4
- Evidence self-trust: 0.178429
- Live action trust: 0.06245
- Decision posture: wait_for_live_data
- Metacognitive data context: mapped=False coverage=90.0% live_sources=4 tickers=3034 history_rows=222639 usable_for_thought=False usable_for_live_decision=False
- Live stream cache: fresh=False symbols=0 top=
- Fast money: candidates=0 high_vol=0 orderbook=0 aligned=0 top= score=0.0
- HNC operating cycle: status= passed=False fed=False questions=0 action=
- Stale reason: none

| System | Category | Stage | Fresh | Usable | Fed | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| LiveStreamCacheRuntime | live_market_intelligence | market_feed | False | False | False | stream_cache_not_fresh, repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| FastMoneySelectorRuntime | profit_timing | profit_velocity | False | False | False | fast_money_report_missing, not_active_this_cycle, not_wired_to_decision_logic, runtime_data_not_ready |
| OrderBookPressureRuntime | profit_timing | profit_velocity | False | False | False | orderbook_pressure_not_sampled_this_cycle, not_active_this_cycle, not_wired_to_decision_logic, runtime_data_not_ready |
| ModelSignalFeed | live_market_intelligence | market_feed | False | False | False | repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| AurisNodes | hnc_auris_cognition | auris_state | False | False | False | repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| HNCOperatingCycle | hnc_auris_cognition | hnc_proof | False | False | False | missing_cycle_step:who, missing_cycle_step:what, missing_cycle_step:where, missing_cycle_step:when, missing_cycle_step:how, missing_cycle_step:act, repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| RuntimeWatchdog | counter_intelligence_validation | exchange_action_plan | False | False | True | repo_path_missing, runtime_data_not_ready |
| APIGovernor | counter_intelligence_validation | exchange_action_plan | False | False | False | repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| ExchangeRouteClearance | counter_intelligence_validation | exchange_action_plan | False | False | False | no_ready_venues, repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| ProfitVelocityRanker | profit_timing | profit_velocity | False | False | False | repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| ShadowTradeSelfMeasurement | counter_intelligence_validation | shadow_validation | False | False | False | repo_path_missing, not_wired_to_decision_logic, runtime_data_not_ready |
| DataOceanCognitiveContext | metacognitive_data_context | metacognitive_context | False | False | True | configured_registry_not_fully_mapped, coverage_below_configured_threshold, configured_sources_not_all_usable_for_mapping, not_active_this_cycle, runtime_data_not_ready |
| PlanetaryCoverageMap | metacognitive_data_context | metacognitive_context | False | False | True | configured_registry_not_fully_mapped, coverage_below_configured_threshold, configured_sources_not_all_usable_for_mapping, not_active_this_cycle, runtime_data_not_ready |
| ExchangeWaveformMemory | metacognitive_data_context | metacognitive_context | False | False | True | configured_registry_not_fully_mapped, coverage_below_configured_threshold, configured_sources_not_all_usable_for_mapping, runtime_data_not_ready |

This checklist is evidence-only. It does not place orders, change exchange credentials, or bypass runtime truth checks.
