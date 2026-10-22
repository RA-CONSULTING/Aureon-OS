# Aureon Scripts Index

Complete reference for all startup, monitoring, diagnostic, and utility scripts.

> **Tip:** All scripts assume you're running from the repository root directory unless otherwise noted.

---

## Live Trading Startup

### Linux / macOS (Shell)

| Script | Location | Description |
|--------|----------|-------------|
| `START_LIVE_TRADING.sh` | `scripts/shell/start/` | Primary live trading launcher |
| `START_HISTORICAL_LIVE.sh` | `scripts/shell/start/` | Historical-data live trading |
| `START_ORCA_LIVE.sh` | `scripts/shell/start/` | Orca kill-chain live trading |
| `run_live.sh` | `scripts/shell/start/` | Quick live trading start |
| `run_unified_ecosystem.sh` | `scripts/shell/start/` | Full unified ecosystem |
| `start_full_ecosystem.sh` | `scripts/shell/start/` | Complete ecosystem startup |
| `start_aureon.sh` | `scripts/shell/start/` | Core Aureon system startup |
| `start_command_center.sh` | `scripts/shell/start/` | Command center UI |
| `start_unified_master_hub.sh` | `scripts/shell/start/` | Unified master hub |
| `start_mind_thought_action.sh` | `scripts/shell/start/` | Mind-thought-action pipeline |
| `start_fresh_live.sh` | `scripts/shell/start/` | Fresh state live start |
| `start_simulation.sh` | `scripts/shell/start/` | Simulation mode |
| `run_war_ready_kraken.sh` | `scripts/shell/start/` | Kraken war-ready mode |
| `run_pipeline.sh` | `scripts/shell/start/` | Data pipeline |
| `run_probability_generator.sh` | `scripts/shell/start/` | Probability generator |
| `run_specialized_army.sh` | `scripts/shell/start/` | Specialized bot army |
| `run_safe_2bots.sh` | `scripts/shell/start/` | Safe 2-bot configuration |
| `run_multi_bot.sh` | `scripts/shell/start/` | Multi-bot fleet |
| `run_micro_forever.sh` | `scripts/shell/start/` | Micro-profit infinite loop |
| `mine_live.sh` | `scripts/shell/start/` | Mining mode live |
| `gaia_closed_loop.sh` | `scripts/shell/start/` | Gaia closed-loop system |
| `restart_bot.sh` | `scripts/shell/start/` | Restart trading bot |

### Windows (PowerShell / CMD)

| Script | Location | Description |
|--------|----------|-------------|
| `run_unified_live.cmd` | `scripts/runners/` | Unified trader — aggressive live mode |
| `run_alpaca_capital_style.ps1` | `scripts/runners/` | Alpaca capital-style trader |
| `run_capital_swarm.ps1` | `scripts/runners/` | Capital.com swarm trader |
| `run_capital_margin_only.ps1` | `scripts/runners/` | Capital.com margin-only mode |
| `run_capital_monitor.ps1` | `scripts/runners/` | Capital.com universe monitor |
| `run_aureon_voice_agent.ps1` | `scripts/runners/` | Voice agent system |
| `run_aureon_voice_agent.cmd` | `scripts/runners/` | Voice agent system (CMD) |
| `stop_aureon_voice_agent.ps1` | `scripts/runners/` | Stop voice agent |
| `START_WINDOWS.ps1` | `scripts/` | Windows general startup |
| `start_full_ecosystem.ps1` | `scripts/` | Full ecosystem (Windows) |
| `start_queen_hive_mind.ps1` | `scripts/` | Queen hive mind (Windows) |

---

## Global Memory / Data Ingest

These scripts build and refresh the single-file SQLite dataset used as Aureon's "memory":
`state/aureon_global_history.sqlite`.

| Script | Location | Description |
|--------|----------|-------------|
| `ingest_global_memory.cmd` | `scripts/runners/` | One-command orchestrator (`--profile standard|max|unsafe-all`) |
| `ingest_all_global_history.cmd` | `scripts/runners/` | Legacy full ingest (simple chain, passes args to all steps) |
| `sync_global_history_db.cmd` | `scripts/runners/` | Sync private account trades into the DB |
| `ingest_market_history.cmd` | `scripts/runners/` | Public market history ingest (CoinAPI + Alpaca) |
| `ingest_yfinance.cmd` | `scripts/runners/` | Yahoo Finance OHLCV ingest |
| `ingest_fred.cmd` | `scripts/runners/` | FRED macro indicator ingest |
| `ingest_existing_feeds.cmd` | `scripts/runners/` | CoinGecko/news/onchain/coinbase/macro feeds ingest |
| `ingest_economic_calendar.cmd` | `scripts/runners/` | Calendar + events ingest |
| `ingest_queen_knowledge.cmd` | `scripts/runners/` | Queen memories/insights/thoughts/strategies ingest |

### Python Runners

| Script | Location | Description |
|--------|----------|-------------|
| `run_live_trading.py` | `scripts/runners/` | Core live trading runner |
| `start_live_trading.py` | `scripts/runners/` | Live trading startup |
| `run_unified.py` | `scripts/runners/` | Unified system runner |
| `run_unified_ecosystem_live.py` | `scripts/runners/` | Full unified ecosystem |
| `start_aureon_unified.py` | `scripts/runners/` | Unified Aureon startup |
| `run_unified_orca.py` | `scripts/runners/` | Unified Orca system |
| `run_live_imperial.py` | `scripts/runners/` | Imperial protocol live |
| `run_queen_hive_mind.py` | `scripts/runners/` | Queen hive mind runner |
| `start_nexus.py` | `scripts/runners/` | Nexus core startup |
| `run_aureon_windows.py` | `scripts/runners/` | Windows Aureon runner |
| `run_platypus.py` | `scripts/runners/` | Platypus strategy runner |
| `run_snowball.py` | `scripts/runners/` | Snowball compound runner |
| `run_miner.py` | `scripts/runners/` | Mining strategy runner |

---

## Monitoring

### Shell

| Script | Location | Description |
|--------|----------|-------------|
| `check_status.sh` | `scripts/shell/monitor/` | System status check |
| `check_funds.sh` | `scripts/shell/monitor/` | Account funds check |
| `check_system_logs.sh` | `scripts/shell/monitor/` | System log viewer |
| `monitor_trading.sh` | `scripts/shell/monitor/` | Live trading monitor |
| `monitor_bot.sh` | `scripts/shell/monitor/` | Individual bot monitor |
| `monitor_army.sh` | `scripts/shell/monitor/` | Bot army monitor |
| `watch_bots.sh` | `scripts/shell/monitor/` | Bot watcher |

### Python

| Script | Location | Description |
|--------|----------|-------------|
| `show_live_status.py` | `scripts/python/` | Live system status |
| `show_portfolio.py` | `scripts/python/` | Portfolio overview |
| `monitor_trades.py` | `scripts/python/` | Trade monitor |
| `monitor_ecosystem.py` | `scripts/python/` | Ecosystem health |
| `monitor_batten_matrix.py` | `scripts/python/` | Batten matrix status |
| `quick_balance_check.py` | `scripts/python/` | Quick balance check |
| `quick_profit_check.py` | `scripts/python/` | Quick profit check |
| `show_binance_raw.py` | `scripts/python/` | Raw Binance data |
| `show_firm_database.py` | `scripts/python/` | Firm intelligence database |
| `run_continuous_accuracy_monitor.py` | `scripts/runners/` | Prediction accuracy tracker |

---

## Diagnostics

All diagnostic scripts are in `scripts/diagnostics/`.

### Balance & Portfolio Checks

| Script | Description |
|--------|-------------|
| `check_actual_balance.py` | Actual exchange balances |
| `check_all_balances.py` | All exchanges combined |
| `check_unified_balances.py` | Unified balance view |
| `check_kraken_balance.py` | Kraken balance |
| `check_portfolio.py` | Portfolio summary |
| `check_real_pnl.py` | Real P&L calculation |
| `check_unrealized_pnl.py` | Unrealized P&L |
| `check_redeemed_balance.py` | Redeemed balance |
| `debug_balances.py` | Balance debugging |

### Exchange Diagnostics

| Script | Description |
|--------|-------------|
| `check_binance_pnl.py` | Binance P&L |
| `check_full_binance.py` | Full Binance audit |
| `check_capital.py` | Capital.com status |
| `check_kraken_ledger.py` | Kraken ledger |
| `check_kraken_orders.py` | Kraken orders |
| `check_kraken_trades_10h.py` | Kraken recent trades |
| `check_uk_pairs.py` | UK-available trading pairs |
| `debug_capital_prices.py` | Capital.com price data |
| `debug_crypto_history.py` | Crypto history |
| `debug_exchanges.py` | Exchange connectivity |
| `debug_kraken_binance.py` | Kraken/Binance comparison |
| `debug_kraken_pairs.py` | Kraken pair data |
| `diagnose_api_key.py` | API key validation |
| `diagnose_binance.py` | Binance diagnostics |
| `diagnose_exchange_connectivity.py` | Exchange connectivity |

### System Diagnostics

| Script | Description |
|--------|-------------|
| `check_batten_matrix.py` | Batten matrix |
| `check_coherence_lambda.py` | Lambda coherence |
| `check_dashboard_health.py` | Dashboard health |
| `check_live_environment.py` | Live environment |
| `check_stargate_status.py` | Stargate protocol |
| `check_system_flow.py` | System flow |
| `check_system_logs.py` | System logs |
| `diagnose_system.py` | General diagnostics |
| `diagnose_trading_engine.py` | Trading engine |
| `diagnose_no_trades.py` | Debug no-trade situations |
| `diagnose_not_working.py` | General troubleshooting |
| `diagnose_dashboard_data.py` | Dashboard data |

### Trading Diagnostics

| Script | Description |
|--------|-------------|
| `check_boys.py` | Active bot check |
| `check_chz_status.py` | CHZ token status |
| `check_goal_proof.py` | Goal proof verification |
| `check_recent_trades.py` | Recent trades |
| `debug_force_sniper_kill.py` | Sniper kill chain debug |
| `debug_leap_opportunities.py` | Leap opportunities |
| `debug_opportunities.py` | Trading opportunities |
| `debug_orca_binance.py` | Orca Binance integration |
| `debug_portfolio_status.py` | Portfolio status |
| `debug_tickers_opps.py` | Ticker opportunities |
| `debug_usd_source.py` | USD source tracking |
| `quick_sniper.py` | Quick sniper execution |

### Audit Scripts

| Script | Description |
|--------|-------------|
| `audit_capital_harmonic_wiring.py` | Capital.com harmonic wiring audit |
| `audit_runtime_linkage.py` | Runtime linkage verification |

### DigitalOcean Deployment

| Script | Description |
|--------|-------------|
| `check_digitalocean_compat.py` | DigitalOcean compatibility |
| `check_digitalocean_config.py` | DigitalOcean config |

---

## Simulation & Backtesting

| Script | Location | Description |
|--------|----------|-------------|
| `run_backtest_cached.py` | `scripts/runners/` | Cached data backtest |
| `run_big_sim.py` | `scripts/runners/` | Large simulation |
| `run_billion_sim.py` | `scripts/runners/` | Billion-target simulation |
| `run_penny_profit_sim.py` | `scripts/runners/` | Penny profit simulation |
| `run_real_data_simulation.py` | `scripts/runners/` | Real data simulation |
| `run_wisdom_learning_sim.py` | `scripts/runners/` | Wisdom learning simulation |
| `run_adaptive_sandbox.py` | `scripts/runners/` | Adaptive strategy sandbox |
| `run_ecosystem_debug.py` | `scripts/runners/` | Ecosystem debug mode |
| `run_ecosystem_with_logging.py` | `scripts/runners/` | Ecosystem with logging |

---

## Deployment

| Script | Location | Description |
|--------|----------|-------------|
| `deploy_digitalocean.sh` | `scripts/shell/deploy/` | DigitalOcean deployment |
| `setup_coinapi.sh` | `scripts/shell/deploy/` | CoinAPI setup |
| `test-docker.sh` | `scripts/shell/deploy/` | Docker test |
| `deploy_digital_ocean.py` | `scripts/python/` | DigitalOcean deployment (Python) |
| `deployment_verification.py` | `scripts/python/` | Post-deployment verification |

---

## Utilities

| Script | Location | Description |
|--------|----------|-------------|
| `capture_test.sh` | `scripts/shell/util/` | Capture test output |
| `debug_runner.sh` | `scripts/shell/util/` | Debug runner |
| `run_diagnostic_with_log.sh` | `scripts/shell/util/` | Diagnostic with log |
| `run_test.sh` | `scripts/shell/util/` | Run tests |
| `quick_test.py` | `scripts/python/` | Quick test runner |
| `enhancement_cli.py` | `scripts/python/` | Enhancement CLI |
| `learning_analytics_cli.py` | `scripts/python/` | Learning analytics CLI |
| `reset_learned_analytics.py` | `scripts/python/` | Reset learned analytics |

---

## TypeScript Traders

All TypeScript trader scripts are in `scripts/traders/`. These are alternative trading implementations.

### Exchange-Specific
| Script | Description |
|--------|-------------|
| `krakenTrader.ts` / `krakenFullTrader.ts` | Kraken traders |
| `alpacaTrader.ts` / `alpacaDance.ts` / `alpacaFullSpread.ts` | Alpaca traders |
| `binanceLive.ts` | Binance live trader |
| `capitalTrader.ts` / `capitalDance.ts` | Capital.com traders |
| `forexTrader.ts` | Forex trader |

### Exchange API Connectors
| Script | Description |
|--------|-------------|
| `alpacaApi.ts` | Alpaca API |
| `capitalComApi.ts` | Capital.com API |
| `bitstampApi.ts` | Bitstamp API |
| `coinbaseApi.ts` | Coinbase API |
| `geminiApi.ts` | Gemini API |
| `okxApi.ts` | OKX API |
| `oandaApi.ts` / `oandaDance.ts` | OANDA API |
| `fxcmApi.ts` | FXCM API |
| `igMarketsApi.ts` | IG Markets API |
| `interactiveBrokersApi.ts` | Interactive Brokers API |
| `saxoBankApi.ts` | Saxo Bank API |
| `cmcMarketsApi.ts` | CMC Markets API |

### Strategy Implementations
| Script | Description |
|--------|-------------|
| `unifiedOrchestrator.ts` | Unified trading orchestrator |
| `unifiedSymphony.ts` / `unifiedSymphonyPro.ts` | Unified symphony strategies |
| `coherenceTrader.ts` | Coherence-based trader |
| `trendFollower.ts` | Trend following strategy |
| `gammaSync.ts` | Gamma synchronization |
| `aggressiveWaveRider.ts` / `immediateWaveRider.ts` | Wave riding strategies |
| `netProfitCycleTrader.ts` / `netProfitWaveRider.ts` | Net profit strategies |
| `danceOfSpaceTime.ts` / `dynamicDance.ts` / `grandDance.ts` / `permittedDance.ts` | Dance-pattern strategies |
| `grandSymphony500.ts` / `liveSymphony.ts` / `liveMarketSymphony.ts` | Symphony strategies |
| `quackersFleet.ts` / `quackersLive.ts` | Quackers fleet |
| `realMoneyMaker.ts` / `realMoneyTrade.ts` | Real money traders |
| `challenge400to40k.ts` / `live400to40k.ts` / `realistic400to40k.ts` | $400→$40K challenge |
| `dayTradingSim.ts` / `paperTradeSimulation.ts` / `monteCarloSimulation.ts` | Simulations |

### Testing & Validation
| Script | Description |
|--------|-------------|
| `testTrades.ts` | Trade testing |
| `testNotional.ts` | Notional value testing |
| `testEarthIntegration.ts` | Earth integration testing |
| `testNexusIntegration.ts` | Nexus integration testing |
| `checkPermissions.ts` | API permission check |
| `validateSecrets.ts` | Secret validation |
| `apiCapacityAnalysis.ts` | API capacity analysis |
| `convertUsdcToUsdt.ts` | USDC→USDT conversion |

---

## Validation Scripts

Located in `validation/`:

| Script | Description |
|--------|-------------|
| `flight_check_unified_margin_trader.py` | Pre-flight unified margin trader validation |
| `verify_safe_desktop_control.py` | Safe desktop control verification |

---

## See Also

- [Navigation Guide](NAVIGATION_GUIDE.md) — Guided paths by role
- [Module Reference](MODULES_AT_A_GLANCE.md) — All 715 Python modules
- [Live Trading Runbook](LIVE_TRADING_RUNBOOK.md) — Day-to-day operations
