# Aureon Current Capabilities

This document describes the current public runtime surfaces and capability map. For commands, see [RUNNING.md](RUNNING.md) and [QUICK_START.md](QUICK_START.md). For a deeper end-user explanation of how all subsystems connect, see [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md).

## Current Full-System Entrypoint

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791
```

Safe launcher validation:

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
```

Dev/audit ignition:

```powershell
python scripts/aureon_ignition.py --audit-only
```

Low-priority data ocean supervisor:

```powershell
.\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable
```

## Capability Table

| Capability | What it does | Primary surfaces |
|---|---|---|
| Live/safe runtime supervision | Starts and supervises the organism from one terminal, publishes manifests, and keeps reboot timing visible. | `AUREON_PRODUCTION_LIVE.cmd`, `AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` |
| Multi-exchange market coverage | Runs unified market telemetry and exchange readiness for Kraken, Binance, Alpaca, and Capital. | `aureon/exchanges/unified_market_trader.py`, `aureon/exchanges/unified_market_status_server.py` |
| Planetary financial data ocean | Maps configured/licensed financial signals across exchanges, history, macro, news, on-chain, forecasts, and internal knowledge without competing with execution/risk loops. | `AUREON_DATA_OCEAN.cmd`, `aureon/autonomous/aureon_data_ocean.py`, `aureon_global_financial_coverage_map.py` |
| Official exchange rate budgets | Records Binance, Kraken, Alpaca, and Capital provider limits, then builds cash-aware call plans that reserve execution capacity and boost idle/no-cash venue discovery safely. | `aureon/core/exchange_rate_limit_registry.py`, `api_governor`, `state/aureon_data_ocean_status.json` |
| Exchange data capability matrix | Shows what each exchange can observe, trade, leverage, and optimize: data channels, modes, feed freshness, decision-fed state, call budget, gaps, and next optimization. | `aureon/autonomous/aureon_exchange_data_capability_matrix.py`, `docs/audits/aureon_exchange_data_capability_matrix.json`, `frontend/public/aureon_exchange_data_capability_matrix.json` |
| Capital wave-validated portfolio brain | Lets Capital expand beyond fixed buy/sell lanes only when portfolio memory, margin survival, stress buffer, cross-exchange waveform checks, and confidence ratchet pass. | `aureon/exchanges/capital_cfd_trader.py`, `/api/terminal-state#capital_risk_envelope`, Trading console Capital Survival Brain |
| Capital tradable asset registry | Records every discovered Capital market, epic, estimated cost, margin, leverage, minimum deal size, and the exact buy/sell/close/pending-order code route. | `aureon/exchanges/capital_asset_registry.py`, `state/capital_tradable_asset_registry.sqlite`, `docs/audits/aureon_capital_tradable_asset_registry.json` |
| Capital pending order survival | Plans limit bids with broker take-profit evidence and blocks unsafe working-order ladders by assuming every pending order fills together. | `capital_pending_order_envelope`, `CapitalClient.place_working_order`, `CapitalClient.update_position_limits` |
| Kraken spot/margin asset registry | Records Kraken AssetPairs, ticker/spread, order minimum, cost minimum, maker/taker fee tiers, margin leverage, take-profit route, and exact spot/margin code route. | `aureon/exchanges/kraken_asset_registry.py`, `state/kraken_tradable_asset_registry.sqlite`, `/api/terminal-state#kraken_asset_registry` |
| Kraken pending order survival | Stress-tests planned crypto spot/margin ladders as if every pending order fills, including spot quote budget, maker/taker fees, margin collateral, and stress-loss buffer. | `build_kraken_order_survival_envelope`, Trading intelligence checklist `KrakenPendingOrderSurvival` |
| Spot/margin observation and trading readiness | Tracks runtime state, open positions, stale ticks, and flight-test reboot decisions before action. | `/api/terminal-state`, `/api/flight-test`, `/api/reboot-advice` |
| Runtime resilience and recovery | Shows connected-but-guarded states, tick phase, route timeouts, executor in-flight state, and safe reboot advice. | `/api/terminal-state`, `runtime_watchdog`, `executor_route_state` |
| Exchange clients | Provides exchange-specific adapters for market data, balances, and order paths through the runtime gates. | `kraken_client.py`, `binance_client.py`, `alpaca_client.py`, `capital_client.py` |
| Multi-exchange live market cache | Keeps Binance websocket/REST, Kraken public ticker, Alpaca snapshot, and Capital snapshot evidence in one shared cache with per-source health so scanners can use fresh venue data without overloading APIs. | `aureon/data_feeds/ws_market_data_feeder.py`, `aureon/data_feeds/unified_market_cache.py`, `ws_cache/ws_prices.json` |
| Planetary waveform history recorder | Persists budgeted live cache ticks into the global history database so multi-horizon models can compare fresh energy against 1h-to-1y memory. | `aureon/data_feeds/ws_market_data_feeder.py --history-recording`, `state/aureon_global_history.sqlite`, `state/aureon_live_waveform_recorder.json` |
| Cognitive order-intent path | Lets the cognitive layer observe, ask, reason, and emit order-intent evidence into the runtime rather than bypassing exchange gates. | `aureon/autonomous/aureon_self_questioning_ai.py`, `aureon/autonomous/aureon_mind_thought_action_hub.py` |
| HNC/Auris harmonic affect reporting | Produces timestamped cognitive trade evidence, harmonic affect state, and benchmark reporting. | `aureon_cognitive_trade_evidence.py`, `aureon_harmonic_affect_state.py`, `aureon_live_cognition_benchmark.py` |
| Self-questioning and mind hub | Runs the local thought/action hub and self-questioning loop for operator-visible reasoning. | `http://127.0.0.1:13002/api/thoughts` |
| Local OS/task capability | Queues goals, searches the repo, inspects files, and routes operator/voice tasks into visible state. | `aureon_local_task_queue.py`, `aureon_repo_explorer_service.py`, `aureon_voice_command_bridge.py` |
| LLM capability | Uses local LLM backends when available and AureonBrain fallback in audit mode. | `aureon/inhouse_ai/llm_adapter.py` |
| Code-writing capability | Produces reviewable code tasks and patch proposals, routes operator prompts through the organism, and connects to CodeArchitect/SkillLibrary for validated skills. | `aureon_safe_code_control.py`, `aureon_queen_code_bridge.py`, `aureon_coding_organism_bridge.py`, `aureon/code_architect/` |
| Operator coding organism bridge | Accepts a coding prompt from CLI or the mind hub, routes it through `GoalExecutionEngine`, queues safe code work, runs focused tests, publishes who/what/where/when/how/act evidence, and creates the finished-product audit. | `aureon/autonomous/aureon_coding_organism_bridge.py`, `/api/coding/prompt`, `frontend/src/components/generated/AureonCodingOrganismConsole.tsx` |
| Director capability bridge | Maps Codex-class capabilities against Aureon's current systems, scores ready/partial/gap coverage, and queues exact Aureon build prompts for missing bridge systems. | `aureon/autonomous/aureon_director_capability_bridge.py`, `docs/audits/aureon_director_capability_bridge.json`, `frontend/src/components/generated/AureonDirectorCapabilityBridgeConsole.tsx` |
| Desktop/run handoff | Connects finished coding products to a dry-run local desktop handoff and the VM/remote-control tool registry so inspection, browser checks, typing, clicking, shell runs, and screenshots are part of the same evidence flow. | `aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `state/aureon_coding_organism_desktop_state.json` |
| Desktop capability | Offers local desktop action proposals with dry-run default, arm/disarm, emergency stop, and allowlisted actions. | `aureon_safe_desktop_control.py`, `aureon_queen_desktop_bridge.py`, `aureon_laptop_control.py` |
| Unified autonomous console | Shows organism pulse, runtime mirror, blockers, exchange state, evolution queue, audits, and current capability modes. | `frontend/src/App.tsx`, `frontend/src/services/aureonAutonomousFrontend.ts`, `frontend/src/hooks/useTerminalSync.ts` |
| Accounting/HMRC support pack tooling | Generates statutory support packs, CT support notes, and accounting evidence while keeping filing manual. | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py`, `aureon/queen/accounting_context_bridge.py` |
| SaaS/security/local authorized audit tooling | Catalogs SaaS/frontend surfaces, security blockers, authorized local findings, and migration work orders. | `aureon/autonomous/aureon_saas_system_inventory.py`, `aureon/autonomous/hnc_authorized_attack_lab.py` |
| Continuous self-audit | Rebuilds readiness, switchboard, catalog, and mind-wiring reports for the console and operator review. | `aureon_organism_runtime_observer.py`, `aureon_system_readiness_audit.py`, `aureon_autonomous_capability_switchboard.py`, `aureon_repo_self_catalog.py`, `mind_wiring_audit.py` |

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
| Launcher/supervisor | Start the whole organism once and know what is alive. | `AUREON_PRODUCTION_LIVE.cmd`, wake-up manifests |
| Exchange runtime | Bring Kraken, Binance, Alpaca, and Capital into one market state. | `aureon/exchanges/`, `/api/terminal-state` |
| Trading/portfolio/risk | Convert market state into readiness, intent, position, and execution evidence. | `aureon/trading/`, `aureon/portfolio/`, `aureon/strategies/` |
| Scanners/analytics | Find movement, anomalies, backtest context, and opportunity candidates. | `aureon/scanners/`, `aureon/analytics/` |
| Cognition/agents | Ask questions, route goals, choose capabilities, and expose thought/action state. | `aureon/autonomous/`, `/api/thoughts` |
| OS/code/desktop layer | Search the repo, queue tasks, route coding prompts, propose code, execute validated skills, audit the finished product, and drive local/remote desktop run handoffs through safe controllers. | `aureon_repo_explorer_service.py`, `aureon_coding_organism_bridge.py`, `aureon_safe_code_control.py`, `aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `aureon/code_architect/` |
| HNC/Auris evidence | Timestamp coherence, cognitive trade evidence, harmonic affect, and benchmark state. | `docs/audits/`, `aureon/autonomous/aureon_live_cognition_benchmark.py` |
| Frontend console | Give the operator a single live surface for runtime, blockers, audits, and capability modes. | `frontend/src/App.tsx`, `frontend/public/` |
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

| Mode | Meaning |
|---|---|
| `safe_observation` | Runtime/feed is offline, or the environment is not in live mode. |
| `guarded_observe_plan` | Runtime is live but action is blocked by evidence such as stale data, booting state, open-position reboot timing, or unavailable downtime window. |
| `guarded_live_action` | Runtime is fresh, live mode is enabled, real order capability is enabled, and all runtime gates are clear. |

`ok:false` from the runtime does not always mean offline. If the heartbeat and status file are fresh, Aureon is connected but guarded; use `stale_reason`, `tick_phase`, `executor_route_state`, and reboot advice to decide what happens next.

## Exchange Coverage

| Exchange | Current role |
|---|---|
| Kraken | Spot/margin-capable crypto client with tradable asset registry, maker/taker fee evidence, leverage map, pending-order survival, take-profit route, fast-profit monitor, and runtime-gated live execution path. |
| Binance | Market and trade adapter with symbol normalization and account readiness checks. |
| Alpaca | Stocks/crypto adapter with account and position readiness checks. |
| Capital | CFD account and position adapter with tradable asset registry, portfolio survival envelope, dynamic live lanes, no-loss hold queue, broker take-profit, pending-order survival, fast profit capture, and signed trade evidence. |

The unified runtime is responsible for coordinating these clients. Individual exchange bots are not the recommended public run path.

## Manual Boundaries

Aureon can generate evidence, reports, runtime state, order intent, and accounting support packs. It does not remove the need for configured credentials, runtime freshness, safe reboot windows, valid exchange permissions, or manual review of filings/payments. Official filings, payments, credential reveal, and unowned security mutation remain manual or explicitly authorized operations.
