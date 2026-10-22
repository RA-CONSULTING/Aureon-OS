# Running Aureon

Last updated: 2026-05-13

This is the canonical runbook for the current Aureon runtime. The recommended full-organism terminal entrypoint is the production wake-up launcher, not individual exchange bots.

For a plain-English map of every major subsystem and what it can do, read [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md).

The launcher starts the production supervisor, market runtime, status/telemetry server, mind hub, self-questioning loop, organism observer, manifest refresh, and unified frontend console.

## Current Entrypoints

| Purpose | Command |
|---|---|
| Full Windows production supervisor | `.\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791` |
| Validate launcher and flags without opening services | `.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791` |
| Low-priority data ocean supervisor | `.\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable` |
| Prompt Aureon coding organism | `.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon, inspect this coding goal and run the focused tests."` |
| Director capability bridge | `.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon director mode must create a Codex-class capability list, marry it to Aureon capabilities, bridge the gaps, and publish exact code work orders."` |
| Dev/audit ignition path | `python scripts/aureon_ignition.py --audit-only` |
| Standalone runtime status server | `python aureon/exchanges/unified_market_status_server.py --port 8791` |
| Frontend development server | `cd frontend; npm run dev` |

Use port `8791` for the current runtime feed when older local sessions may still own `8790`.

## Run The Whole Organism

Open PowerShell:

```powershell
cd C:\path\to\aureon-trading
.\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791
```

Leave this terminal open. It is the production supervisor. A healthy launch prints:

```text
Mode: LIVE_TRADING_OPERATOR_CONFIRMED + COGNITIVE_ORDER_INTENT_AUTHORITY + PRODUCTION_SUPERVISOR
LLM/cognitive order-intent authority: ON
Production supervisor attached
```

The production launcher now defaults the cockpit voice lane to local Aureon+Ollama cognition:

```powershell
$env:AUREON_VOICE_BACKEND = "ollama_hybrid"
$env:AUREON_LLM_BASE_URL = "http://localhost:11434/v1"
$env:AUREON_LLM_MODEL = "llama3:latest"
$env:AUREON_LLM_ALLOW_HTTP_IN_AUDIT = "1"
$env:AUREON_LLM_SKIP_PROBE = "1"
$env:AUREON_LLM_REQUEST_TIMEOUT_S = "180"
$env:AUREON_PHI_CHAT_TIMEOUT_S = "180"
$env:AUREON_OLLAMA_CONTEXT_WEAVER = "1"
$env:AUREON_OLLAMA_WEAVER_MODEL = "qwen2.5:0.5b"
$env:AUREON_OLLAMA_WEAVER_SHARD_TOKENS = "90"
```

That keeps safe/audit observation mode from blocking local Ollama HTTP while all live trading, payment, filing, credential, and destructive OS gates remain closed. The context weaver splits large cockpit prompts into small Ollama packets, then lets Aureon's cognitive layer compose the final reply. `AUREON_LLM_SKIP_PROBE=1` avoids an expensive 1-token health probe on slow local CPU models; the actual shard calls still prove the path. If you change models while the hub is running, reload the cached Phi worker:

```powershell
Invoke-RestMethod http://127.0.0.1:13002/api/phi-bridge/reload -Method Post | ConvertTo-Json -Depth 8
```

## Safe Validation

Run this before a live session, after pulling updates, or after editing launch docs:

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
```

Validation checks the launcher profile and command wiring without starting the full console stack.

## Watch The Runtime

Open the unified console:

```text
http://127.0.0.1:8081/
```

Watch local endpoints from a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8791/api/terminal-state | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8791/api/flight-test | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8791/api/reboot-advice | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:13002/api/thoughts | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:13002/api/coding/status | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:13002/api/ollama-cognitive/status | ConvertTo-Json -Depth 8
```

The console also reads the wake-up manifest from:

```text
state/aureon_wake_up_manifest.json
frontend/public/aureon_wake_up_manifest.json
```

## Run The Data Ocean

Use a second PowerShell terminal for wide market mapping and historical/context refresh:

```powershell
.\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable
```

This supervisor runs below normal priority and keeps heavy ingestion/backfill separate from live trading. Its reports are:

```text
state/aureon_data_ocean_status.json
frontend/public/aureon_data_ocean_status.json
docs/audits/aureon_global_financial_coverage_map.json
frontend/public/aureon_global_financial_coverage_map.json
docs/audits/aureon_exchange_data_capability_matrix.json
frontend/public/aureon_exchange_data_capability_matrix.json
```

Private account-history sync is budgeted so it does not overload Kraken or other account APIs while the live runtime is active. The default Kraken private trade-history cap is `50` records per cycle. To run only public/context/history ingestion for a cycle, use:

```powershell
.\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable -SkipAccountSync
```

The data ocean report includes the official exchange rate-limit registry from `aureon/core/exchange_rate_limit_registry.py`. Live exchange rows expose `official_rate_limit` and `cash_aware_call_plan`: venues with active cash or positions reserve calls for execution, balances, positions, and recovery; idle/no-cash venues can use more of their safe provider budget for streams, quote probes, and candidate discovery.

The exchange data capability matrix turns that into an operator checklist for each venue: data channels, trading modes, fresh feed state, decision-fed state, official call budget, cash-aware optimization mode, gaps, and next optimization. It is published to `docs/audits/aureon_exchange_data_capability_matrix.json` and mirrored to `frontend/public/aureon_exchange_data_capability_matrix.json` for the Trading console.

## Prompt Aureon To Code

After the production launcher has the mind hub alive, use the Coding Organism panel in the console or post directly to the hub:

```powershell
Invoke-RestMethod http://127.0.0.1:13002/api/coding/prompt `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt":"Aureon, inspect this code goal, choose the safest route, propose the patch, run focused tests, audit the finished product, and prepare the desktop run handoff.","run_tests":true,"include_desktop":true}' |
  ConvertTo-Json -Depth 8
```

For a terminal-only run:

```powershell
.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon must inspect this coding goal, propose the smallest safe code route, and run focused tests."
```

The bridge writes `state/aureon_coding_organism_last_run.json`, `docs/audits/aureon_coding_organism_bridge.json`, and `frontend/public/aureon_coding_organism_bridge.json`. By default it also creates a finished-product audit and a dry-run desktop/run handoff in `state/aureon_coding_organism_desktop_state.json`, using `aureon/autonomous/aureon_safe_desktop_control.py` and the VM-control tool registry as the run surface.

That coding path is the full cognitive loop:

```text
operator prompt -> mind hub or CLI -> GoalExecutionEngine route
-> safe code proposal/work queue -> focused tests/build checks
-> finished_product_audit -> desktop/remote run handoff -> console evidence
```

Use `--no-desktop` on the CLI, or `"include_desktop": false` through the HTTP endpoint, only when you want a coding evidence run without desktop/run handoff.

To ask Aureon to compare itself against a Codex-class coding/operator agent and create exact bridge work orders for anything missing:

```powershell
.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon director mode must create a Codex-class capability list, marry it to Aureon capabilities, bridge the gaps, and publish exact code work orders."
```

This writes `state/aureon_director_capability_bridge_last_run.json`, `docs/audits/aureon_director_capability_bridge.json`, `frontend/public/aureon_director_capability_bridge.json`, and the `AureonDirectorCapabilityBridgeConsole` panel.

Capital.com live expansion is controlled by the Capital Survival Brain in the Trading console. The runtime publishes `capital_risk_envelope`, `capital_trade_evidence`, `capital_confidence_ratchet`, `capital_unified_waveform_check`, `capital_no_loss_hold_queue`, and `capital_pending_order_envelope`; live Capital entries are dynamically sized or held when portfolio reserve, margin utilization, stress buffer, concentration, confidence, or cross-exchange waveform evidence is not strong enough.

Build or widen the Capital tradable asset book when you want every discovered Capital market mapped to epic, cost, margin, leverage, minimum deal size, and execution route:

```powershell
.\.venv\Scripts\python.exe -m aureon.exchanges.capital_asset_registry --max-snapshots 250
```

The registry writes `state/capital_tradable_asset_registry.sqlite`, `state/aureon_capital_tradable_asset_registry.json`, and audit/public JSON/CSV/Markdown outputs. Pending Capital bids are planned as working orders with broker take-profit evidence, but submission remains opt-in through `CAPITAL_PENDING_ORDER_SUBMIT_ENABLED=1`; the survival envelope blocks ladders that would be unsafe if all pending orders filled at once.

Build or widen the Kraken crypto asset/cost book when you want every Kraken spot and margin pair mapped to AssetPairs metadata, order minimums, cost minimums, maker/taker fees, leverage options, take-profit route, margin route, and pending-order survival policy:

```powershell
.\.venv\Scripts\python.exe -m aureon.exchanges.kraken_asset_registry --max-tickers 250
```

The data ocean calls this automatically with `-KrakenAssetRegistryTickers`. The registry writes `state/kraken_tradable_asset_registry.sqlite`, `state/aureon_kraken_tradable_asset_registry.json`, and audit/public JSON/CSV/Markdown outputs. Runtime publishes the summary at `/api/terminal-state#kraken_asset_registry`, and the trading intelligence checklist turns it into Kraken spot readiness, margin cost readiness, and pending-order survival rows.

For a no-ingest validation pass:

```powershell
.\AUREON_DATA_OCEAN.cmd -ValidateOnly -DryRun -RunOnce -NoIngest
```

## What The Launcher Starts

| Surface | Active path |
|---|---|
| Production wrapper | `AUREON_PRODUCTION_LIVE.cmd` |
| Full wake-up launcher | `AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` |
| Data ocean supervisor | `AUREON_DATA_OCEAN.cmd`, `AUREON_DATA_OCEAN.ps1` |
| Official exchange rate budgets | `aureon/core/exchange_rate_limit_registry.py` |
| Exchange data capability matrix | `aureon/autonomous/aureon_exchange_data_capability_matrix.py` |
| Market runtime | `aureon/exchanges/unified_market_trader.py` |
| Runtime status server | `aureon/exchanges/unified_market_status_server.py` |
| Kraken client | `aureon/exchanges/kraken_client.py` |
| Kraken asset/cost registry | `aureon/exchanges/kraken_asset_registry.py`, `state/kraken_tradable_asset_registry.sqlite` |
| Kraken pending order survival | `build_kraken_order_survival_envelope`, `/api/terminal-state#kraken_asset_registry` |
| Binance client | `aureon/exchanges/binance_client.py` |
| Alpaca client | `aureon/exchanges/alpaca_client.py` |
| Capital client | `aureon/exchanges/capital_client.py` |
| Capital survival brain | `aureon/exchanges/capital_cfd_trader.py`, `/api/terminal-state#capital_risk_envelope` |
| Capital asset registry | `aureon/exchanges/capital_asset_registry.py`, `state/capital_tradable_asset_registry.sqlite` |
| Capital pending order controls | `capital_pending_order_envelope`, `CapitalClient.place_working_order`, `CapitalClient.update_position_limits` |
| Self-questioning loop | `aureon/autonomous/aureon_self_questioning_ai.py` |
| Mind hub | `aureon/autonomous/aureon_mind_thought_action_hub.py` |
| Organism observer | `aureon/autonomous/aureon_organism_runtime_observer.py` |
| Readiness audit | `aureon/autonomous/aureon_system_readiness_audit.py` |
| Capability switchboard | `aureon/autonomous/aureon_autonomous_capability_switchboard.py` |
| Repo self-catalog | `aureon/autonomous/aureon_repo_self_catalog.py` |
| Mind wiring audit | `aureon/autonomous/mind_wiring_audit.py` |
| Cognitive trade evidence | `aureon/autonomous/aureon_cognitive_trade_evidence.py` |
| Harmonic affect state | `aureon/autonomous/aureon_harmonic_affect_state.py` |
| Live cognition benchmark | `aureon/autonomous/aureon_live_cognition_benchmark.py` |
| Frontend shell | `frontend/src/App.tsx` |
| Frontend autonomous service | `frontend/src/services/aureonAutonomousFrontend.ts` |
| Terminal sync hook | `frontend/src/hooks/useTerminalSync.ts` |
| Coding organism bridge | `aureon/autonomous/aureon_coding_organism_bridge.py`, `frontend/src/components/generated/AureonCodingOrganismConsole.tsx` |
| Director capability bridge | `aureon/autonomous/aureon_director_capability_bridge.py`, `frontend/src/components/generated/AureonDirectorCapabilityBridgeConsole.tsx` |
| Desktop/run handoff | `aureon/autonomous/aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `state/aureon_coding_organism_desktop_state.json` |
| Accounting pack generator | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py` |
| Accounting context bridge | `aureon/queen/accounting_context_bridge.py` |
| Data ocean registry/governor | `aureon/autonomous/aureon_data_ocean.py` |
| Global financial coverage map | `aureon/autonomous/aureon_global_financial_coverage_map.py` |
| Exchange monitoring/data matrix | `aureon/autonomous/aureon_exchange_monitoring_checklist.py`, `aureon/autonomous/aureon_exchange_data_capability_matrix.py` |

## Runtime Modes

| Mode | Meaning |
|---|---|
| `safe_observation` | Runtime or feed is offline, or live environment is not enabled. |
| `guarded_observe_plan` | Live runtime is enabled, but action blockers such as stale ticks, open-position restart windows, or booting state remain active. |
| `guarded_live_action` | Runtime is fresh, live environment is enabled, real order capability is enabled, and guards are clear. |

The guard layer is not a separate trading strategy. It is the runtime evidence layer that prevents stale data, duplicate supervisors, unsafe reboot timing, credential mistakes, API-rate overload, payment/filing automation, and unowned security mutation from being treated as live action.

## Runtime Resilience

The status feed should be read as connected-but-guarded when `ok:false` appears with a fresh status file and heartbeat. `/api/terminal-state` exposes stale reason, open positions, API governor state, exchange readiness, executor route state, and tick phase. Direct execution routes use a timeout so a slow exchange call is held and reported instead of freezing the whole tick loop.

Use `/api/flight-test` and `/api/reboot-advice` before any restart. If open positions exist, the launcher should preserve monitoring and wait until the flight-test reports `can_reboot_now: true`.

## Live Trading Preconditions

Before live operation, confirm:

- Exchange credentials are present in `.env` for Kraken, Binance, Alpaca, and Capital as applicable.
- Withdrawal permissions are disabled on exchange keys.
- The launcher validation command passes.
- `http://127.0.0.1:8791/api/terminal-state` reports `trading_ready: true` and `data_ready: true`.
- `stale` is `false`, or the console clearly shows a guarded state while waiting.
- Capital.com entries show a positive stress buffer and clear waveform/ratchet state in the Capital Survival Brain before dynamic live slots expand.
- `http://127.0.0.1:8791/api/flight-test` allows reboot only when the runtime is in a safe downtime window.

## Dev And Audit Paths

Use ignition for local audit and dry-run checks:

```powershell
python scripts/aureon_ignition.py --audit-only
python scripts/aureon_ignition.py --no-trade
python scripts/aureon_ignition.py --accounts-status
```

The production launcher remains the recommended full Windows organism entrypoint.

## Legacy Or Dev-Only Commands

Do not use old root scripts as the main run path. These are obsolete, deprecated, or dev-only references:

- `python aureon_live.py`
- `python aureon_unified_ecosystem.py`
- `python3 scripts/paperTradeSimulation.ts`
- `.\scripts\runners\run_unified_live.cmd`

Use the production launcher for full operation and `scripts/aureon_ignition.py --audit-only` for dev/audit checks.

## Verification

```powershell
.\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
.\.venv\Scripts\python.exe -m pytest tests/test_ignition_live_profile.py tests/test_unified_market_status_server.py tests/test_aureon_organism_runtime_observer.py -q
```

Verify the active OS/LLM/task/code/skill surfaces:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_safe_code_control.py tests/test_inhouse_llm_adapter_audit_mode.py tests/test_goal_capability_map.py tests/test_capability_growth_loop.py tests/vault/test_skill_executor_bridge.py -q
```

Frontend build check:

```powershell
cd frontend
npm run build
```

## Stop And Recovery

Press `Ctrl+C` in the production supervisor terminal to stop supervising. Background services keep their own process state.

To relaunch cleanly, close older elevated terminals that may still own ports `8081`, `8790`, or `8791`, then run the production launcher once. Do not force-kill the market runtime while positions are open; use the flight-test and reboot-advice endpoints to wait for a safe downtime window.
