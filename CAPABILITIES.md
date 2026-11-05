# Aureon capability map (go-live HOLD)

This document maps designed public surfaces and module names. It is not a measured live system, not a production clearance, and not a validation. Go-live is terminal HOLD. The orange release-boundary badge stays HOLD. For the run boundary, see [RUNNING.md](RUNNING.md) and [QUICK_START.md](QUICK_START.md). For how the subsystems are drawn, see [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md).

Names in the tables below, including "live" and "validated", are design labels. They are not a measured validation and not a statement that a process is running.

## Canonical launcher paths (not an approved start)

Historical invocation text. Withdrawn as a start command. These paths do not clear HOLD.

```powershell
.\scripts\launchers\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791
```

Historical validate-only text, not a clearance:

```powershell
.\scripts\launchers\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
```

Historical audit-only ignition text, not a start:

```powershell
python scripts/aureon_ignition.py --audit-only
```

Historical data-ocean invocation text, not a start:

```powershell
.\scripts\launchers\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable
```

## Capability Table

| Capability | What the code is designed to do | Primary surfaces |
|---|---|---|
| Live/safe runtime supervision | Designed to start and supervise from one terminal, publish manifests, and show reboot timing. Not an approved start while go-live is HOLD. | `scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`, `scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` |
| Multi-exchange market coverage | Designed to run unified market telemetry and exchange readiness for Kraken, Binance, Alpaca, and Capital. Not a claim a feed is connected. | `aureon/exchanges/unified_market_trader.py`, `aureon/exchanges/unified_market_status_server.py` |
| Planetary financial data ocean | Maps configured/licensed financial signals across exchanges, history, macro, news, on-chain, forecasts, and internal knowledge without competing with execution/risk loops. | `scripts/launchers/AUREON_DATA_OCEAN.cmd`, `aureon/autonomous/aureon_data_ocean.py`, `aureon_global_financial_coverage_map.py` |
| Official exchange rate budgets | Designed to record Binance, Kraken, Alpaca, and Capital provider limits, then build cash-aware call plans that reserve execution capacity and name idle/no-cash venue discovery. Not a measured safety proof. | `aureon/core/exchange_rate_limit_registry.py`, `api_governor`, `state/aureon_data_ocean_status.json` |
| Exchange data capability matrix | Shows what each exchange can observe, trade, leverage, and optimize: data channels, modes, feed freshness, decision-fed state, call budget, gaps, and next optimization. | `aureon/autonomous/aureon_exchange_data_capability_matrix.py`, `docs/audits/aureon_exchange_data_capability_matrix.json`, `frontend/public/aureon_exchange_data_capability_matrix.json` |
| Capital wave-validated portfolio brain | Design label only. The code names expansion past fixed buy/sell lanes when portfolio memory, margin survival, stress buffer, cross-exchange waveform checks, and a confidence ratchet pass. That is not a measured validation, and go-live does not clear it. | `aureon/exchanges/capital_cfd_trader.py`, `/api/terminal-state#capital_risk_envelope`, Trading console Capital Survival Brain |
| Capital tradable asset registry | Records every discovered Capital market, epic, estimated cost, margin, leverage, minimum deal size, and the exact buy/sell/close/pending-order code route. | `aureon/exchanges/capital_asset_registry.py`, `state/capital_tradable_asset_registry.sqlite`, `docs/audits/aureon_capital_tradable_asset_registry.json` |
| Capital pending order survival | Designed to plan limit bids with broker take-profit fields and to block ladders the envelope marks unsafe, by assuming every pending order fills together. Not a measured survival proof. | `capital_pending_order_envelope`, `CapitalClient.place_working_order`, `CapitalClient.update_position_limits` |
| Kraken spot/margin asset registry | Records Kraken AssetPairs, ticker/spread, order minimum, cost minimum, maker/taker fee tiers, margin leverage, take-profit route, and exact spot/margin code route. | `aureon/exchanges/kraken_asset_registry.py`, `state/kraken_tradable_asset_registry.sqlite`, `/api/terminal-state#kraken_asset_registry` |
| Kraken pending order survival | Designed to score planned crypto spot/margin ladders as if every pending order fills, including spot quote budget, maker/taker fees, margin collateral, and a stress-loss buffer. Not a measured stress result. | `build_kraken_order_survival_envelope`, Trading intelligence checklist `KrakenPendingOrderSurvival` |
| Spot/margin observation and trading readiness | Designed to track runtime state, open positions, stale ticks, and flight-test reboot decisions before action. Not a cleared trading session. | `/api/terminal-state`, `/api/flight-test`, `/api/reboot-advice` |
| Runtime resilience and recovery | Designed to show connected-but-guarded states, tick phase, route timeouts, executor in-flight state, and reboot advice. Not evidence a session is connected. | `/api/terminal-state`, `runtime_watchdog`, `executor_route_state` |
| Exchange clients | Provides exchange-specific adapters for market data, balances, and order paths through the runtime gates. | `kraken_client.py`, `binance_client.py`, `alpaca_client.py`, `capital_client.py` |
| Multi-exchange live market cache | Designed to keep Binance websocket/REST, Kraken public ticker, Alpaca snapshot, and Capital snapshot fields in one shared cache with per-source health. Not a claim a feed is connected. | `aureon/data_feeds/ws_market_data_feeder.py`, `aureon/data_feeds/unified_market_cache.py`, `ws_cache/ws_prices.json` |
| Planetary waveform history recorder | Designed to persist budgeted cache ticks into the global history database so multi-horizon models can compare a fresh reading against 1h-to-1y memory. Not a claim that recording is running. | `aureon/data_feeds/ws_market_data_feeder.py --history-recording`, `state/aureon_global_history.sqlite`, `state/aureon_live_waveform_recorder.json` |
| Cognitive order-intent path | Designed to let the cognitive layer observe, ask, reason, and emit order-intent evidence into the runtime rather than bypassing exchange gates. Not a cleared order path. | `aureon/autonomous/aureon_self_questioning_ai.py`, `aureon/autonomous/aureon_mind_thought_action_hub.py` |
| HNC/Auris harmonic affect reporting | Designed to write timestamped cognitive trade evidence, harmonic affect state, and benchmark fields. Not a measured live benchmark. | `aureon_cognitive_trade_evidence.py`, `aureon_harmonic_affect_state.py`, `aureon_live_cognition_benchmark.py` |
| Self-questioning and mind hub | Designed to run a local thought/action hub and self-questioning loop for operator-visible reasoning. Not a claim the loop is running. | `http://127.0.0.1:13002/api/thoughts` |
| Local OS/task capability | Queues goals, searches the repo, inspects files, and routes operator/voice tasks into visible state. | `aureon_local_task_queue.py`, `aureon_repo_explorer_service.py`, `aureon_voice_command_bridge.py` |
| LLM capability | Uses local LLM backends when available and AureonBrain fallback in audit mode. | `aureon/inhouse_ai/llm_adapter.py` |
| Code-writing capability | Designed to produce reviewable code tasks and patch proposals, route operator prompts through the organism, and connect to CodeArchitect/SkillLibrary. "Validated skills" here means checks the library is written to run. Not a measured validation of this checkout. | `aureon_safe_code_control.py`, `aureon_queen_code_bridge.py`, `aureon_coding_organism_bridge.py`, `aureon/code_architect/` |
| Operator coding organism bridge | Designed to accept a coding prompt from CLI or the mind hub, route it through `GoalExecutionEngine`, queue code work, run focused tests, publish who/what/where/when/how/act evidence, and write a finished-product audit. Not a claim a run has passed. | `aureon/autonomous/aureon_coding_organism_bridge.py`, `/api/coding/prompt`, `frontend/src/components/generated/AureonCodingOrganismConsole.tsx` |
| Director capability bridge | Designed to map Codex-class capabilities against Aureon module names, score ready/partial/gap coverage, and queue build prompts for missing bridge systems. Those scores are not a go-live clearance. | `aureon/autonomous/aureon_director_capability_bridge.py`, `docs/audits/aureon_director_capability_bridge.json`, `frontend/src/components/generated/AureonDirectorCapabilityBridgeConsole.tsx` |
| Desktop/run handoff | Connects finished coding products to a dry-run local desktop handoff and the VM/remote-control tool registry so inspection, browser checks, typing, clicking, shell runs, and screenshots are part of the same evidence flow. | `aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `state/aureon_coding_organism_desktop_state.json` |
| Desktop capability | Offers local desktop action proposals with dry-run default, arm/disarm, emergency stop, and allowlisted actions. | `aureon_safe_desktop_control.py`, `aureon_queen_desktop_bridge.py`, `aureon_laptop_control.py` |
| Unified autonomous console | Designed to show organism pulse, a runtime mirror, blockers, exchange state, an evolution queue, audits, and capability-mode labels. Not a live production console. | `frontend/src/App.tsx`, `frontend/src/services/aureonAutonomousFrontend.ts`, `frontend/src/hooks/useTerminalSync.ts` |
| Accounting/HMRC support pack tooling | Generates statutory support packs, CT support notes, and accounting evidence while keeping filing manual. | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py`, `aureon/queen/accounting_context_bridge.py` |
| SaaS/security/local authorized audit tooling | Catalogs SaaS/frontend surfaces, security blockers, authorized local findings, and migration work orders. | `aureon/autonomous/aureon_saas_system_inventory.py`, `aureon/autonomous/hnc_authorized_attack_lab.py` |
| Continuous self-audit | Designed to rebuild readiness, switchboard, catalog, and mind-wiring reports for the console and operator review. A rebuilt report is not a production clearance. | `aureon_organism_runtime_observer.py`, `aureon_system_readiness_audit.py`, `aureon_autonomous_capability_switchboard.py`, `aureon_repo_self_catalog.py`, `mind_wiring_audit.py` |

## HNC Use Cases For AI Logic

The Harmonic Nexus Core is the coherence and evidence logic layer used by Aureon agents. It does not override runtime gates, tests, or human review. It makes AI work inspectable by asking whether the available metadata is coherent enough to continue, which route owns the next action, and what proof must be written before handover.

| Use case | Practical meaning | Surfaces |
|---|---|---|
| Goal routing | Match an operator prompt to the right subsystem and capability route. | `aureon_goal_capability_map.py`, `aureon_autonomous_capability_switchboard.py` |
| Prompt logic | Build compact source packets, HNC/Auris context, redaction, and answer contracts before LLM use. | `aureon_dynamic_prompt_filter.py`, `aureon/inhouse_ai/llm_adapter.py` |
| Agent drift control | Hold generated work when scope, role, evidence, tests, or handover proof are incomplete. | `aureon_coding_organism_bridge.py`, `aureon_agent_creative_process_guardian.py` |
| Evidence grading | Classify proof as ready, stale, blocked, held, completed, or already correct. | `aureon_harmonic_affect_state.py`, audit JSON, frontend public mirrors |
| Research logic | Turn HNC research and simulations into traceable reports and reproducible commands. | `aureon_hnc_essay_benchmark.py`, `aureon/harmonic/harmonic_nexus_bridge.py`, `docs/` |
| Security reasoning | Route authorized local/staging findings into cognitive questions, fixes, and deployment blockers. | `hnc_saas_cognitive_bridge.py`, `hnc_saas_security_architect.py`, `hnc_authorized_attack_lab.py` |
| Knowledge memory | Preserve symbolic packets, route seals, vault state, and reusable reasoning artifacts. | `hnc_symbolic_route_seal.py`, `hnc_repo_singularity_vault.py`, `hnc_swarm_key_store.py` |

## Subsystem Atlas

| Subsystem | End-user purpose | Where to start |
|---|---|---|
| Launcher/supervisor | Designed to report what a launcher would start. This checkout does not claim the organism is alive. | `scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`, wake-up manifests |
| Exchange runtime | Bring Kraken, Binance, Alpaca, and Capital into one market state. | `aureon/exchanges/`, `/api/terminal-state` |
| Trading/portfolio/risk | Convert market state into readiness, intent, position, and execution evidence. | `aureon/trading/`, `aureon/portfolio/`, `aureon/strategies/` |
| Scanners/analytics | Find movement, anomalies, backtest context, and opportunity candidates. | `aureon/scanners/`, `aureon/analytics/` |
| Cognition/agents | Ask questions, route goals, choose capabilities, and expose thought/action state. | `aureon/autonomous/`, `/api/thoughts` |
| OS/code/desktop layer | Designed to search the repo, queue tasks, route coding prompts, propose code, run skills after the code path's own checks, audit a finished product, and hand off a local/remote desktop run. Not a measured validation. | `aureon_repo_explorer_service.py`, `aureon_coding_organism_bridge.py`, `aureon_safe_code_control.py`, `aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `aureon/code_architect/` |
| HNC/Auris evidence | Timestamp coherence, cognitive trade evidence, harmonic affect, and benchmark state. | `docs/audits/`, `aureon/autonomous/aureon_live_cognition_benchmark.py` |
| Frontend console | Designed as one local console surface for runtime, blockers, audits, and capability modes. Not a production endpoint. | `frontend/src/App.tsx`, `frontend/public/` |
| Accounting/HMRC support | Build evidence packs and manual filing support without changing accounts totals silently. | `Kings_Accounting_Suite/tools/`, `aureon/queen/accounting_context_bridge.py` |
| SaaS/security audit | Show frontend/SaaS blockers, owned-scope security findings, and migration work. | `aureon_saas_system_inventory.py`, `hnc_authorized_attack_lab.py` |
| Vault/research/memory | Keep local knowledge, learning history, research context, and voice/persona state. | `aureon/vault/`, `docs/`, `queen_research/` |
| Self-improvement | Catalog what exists, what is stale, and what can safely be improved next. | readiness audit, repo catalog, growth loop, self-enhancement lifecycle |

## Public Local Interfaces

| Interface | URL or file |
|---|---|
| Unified autonomous console | `http://127.0.0.1:8081/` |
| Runtime terminal state | `http://127.0.0.1:8791/api/terminal-state` |
| Flight test | `http://127.0.0.1:8791/api/flight-test` |
| Reboot advice | `http://127.0.0.1:8791/api/reboot-advice` |
| Mind thoughts | `http://127.0.0.1:13002/api/thoughts` |
| Coding organism prompt | `POST http://127.0.0.1:13002/api/coding/prompt` |
| Coding organism status | `http://127.0.0.1:13002/api/coding/status` |
| Director capability bridge | `docs/audits/aureon_director_capability_bridge.json` and `frontend/public/aureon_director_capability_bridge.json` |
| Coding desktop handoff state | `state/aureon_coding_organism_desktop_state.json` |
| Wake-up manifest | `state/aureon_wake_up_manifest.json` |
| Frontend manifest mirror | `frontend/public/aureon_wake_up_manifest.json` |
| Cognitive trade evidence | `docs/audits/aureon_cognitive_trade_evidence.json` |
| Harmonic affect state | `docs/audits/aureon_harmonic_affect_state.json` and `frontend/public/aureon_harmonic_affect_state.json` |
| Exchange monitoring checklist | `docs/audits/aureon_exchange_monitoring_checklist.json` and `frontend/public/aureon_exchange_monitoring_checklist.json` |
| Exchange data capability matrix | `docs/audits/aureon_exchange_data_capability_matrix.json` and `frontend/public/aureon_exchange_data_capability_matrix.json` |
| Global financial coverage map | `docs/audits/aureon_global_financial_coverage_map.json` and `frontend/public/aureon_global_financial_coverage_map.json` |
| Data ocean status | `state/aureon_data_ocean_status.json` and `frontend/public/aureon_data_ocean_status.json` |
| Official exchange rate budget evidence | `state/aureon_data_ocean_status.json#sources[*].official_rate_limit` and `/api/terminal-state#api_governor` |

## Runtime Modes

These names are design labels. Go-live stays HOLD. None of them is a measured live session, and `guarded_live_action` is not cleared.

| Mode | Meaning |
|---|---|
| `safe_observation` | Design label for a runtime or feed that is offline, or for an environment that is not in live mode. |
| `guarded_observe_plan` | Design label for a runtime whose action is blocked by evidence such as stale data, booting state, open-position reboot timing, or an unavailable downtime window. |
| `guarded_live_action` | Design label for a fresh runtime with live mode and real-order capability enabled and gates clear. This checkout does not report that state. |

`ok:false` from that API is designed so it does not always mean offline. A fresh heartbeat and status file are designed to mean connected-but-guarded. That is not a supported live instance. The fields a reader would use are `stale_reason`, `tick_phase`, `executor_route_state`, and reboot advice.

## Exchange Coverage

Designed roles. Not a cleared live book. Go-live stays HOLD.

| Exchange | Designed role |
|---|---|
| Kraken | Spot/margin-capable crypto client with tradable asset registry, maker/taker fee fields, leverage map, pending-order survival, take-profit route, fast-profit monitor, and a runtime-gated order path. Go-live does not clear that path. |
| Binance | Market and trade adapter with symbol normalization and account readiness checks. Not a claim an account is connected. |
| Alpaca | Stocks/crypto adapter with account and position readiness checks. Not a claim an account is connected. |
| Capital | CFD account and position adapter with tradable asset registry, portfolio survival envelope, lane fields, no-loss hold queue, broker take-profit, pending-order survival, and fast-profit fields. Not a cleared live book, and not signed trade evidence. |

The unified runtime is the module the design names for coordinating these clients. Individual exchange bots are not an approved public run path.

## Manual Boundaries

The code is written to generate evidence, reports, runtime state, order intent, and accounting support packs. That does not remove the need for configured credentials, runtime freshness, safe reboot windows, valid exchange permissions, or manual review of filings/payments. Official filings, payments, credential reveal, and unowned security mutation remain manual or explicitly authorized operations. None of this map is a go-live clearance.
