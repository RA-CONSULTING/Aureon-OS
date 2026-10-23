# Aureon Whole-System Guide

This guide explains Aureon as a complete operating system, not a single trading bot. It is written for an end user who wants to understand what starts, what each subsystem does, where evidence is written, and how the pieces connect.

For run commands, start with [RUNNING.md](RUNNING.md). For the short version, use [QUICK_START.md](QUICK_START.md). For a capability matrix, use [CAPABILITIES.md](CAPABILITIES.md).

## One Sentence

Aureon is a local autonomous trading, cognition, evidence, audit, frontend, research, and accounting organism that observes markets through multiple exchange clients, reasons through cognitive/HNC layers, exposes state in a unified console, and only acts when the configured live runtime and exchange conditions are valid.

## First Mental Model

Think of Aureon as eight connected layers:

| Layer | What it answers | Main outputs |
|---|---|---|
| Launcher and supervisor | What is running, on which port, and with which mode? | Wake-up manifest, logs, process supervision |
| Exchange and market runtime | What do Binance, Kraken, Alpaca, and Capital currently show? | Runtime feed, balances, positions, readiness |
| Trading and portfolio logic | Can this opportunity become a valid action? | Position state, order intent, risk/readiness evidence |
| Cognition and agents | What is the system thinking, asking, and choosing next? | Thought stream, task queue, self-questioning records |
| HNC/Auris evidence | Are signals, coherence, affect, and outcomes timestamped? | Cognitive trade evidence, harmonic affect reports |
| Frontend console | What can the operator see now? | Unified autonomous console at `http://127.0.0.1:8081/` |
| Accounting and filing support | What evidence supports manual accounts and tax work? | Statutory filing pack, HMRC support notes, checklists |
| Audits, security, and self-improvement | What is stale, blocked, missing, or ready to improve? | Readiness audit, switchboard, repo catalog, SaaS/security inventory |

## Current Full-System Entrypoint

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791
```

Safe validation:

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
```

Development and audit ignition:

```powershell
python scripts/aureon_ignition.py --audit-only
```

## What Starts In Production

| Component | Purpose | Path or URL |
|---|---|---|
| Production wrapper | Windows command entrypoint for the full organism | `AUREON_PRODUCTION_LIVE.cmd` |
| Wake-up launcher | Starts and supervises the runtime stack | `AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` |
| Market runtime | Coordinates market/exchange state | `aureon/exchanges/unified_market_trader.py` |
| Status server | Publishes local runtime endpoints | `aureon/exchanges/unified_market_status_server.py` |
| Frontend console | Operator view for state, blockers, and capability modes | `http://127.0.0.1:8081/` |
| Mind hub | Local thought/action HTTP surface | `http://127.0.0.1:13002/api/thoughts` |
| Self-questioning loop | Keeps questions, goals, and next actions moving | `aureon/autonomous/aureon_self_questioning_ai.py` |
| Organism observer | Refreshes organism status and audit manifests | `aureon/autonomous/aureon_organism_runtime_observer.py` |
| Wake-up manifest | Tells frontend and operators which ports/endpoints are live | `state/aureon_wake_up_manifest.json` |
| Frontend manifest mirror | Same manifest copied for the browser app | `frontend/public/aureon_wake_up_manifest.json` |

## Live Runtime Endpoints

| Endpoint | What to use it for |
|---|---|
| `http://127.0.0.1:8791/api/terminal-state` | Current trading readiness, exchange readiness, stale state, positions, account/runtime mirror |
| `http://127.0.0.1:8791/api/flight-test` | Internal flight test: can the system safely restart or act now? |
| `http://127.0.0.1:8791/api/reboot-advice` | Human-readable reboot/recovery decision |
| `http://127.0.0.1:13002/api/thoughts` | Mind hub thoughts and action context |

## Core Data Flow

```text
Exchange clients
  -> unified market runtime
  -> runtime status server
  -> organism observer
  -> cognitive trade evidence + harmonic affect state
  -> frontend unified console
  -> operator review / runtime-gated action path
```

Accounting and audit flows run beside the trading loop:

```text
Repo files + accounting inputs + runtime manifests
  -> accounting/context/audit tools
  -> generated support packs and audit JSON
  -> frontend/public mirrors where needed
  -> operator review
```

## Exchange And Market Coverage

| Exchange | Current role | Key files |
|---|---|---|
| Kraken | Spot and margin-oriented market/account path, fee tracking, diagnostics, adapters | `aureon/exchanges/kraken_client.py`, `aureon/exchanges/kraken_trading_adapter.py`, `aureon/exchanges/kraken_margin_penny_trader.py`, `aureon/exchanges/kraken_diagnostics.py` |
| Binance | Market data, symbol normalization, account readiness, diagnostics, websocket/client support | `aureon/exchanges/binance_client.py`, `aureon/exchanges/binance_ws_client.py`, `aureon/exchanges/binance_uk_allowed_pairs.py`, `aureon/exchanges/binance_diagnostics.py` |
| Alpaca | Stocks/crypto account and position readiness, SSE stream, options/client extensions | `aureon/exchanges/alpaca_client.py`, `aureon/exchanges/alpaca_sse_client.py`, `aureon/exchanges/alpaca_options_client.py`, `aureon/exchanges/alpaca_position_audit.py` |
| Capital | CFD account, market monitoring, stock cache feeder, swarm runner | `aureon/exchanges/capital_client.py`, `aureon/exchanges/capital_cfd_trader.py`, `aureon/exchanges/capital_market_monitor.py`, `aureon/exchanges/capital_swarm_runner.py` |
| External/on-chain data | Price, anomaly, and on-chain providers used as context | `aureon/exchanges/onchain_providers.py`, `aureon/exchanges/coingecko_price_feeder.py`, `aureon/exchanges/coinapi_anomaly_detector.py`, `aureon/exchanges/glassnode_client.py` |

The unified runtime is the public run path. Individual exchange tools are useful for diagnostics, development, or focused checks.

The operator-facing exchange data capability matrix is generated by `aureon/autonomous/aureon_exchange_data_capability_matrix.py`. It shows, per exchange, what data channels are wired, which trading modes are possible, whether the live feed is fresh, whether the exchange is feeding decision logic, which official call budget applies, and what should be optimized next. Its public outputs are:

```text
docs/audits/aureon_exchange_data_capability_matrix.json
docs/audits/aureon_exchange_data_capability_matrix.md
frontend/public/aureon_exchange_data_capability_matrix.json
```

## Trading, Portfolio, And Strategy Layer

| Area | What it does | Representative paths |
|---|---|---|
| Trading engines | Strategy and execution logic behind the runtime path | `aureon/trading/`, `aureon/strategies/`, `aureon/conversion/` |
| Portfolio state | Tracks balances, positions, and account truth surfaces | `aureon/portfolio/`, `real_portfolio_state.json` |
| Scanners | Finds market movement, momentum, anomalies, and signal candidates | `aureon/scanners/` |
| Analytics | Backtests, measurements, and performance analysis | `aureon/analytics/` |
| Monitors | Watches runtime and market conditions | `aureon/monitors/`, `scripts/validation/verify_trading_activity.py` |
| Exchange verification | Flight checks and platform connectivity validation | `scripts/validation/verify_platform_connectivity.py`, `scripts/validation/verify_exchange_cycles.py`, `scripts/validation/flight_check_unified_margin_trader.py` |

Trading action depends on runtime truth: fresh ticks, exchange readiness, valid credentials, order permissions, position state, and the configured live mode. The docs keep those conditions visible because they are part of reliable trading, not a side feature.

## Cognition, Agents, And Goal Flow

| Area | What it does | Representative paths |
|---|---|---|
| Self-questioning loop | Keeps Aureon asking what it should inspect, validate, or improve next | `aureon/autonomous/aureon_self_questioning_ai.py` |
| Mind hub | HTTP thought/action hub used by the console and operator | `aureon/autonomous/aureon_mind_thought_action_hub.py` |
| Capability switchboard | Maps major abilities and blocker states | `aureon/autonomous/aureon_autonomous_capability_switchboard.py` |
| Goal/capability map | Connects user goals to available subsystem routes | `aureon/autonomous/aureon_goal_capability_map.py` |
| Local task queue | Keeps local tasks inspectable | `aureon/autonomous/aureon_local_task_queue.py` |
| Queen/autonomy bridges | Bridges cognition to exchange, desktop, code, and runtime context | `aureon/autonomous/aureon_queen_exchange_autonomy.py`, `aureon/autonomous/aureon_queen_code_bridge.py`, `aureon/autonomous/aureon_queen_desktop_bridge.py` |
| In-house AI | Local model/adapters and reasoning helpers | `aureon/inhouse_ai/`, `aureon/cognition/`, `aureon/intelligence/` |

The cognitive layer should be read as an evidence-producing controller: it reasons, routes, asks, and proposes. The runtime feed and exchange clients determine what can become live action.

## Operating System, LLM, Code, Skills, And Desktop Control

Aureon also has local operating-system style capabilities. This is the part of the organism that can inspect the repo, queue tasks, reason through local/in-house LLM adapters, produce code proposals, route voice/text intents, execute validated skills, and control the local desktop through a constrained action layer.

| Capability | What is active | Key paths |
|---|---|---|
| Repo explorer | Read-only file listing, text search, and file inspection for task/code context | `aureon/autonomous/aureon_repo_explorer_service.py` |
| Local task queue | Persistent visible task queue for operator and agent goals | `aureon/autonomous/aureon_local_task_queue.py` |
| Repo task bridge | Turns repo findings into queued local tasks | `aureon/autonomous/aureon_repo_task_bridge.py` |
| LLM adapter layer | Backend-agnostic prompt/stream interface for local LLMs, hybrid mode, and AureonBrain fallback | `aureon/inhouse_ai/llm_adapter.py` |
| Cognitive authoring loop | Observes gaps and routes validated skill/code authoring through CodeArchitect | `aureon/core/aureon_cognitive_authoring_loop.py` |
| CodeArchitect | Authors, validates, stores, and executes skills through the SkillLibrary pipeline | `aureon/code_architect/` |
| Safe code control | Queues code tasks, patch proposals, and file-edit proposals for review | `aureon/autonomous/aureon_safe_code_control.py` |
| Queen code bridge | Routes ThoughtBus/code events into safe code proposals | `aureon/autonomous/aureon_queen_code_bridge.py` |
| Skill executor bridge | Turns aligned goals into skill artefacts and vault cards | `aureon/vault/voice/skill_executor_bridge.py` |
| Voice command bridge | Routes text/speech commands into repo search, tasks, code proposals, and desktop actions | `aureon/autonomous/aureon_voice_command_bridge.py` |
| Conversation loop | Operator-facing conversation route into local capabilities | `aureon/autonomous/aureon_conversation_loop.py` |
| Safe desktop control | Local-only desktop automation with dry-run default, arm/disarm, emergency stop, and allowlisted actions | `aureon/autonomous/aureon_safe_desktop_control.py` |
| Queen desktop bridge | ThoughtBus-to-desktop proposal bridge | `aureon/autonomous/aureon_queen_desktop_bridge.py` |
| Laptop control abstraction | Raw local hardware/OS abstraction layer for screenshots, windows, clipboard, voice, camera, and system state | `aureon/autonomous/aureon_laptop_control.py` |

The active public control path is the safe layer:

```text
operator / voice / ThoughtBus
  -> intent cognition
  -> repo explorer / task queue / code proposal queue / desktop proposal queue
  -> review, arm, approve, test, or execute
  -> persisted state under state/
```

Important operating boundaries:

- Code proposals queue for review by default. `AUREON_CODE_AUTO_APPROVE=1` is an explicit opt-in and still does not apply patches by itself.
- Desktop control is local-only, dry-run by default, and requires arming before execution.
- The raw laptop abstraction exists, but public docs should route users through `SafeDesktopControl` and bridges first.
- Audit-mode LLM calls do not require an external model server; `AureonHybridAdapter` falls back to `AureonBrain`.

Validated active checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_safe_code_control.py tests/test_inhouse_llm_adapter_audit_mode.py tests/test_goal_capability_map.py tests/test_capability_growth_loop.py tests/vault/test_skill_executor_bridge.py -q
```

## HNC, Auris, Harmonic, And Research Evidence

| Area | What it does | Representative paths |
|---|---|---|
| HNC evidence | Creates timestamped cognitive trade and harmonic affect evidence | `aureon/autonomous/aureon_cognitive_trade_evidence.py`, `aureon/autonomous/aureon_harmonic_affect_state.py` |
| Live cognition benchmark | Measures how quickly cognition and runtime evidence respond | `aureon/autonomous/aureon_live_cognition_benchmark.py` |
| Harmonic modules | Frequency, coherence, and harmonic signal work | `aureon/harmonic/`, `run_hnc_live.py`, `run_dj_resonance.py` |
| Wisdom modules | Historical, symbolic, and research-inspired reasoning layers | `aureon/wisdom/`, `wisdom_data/`, `queen_research/` |
| Decoders | Domain-specific symbolic/market decoders | `aureon/decoders/` |
| Research docs | Public research, claims, evidence, and reading paths | `docs/`, `LIVE_PROOF.md`, `DATA_FLOW.md` |

Key generated evidence paths:

```text
docs/audits/aureon_cognitive_trade_evidence.json
docs/audits/aureon_harmonic_affect_state.json
frontend/public/aureon_harmonic_affect_state.json
```

## Frontend Unified Autonomous Console

| Area | What it does | Paths |
|---|---|---|
| App shell | Main React/Vite app | `frontend/src/App.tsx` |
| Autonomous frontend service | Loads audits, manifests, runtime feed, and public JSON mirrors | `frontend/src/services/aureonAutonomousFrontend.ts` |
| Terminal sync hook | Keeps runtime feed visible in the UI | `frontend/src/hooks/useTerminalSync.ts` |
| Trading and service helpers | Browser-side services for trading/status surfaces | `frontend/src/services/` |
| Pages and components | Operator, systems, war room, and unified views | `frontend/src/pages/`, `frontend/src/components/` |
| Public mirrors | Browser-readable generated JSON | `frontend/public/` |

The console is where an end user sees the organism state, runtime mirror, blockers, stale/missing manifests, exchange state, evolution queue, and capability modes.

## Accounting And HMRC Support

| Area | What it does | Paths |
|---|---|---|
| Statutory filing pack | Builds manual filing support packs and HMRC/Companies House evidence | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py` |
| Full company accounts | Builds full accounts support files | `Kings_Accounting_Suite/tools/generate_full_company_accounts.py` |
| Period accounts pack | Builds accounting-period views | `Kings_Accounting_Suite/tools/build_period_accounts_pack.py` |
| CT/HMRC requirements brain | Maps support docs to UK filing requirements | `Kings_Accounting_Suite/tools/uk_accounting_requirements_brain.py` |
| Accounting context bridge | Connects accounting state into Aureon context | `aureon/queen/accounting_context_bridge.py` |
| Handoff pack | Builds accountant/operator handoff evidence | `Kings_Accounting_Suite/tools/accounting_handoff_pack.py` |
| Raw data intake and enrichment | Normalizes and labels accounting inputs | `Kings_Accounting_Suite/tools/company_raw_data_intake.py`, `Kings_Accounting_Suite/tools/accounting_report_enrichment.py` |

Accounting output is support evidence. Official submissions and payments remain manual unless a future operator explicitly configures an authorized workflow.

## SaaS, Security, And Authorized Local Audit

| Area | What it does | Paths |
|---|---|---|
| SaaS inventory | Catalogs frontend/SaaS surfaces, orphaned routes, and blockers | `aureon/autonomous/aureon_saas_system_inventory.py` |
| Frontend unification plan | Maps legacy and current frontend surfaces into the unified console | `aureon/autonomous/aureon_frontend_unification_plan.py` |
| Evolution queue | Queues adapter/migration work with blockers visible | `aureon/autonomous/aureon_frontend_evolution_queue.py` |
| Security architecture | Produces local/owned-scope security planning | `aureon/autonomous/hnc_saas_security_architect.py` |
| Authorized attack lab | Runs authorized local or owned-scope tests only | `aureon/autonomous/hnc_authorized_attack_lab.py` |
| Safe code/desktop control | Local safety wrappers for code and desktop actions | `aureon/autonomous/aureon_safe_code_control.py`, `aureon/autonomous/aureon_safe_desktop_control.py` |

Security tooling is designed to show blockers, owned scope, and evidence. It is not for unowned targets.

## Vault, Memory, Research, And Voice

| Area | What it does | Paths |
|---|---|---|
| Vault memory | Stores local memory, context, self-feedback, and research bridges | `aureon/vault/` |
| Voice/persona layer | Thought stream, self-dialogue, goal dispatch, and persona action helpers | `aureon/vault/voice/` |
| Obsidian bridge | Connects local research/vault surfaces | `aureon/vault/obsidian_adapter.py`, `.obsidian/` |
| Memory files | Historical learning, predictions, and node state | `adaptive_learning_history.json`, `brain_predictions_history.json`, `miner_brain_knowledge.json`, `queen_elephant_memory.json` |
| Research corpus | Public docs, research notes, and evidence references | `docs/`, `queen_research/`, `wisdom_data/` |

These layers help Aureon keep context over time. Large local memory files are operational artifacts and should not be treated as public secrets.

## Command Centers, Legacy Surfaces, And Migration

| Area | What it does | Paths |
|---|---|---|
| Command centers | Local dashboards and older command surfaces being cataloged/migrated | `aureon/command_centers/` |
| War room / systems UI | Frontend pages for operator and system views | `frontend/src/pages/WarRoom.tsx`, `frontend/src/pages/Systems.tsx` |
| Legacy trader scripts | Older TypeScript/Python experiments and adapters | `scripts/traders/` |
| Windows helpers | Windows setup, terminal, and quick-reference docs | `docs/windows/` |

The current public run path is still the production launcher. Older command centers and trader scripts remain useful as inventory, diagnostics, or migration sources.

## Self-Audit And Continuous Improvement

| Audit | What it answers | Path |
|---|---|---|
| Organism runtime observer | What is the organism pulse now? | `aureon/autonomous/aureon_organism_runtime_observer.py` |
| System readiness audit | What is ready, stale, blocked, or missing? | `aureon/autonomous/aureon_system_readiness_audit.py` |
| Capability switchboard | Which major modes are ready or blocked? | `aureon/autonomous/aureon_autonomous_capability_switchboard.py` |
| Repo self-catalog | What files and surfaces exist? | `aureon/autonomous/aureon_repo_self_catalog.py` |
| Mind wiring audit | Are thought/cognition services wired? | `aureon/autonomous/mind_wiring_audit.py` |
| Capability growth loop | What should be improved next? | `aureon/autonomous/aureon_capability_growth_loop.py` |
| Self-enhancement lifecycle | What generated change passed proposal, patch, test, and retest? | `aureon/autonomous/aureon_self_enhancement_lifecycle.py` |

The console surfaces many of these reports from `docs/audits/` and `frontend/public/`.

## End-User Journeys

| Goal | Start here | Then inspect |
|---|---|---|
| Run the full organism | [RUNNING.md](RUNNING.md) | `8081`, `/api/terminal-state`, wake-up manifest |
| Understand every capability | [CAPABILITIES.md](CAPABILITIES.md) | This guide and `docs/audits/` |
| Check if trading can act | `/api/terminal-state` | `trading_ready`, `data_ready`, `stale`, open positions, exchange readiness |
| Check if reboot is safe | `/api/flight-test` | `can_reboot_now`, downtime window, open-position state |
| See the cognitive layer | `/api/thoughts` | self-questioning logs, mind hub output, cognitive trade evidence |
| Benchmark live cognition | `aureon/autonomous/aureon_live_cognition_benchmark.py` | benchmark report JSON/Markdown |
| Generate accounting support | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py` | filing pack manifest, checklist, support notes |
| Inspect security/SaaS blockers | `aureon/autonomous/aureon_saas_system_inventory.py` | frontend unification plan, attack lab report |
| Add a frontend adapter | `aureon_frontend_evolution_queue.py` | generated work order and read-only component path |

## What Aureon Can Do

- Run a full local production organism from one terminal.
- Observe multiple exchange accounts and market feeds.
- Publish local runtime state, flight tests, and reboot advice.
- Keep the operator console synchronized with live runtime and audit evidence.
- Route market observations through cognitive and HNC evidence layers.
- Produce timestamped cognitive trade, harmonic affect, and benchmark reports.
- Track stale data, open positions, boot state, and downtime windows.
- Generate accounting/HMRC support packs while preserving manual filing boundaries.
- Catalog frontend/SaaS surfaces and queue migration work.
- Run authorized local/owned-scope security audits.
- Maintain local memory, research, and self-improvement manifests.

## What Still Requires Operator Responsibility

- Supplying and protecting exchange credentials.
- Confirming live trading risk and exchange permissions.
- Reviewing any official filing, tax, payment, or legal submission.
- Keeping API withdrawals disabled.
- Confirming security testing scope is local, owned, or explicitly authorized.
- Reviewing generated code or adapters before publishing them.

## Troubleshooting Map

| Symptom | Where to look |
|---|---|
| Console says runtime offline | `state/aureon_wake_up_manifest.json`, `frontend/public/aureon_wake_up_manifest.json`, status server port |
| Runtime is connected but action is blocked | `/api/terminal-state`, `/api/flight-test`, `/api/reboot-advice` |
| Mind hub restarts repeatedly | `logs/wake_up/mind_thought_action_hub.out.log`, `http://127.0.0.1:13002/api/thoughts` |
| Exchange coverage looks incomplete | Exchange readiness in `/api/terminal-state`, then exchange client diagnostics |
| HNC affect state is stale | `docs/audits/aureon_harmonic_affect_state.json`, `aureon_harmonic_affect_state.py` |
| Accounting pack needs refreshed | statutory filing pack generator and accounting requirements brain |
| Frontend shows blind spots | `aureon_frontend_evolution_queue.py`, `aureon_saas_system_inventory.py`, `docs/audits/` |

## Verification Commands

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
.\.venv\Scripts\python.exe -m pytest tests/test_ignition_live_profile.py tests/test_unified_market_status_server.py tests/test_aureon_organism_runtime_observer.py -q
cd frontend
npm run build
```

This guide is intentionally broad. The runbook tells you how to start Aureon; this file explains what is alive once it starts.
