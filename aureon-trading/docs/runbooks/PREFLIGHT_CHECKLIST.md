# 🚀 Aureon Trading System - Pre-Flight Checklist

**Before deploying to DigitalOcean, complete ALL items below.**

---

## ✅ Phase 1: Local Development Validation

### 1.1 Code Quality
- [ ] All Python files have UTF-8 encoding fix at top
- [ ] No hardcoded Windows paths (e.g., `C:\Users\...`)
- [ ] No hardcoded codespaces paths (e.g., `/workspaces/...`)
- [ ] All paths use `Path()` from pathlib or `os.getenv()` with defaults
- [ ] No `print()` statements without logger (use `logger.info()` instead)

### 1.2 Dependencies
- [ ] Run: `python check_digitalocean_compat.py` - ALL CHECKS PASS
- [ ] Requirements.txt exists and is complete
- [ ] All imports are standard library or in requirements.txt
- [ ] No dev-only dependencies in production code

### 1.3 Configuration
- [ ] `.env.example` exists with all required variables
- [ ] Real API keys stored in `.env` (not committed to git)
- [ ] `.gitignore` includes: `.env`, `*.log`, `ws_cache/`, `*.json` (state files)
- [ ] All API keys have correct permissions (read-only for scanning, trading for Orca)

### 1.4 Safety Gates
- [ ] Queen's 1.88% profit gate (QUEEN_MIN_COP = 1.0188) in orca_complete_kill_cycle.py
- [ ] Black box buy gate (expected P&L > 3× costs) enabled
- [ ] Black box exit gate (realized P&L > 3× costs) enabled
- [ ] Portfolio truth monitoring enabled (60s reconciliation)
- [ ] 30-second prediction window gate enabled (≥3 validated samples)
- [ ] Truth Prediction Engine gates wired into all buy/sell paths
- [ ] Auris validation threshold = 0.618 (golden ratio)
- [ ] Pattern confidence threshold = 0.65

---

## ✅ Phase 2: Local Testing (24-48 Hours)

### 2.1 WebSocket Feeder
- [ ] Run: `python ws_market_data_feeder.py --binance --write-interval-s 1.0`
- [ ] Verify: `ws_cache/ws_prices.json` updates every 1 second
- [ ] Verify: 100-365 base prices per second in logs
- [ ] No errors in terminal output
- [ ] File size stays reasonable (<1 MB)

### 2.2 Truth Prediction Engine
- [ ] Run: `python aureon_live_tv_station.py` (with WS feeder running)
- [ ] Verify: "Probability Ultimate Intelligence: 95% accuracy, 57 patterns" loaded
- [ ] Verify: Queen↔Auris validation shows resonance = 1.00
- [ ] Verify: `aureon_truth_prediction_state.json` created and updating
- [ ] Verify: Predictions generated every 20th symbol (rate limiting working)
- [ ] Verify: Validations appear after 30 seconds (horizon elapsed)
- [ ] Check: `live_tv_stream.jsonl` logging predictions and validations

### 2.3 Truth Prediction Bridge
- [ ] Run: `python -c "from aureon_truth_prediction_bridge import get_truth_bridge; tb = get_truth_bridge(); print(tb.get_validation_stats())"`
- [ ] Verify: Returns accuracy stats (may be 0% initially, needs 30s validations)
- [ ] Verify: State file reads successfully (no errors)
- [ ] Verify: Cache TTL = 2 seconds working (check timestamps)

### 2.4 Prediction Accuracy Validation (CRITICAL - 7 Days Minimum)
- [ ] Run WS feeder + Truth Engine for 7 days continuously
- [ ] Monitor: `jq '.validations | length' aureon_truth_prediction_state.json` - should grow
- [ ] Calculate accuracy: `jq '.validations | map(.correct) | (map(select(. == true)) | length) / length * 100' aureon_truth_prediction_state.json`
- [ ] **REQUIRED**: Accuracy ≥ 60% before proceeding to Orca testing
- [ ] **REQUIRED**: Average geometric truth ≥ 0.7
- [ ] **REQUIRED**: Pattern confidence stabilizes ≥ 0.65
- [ ] **REQUIRED**: No system crashes or memory leaks over 7 days

**⚠️ DO NOT PROCEED WITHOUT 60%+ ACCURACY VALIDATION ⚠️**

---

## ✅ Phase 3: Orca Dry-Run Testing (48 Hours)

### 3.1 Dry-Run Mode
- [ ] Run: `python orca_complete_kill_cycle.py --dry-run` (with WS + Truth Engine running)
- [ ] Verify: "Truth Prediction Bridge: WIRED!" message on startup
- [ ] Verify: Truth Engine gates blocking trades without approval
- [ ] Verify: Logs show: "🌉 Truth Engine APPROVED" or "🚫 Truth Engine BLOCKED"
- [ ] Verify: Queen 1.88% gate blocking unprofitable trades
- [ ] Verify: Black box gates validating P&L > 3× costs
- [ ] Verify: Portfolio truth checks passing (no position drift)
- [ ] Verify: NO actual trades executed (dry-run mode)

### 3.2 Gate Validation
Test each gate blocks correctly:

- [ ] **Truth Engine Gate**: Manually edit `aureon_truth_prediction_state.json` to set `win_probability = 0.5` → verify trade BLOCKED
- [ ] **Auris Gate**: Set `auris_resonance = 0.5` → verify trade BLOCKED
- [ ] **Confidence Gate**: Set `pattern_confidence = 0.5` → verify trade BLOCKED
- [ ] **Direction Gate**: Set `predicted_direction = "DOWN"` for BUY order → verify trade BLOCKED
- [ ] **Queen 1.88% Gate**: Create scenario with <1.88% profit → verify trade BLOCKED
- [ ] **Black Box Buy Gate**: Create scenario with expected P&L < 3× costs → verify trade BLOCKED
- [ ] **Prediction Window Gate**: Clear `prediction_buffer` → verify trade BLOCKED with "Need at least 30s of validated predictions"

### 3.3 Logging & Monitoring
- [ ] All gates log clear APPROVED/BLOCKED messages
- [ ] Timestamps in logs match prediction state file
- [ ] No Python exceptions or tracebacks in logs
- [ ] Memory usage stable (<500 MB for all 3 processes combined)
- [ ] CPU usage reasonable (<30% average)

---

## ✅ Phase 4: DigitalOcean Deployment

### 4.1 Droplet Setup
- [ ] Create droplet: Ubuntu 24.04 LTS, 2-4 GB RAM, 1-2 vCPUs, $12-48/mo
- [ ] Select region close to exchange APIs (NYC, LON, SGP)
- [ ] Enable IPv6 (optional but recommended)
- [ ] Add SSH key (NEVER use password authentication)
- [ ] Note droplet IP address: `___.___.___.___`

### 4.2 Initial Access
- [ ] SSH into droplet: `ssh root@<DROPLET_IP>`
- [ ] Update system: `apt update && apt upgrade -y`
- [ ] Clone repo: `git clone https://github.com/YOUR_USERNAME/aureon-trading.git /opt/aureon-trading`
- [ ] Run deployment script: `cd /opt/aureon-trading && ./deploy_digitalocean.sh`
- [ ] Script completes without errors

### 4.3 Configuration
- [ ] Edit `.env`: `nano /opt/aureon-trading/.env`
- [ ] Add real API keys (copy from local `.env`)
- [ ] Set permissions: `chmod 600 /opt/aureon-trading/.env`
- [ ] Verify: `ls -l .env` shows `-rw-------` (owner read/write only)

### 4.4 Service Startup
- [ ] Start WS feeder: `sudo systemctl start aureon-ws-feeder`
- [ ] Check status: `sudo systemctl status aureon-ws-feeder` → **active (running)**
- [ ] Verify cache updating: `watch -n 1 stat /opt/aureon-trading/ws_cache/ws_prices.json`
- [ ] Start Truth Engine: `sudo systemctl start aureon-truth-engine`
- [ ] Check status: `sudo systemctl status aureon-truth-engine` → **active (running)**
- [ ] Wait 5 minutes, then check predictions: `cat /opt/aureon-trading/aureon_truth_prediction_state.json | jq '.predictions | length'`

### 4.5 Monitoring (First 24 Hours)
- [ ] Run: `/opt/aureon-trading/monitor.sh` every hour
- [ ] Check logs: `tail -f /opt/aureon-trading/logs/ws-feeder.log`
- [ ] Check logs: `tail -f /opt/aureon-trading/logs/truth-engine.log`
- [ ] Verify predictions increasing: `jq '.predictions | length' aureon_truth_prediction_state.json`
- [ ] Verify validations working: `jq '.validations | length' aureon_truth_prediction_state.json`
- [ ] Check accuracy: `jq '.validations | map(.correct) | (map(select(. == true)) | length) / length * 100' aureon_truth_prediction_state.json`
- [ ] Disk usage: `df -h` (should have >10 GB free)
- [ ] Memory usage: `free -h` (should have >500 MB free)

### 4.6 Security
- [ ] UFW firewall enabled: `sudo ufw status` → **active**
- [ ] SSH allowed: `sudo ufw status | grep 22` → **ALLOW**
- [ ] No unnecessary ports open: `sudo netstat -tuln | grep LISTEN`
- [ ] Disable root login: Edit `/etc/ssh/sshd_config` → `PermitRootLogin no`
- [ ] Reload SSH: `sudo systemctl reload sshd`
- [ ] Test SSH with non-root user (create if needed)

### 4.7 Backups
- [ ] Manual backup test: `/opt/aureon-trading/backup.sh`
- [ ] Verify: `ls -lh /opt/aureon-trading/backups/` → files exist
- [ ] Cron job installed: `crontab -l | grep backup` → runs every 6 hours
- [ ] Set reminder to snapshot droplet weekly (DigitalOcean console)

---

## ✅ Phase 5: Production Deployment (After Extensive Testing)

### 5.1 Pre-Production Validation
- [ ] Truth Engine running on DigitalOcean for 7+ days
- [ ] Prediction accuracy sustained ≥ 60%
- [ ] Average geometric truth ≥ 0.7
- [ ] No crashes or restarts in past 7 days
- [ ] Logs clean (no errors, warnings acceptable)

### 5.2 Orca Dry-Run on DigitalOcean (48 Hours)
- [ ] Update `aureon-orca-trading.service`:
  ```ini
  ExecStart=/opt/aureon-trading/venv/bin/python orca_complete_kill_cycle.py --dry-run
  ```
- [ ] Reload: `sudo systemctl daemon-reload`
- [ ] Start: `sudo systemctl start aureon-orca-trading`
- [ ] Monitor for 48 hours continuously
- [ ] Verify all gates working correctly (same as Phase 3.2)
- [ ] Verify no actual trades executed

### 5.3 Small Capital Testing ($10-50 Positions)
- [ ] Remove `--dry-run` flag from service file
- [ ] Set position limits in Orca config: `MAX_POSITION_SIZE = 50.0` (USD)
- [ ] Enable live mode: `sudo systemctl restart aureon-orca-trading`
- [ ] Monitor EVERY TRADE for first week:
  - Check actual P&L matches expected
  - Verify fees calculated correctly
  - Confirm COP ≥ 1.0188 (1.88% profit minimum)
  - Ensure portfolio truth checks passing
  - No position drift detected
- [ ] After 1 week, evaluate:
  - Win rate ≥ 60%?
  - Average profit per trade ≥ 1.88%?
  - No violations of safety gates?
  - Ready to scale up?

### 5.4 Scale-Up (Only After Profitable Week)
- [ ] Increase position limits gradually: $50 → $100 → $250 → $500
- [ ] Monitor closely at each tier for 3-7 days
- [ ] Check exchange API rate limits (may need tier upgrade)
- [ ] Verify Orca turn-based rotation preventing rate limit hits
- [ ] Consider upgrading droplet if CPU/memory constrained (4-8 GB RAM)

---

## 🚨 CRITICAL SAFETY RULES

### NEVER:
- ❌ Deploy to production without 7 days of prediction validation
- ❌ Enable live trading with <60% prediction accuracy
- ❌ Disable Queen's 1.88% profit gate (QUEEN_MIN_COP)
- ❌ Disable Truth Engine gates
- ❌ Disable portfolio truth monitoring
- ❌ Trade without 30 seconds of validated predictions
- ❌ Use API keys with withdrawal permissions (trading only)
- ❌ Skip dry-run testing phase
- ❌ Ignore prediction accuracy metrics
- ❌ Scale up without profitable week at lower tier

### ALWAYS:
- ✅ Run dry-run mode FIRST (--dry-run flag)
- ✅ Monitor prediction accuracy DAILY
- ✅ Check portfolio truth HOURLY (first week)
- ✅ Backup state files BEFORE changes
- ✅ Review logs AFTER every trade
- ✅ Start with small positions ($10-50)
- ✅ Test gate rejections manually
- ✅ Keep API keys in .env with 600 permissions
- ✅ Enable UFW firewall on DigitalOcean
- ✅ Snapshot droplet before major changes

---

## 📊 Success Criteria (Before Live Trading)

**Prediction Engine:**
- ✅ Accuracy ≥ 60% over 7 days
- ✅ Avg geometric truth ≥ 0.7
- ✅ Pattern confidence ≥ 0.65
- ✅ No system crashes

**Safety Gates:**
- ✅ All 7 gates blocking correctly
- ✅ Truth Engine approval required
- ✅ Queen 1.88% gate enforced
- ✅ Auris resonance ≥ 0.618

**System Stability:**
- ✅ 7 days uptime without restarts
- ✅ Memory usage stable (<500 MB)
- ✅ Logs clean (no errors)
- ✅ Backups running automatically

**Dry-Run Results:**
- ✅ 48 hours clean operation
- ✅ Hypothetical trades would be profitable
- ✅ No gate violations
- ✅ Portfolio truth checks passing

**Small Capital Results (1 Week):**
- ✅ Win rate ≥ 60%
- ✅ Avg profit ≥ 1.88% per trade
- ✅ No unexpected losses
- ✅ Fees < 30% of gross profit

---

## 📝 Deployment Log Template

```markdown
## Deployment: [DATE]

### Pre-Flight
- [ ] Compatibility check: PASS/FAIL
- [ ] Local testing: 7 days completed
- [ ] Prediction accuracy: ___%
- [ ] Avg geometric truth: ____

### Droplet Info
- IP: ___.___.___.___
- Region: ___________
- Size: ___ GB RAM, ___ vCPUs
- Cost: $___/month

### Service Status
- [ ] aureon-ws-feeder: ACTIVE
- [ ] aureon-truth-engine: ACTIVE
- [ ] aureon-orca-trading: DISABLED (dry-run pending)

### Post-Deployment Checks
- [ ] Predictions generating: YES/NO
- [ ] Validations working: YES/NO
- [ ] Accuracy after 24h: ___%
- [ ] Backups running: YES/NO
- [ ] Firewall enabled: YES/NO

### Notes
[Any issues, observations, or deviations from checklist]
```

---

## 🆘 Emergency Procedures

### If Prediction Accuracy Drops Below 50%
1. `sudo systemctl stop aureon-orca-trading` (IMMEDIATELY)
2. Review `aureon_truth_prediction_state.json` validations
3. Check for data feed issues (WS feeder logs)
4. Verify Queen↔Auris resonance still 1.00
5. DO NOT RESUME TRADING until accuracy recovers

### If Unauthorized Trade Detected
1. `sudo systemctl stop aureon-orca-trading` (IMMEDIATELY)
2. Check Orca logs: `grep "UNAUTHORIZED" /opt/aureon-trading/logs/orca-trading.log`
3. Verify all safety gates enabled in code
4. Review `active_position.json` for discrepancies
5. Contact exchange support if funds at risk

### If System Crashes Repeatedly
1. Check memory: `free -h` (upgrade droplet if <200 MB free)
2. Check disk: `df -h` (clean logs if <10% free)
3. Review logs: `journalctl -u aureon-ws-feeder -n 200`
4. Disable Orca: `sudo systemctl disable aureon-orca-trading`
5. Debug with: `python orca_complete_kill_cycle.py --dry-run` (foreground mode)

---

**Version**: 1.0  
**Last Updated**: 2025-01-27  
**Owner**: Aureon Trading System  
**Next Review**: Before each production deployment
