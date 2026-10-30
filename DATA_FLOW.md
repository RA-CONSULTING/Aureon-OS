# Aureon Trading System — Data Flow Architecture

Measured trading performance is not yet measured. There is no verified live track record. The live routes are active: with exchange keys in `.env`, the launcher boots into live trading. The diagrams below are the path the code is designed to follow. They are not a measured result.

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Exchange APIs     │ Historical Data  │ Wisdom Databases  │ Bot Patterns │
│  (Binance, Kraken)│ (Backtest files) │ (12 civilizations)│ (Detection) │
└─────────┬───────────────┬──────────────────┬─────────────────┬──────────┘
          │               │                  │                 │
          ▼               ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     1_SUBSTRATE (FOUNDATION)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Market Feeds           Data Models           Frequencies               │
│  ├─ OHLCV candles      ├─ Schemas            ├─ Harmonic constants    │
│  ├─ Order books        ├─ Caches             ├─ φ (1.618)             │
│  ├─ Trade streams      ├─ Configs            ├─ Solfeggio (528 Hz)    │
│  └─ Tick data          └─ Conversions        ├─ Schumann (7.83 Hz)    │
│                                              └─ Sacred frequencies     │
│                                                                          │
└─────────┬──────────────────────────────────────┬───────────────────────┘
          │                                      │
          ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      2_DYNAMICS (INTELLIGENCE)                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Trading Logic              Probability Networks      Echo Feedback      │
│  ├─ HNC signal gen         ├─ Γ coherence calc      ├─ Temporal τₖ      │
│  ├─ Bot detection          ├─ Threshold operators   ├─ φ-spaced         │
│  ├─ Harmonic analysis      ├─ Branch scoring        ├─ Feedback loops   │
│  └─ Bot intelligence       └─ Probability matrix    └─ Multiverse       │
│                                                                           │
│  INPUT:                                                                  │
│    Price data → Harmonic frequency analysis → Coherence scoring         │
│    Historical patterns → Bot fingerprints → Attribution                 │
│    Wisdom convergence → Market probability → Confidence metric          │
│                                                                           │
│  OUTPUT:                                                                 │
│    Signal strength (0-1)                                                │
│    Entry/exit recommendations                                           │
│    Coherence scores                                                     │
│    Risk assessments                                                     │
│                                                                           │
└──────────┬────────────────────────────────────────┬─────────────────────┘
           │                                        │
           ▼                                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     3_FORCING (EXECUTION)                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Market Events          Coherence Gates          Execution Engines      │
│  ├─ Scanners           ├─ Γ thresholds         ├─ Order placement      │
│  ├─ Whale trackers     ├─ φ gates              ├─ Trade emission       │
│  ├─ Volatility spikes  ├─ Risk limits          ├─ Position updates     │
│  └─ Pattern triggers   └─ Kill switches        └─ Confirmations        │
│                                                                           │
│  Real-Time Triggers:                                                    │
│    Signal → Gate check → Risk assessment → Execute or Hold             │
│                                                                           │
│  Position Sizing:                                                       │
│    Portfolio equity × Coherence × Risk tolerance = Size               │
│                                                                           │
│  Stop Loss:                                                             │
│    Entry price ± (ATR × volatility factor) = Dynamic stops            │
│                                                                           │
└──────────┬────────────────────────────────────────────┬────────────────┘
           │                                            │
           ▼                                            ▼
    ┌─────────────────┐                      ┌─────────────────┐
    │  Exchange APIs  │                      │  Order Books    │
    │  (Real Execute) │                      │  (Verification) │
    └────────┬────────┘                      └────────┬────────┘
             │                                        │
             └────────────┬─────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      4_OUTPUT (RESULTS)                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Trade Outputs         Portfolio Management      Performance Metrics    │
│  ├─ Trade records      ├─ Position tracking     ├─ PnL tracking        │
│  ├─ Entry/exit logs    ├─ Balance updates       ├─ Win rate            │
│  ├─ Execution proofs   ├─ Multi-exchange state ├─ Sharpe ratio         │
│  └─ Timestamp proofs   └─ Accounting            └─ Drawdown            │
│                                                                           │
│  Dashboard:                                                             │
│    Live portfolio → Real-time P&L → Trade history → Performance        │
│                                                                           │
│  Verification:                                                          │
│    ETA predictions → Actual timing → Accuracy audit → Validation       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
           │
           └─→ VALIDATION & AUDIT
               ├─ Trade profit validator
               ├─ Timing accuracy checks
               ├─ Risk limit verification
               └─ Compliance records
```

---

## Detailed Flow: Single Trade Execution

Prices in this walkthrough show the shape of one order moving through the layers. They are not a measured run. Live P&L, win rate, and trade counts are not yet measured. There is no verified live track record. The live routes are active.

```
STEP 1: DATA INGESTION
┌─────────────────────────────────┐
│  Exchange: Binance              │
│  Symbol: ETHUSDT                │
│  Price: $3,247.50               │
│  Volume: 125.6 BTC              │
│  Timestamp: 2026-04-24 14:35:42 │
└────────────┬────────────────────┘
             │
             ▼
STEP 2: SUBSTRATE PROCESSING
┌─────────────────────────────────────────┐
│  1. Normalize price data                │
│  2. Calculate technical indicators      │
│  3. Store in cache (1_substrate/)       │
│  4. Verify data integrity               │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 3: HARMONIC ANALYSIS (2_dynamics)
┌─────────────────────────────────────────┐
│  1. Extract frequency from price        │
│     Price movement → FFT analysis       │
│     Result: 512.19 Hz detected          │
│                                         │
│  2. Check harmonic alignment            │
│     512.19 Hz ↔ Sacred frequencies      │
│     Match: φ ratio (1.618)              │
│                                         │
│  3. Calculate coherence (Γ)             │
│     φ alignment strength = 0.8876       │
│     (Range: 0-1, Productive: 0.35-0.945)│
│                                         │
│  4. Generate probability               │
│     HNC Master Formula                  │
│     Probability: 0.7937 (79.4%)        │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 4: SIGNAL GENERATION
┌─────────────────────────────────────────┐
│  Inputs:                                │
│    ├─ Coherence: 0.8876                │
│    ├─ Frequency: 512.19 Hz             │
│    ├─ Probability: 0.7937              │
│    ├─ Momentum: UP                     │
│    └─ Historical pattern: MATCH        │
│                                         │
│  Logic:                                 │
│    IF (Coherence > 0.7) AND            │
│       (Probability > 0.75) THEN        │
│      ACTION = "STRONG BUY"             │
│                                         │
│  Result:                                │
│    ✓ Signal generated                  │
│    ✓ Confidence: HIGH                  │
│    ✓ Recommendation: BUY               │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 5: RISK ASSESSMENT (3_forcing)
┌─────────────────────────────────────────┐
│  Portfolio Check:                       │
│    ├─ Account balance: $10,000         │
│    ├─ Current positions: 2 open        │
│    ├─ Risk allocation: 2% per trade    │
│    └─ Max position: $200               │
│                                         │
│  Market Check:                          │
│    ├─ Volatility (ATR): 45.23          │
│    ├─ Bid-ask spread: 0.12%            │
│    ├─ Liquidity: 1M volume/5m          │
│    └─ Recent volatility spike: NO      │
│                                         │
│  Risk Limits:                           │
│    ├─ Max drawdown allowed: 2%         │
│    ├─ Current drawdown: 0.3%           │
│    ├─ Stop loss: $3,200 (entry-1.5%)  │
│    └─ Take profit: $3,295 (+1.5%)      │
│                                         │
│  Gate Checks:                           │
│    ✓ Coherence gate: PASS (0.8876 > 0.35)
│    ✓ Risk gate: PASS (position size OK)
│    ✓ Portfolio gate: PASS (allocation OK)
│    ✓ Market gate: PASS (liquidity OK)  │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 6: EXECUTION (3_forcing/execution_engines)
┌─────────────────────────────────────────┐
│  1. Calculate position size             │
│     $200 ÷ $3,247.50 = 0.0616 ETH      │
│                                         │
│  2. Place limit order                   │
│     Side: BUY                           │
│     Symbol: ETHUSDT                     │
│     Quantity: 0.0616 ETH                │
│     Price: $3,247.50 (limit)            │
│     Time-in-force: GTC (Good-til-cancel)│
│                                         │
│  3. Send to exchange                    │
│     API: POST /orders                   │
│     Exchange: Binance                   │
│     Result: Order ID 12345789           │
│                                         │
│  4. Confirm execution                   │
│     Status: PENDING (waiting for fill)  │
│     Timestamp: 2026-04-24 14:35:47.234  │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 7: MONITORING (Real-time loop)
┌─────────────────────────────────────────┐
│  Every 1 second (or tick):              │
│    ├─ Check order status                │
│    ├─ Monitor price movement            │
│    ├─ Track position P&L                │
│    ├─ Update coherence score            │
│    ├─ Check stop-loss trigger           │
│    └─ Check take-profit trigger         │
│                                         │
│  At 14:35:52 (5 seconds later):        │
│    ├─ Order filled at $3,247.45        │
│    ├─ Entry price: $3,247.45           │
│    ├─ Position: +0.0616 ETH            │
│    ├─ Unrealized P&L field: written    │
│    └─ Status: OPEN                     │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 8: EXIT DECISION (2_dynamics re-analyzes)
┌─────────────────────────────────────────┐
│  Scenario A: Price rises to $3,295     │
│    ├─ Unrealized profit: +1.46%        │
│    ├─ Coherence: Still 0.88            │
│    ├─ Decision: TAKE PROFIT            │
│    └─ Action: SELL                     │
│                                         │
│  Scenario B: Price drops to $3,200     │
│    ├─ Unrealized loss: -1.46%          │
│    ├─ Coherence breaks: 0.32           │
│    ├─ Decision: STOP LOSS              │
│    └─ Action: SELL                     │
│                                         │
│  Scenario C: 94 seconds pass           │
│    ├─ Coherence timeout                │
│    ├─ Decision: SESSION EXIT           │
│    └─ Action: SELL (best available)    │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 9: EXIT EXECUTION (3_forcing)
┌─────────────────────────────────────────┐
│  Place SELL order:                      │
│    Side: SELL                           │
│    Symbol: ETHUSDT                      │
│    Quantity: 0.0616 ETH                 │
│    Price: $3,295.20 (limit)             │
│                                         │
│  Execution:                             │
│    Filled at: $3,295.18                 │
│    Timestamp: 2026-04-24 14:36:46.512  │
│    Proceeds field: written on fill      │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 10: RECORDING & VALIDATION (4_output)
┌─────────────────────────────────────────┐
│  Trade Record:                          │
│  {                                      │
│    "symbol": "ETHUSDT",                │
│    "entry_price": 3247.45,             │
│    "exit_price": 3295.18,              │
│    "quantity": 0.0616,                 │
│    "pnl": "(field; unmeasured)",       │
│    "pnl_pct": "(field; unmeasured)",   │
│    "entry_time": 1764797752.234,       │
│    "exit_time": 1764797806.512,        │
│    "hold_time_sec": 94,                │
│    "coherence": 0.8876,                │
│    "probability": 0.7937,              │
│    "frequency": 512.19,                │
│    "hnc_action": "STRONG BUY",         │
│    "exchange": "binance",              │
│    "status": "CLOSED"                  │
│  }                                      │
│                                         │
│  Validations:                           │
│    ✓ Price alignment verified           │
│    ✓ Timing accuracy validated          │
│    ✓ P&L reconciliation checked        │
│    ✓ Risk limits respected              │
│    ✓ Audit trail recorded               │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 11: PORTFOLIO UPDATE
┌─────────────────────────────────────────┐
│  The book is designed to store:        │
│    ├─ cash balance                      │
│    ├─ open position count               │
│    ├─ unrealized P&L field              │
│    ├─ realized P&L field                │
│    └─ a cumulative P&L field            │
│                                         │
│  Those amounts are not yet measured.    │
│  No verified live track record.         │
│  Live routes are active.                │
└────────────┬────────────────────────────┘
             │
             ▼
STEP 12: VISUALIZATION & REPORTING
┌─────────────────────────────────────────┐
│  Dashboard fields the path can show:   │
│    ├─ live portfolio                    │
│    ├─ session trade count               │
│    ├─ session P&L                       │
│    ├─ win rate                          │
│    ├─ average trade                     │
│    └─ max drawdown                      │
│                                         │
│  Also designed, still unmeasured:      │
│    ├─ Sharpe                            │
│    ├─ Sortino                           │
│    ├─ profit factor                     │
│    └─ consecutive wins                  │
│                                         │
│  No figure is quoted. Results are not │
│  yet measured.                          │
│                                         │
│  Audit Trail:                           │
│    Logged to: 4_output/trade_outputs/  │
│    File: paper_trade_history.json      │
│    Searchable by symbol, date, etc.    │
└─────────────────────────────────────────┘
```

---

## Data Flow: Bot Detection

```
DETECTION PIPELINE:

Price Data                Bot Fingerprints          Pattern Database
     │                           │                       │
     └──────────┬────────────────┴───────────────┬──────┘
                │                                │
                ▼                                ▼
    ┌──────────────────────────┐    ┌────────────────────────┐
    │  Ocean Wave Scanner      │    │  Harmonic Sweep        │
    │  ├─ Order book patterns  │    │  ├─ Frequency matching │
    │  ├─ Price action timing  │    │  ├─ Coherence analysis │
    │  ├─ Whale accumulation   │    │  └─ Harmonic alignment │
    │  └─ Wash trading signs   │    └────────────────────────┘
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────────────────┐
    │  Bot Intelligence Profiler           │
    │  ├─ Clustering analysis              │
    │  ├─ Similarity matching              │
    │  ├─ Attribution scoring              │
    │  └─ Firm association                 │
    └──────────┬───────────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────┐
    │  Output:                             │
    │  ├─ 193 detected patterns            │
    │  ├─ 23 attributed algorithms         │
    │  ├─ 37 firms identified              │
    │  ├─ 44,000+ bots tracked             │
    │  └─ 1,500 coordination links         │
    └──────────────────────────────────────┘
```

---

## Data Flow: Historical Analysis

```
FORENSIC PIPELINE:

Historical Events           Extraction Timeline       Perpetrator Network
(1913-2024)               (109 years)               (34 nodes)
     │                           │                       │
     └──────────┬────────────────┴───────────────┬──────┘
                │                                │
                ▼                                ▼
    ┌──────────────────────────┐    ┌────────────────────────┐
    │  Manipulation Hunter     │    │  Money Flow Analysis   │
    │  ├─ Event pattern matching│   │  ├─ Extraction timeline │
    │  ├─ Perpetrator linkage  │    │  ├─ Flow tracing       │
    │  ├─ Impact calculation   │    │  ├─ $33.5T mapped      │
    │  └─ Evidence assembly    │    │  └─ Node connections   │
    └──────────┬───────────────┘    └────────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────┐
    │  Output:                             │
    │  ├─ $33.5 trillion extraction        │
    │  ├─ 11 major events mapped           │
    │  ├─ Rothschild, Fed, Goldman linked  │
    │  ├─ Retail→Institution flow proof    │
    │  └─ Bailout evidence documented      │
    └──────────────────────────────────────┘
```

---

## Data Flow: Backtesting

```
Historical Data          Strategy Logic           Validation Engine
(OHLCV candles)         (HNC signals)            (Performance metrics)
     │                       │                          │
     └──────────┬────────────┴──────────────┬───────────┘
                │                          │
                ▼                          ▼
    ┌────────────────────────┐   ┌──────────────────────┐
    │  Event-Driven Loop     │   │  Risk Calculation    │
    │  ├─ Bar-by-bar replay  │   │  ├─ Drawdown tracking │
    │  ├─ Signal generation  │   │  ├─ Position sizing  │
    │  ├─ Execution         │   │  └─ Sharpe ratio     │
    │  └─ P&L tracking      │   └──────────────────────┘
    └────────────┬──────────┘
                │
                ▼
    ┌──────────────────────────────────────────┐
    │  Output the engine is designed to write │
    │  ├─ a trade record for each replay      │
    │  ├─ accuracy (not yet measured)         │
    │  ├─ combined P&L (not yet measured)     │
    │  ├─ drawdown (not yet measured)         │
    │  └─ an audit trail                      │
    └──────────────────────────────────────────┘
```

---

## Data Persistence

```
MEMORY                    DISK                    VALIDATION
(Cache)                   (Storage)               (Audit)
  │                           │                       │
  ├─ Price feeds          ├─ Trade records     ├─ Checksums
  ├─ Signals (real-time)  ├─ Portfolio state   ├─ Timestamps
  ├─ Positions            ├─ Backtest results  ├─ Signatures
  └─ Metrics              ├─ Bot registry      └─ Reconciliation
                          ├─ Wisdom databases
                          ├─ Metadata
                          └─ Config files
```

---

**Summary:** Data flows through 4 layers:
- **Substrate:** Ingestion & normalization
- **Dynamics:** Analysis & signal generation  
- **Forcing:** Execution & risk management
- **Output:** Recording & validation

Every trade is recorded, auditable, and traceable.
