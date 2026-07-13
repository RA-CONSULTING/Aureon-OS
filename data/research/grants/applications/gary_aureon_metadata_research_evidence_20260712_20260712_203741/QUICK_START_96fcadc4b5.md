# AUREON LIVE TRADING - QUICK REFERENCE

**Get Started in 2 Minutes**

```bash
# 1. SETUP (one time)
cp .env.example .env
# Edit .env — add your NEW Binance API keys (not the exposed ones!)

# 2. PREFLIGHT CHECK
python3 check_live_environment.py

# 3. RUN STAGE 0 (testnet + dry-run, NO real money)
export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=true
python3 aureon_live.py --stage 0 --symbol BTCUSDT

# 4. RUN STAGE 1 (testnet + real orders, testnet money)
export BINANCE_USE_TESTNET=true BINANCE_DRY_RUN=false
python3 aureon_live.py --stage 1 --symbol BTCUSDT --trades 3

# 5. RUN STAGE 2 (mainnet + real money — ONLY after 1+ hrs on testnet)
export BINANCE_USE_TESTNET=false CONFIRM_LIVE=yes
python3 aureon_live.py --stage 2 --symbol BTCUSDT
```

---

## Commands

| Command | Purpose |
|---------|---------|
| `python3 check_live_environment.py` | Pre-flight validation |
| `python3 binance_trade_sample.py` | Test order placement logic |
| `python3 binance_get_address.py BTC` | Retrieve deposit address |
| `python3 aureon_live.py --stage 0 --symbol BTCUSDT` | Validate strategy (dry-run) |
| `tail -f trade_audit.log` | Monitor live trades in real-time |

---

## Key Environment Variables

```bash
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_USE_TESTNET=true          # false for mainnet
BINANCE_DRY_RUN=true              # false to place real orders
BINANCE_RISK_MAX_ORDER_USDT=25    # max notional per order
BINANCE_RISK_FRACTION=0.02        # 2% risk per trade
BINANCE_SYMBOL=BTCUSDT            # default symbol
```

---

## System Architecture

**Master Equation:** Λ(t) = S(t) + O(t) + E(t)
- **S(t)** = Substrate (9 Auris nodes: tiger, falcon, hummingbird, dolphin, deer, owl, panda, cargoship, clownfish)
- **O(t)** = Observer (self-referential awareness)
- **E(t)** = Echo (momentum memory)
- **Coherence Γ** ∈ [0, 1]: Entry @ Γ > 0.938, Exit @ Γ < 0.934

---

## Risk Controls (Enforced)

✅ Testnet by default  
✅ Dry-run by default  
✅ Max 25 USDT per order  
✅ 2% of balance risk per trade  
✅ Min 5 USDT notional  
✅ API key: spot trade only, no withdraw  
✅ All trades logged to `trade_audit.log`  

---

## Checklist Before Stage 2

- [ ] Generated NEW Binance API keys (not the exposed ones)
- [ ] Restricted permissions: spot trade only, no withdrawals
- [ ] IP whitelisted the keys
- [ ] Ran Stage 0 (testnet + dry-run) successfully
- [ ] Ran Stage 1 (testnet + real orders) for ≥1 hour
- [ ] Reviewed `trade_audit.log` for anomalies
- [ ] Funded Binance account via deposit address
- [ ] Ready to lose the capital (realistic mindset)

---

## Monitoring

```bash
# Watch logs
tail -f trade_audit.log

# Count today's trades
grep "$(date +%Y-%m-%d)" trade_audit.log | wc -l

# Check for errors
grep ERROR trade_audit.log | tail -10

# Export trades to JSON (manual parsing)
grep "✅ Trade executed" trade_audit.log
```

---

## Emergency (If Suspicious Activity)

1. Stop execution: `export BINANCE_DRY_RUN=true`
2. Disable API key: Binance Account → API Management → Delete
3. Review logs: `grep ERROR trade_audit.log`
4. Generate NEW key
5. Restart from Stage 0

---

## Files You Need

| File | Type | Purpose |
|------|------|---------|
| `.env` | Config | Store API keys (gitignored) |
| `binance_client.py` | Module | Core Binance client |
| `aureon_live.py` | Script | Main trading engine |
| `trade_audit.log` | Log | All trades recorded here |
| `LIVE_TRADING_RUNBOOK.md` | Guide | Full setup instructions |
| `SECURITY_TRADING.md` | Reference | Risk & key management |

---

**Status:** Ready to trade with NEW keys | Audit logging enabled | Risk controls enforced  
**Last Updated:** November 28, 2025

