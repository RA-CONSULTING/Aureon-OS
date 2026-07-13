# 🚀 Quick Deploy to DigitalOcean

All deployment files are ready! Choose your method:

---

## 🎯 Fastest: App Platform (5 minutes)

```bash
# 1. Push to GitHub
git add .
git commit -m "🚀 Add DigitalOcean deployment files"
git push origin main

# 2. Create app (via CLI)
doctl apps create --spec .do/app.yaml

# OR via Dashboard:
# - Go to https://cloud.digitalocean.com/apps/new
# - Select your GitHub repo: RA-CONSULTING/aureon-trading
# - DigitalOcean will auto-detect the Dockerfile
# - Add environment variables (API keys)
# - Deploy!

# 3. Add API keys in DO dashboard
# Apps → Settings → Environment Variables → Edit
# Add as ENCRYPTED:
#   - KRAKEN_API_KEY
#   - KRAKEN_API_SECRET
#   - BINANCE_API_KEY
#   - BINANCE_API_SECRET
#   - ALPACA_API_KEY
#   - ALPACA_API_SECRET
#   - CAPITAL_API_KEY
#   - CAPITAL_API_PASSWORD
#   - CAPITAL_IDENTIFIER
```

**Cost**: $12/month (1GB RAM)  
**URL**: Auto-generated `.ondigitalocean.app`

---

## 💪 Best: Droplet (10 minutes, Full Control)

```bash
# 1. Create droplet
doctl compute droplet create aureon-trading \
  --image ubuntu-24-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -n1)

# 2. Get IP address
doctl compute droplet list

# 3. Run setup script
ssh root@YOUR_DROPLET_IP
curl -sSL https://raw.githubusercontent.com/RA-CONSULTING/aureon-trading/main/deploy/droplet-setup.sh | bash

# 4. Edit API keys
nano /root/aureon-trading/.env

# 5. Start trading!
systemctl start aureon-trading
systemctl status aureon-trading
journalctl -u aureon-trading -f
```

**Cost**: $24/month (4GB RAM recommended)  
**Access**: SSH + full control

---

## 🐳 Advanced: Docker Compose

```bash
# On your droplet or local machine
git clone https://github.com/RA-CONSULTING/aureon-trading.git
cd aureon-trading
cp .env.example .env
nano .env  # Add your API keys

# Start everything (trading + monitoring)
docker-compose up -d

# View logs
docker-compose logs -f trading-engine

# Access Grafana dashboard
# http://YOUR_IP:3000 (admin/changeme)
```

**Includes**: Prometheus + Grafana monitoring

---

## 📊 What's Included

✅ **Dockerfile** - Production-ready container  
✅ **.do/app.yaml** - App Platform config  
✅ **docker-compose.yml** - Multi-container setup  
✅ **deploy/droplet-setup.sh** - One-command initialization  
✅ **deploy/droplet-deploy.sh** - Easy updates  
✅ **deploy/systemd/aureon-trading.service** - Auto-start on boot  
✅ **.dockerignore** - Optimized builds  
✅ **.env.example** - Environment template  

---

## 🔍 Check Deployment

### App Platform
```bash
doctl apps list
doctl apps logs YOUR_APP_ID --follow
```

### Droplet
```bash
systemctl status aureon-trading
journalctl -u aureon-trading -f
```

### Docker
```bash
docker-compose ps
docker-compose logs -f
```

---

## 🆘 Troubleshooting

### App Platform shows "Script not found 'start'"
✅ Fixed! We're using Dockerfile now, not Node.js buildpack.

### Can't connect to exchanges
- Check API keys in `.env` or DO environment variables
- Verify keys have trading permissions
- Check firewall allows outbound HTTPS

### System crashes or restarts
- View logs: `journalctl -u aureon-trading -n 100`
- Increase memory: Upgrade to 4GB droplet
- Check Capital.com rate limiting (fixed with lazy-loading)

---

## 📚 Full Documentation

See [DEPLOY.md](DEPLOY.md) for complete guide.

---

**Ready to deploy?** Pick your method above and follow the steps! 🚀
