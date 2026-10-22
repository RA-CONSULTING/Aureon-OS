# 🚀 DigitalOcean Deployment Guide

## Quick Start Options

### Option 1: App Platform (Managed, Easy)
```bash
# 1. Create app from GitHub
doctl apps create --spec .do/app.yaml

# 2. Add API keys in dashboard
# Go to: Apps → Settings → Environment Variables
# Add: KRAKEN_API_KEY, BINANCE_API_KEY, etc. as encrypted variables

# 3. Deploy
# Automatic on git push to main
```

**Cost**: $12-24/month | **Setup**: 5 minutes

---

### Option 2: Droplet (Full Control, Recommended)
```bash
# 1. Create droplet
doctl compute droplet create aureon-trading \
  --image ubuntu-24-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys YOUR_SSH_KEY_ID

# 2. Get droplet IP
doctl compute droplet list

# 3. SSH and run setup script
ssh root@DROPLET_IP
curl -sSL https://raw.githubusercontent.com/RA-CONSULTING/aureon-trading/main/deploy/droplet-setup.sh | bash

# 4. Edit API keys
nano /root/aureon-trading/.env

# 5. Start trading
systemctl start aureon-trading
```

**Cost**: $12/month (2GB) or $24/month (4GB) | **Setup**: 10 minutes

---

### Option 3: Docker Compose (Advanced)
```bash
# On your droplet
git clone https://github.com/RA-CONSULTING/aureon-trading.git
cd aureon-trading
cp .env.example .env
nano .env  # Add API keys
docker-compose up -d
```

---

## Deployment Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image for trading system |
| `.dockerignore` | Optimize Docker builds |
| `.do/app.yaml` | App Platform configuration |
| `docker-compose.yml` | Multi-container setup with monitoring |
| `deploy/droplet-setup.sh` | One-command droplet initialization |
| `deploy/droplet-deploy.sh` | Update code on running droplet |
| `deploy/systemd/aureon-trading.service` | Auto-start service |

---

## Environment Variables Required

Add these in `.env` file (Droplet) or DO dashboard (App Platform):

```bash
# Exchange APIs
KRAKEN_API_KEY=your_key
KRAKEN_API_SECRET=your_secret
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
CAPITAL_API_KEY=your_key
CAPITAL_API_PASSWORD=your_password
CAPITAL_IDENTIFIER=your_identifier
```

---

## Management Commands

### App Platform
```bash
# View logs
doctl apps logs <app-id> --type run --follow

# Restart
doctl apps create-deployment <app-id>

# Scale up
doctl apps update <app-id> --spec .do/app.yaml
```

### Droplet (Systemd)
```bash
# Start
systemctl start aureon-trading

# Stop
systemctl stop aureon-trading

# Restart
systemctl restart aureon-trading

# Status
systemctl status aureon-trading

# Logs (live)
journalctl -u aureon-trading -f

# Logs (last 100 lines)
journalctl -u aureon-trading -n 100
```

### Docker Compose
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f trading-engine

# Update
git pull
docker-compose build
docker-compose up -d
```

---

## Monitoring

### App Platform
- Built-in metrics in DO dashboard
- CPU, Memory, Restart count
- Alerts configured in `.do/app.yaml`

### Droplet
```bash
# Install netdata (real-time monitoring)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)

# Access at: http://DROPLET_IP:19999
```

### Docker Compose
- Prometheus: http://DROPLET_IP:9090
- Grafana: http://DROPLET_IP:3000 (admin/changeme)

---

## Backups

### Automated (Droplet)
```bash
# Runs daily at 2 AM via cron
/root/backup-aureon.sh

# View backups
ls -lh /root/aureon-backups/
```

### Manual
```bash
# Backup state files
tar -czf aureon-backup-$(date +%Y%m%d).tar.gz \
  *.json state/ logs/

# Upload to DigitalOcean Spaces
s3cmd put aureon-backup-*.tar.gz s3://your-bucket/
```

---

## Troubleshooting

### App Platform: "Script not found 'start'"
✅ **Fixed**: Using Dockerfile instead of buildpack detection

### System won't start
```bash
# Check logs
journalctl -u aureon-trading -n 100

# Check Python errors
systemctl status aureon-trading

# Verify API keys loaded
systemctl show aureon-trading | grep Environment
```

### High memory usage
```bash
# Check usage
free -h
docker stats  # If using Docker

# Restart if needed
systemctl restart aureon-trading
```

### Capital.com rate limiting
✅ **Fixed**: Lazy-loading prevents init-time rate limits

---

## Cost Comparison

| Option | Specs | Monthly Cost | Control |
|--------|-------|--------------|---------|
| App Platform (Basic) | 512MB RAM | $5 | ❌ Low |
| App Platform (Pro) | 1GB RAM | $12 | ⚠️ Medium |
| Droplet (2GB) | 2GB RAM, 1 vCPU | $12 | ✅ Full |
| Droplet (4GB) | 4GB RAM, 2 vCPU | $24 | ✅ Full |

**Recommendation**: Droplet (4GB) for production - $24/month

---

## Next Steps

1. ✅ Commit deployment files
2. ✅ Push to GitHub
3. 🚀 Choose deployment method
4. 🔑 Add API keys
5. 📊 Monitor performance
6. 💰 Start trading!

---

**Need help?** Check system logs or contact support.
