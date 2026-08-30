# Aureon Quick Start

Use this when you only need the current commands. For the full runbook, see [RUNNING.md](RUNNING.md). For the full subsystem map, see [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md).

## 1. Install

```powershell
cd C:\path\to\aureon-trading
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

## 2. Validate The Launcher

```powershell
.\scripts\launchers\AUREON_PRODUCTION_LIVE.cmd -ValidateOnly -NoOpen -MarketStatusPort 8791
```

Use this command after pulling from `main`, before a live session, or after any launcher/doc change.

## 3. Run The Full Organism

```powershell
.\scripts\launchers\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791
```

Leave the terminal open. It supervises the live runtime, market feed, frontend console, mind hub, self-questioning loop, observer, and manifest refresh.

## 4. Open The Console

```text
http://127.0.0.1:8081/
```

Runtime endpoints:

```text
http://127.0.0.1:8791/api/terminal-state
http://127.0.0.1:8791/api/flight-test
http://127.0.0.1:8791/api/reboot-advice
http://127.0.0.1:13002/api/thoughts
http://127.0.0.1:13002/api/coding/status
```

If `terminal-state` returns `ok:false` but the status file and heartbeat are fresh, treat it as connected-but-guarded. Check `stale_reason`, `runtime_watchdog`, `executor_route_state`, and `/api/reboot-advice` before restarting. Do not restart the market runtime while open positions exist unless the flight-test reports `can_reboot_now: true`.

Manifest files:

```text
state/aureon_wake_up_manifest.json
frontend/public/aureon_wake_up_manifest.json
```

## 5. Optional Data Ocean

Run this in a second low-priority terminal when you want Aureon to widen live/history/context coverage without blocking the trading runtime:

```powershell
.\scripts\launchers\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable
```

If Kraken or another private account endpoint starts rate-limiting, keep the public/context ocean running without private account-history sync:

```powershell
.\scripts\launchers\AUREON_DATA_OCEAN.cmd -Adaptive -CoverageProfile LicensedReachable -SkipAccountSync
```

The data ocean uses `aureon/core/exchange_rate_limit_registry.py` to expose official provider limits and cash-aware call budgets. Check `state/aureon_data_ocean_status.json` for each live exchange row's `official_rate_limit`, `cash_aware_call_plan`, and `rate_budget`.

To see what each exchange can observe, trade, leverage, and optimize, check `docs/audits/aureon_exchange_data_capability_matrix.json` or the Trading console. The matrix shows Binance, Kraken, Alpaca, and Capital data channels, fresh-feed state, decision-fed state, cash-aware rate plan, gaps, and next optimization.

For Capital.com, watch the Trading console's Capital Survival Brain. It shows the live `capital_risk_envelope`, confidence ratchet, waveform contradiction check, no-loss hold queue, pending-order survival envelope, and whether dynamic live slots can expand without putting the whole Capital portfolio at risk.

To build the Capital tradable asset book, including epic, estimated cost, margin, leverage, minimum deal size, and execution route:

```powershell
.\.venv\Scripts\python.exe -m aureon.exchanges.capital_asset_registry --max-snapshots 250
```

Pending bids and take-profit planning are budgeted separately. Aureon treats every pending Capital working order as if it could fill together, then blocks unsafe ladders before they can threaten the whole account.

For Kraken, build the crypto spot/margin asset book so Aureon knows each tradable pair, fee tier, order minimum, cost minimum, leverage route, take-profit route, and pending-order survival rule:

```powershell
.\.venv\Scripts\python.exe -m aureon.exchanges.kraken_asset_registry --max-tickers 250
```

The data ocean also runs this automatically with `-KrakenAssetRegistryTickers`.

Validation-only:

```powershell
.\scripts\launchers\AUREON_DATA_OCEAN.cmd -ValidateOnly -DryRun -RunOnce -NoIngest
```

## 6. Prompt Aureon To Code

Use the Coding Organism panel in the console, or send a coding prompt through the mind hub:

```powershell
Invoke-RestMethod http://127.0.0.1:13002/api/coding/prompt `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt":"Aureon, inspect this code goal, choose the safest route, propose the patch, run focused tests, audit the finished product, and prepare the desktop run handoff.","run_tests":true,"include_desktop":true}' |
  ConvertTo-Json -Depth 8
```

Terminal-only:

```powershell
.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon must inspect this coding goal, propose the smallest safe code route, and run focused tests."
```

This is the prompt-to-product flow: prompt, route, code proposal/work queue, focused tests, finished-product audit, dry-run desktop/run handoff, and console evidence. The handoff state is written to `state/aureon_coding_organism_desktop_state.json`; use `--no-desktop` or `"include_desktop":false` only for a coding run without desktop/run handoff.

Director-mode capability comparison:

```powershell
.\.venv\Scripts\python.exe -m aureon.autonomous.aureon_coding_organism_bridge --prompt "Aureon director mode must create a Codex-class capability list, marry it to Aureon capabilities, bridge the gaps, and publish exact code work orders."
```

This creates the capability parity report and the exact Aureon build prompts for missing bridge systems.

## Dev And Audit Mode

```powershell
python scripts/aureon_ignition.py --audit-only
```

This is the development/audit ignition path. The production launcher is the full-organism entrypoint.

## Active File Map

| Area | Paths |
|---|---|
| Production launcher | `scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`, `scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1` |
| Data ocean | `scripts/launchers/AUREON_DATA_OCEAN.cmd`, `aureon/autonomous/aureon_data_ocean.py`, `aureon/autonomous/aureon_global_financial_coverage_map.py` |
| Official exchange rate budgets | `aureon/core/exchange_rate_limit_registry.py` |
| Exchange data capability matrix | `aureon/autonomous/aureon_exchange_data_capability_matrix.py` |
| Market runtime | `aureon/exchanges/unified_market_trader.py`, `aureon/exchanges/unified_market_status_server.py` |
| Exchange clients | `aureon/exchanges/kraken_client.py`, `aureon/exchanges/binance_client.py`, `aureon/exchanges/alpaca_client.py`, `aureon/exchanges/capital_client.py` |
| Cognitive runtime | `aureon/autonomous/aureon_self_questioning_ai.py`, `aureon/autonomous/aureon_mind_thought_action_hub.py` |
| Coding organism | `aureon/autonomous/aureon_coding_organism_bridge.py`, `aureon/autonomous/aureon_safe_code_control.py`, `aureon/autonomous/aureon_queen_code_bridge.py` |
| Director capability bridge | `aureon/autonomous/aureon_director_capability_bridge.py`, `frontend/src/components/generated/AureonDirectorCapabilityBridgeConsole.tsx` |
| Desktop/run handoff | `aureon/autonomous/aureon_safe_desktop_control.py`, `aureon/autonomous/vm_control/`, `state/aureon_coding_organism_desktop_state.json` |
| Observer and audits | `aureon/autonomous/aureon_organism_runtime_observer.py`, `aureon/autonomous/aureon_system_readiness_audit.py`, `aureon/autonomous/aureon_autonomous_capability_switchboard.py`, `aureon/autonomous/aureon_repo_self_catalog.py`, `aureon/autonomous/mind_wiring_audit.py` |
| HNC evidence | `aureon/autonomous/aureon_cognitive_trade_evidence.py`, `aureon/autonomous/aureon_harmonic_affect_state.py`, `aureon/autonomous/aureon_live_cognition_benchmark.py` |
| Frontend | `frontend/src/App.tsx`, `frontend/src/services/aureonAutonomousFrontend.ts`, `frontend/src/hooks/useTerminalSync.ts` |
| Accounting | `Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py`, `aureon/queen/accounting_context_bridge.py` |

## Safety Notes

Live trading requires configured exchange credentials and clear runtime gates. The runtime keeps stale-data, reboot-window, open-position, API-rate, credential, filing, payment, and security boundaries visible. Validation and audit commands do not place orders.
