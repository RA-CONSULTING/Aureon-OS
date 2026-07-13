# 🚀 Quick Start: DigitalOcean Deployment in 5 Minutes

**Deploy Aureon Trading System to production in 5 simple steps.**

---

## Prerequisites

- DigitalOcean account ([sign up here](https://www.digitalocean.com))
- SSH key added to DigitalOcean ([instructions](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/))
- Exchange API keys (Kraken, Binance, or Alpaca)
- 5 minutes of your time

---

## Step 1: Create Droplet (2 minutes)

1. Log into [DigitalOcean Console](https://cloud.digitalocean.com)
2. Click **"Create"** → **"Droplets"**
3. Configure:
   - **Image**: Ubuntu 24.04 LTS
   - **Plan**: Basic ($12/mo for testing, $24/mo recommended)
   - **Size**: 2 GB RAM / 1 vCPU (or 4 GB / 2 vCPU)
   - **Region**: NYC, LON, or SGP (close to exchanges)
   - **Authentication**: Select your SSH key
   - **Hostname**: `aureon-trading-1`
4. Click **"Create Droplet"**
5. Wait 30 seconds, then copy the droplet IP address

---

## Step 2: SSH & Deploy (2 minutes)

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Download deployment script
curl -O https://raw.githubusercontent.com/YOUR_REPO/aureon-trading/main/deploy_digitalocean.sh
chmod +x deploy_digitalocean.sh

# Run deployment (installs everything)
./deploy_digitalocean.sh
```

**What it does:**
- ✅ Updates Ubuntu packages
- ✅ Installs Python 3.12 + dependencies
- ✅ Creates `/opt/aureon-trading` directory
- ✅ Sets up Python virtual environment
- ✅ Creates systemd services (auto-restart on failure)
- ✅ Configures log rotation
- ✅ Enables firewall (UFW)
- ✅ Sets up backups (every 6 hours)

---

## Step 3: Configure API Keys (1 minute)

```bash
# Edit .env file
nano /opt/aureon-trading/.env

# Replace placeholders with REAL API keys:
BINANCE_API_KEY=abc123...
BINANCE_API_SECRET=xyz789...

# Save: Ctrl+O, Enter, Ctrl+X

# Secure permissions
chmod 600 /opt/aureon-trading/.env
```

**⚠️ CRITICAL**: Use **READ-ONLY** API keys for testing (no withdrawal permissions)

---

## Step 4: Start Services (30 seconds)

```bash
# Start WebSocket data feeder
sudo systemctl start aureon-ws-feeder
sudo systemctl status aureon-ws-feeder  # Should show "active (running)"

# Start Truth Prediction Engine
sudo systemctl start aureon-truth-engine
sudo systemctl status aureon-truth-engine  # Should show "active (running)"

# Enable auto-start on boot
sudo systemctl enable aureon-ws-feeder aureon-truth-engine
```

---

## Step 5: Verify It's Working (30 seconds)

```bash
# Check market data is flowing
cat /opt/aureon-trading/ws_cache/ws_prices.json | jq '.prices | keys | length'
# Should show number like: 100-365 (symbols being tracked)

# Check predictions are generating (wait 2 minutes first)
cat /opt/aureon-trading/aureon_truth_prediction_state.json | jq '.predictions | length'
# Should show increasing number

# Run monitoring dashboard
/opt/aureon-trading/monitor.sh
```

**Expected output:**
```
🔍 AUREON TRADING SYSTEM - STATUS
============================================================
SERVICE STATUS:
  aureon-ws-feeder         ✅ active (running)
  aureon-truth-engine      ✅ active (running)
  aureon-orca-trading      ⏸️  inactive (disabled)

PREDICTIONS:
  Total Predictions: 15
  Total Validations: 3
  Accuracy: 66.67%

DISK USAGE:
  /opt/aureon-trading: 156M
```

---

## ✅ Success! What Now?

### ⏳ Next 7 Days: Validation Period

**DO NOT TRADE YET**. Let the system run and validate predictions:

```bash
# Check daily
ssh root@YOUR_DROPLET_IP
/opt/aureon-trading/monitor.sh

# Calculate accuracy
cat /opt/aureon-trading/aureon_truth_prediction_state.json | \
  jq '.validations | map(.correct) | (map(select(. == true)) | length) / length * 100'
```

**Required before trading:**
- ✅ Accuracy ≥ 60% over 7 days
- ✅ No crashes or restarts
- ✅ Logs clean (no errors)

### 📋 After 7 Days: Enable Dry-Run Trading

```bash
# Edit Orca service
sudo nano /etc/systemd/system/aureon-orca-trading.service

# Change ExecStart line to:
ExecStart=/opt/aureon-trading/venv/bin/python orca_complete_kill_cycle.py --dry-run

# Save, reload, start
sudo systemctl daemon-reload
sudo systemctl start aureon-orca-trading
sudo systemctl enable aureon-orca-trading

# Monitor for 48 hours
tail -f /opt/aureon-trading/logs/orca-trading.log
```

### 🚀 After Dry-Run Success: Live Trading (SMALL CAPITAL)

```bash
# Remove --dry-run flag
sudo nano /etc/systemd/system/aureon-orca-trading.service
# ExecStart=/opt/aureon-trading/venv/bin/python orca_complete_kill_cycle.py

# Edit Orca config to limit positions
nano /opt/aureon-trading/orca_complete_kill_cycle.py
# Find: MAX_POSITION_SIZE = 1000.0
# Change to: MAX_POSITION_SIZE = 50.0  # Start with $50 max

# Restart
sudo systemctl restart aureon-orca-trading

# WATCH EVERY TRADE CLOSELY
tail -f /opt/aureon-trading/logs/orca-trading.log | grep "TRADE"
```

**⚠️ ONLY proceed if 1 week profitable at $50 positions ⚠️**

---

## 🆘 Troubleshooting

### Service won't start
```bash
# Check status
sudo systemctl status aureon-ws-feeder
sudo systemctl status aureon-truth-engine

# Check logs
sudo journalctl -u aureon-ws-feeder -n 50
sudo journalctl -u aureon-truth-engine -n 50

# Common fix: permissions
sudo chown -R $USER:$USER /opt/aureon-trading
```

### No market data
```bash
# Check WS feeder is running
ps aux | grep ws_market_data_feeder

# Check cache file
ls -lh /opt/aureon-trading/ws_cache/ws_prices.json

# Watch live updates
watch -n 1 stat /opt/aureon-trading/ws_cache/ws_prices.json

# Restart feeder
sudo systemctl restart aureon-ws-feeder
```

### No predictions
```bash
# Check Truth Engine logs
tail -f /opt/aureon-trading/logs/truth-engine.log

# Verify intelligence loaded (should see this in logs):
# "Probability Ultimate Intelligence: 95% accuracy, 57 patterns"

# Check state file
cat /opt/aureon-trading/aureon_truth_prediction_state.json

# Restart engine
sudo systemctl restart aureon-truth-engine
```

### High memory usage
```bash
# Check memory
free -h

# Check processes
top

# Upgrade droplet if <500 MB free:
# DigitalOcean Console → Resize → 4 GB RAM ($24/mo)
```

---

## 📚 Full Documentation

- **Complete Setup Guide**: [DIGITALOCEAN_DEPLOYMENT.md](DIGITALOCEAN_DEPLOYMENT.md)
- **Pre-Flight Checklist**: [PREFLIGHT_CHECKLIST.md](../runbooks/PREFLIGHT_CHECKLIST.md)
- **Compatibility Check**: Run `python check_digitalocean_compat.py`

---

## 💰 Cost Breakdown

| Tier | RAM | vCPUs | Storage | Cost/Month | Use Case |
|------|-----|-------|---------|------------|----------|
| Basic | 2 GB | 1 | 50 GB | $12 | Testing predictions |
| Regular | 4 GB | 2 | 80 GB | $24 | Dry-run trading |
| Professional | 8 GB | 4 | 160 GB | $48 | Live trading (high frequency) |

**Recommendation**: Start with $12 tier for 7-day validation, upgrade to $24 for live trading.

---

## 🔒 Security Checklist

- [x] UFW firewall enabled (SSH only)
- [ ] Disable root login after creating non-root user
- [ ] .env file permissions: `chmod 600 .env`
- [ ] API keys are READ-ONLY (no withdrawal)
- [ ] SSH key authentication only (no passwords)
- [ ] Weekly snapshots enabled (DigitalOcean console)
- [ ] Regular `apt update && apt upgrade`

---

## 🎯 Success Criteria Summary

**Before ANY trading:**
1. ✅ 7 days uptime without crashes
2. ✅ Prediction accuracy ≥ 60%
3. ✅ Avg geometric truth ≥ 0.7
4. ✅ Pattern confidence ≥ 0.65
5. ✅ All safety gates tested and working
6. ✅ Dry-run trades would be profitable
7. ✅ 1 week profitable at $50 positions

**If ANY criterion not met: DO NOT TRADE**

---

**Need help?** Check logs first:
```bash
# Service logs
sudo journalctl -u aureon-ws-feeder -n 100
sudo journalctl -u aureon-truth-engine -n 100

# Application logs
tail -f /opt/aureon-trading/logs/*.log

# System status
/opt/aureon-trading/monitor.sh
```

---

**Version**: 1.0  
**Last Updated**: 2025-01-27  
**Estimated Time**: 5 minutes (plus 7-day validation period)
