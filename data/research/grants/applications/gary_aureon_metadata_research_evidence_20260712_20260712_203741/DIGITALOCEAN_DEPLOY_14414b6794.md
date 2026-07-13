# Aureon Trading - DigitalOcean Deployment Guide
# Autonomous Volatility/Momentum Trading Bot

## Quick Deploy to DigitalOcean (3 Methods)

### Method 1: App Platform (Easiest - Managed Service)

1. **Create App from GitHub:**
   - Go to DigitalOcean Dashboard → Apps → Create App
   - Connect GitHub: `RA-CONSULTING/aureon-trading`
   - Branch: `main`

2. **Configure Resources:**
   - Plan: **Professional XS** (1GB RAM) minimum
   - **Recommended: Professional S** (2GB RAM) for better performance
   - Region: Choose closest to exchange APIs (US East recommended)

3. **Set Environment Variables:**
   ```
   MODE=autonomous
   MAX_POSITIONS=3
   AMOUNT_PER_POSITION=5.0
   TARGET_PCT=1.0
   MIN_CHANGE_PCT=0.25
   
   KRAKEN_API_KEY=your_key
   KRAKEN_API_SECRET=your_secret
   BINANCE_API_KEY=your_key
   BINANCE_API_SECRET=your_secret
   ALPACA_API_KEY=your_key
   ALPACA_API_SECRET=your_secret
   ```

4. **Deploy:** Click "Create Resources" - Done! ✅

**Cost:** $12-24/month (fully managed)

---

### Method 2: Docker on Droplet (Best Performance)

1. **Create Droplet:**
   - OS: Ubuntu 24.04 LTS
   - Size: Basic - 2GB RAM / 1 vCPU ($12/mo) or 4GB / 2 vCPU ($24/mo)
   - Region: New York 1 (closest to exchanges)

2. **SSH and Setup:**
   ```bash
   ssh root@your_droplet_ip
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Clone repo
   git clone https://github.com/RA-CONSULTING/aureon-trading.git
   cd aureon-trading
   
   # Create .env file with your API keys
   nano .env
   ```

3. **Configure `.env`:**
   ```ini
   # Exchange API Keys
   KRAKEN_API_KEY=your_key_here
   KRAKEN_API_SECRET=your_secret_here
   BINANCE_API_KEY=your_key
   BINANCE_API_SECRET=your_secret
   ALPACA_API_KEY=your_key
   ALPACA_API_SECRET=your_secret
   
   # Trading Config
   MODE=autonomous
   MAX_POSITIONS=3
   AMOUNT_PER_POSITION=5.0
   TARGET_PCT=1.0
   MIN_CHANGE_PCT=0.25
   ```

4. **Run with Docker Compose:**
   ```bash
   # Autonomous mode (pure trading, no UI)
   docker-compose -f docker-compose.autonomous.yml up -d
   
   # OR Full stack (trading + web UI + monitoring)
   docker-compose up -d
   ```

5. **Monitor Logs:**
   ```bash
   docker logs -f aureon-autonomous-trader
   ```

**Cost:** $12-24/month droplet only

---

### Method 3: SystemD Service (Traditional)

1. **Create Droplet** (same as Method 2)

2. **Auto-Setup Script:**
   ```bash
   ssh root@your_droplet_ip
   curl -sSL https://raw.githubusercontent.com/RA-CONSULTING/aureon-trading/main/deploy/droplet-setup.sh | bash
   ```

3. **Configure API Keys:**
   ```bash
   nano /root/aureon-trading/.env
   # Add your exchange API keys
   ```

4. **Start Service:**
   ```bash
   systemctl start orca-kill-cycle
   systemctl status orca-kill-cycle
   journalctl -u orca-kill-cycle -f  # Watch logs
   ```

---

## How the Volatility Scanner Works

The system scans **entire market** every 3-10 seconds:

1. **Scan Phase:** 
   - Alpaca, Kraken, Binance, Capital.com
   - Detects price moves ≥ 0.25% (configurable)
   - Scores by momentum (price change × volume)

2. **Filter Phase:**
   - Queen AI approval (30% confidence minimum)
   - COP energy efficiency > 0.85
   - Minimum position size $20 (prevents fee losses)

3. **Execute Phase:**
   - Buy best opportunity with available cash
   - Monitor position every 0.5-1 second
   - Sell ONLY when profitable (no stop loss)

4. **Profit Taking:**
   - Target hit: immediate exit
   - Momentum reversal: exit if in profit
   - Cost basis validation prevents selling at loss

---


## Runtime Validation (Proves Parallel + Optimized Operation)

Run these checks on the droplet after deployment to confirm the system is truly utilizing DigitalOcean resources:

```bash
# 1) Confirm containers are running and healthy
docker compose -f docker-compose.autonomous.yml ps
docker inspect --format='{{json .State.Health}}' aureon-autonomous-trader | jq

# 2) Confirm CPU/RAM usage and no restart loops
docker stats --no-stream aureon-autonomous-trader
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}'

# 3) Confirm bot/runtime processes in parallel
pgrep -af "(aureon|orca|queen|ws_market_data_feeder|aureon_live_tv_station|deploy_digital_ocean)"

# 4) If using supervisor mode, verify all programs are RUNNING
supervisorctl -c supervisord.conf status

# 5) Unified local status helper
bash check_status.sh
```

If any service is missing or unhealthy, do not assume optimization is active. Fix health/restarts first, then re-run the checklist.

---

## Monitoring Your Bot

### Docker Logs
```bash
# Autonomous mode
docker logs -f aureon-autonomous-trader

# Full stack
docker logs -f aureon-trading
```

### Check Trade History
```bash
# SSH into container
docker exec -it aureon-autonomous-trader bash

# View recent trades
tail -50 orca_trade_history.json
cat cost_basis_history.json | jq '.positions | length'  # Position count
```

### Prometheus Metrics (Full Stack Only)
- Grafana: `http://your_droplet_ip:3000`
- Prometheus: `http://your_droplet_ip:9090`

---

## Troubleshooting

### No Trades Executing
```bash
# Check logs for:
# - "BUY BLOCKED: COP" → Lower MIN_CHANGE_PCT to 0.2
# - "Queen unavailable" → Normal, uses default approval
# - "No cash available" → Fund your exchanges
# - "No profitable positions" → Working as designed (won't sell at loss)
```

### Container Keeps Restarting
```bash
docker logs aureon-autonomous-trader
# Common fixes:
# 1. Missing .env file → Create it with API keys
# 2. Invalid API keys → Check exchange dashboards
# 3. Out of memory → Upgrade droplet to 4GB RAM
```

### API Rate Limits
```bash
# Edit docker-compose.autonomous.yml
# Increase scan_interval in environment:
- SCAN_INTERVAL=15  # Scan every 15s instead of 10s
```

---

## Cost Breakdown

| Deployment | Monthly Cost | Best For |
|------------|-------------|----------|
| App Platform (1GB) | $12 | Beginners, small accounts |
| App Platform (2GB) | $24 | Recommended for production |
| Droplet (2GB) + Docker | $12 | Advanced users |
| Droplet (4GB) + Docker | $24 | High-frequency trading |

---

## Security Best Practices

1. **API Keys:**
   - Use **read + trade** permissions only (no withdrawals)
   - Whitelist DigitalOcean IPs in exchange settings
   - Rotate keys every 90 days

2. **Environment Variables:**
   - Never commit `.env` to git
   - Use DigitalOcean Secrets for App Platform

3. **Firewall:**
   ```bash
   # Block all except SSH (Droplet only)
   ufw allow 22/tcp
   ufw enable
   ```

---

## Support

- **Logs Location:** `/app/logs/` (in container) or `./logs/` (host)
- **State Files:** All `*.json` files preserve trade history
- **Emergency Stop:** `docker stop aureon-autonomous-trader`
- **Full Reset:** Delete all `*.json` files (loses history)

---

**Ready to Deploy?** Choose Method 1 (App Platform) for easiest setup, or Method 2 (Docker) for best performance!
