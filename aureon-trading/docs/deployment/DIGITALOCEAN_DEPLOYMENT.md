# Aureon Trading System - DigitalOcean Deployment Guide

## 🌊 Quick Start on DigitalOcean

### 1. Create Droplet

**Recommended Specs:**
- **Size**: Basic ($12/mo) or Regular ($24/mo)
  - 2 GB RAM minimum (4 GB recommended for Orca trading)
  - 1-2 vCPUs
  - 50 GB SSD
- **OS**: Ubuntu 24.04 LTS x64
- **Region**: Choose closest to your exchange APIs (e.g., NYC for US, London for EU)
- **Add SSH Key**: For secure access

### 2. Initial Setup

SSH into your droplet:
```bash
ssh root@your_droplet_ip
```

Download and run setup script:
```bash
cd /opt
git clone https://github.com/your-repo/aureon-trading.git
cd aureon-trading
chmod +x deploy_digitalocean.sh
./deploy_digitalocean.sh
```

### 3. Configure API Keys

Edit the `.env` file with your real API keys:
```bash
nano /opt/aureon-trading/.env
```

**Replace these values:**
```env
KRAKEN_API_KEY=your_actual_kraken_api_key
KRAKEN_API_SECRET=your_actual_kraken_secret
BINANCE_API_KEY=your_actual_binance_api_key
BINANCE_API_SECRET=your_actual_binance_secret
ALPACA_API_KEY=your_actual_alpaca_api_key
ALPACA_API_SECRET=your_actual_alpaca_secret
```

Save and exit (`Ctrl+X`, `Y`, `Enter`)

### 4. Start Services

```bash
# Start WebSocket feeder (gets live market data)
sudo systemctl start aureon-ws-feeder

# Start Truth Prediction Engine (generates predictions)
sudo systemctl start aureon-truth-engine

# Check status
sudo systemctl status aureon-ws-feeder
sudo systemctl status aureon-truth-engine
```

### 5. Monitor System

Use the monitoring script:
```bash
cd /opt/aureon-trading
./monitor.sh
```

View live logs:
```bash
# WS Feeder logs
tail -f /opt/aureon-trading/logs/ws-feeder.log

# Truth Engine logs
tail -f /opt/aureon-trading/logs/truth-engine.log

# Prediction stream
tail -f /opt/aureon-trading/live_tv_stream.jsonl
```

Check predictions:
```bash
cat aureon_truth_prediction_state.json | jq '.validations[-10:]'
```

---

## 🔧 Service Management

### Start/Stop/Restart Services

```bash
# WS Feeder
sudo systemctl start aureon-ws-feeder
sudo systemctl stop aureon-ws-feeder
sudo systemctl restart aureon-ws-feeder

# Truth Engine
sudo systemctl start aureon-truth-engine
sudo systemctl stop aureon-truth-engine
sudo systemctl restart aureon-truth-engine

# Orca Trading (when ready for production)
sudo systemctl start aureon-orca-trading
sudo systemctl stop aureon-orca-trading
```

### Enable/Disable Auto-Start on Boot

```bash
# Enable (already done by setup script)
sudo systemctl enable aureon-ws-feeder
sudo systemctl enable aureon-truth-engine

# Disable
sudo systemctl disable aureon-ws-feeder
sudo systemctl disable aureon-truth-engine
```

### View Service Logs

```bash
# Last 50 lines
sudo journalctl -u aureon-ws-feeder -n 50

# Follow live
sudo journalctl -u aureon-truth-engine -f

# Errors only
sudo journalctl -u aureon-ws-feeder --priority=err
```

---

## 📊 Monitoring & Maintenance

### Check Prediction Accuracy

```bash
cd /opt/aureon-trading

# Overall accuracy
python3 -c "
import json
from pathlib import Path

state = json.loads(Path('aureon_truth_prediction_state.json').read_text())
vals = state.get('validations', [])
if vals:
    correct = sum(1 for v in vals if v.get('correct'))
    print(f'Accuracy: {correct}/{len(vals)} = {correct/len(vals)*100:.1f}%')
else:
    print('No validations yet')
"
```

### Disk Usage

```bash
# Check disk space
df -h /opt/aureon-trading

# Check log sizes
du -sh /opt/aureon-trading/logs/*
du -sh /opt/aureon-trading/*.jsonl
```

### Manual Backup

```bash
cd /opt/aureon-trading
./backup.sh
```

### Clean Old Logs (if needed)

```bash
# Delete logs older than 7 days
find /opt/aureon-trading/logs -name "*.log" -mtime +7 -delete
```

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check status and errors
sudo systemctl status aureon-ws-feeder
sudo journalctl -u aureon-ws-feeder -n 50 --no-pager

# Check permissions
ls -la /opt/aureon-trading/ws_cache
ls -la /opt/aureon-trading/logs

# Fix permissions if needed
sudo chown -R $USER:$USER /opt/aureon-trading
chmod 755 /opt/aureon-trading/ws_cache
chmod 755 /opt/aureon-trading/logs
```

### No Market Data

```bash
# Check WS feeder is running
sudo systemctl status aureon-ws-feeder

# Check cache file exists and is updating
ls -lh /opt/aureon-trading/ws_cache/ws_prices.json
watch -n 1 'stat /opt/aureon-trading/ws_cache/ws_prices.json'

# Test WebSocket connection manually
cd /opt/aureon-trading
source venv/bin/activate
python ws_market_data_feeder.py --binance --write-interval-s 1.0
```

### No Predictions Generated

```bash
# Check Truth Engine is running
sudo systemctl status aureon-truth-engine

# Check state file
cat aureon_truth_prediction_state.json | jq '.'

# Check if probability intelligence loaded
grep "Probability Ultimate Intelligence" logs/truth-engine.log

# Restart Truth Engine
sudo systemctl restart aureon-truth-engine
```

### High Memory Usage

```bash
# Check memory
free -h

# Check process memory
top -o %MEM

# Restart services to clear memory
sudo systemctl restart aureon-ws-feeder
sudo systemctl restart aureon-truth-engine
```

---

## 🔐 Security Best Practices

### 1. Secure SSH Access

```bash
# Disable root login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no

# Disable password auth (SSH keys only)
# Set: PasswordAuthentication no

# Restart SSH
sudo systemctl restart sshd
```

### 2. Setup UFW Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

### 3. Keep API Keys Secure

```bash
# Verify .env permissions (should be 600)
ls -la /opt/aureon-trading/.env

# Fix if needed
chmod 600 /opt/aureon-trading/.env
```

### 4. Regular Updates

```bash
# Update system packages weekly
sudo apt-get update && sudo apt-get upgrade -y

# Update Python dependencies monthly
cd /opt/aureon-trading
source venv/bin/activate
pip install --upgrade pip
pip list --outdated
```

---

## 📈 Production Deployment (Orca Trading)

⚠️ **WARNING**: Only enable Orca trading AFTER extensive testing!

### Test Mode (Dry Run)

```bash
# Edit service file
sudo nano /etc/systemd/system/aureon-orca-trading.service

# Change ExecStart to:
ExecStart=/opt/aureon-trading/venv/bin/python /opt/aureon-trading/orca_complete_kill_cycle.py --dry-run

# Reload and start
sudo systemctl daemon-reload
sudo systemctl start aureon-orca-trading

# Monitor for 24-48 hours
tail -f /opt/aureon-trading/logs/orca-trading.log
```

### Live Mode (Real Money)

```bash
# After successful dry-run testing, remove --dry-run flag
sudo nano /etc/systemd/system/aureon-orca-trading.service

# Change to:
ExecStart=/opt/aureon-trading/venv/bin/python /opt/aureon-trading/orca_complete_kill_cycle.py

# Reload and start
sudo systemctl daemon-reload
sudo systemctl start aureon-orca-trading
sudo systemctl enable aureon-orca-trading

# Monitor closely for first week
tail -f /opt/aureon-trading/logs/orca-trading.log
```

---

## 💰 Cost Optimization

**Monthly Costs:**
- Basic Droplet ($12/mo): Good for testing, light trading
- Regular Droplet ($24/mo): Recommended for production
- Professional Droplet ($48/mo): For high-frequency trading

**Reduce Costs:**
- Use snapshot backups instead of 24/7 running (when not trading)
- Start/stop droplet during non-trading hours
- Use monitoring to detect issues quickly (less manual checking)

---

## 📞 Support & Updates

**Check for Updates:**
```bash
cd /opt/aureon-trading
git pull origin main
sudo systemctl restart aureon-ws-feeder
sudo systemctl restart aureon-truth-engine
```

**View System Stats:**
```bash
./monitor.sh
```

**Emergency Stop:**
```bash
# Stop all trading immediately
sudo systemctl stop aureon-orca-trading
sudo systemctl stop aureon-truth-engine
sudo systemctl stop aureon-ws-feeder
```

---

## ✅ Post-Deployment Checklist

- [ ] SSH access working with key (no password)
- [ ] UFW firewall enabled
- [ ] API keys configured in `.env`
- [ ] WS feeder running and populating cache
- [ ] Truth Engine running and generating predictions
- [ ] Predictions being validated (check state file)
- [ ] Log rotation configured
- [ ] Backups running (check `backups/` directory)
- [ ] Monitoring script works (`./monitor.sh`)
- [ ] Tested dry-run mode (if using Orca)
- [ ] Alerts configured (email/SMS for errors)

---

**CRITICAL REMINDER**: Never enable live trading (`aureon-orca-trading.service`) without extensive testing and validation of predictions. The system should show consistent 60%+ accuracy before risking real capital.
