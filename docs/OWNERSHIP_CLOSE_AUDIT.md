# Ownership audit — sell, close, amend, cancel

Gary's rule, 9 November 2026: Aureon must never sell, close, amend, or manage a position or coin balance he opened himself. It skips any position with no Aureon shadow trade, forecast, entry plan, or recorded Aureon fill.

This note is an inventory of the live close paths, taken against `main` `07bfb6ed`. It does not change trading code. Open pull requests that already own a path are named and were not edited here.

## Which Orca kill chain is launched

Two copies of `orca_unified_kill_chain.py` exist.

| Copy | Launched? |
|---|---|
| `aureon_radar/bots/orca_unified_kill_chain.py` | Yes. This is the organ. |
| `aureon/bots/orca_unified_kill_chain.py` | No. Nothing in the launcher, the unity supervisor, or the organ registry starts this file. |

The organ registry sets the script to the radar file (`aureon_fusion/organ_registry.py` line 124, organ `orca_unified_kill_chain` at line 651) and starts it with `--auto`. `aureon/launch/master.py` starts organs from that registry. `aureon_fusion/unity_supervisor.py` restarts a down organ by calling `organ_registry.start`. The radar master launcher (`aureon_radar/master_launcher.py`) does not start either kill chain. It starts the unified hub, phi-radar, and `orca_live_monitor.py --live`.

The registry match string is only the filename `orca_unified_kill_chain.py`. The start command is the radar path. A hand-started `aureon/bots/` process could be mistaken for the organ.

`--hunt-only` is a flag on both Orca copies (radar file near line 965). It is not a flag on `unified_kill_chain.py`. The organ is started with `--auto`, not `--hunt-only`, so phase 1 still scans existing positions and can sell them. With `--hunt-only` set, that harvest phase is skipped.

After #382 merges, only the radar copy calls `orca_real_fills.record_confirmed_fill` after Kraken and Binance buys (and after the Binance arbitrage sell). The `aureon/bots/` copy does not. Owned quantity read from that ledger on the unlaunched copy stays 0. That is safe (it will not treat a balance as Aureon's), and it also means that copy can never sell coins it bought, because the ledger never hears about them.

Recommendation: leave the `aureon/bots/` copy parked as not live. Do not add a second fill writer until something in the launcher actually runs that file. If `queen_quantum_frog.py` or either `orca_complete_kill_cycle.py` is later started as a process, wire `record_confirmed_fill` first. Those modules import `aureon.bots.orca_unified_kill_chain`, not the radar file.

## Open pull requests that already cover a path

Do not edit these files in a competing change.

| Path | What it can do | Ownership today on main | Covering PR |
|---|---|---|---|
| `aureon_radar/bots/orca_unified_kill_chain.py` spot sells (Alpaca, Binance, Kraken), including the Binance arbitrage sell near line 869 | Market sell of a scanned balance when `--hunt-only` is off | No spot ownership check on main. Capital `get_positions` at line 465 is already wrapped in `split_owned_positions` | #370 (spot guard). #382 records confirmed fills on this copy only. #386 relabels the attempt log. #396 reconciles Kraken acks into that ledger, stacked on #382 |
| `aureon_radar/bots/orca_live_monitor.py` `submit_exit_order` and Capital close near lines 487 and 681 | Live Capital close and spot exit when the radar suite passes `--live` | Capital list is filtered (line 389). Spot exits are not, on main | #370 |
| Capital `get_positions()` reads pinned by #370 in `aureon/bots/orca_unified_kill_chain.py`, both `orca_complete_kill_cycle.py` copies, the radar kill chain, and the live monitor | Those reads feed later closes | The pin requires `split_owned_positions(...)[0]` | #370. Spot sells in `aureon/bots/orca_unified_kill_chain.py` and the Alpaca paths in both complete-kill-cycle copies are explicitly not in that PR |
| `aureon_radar/aureon_phi_radar.py`, `aureon_trade_ledger.py`, `aureon_dual_capital.py`, `multi_exchange_router.py` | Adopt and close Capital deals, including router `close_position` | #383 adds `_phi_capital_deal_owned` | #383 (`lrya/phi-radar-capital-ownership`) |
| `AureonPhiRadar.panic()` in `aureon_radar/aureon_phi_radar.py`, `--panic` | On main, closes every live Capital position, including a manual CN50 | None on main | #399, stacked on #383. After that PR, `--panic` no longer flattens the whole Capital account. It closes every Aureon-owned deal (still an emergency stop for Aureon) and skips Gary's manual deals and anything it cannot attribute. Gary closes his own deals by hand |
| `unified_margin_trader/unified_kill_chain.py` and `aureon/trading/unified_kill_chain.py` `_scan_capital` / `_close_capital` | `DELETE /positions/{dealId}` or `close_position` | None on main (line 1572 is the raw DELETE fallback) | #398 (`bc-ded471e8`). Capital only. Spot venues in the same files were left alone |
| Kraken `get_order_status` by txid writing real fills | Read-back after an AddOrder ack. Not itself a sell | In flight | #396 (`bc-76cc66ee`), on top of #382. The same read-back also sits inside `_close_kraken` (both unified kill chains, near line 1600) and in `aureon/exchanges/unified_market_trader.py` fast-profit monitoring |

## Unguarded spot closes in both unified kill chains

`unified_margin_trader/unified_kill_chain.py` and `aureon/trading/unified_kill_chain.py` are the same kill chain. `run_loop` calls the three scans whenever that client is enabled. There is no `--hunt-only` on this file. None of these checks who opened the balance:

| Function | Line on main (`aureon/trading/` and `unified_margin_trader/`) | Sent to the venue |
|---|---|---|
| `_scan_alpaca` → `_close_alpaca` | close at 1576 | `DELETE /v2/positions/{symbol}` |
| `_scan_binance` → `_close_binance` | close at 1578 | Binance market `SELL` of the scanned quantity |
| `_scan_kraken` → `_close_kraken` | close at 1583 | Kraken market `sell`, then one status read-back |

Gary's Binance coins and a Kraken balance such as KNC are on this path if the loop is running. #398 does not guard them.

Proposed follow-up, after #398 merges so the files are free: one pull request on both copies. Before each of those three closes, refuse unless `aureon_owned_qty` from #382 covers the quantity. If that helper is not importable yet, treat owned quantity as 0 and refuse. Any exception refuses. No new numeric threshold. Do not edit the files while #398 has them open.

`aureon/harmonic/aureon_harmonic_liquid_aluminium.py` imports `aureon.trading.unified_kill_chain`. The hub loads harmonic modules for signal scores. It does not call `run_loop`. The import is not the organ entry.

## #398 scan key and close key do not match

On the #398 branch, `_scan_capital` keeps a position when `split_owned_positions` says it is adopted. That helper matches `dealId` or `dealReference` (also `deal_id` / `deal_reference`) against `AUREON_ORCA_CAPITAL_ADOPT_DEALS`. `_close_capital` then requires `str(deal_id) in adopted_deal_ids()`. A deal that was admitted only because its deal reference was on the list can be scanned and still not closed, because the close looks only at the deal id.

That fails closed on the close, which is the safe direction. The two checks should use the same keys, and a lookup error or a missing id should still close nothing. That alignment belongs in #398. It was not edited here.

## `capital_cfd_trader` — report only

Both live copies:

| | `aureon/exchanges/capital_cfd_trader.py` | `aureon_radar/capital_cfd_trader.py` |
|---|---|---|
| `_sync_positions_from_exchange` | 4253 | 4185 |
| `_close_position` | 6217 | 6140 |
| Close caller inside the position monitor | 6635 | (same method in the radar copy) |
| `_deadman_close_all` | 5631 | 5563 |

`_sync_positions_from_exchange` calls `client.get_positions()` and, when the row already has a complete entry receipt, puts that deal into the local book. It does not ask whether Aureon opened it. `tick()` (line 6657 in the `aureon/exchanges` copy) runs that sync, then the monitor closes from the local book through `_close_position`, which calls `client.close_position` (`DELETE /positions/{dealId}`).

The unified market trader organ calls `self.capital.tick()`, so this path is reachable from the launcher. Gary left `_close_position` as an open question. It was not changed. The same applies to the dead-man close-all, which calls `_close_position` for each local position.

## Raw Capital DELETE outside the organs

| File | Line on main | What it does | Recommendation |
|---|---|---|---|
| `aureon/trading/live_kill_chain_demo.py` | 98–100 | After an operator `y/N`, `DELETE /positions/{deal_id}` | Not an organ and not started by the master launcher. Park it. Do not register it |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/unified_kill_chain.py` | 1034 Capital DELETE, 1039 Alpaca DELETE | Old snapshot of the same unguarded closes | Already kept out of runtime controls by `tests/test_import_snapshot_quarantine.py`. Leave it excluded. Do not patch the snapshot |

## Other live paths (grouped)

Launcher and organ reachability is what decides a guard. A paper close, a shadow book, and a backtest are listed so they are not mistaken for a live flatten.

| Path | Venue | Ownership on main | Disposition |
|---|---|---|---|
| `aureon_radar/bots/orca_unified_kill_chain.py` Capital close, line 632 | Capital DELETE | `split_owned_positions` on the scan | Covered on main for the list. Close re-check is part of the ORCA capital work |
| `aureon_radar/bots/orca_live_monitor.py` Capital close, line 487 | Capital | List filtered at 389 | On main. #370 extends the same idea to spot |
| `aureon/exchanges/unified_market_trader.py` Kraken fast-profit market sell, dead-man trailing stop / take-profit, and the Kraken, Alpaca, and Binance spot sell routes | Spot sell of an account balance, including balances adopted from exchange trade history | None. The organ is `unified_market_trader` | Not guarded in this docs change. A later guard should use `aureon_owned_qty` and refuse when the helper is missing. Margin `place_margin_order` on a sell side can also reduce an existing long and needs the same check |
| `aureon_radar/exchange_adapters/shadow_{kraken,binance,alpaca}.py` `propose_signal`, `mark_all`, `close_position` | Shadow book. `live_place` is a separate fail-closed live path | Shadow closes are not exchange deletes | Hub shadow arm calls `propose_signal` and `mark_all` only |
| `aureon_radar/capital_client.py` and `aureon/exchanges/capital_client.py` `close_position` | Capital DELETE | Client primitive. Callers must check | #383 names `capital_client.py`. Do not add a second guard inside the client while that PR is open |
| `aureon_radar/aureon_dual_capital.py` `_close_position` | Capital DELETE | #383 | Covered by #383 |
| `aureon_radar/honey_ladder.py` broker close | Capital | Not an organ entry | Report. Not launched by itself |
| Gaia reclaimers, snowball, fire-trade, and the other bots under `aureon_radar/bots/` and `aureon/bots/` | Spot market sells of balances | None | The hub loads those modules and probes `scan` / `analyze` / `signal`. Those probe methods do not themselves call `place_market_order`. Their `main` / `run` loops are on the hub's never-call list. Not organ scripts. Report, do not run |
| `aureon/trading/emergency_sell_all.py`, `emergency_harvest.py`, `manual_sell.py`, `convert_to_usdt.py`, `force_trade_existing_balances.py`, `aureon/exchanges/alpaca_capital_runner.py` | Standalone flatten or sell scripts | None | Report only. Do not run them |
| `aureon/trading/aureon_btc_trader.py` `liquidate_altcoins_to_btc` | Spot sell | None | Not an organ. Report only |
| `scripts/diagnostics/capital_hft_stress.py` and `aureon-trading/capital_hft_stress.py` | Calls `_deadman_close_all` | None | Diagnostic scripts. Do not run |
| `aureon/queen/queen_quantum_frog.py` market sells | Spot | None. Imports the unlaunched Orca copy | Not an organ |
| Shadow, simulation, and backtest `close_position` methods (`aureon/simulation/`, `aureon_fusion/backtest_engine.py`, strategy paper paths) | No exchange | n/a | Not live closes |

## What was not done

No exchange was contacted. No `.env` was printed. `go_live_clear`, trading switches, and HOLD labels were not touched. Files open in #370, #382, #383, #386, #396, and #398 were not edited by this document.
