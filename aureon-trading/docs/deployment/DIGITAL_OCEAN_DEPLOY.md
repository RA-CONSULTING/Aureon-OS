# Digital Ocean Deployment Guide

## 🚀 Quick Deploy to Digital Ocean

### Option 1: Auto-Deploy via GitHub (Recommended)

1. **Push to main branch** (already configured):
   ```bash
   git push origin main
   ```

2. **Digital Ocean will automatically**:
   - Detect the push
   - Build Docker image from `Dockerfile`
   - Deploy to App Platform
   - Start all 6 systems via supervisord

3. **Monitor deployment**:
   - Go to: https://cloud.digitalocean.com/apps
   - Watch build logs for any errors
   - Health check starts after 120s

### Option 2: Manual Deploy via doctl CLI

```bash
# Install doctl if not already installed
brew install doctl  # macOS
# or
snap install doctl  # Linux

# Authenticate
doctl auth init

# Create app from spec
doctl apps create --spec app.yaml

# Update existing app
doctl apps update YOUR_APP_ID --spec app.yaml
```

## 🐝 Systems Running in Container

Once deployed, these 6 systems run in parallel via supervisord:

1. **Command Center** (Port 8080)
   - Web UI dashboard
   - WebSocket communication
   - System orchestration

2. **Orca Kill Cycle**
   - Trading execution engine
   - Responds to Queen's decisions

3. **Autonomous Engine**
   - 9 parallel intelligence loops
   - Feeds Queen with signals

4. **Queen Power Redistribution** 🆕
   - Energy optimization
   - Autonomous trading decisions
   - Scans every 60s

5. **Queen Power Dashboard** 🆕
   - Real-time monitoring
   - Updates every 5s
   - Logs to `/app/logs/queen_dashboard.log`

6. **Kraken Cache Feeder** 🆕
   - Centralized API access
   - Prevents rate limiting
   - Updates every 15s

## 📊 Monitoring

### View Logs

```bash
# All logs
doctl apps logs YOUR_APP_ID

# Specific component
doctl apps logs YOUR_APP_ID --type deploy
doctl apps logs YOUR_APP_ID --type run
```

### Health Check

The app exposes `/health` endpoint on port 8080:
```bash
curl https://your-app.ondigitalocean.app/health
```

### Queen Dashboard Access

Dashboard logs are written to `/app/logs/queen_dashboard.log` inside container.

To access:
```bash
# Via doctl
doctl apps logs YOUR_APP_ID --follow | grep queen
```

## 🔧 Configuration

### Environment Variables

Set in Digital Ocean App Platform dashboard or in `app.yaml`:

**Required:**
- API keys for exchanges (Binance, Kraken, Alpaca, Capital.com)
- Set in App Platform → Settings → Environment Variables

**System:**
- `PYTHONIOENCODING=utf-8` (already set)
- `PYTHONUNBUFFERED=1` (already set)
- `AUREON_STATE_DIR=/app/state` (already set)
- `AUREON_ENABLE_AUTONOMOUS_CONTROL=1` (already set)

### State Persistence

State files are stored in `/app/` directory:
- `queen_redistribution_state.json`
- `power_station_state.json`
- `queen_energy_balance.json`
- `aureon_kraken_state.json`
- `binance_truth_tracker_state.json`
- `alpaca_truth_tracker_state.json`

**Note**: Digital Ocean App Platform has ephemeral filesystem. For persistence, consider:
1. Using Digital Ocean Spaces (S3-compatible)
2. Adding a managed database
3. Using volume mounts (if available in your plan)

## 🐛 Troubleshooting

### Container Won't Start

1. **Check build logs**:
   ```bash
   doctl apps logs YOUR_APP_ID --type build
   ```

2. **Check startup validation**:
   Look for "Validating Digital Ocean deployment..." in logs

3. **Common issues**:
   - Missing API keys → Add in App Platform settings
   - Import errors → Check `requirements.txt` includes all deps
   - Permission errors → Scripts should be executable (chmod +x)

### Services Not Running

Check supervisord status in logs:
```bash
doctl apps logs YOUR_APP_ID | grep supervisor
```

Expected output:
```
✅ command-center RUNNING
✅ orca-engine RUNNING
✅ autonomous-engine RUNNING
✅ queen-redistribution RUNNING
✅ queen-dashboard RUNNING
✅ kraken-cache RUNNING
```

### Queen Not Making Decisions

1. **Check if idle energy available**:
   - Need minimum $10 idle in relay
   - Check relay balances in logs

2. **Check 7-day validations**:
   - Queen uses validated branches with coherence > 0.618
   - If none available, no opportunities found

3. **Check rate limits**:
   - Kraken cache should prevent this
   - Look for "EAPI:Rate limit exceeded" errors

## 📈 Performance

**Instance Requirements:**
- Minimum: Professional-XS (1GB RAM, 0.5 vCPU)
- Recommended: Professional-S (2GB RAM, 1 vCPU)

**Expected Resource Usage:**
- CPU: 20-40% average
- RAM: 600-800MB
- Network: Low (API calls only)

## 🔒 Security

1. **Never commit API keys** to git
2. **Use Digital Ocean's Secret management**
3. **Enable 2FA** on all exchange accounts
4. **Start in dry-run mode** to validate

## 🚦 Deployment Checklist

- [x] Docker configuration updated
- [x] supervisord.conf includes all 6 systems
- [x] Startup validation script created
- [x] app.yaml configured for Digital Ocean
- [x] State files initialized with valid JSON
- [ ] Add API keys to App Platform
- [ ] Test deployment in staging first
- [ ] Monitor for 24h after production deploy
- [ ] Set up alerts for critical errors

## 📞 Support

If issues persist:
1. Check Digital Ocean status: https://status.digitalocean.com
2. Review App Platform logs
3. Test locally with Docker: `docker-compose up`
4. Check GitHub Actions for build errors

---

**Deployed! 🎉** Queen is now autonomous on Digital Ocean. Monitor her intelligence via logs.
