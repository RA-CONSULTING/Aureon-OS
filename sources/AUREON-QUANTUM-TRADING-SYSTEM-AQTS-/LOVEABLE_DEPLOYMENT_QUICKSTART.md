# LOVEABLE Deployment Quickstart

> Purpose: Give the Loveable platform (or any newcomer) a clear, **safe, reproducible** path to stand up the AUREON Quantum Trading System (AQTS) in dry-run and (optionally) live trading mode.
>
> Audience: Engineer with general Node.js & Linux knowledge but **no prior AQTS context**.

---
## 1. High-Level Overview
AQTS consists of:
- Frontend React console (Vite dev server)
- Simulation & trading scripts (TypeScript / Python helpers)
- Core orchestration & signal engines under `core/`
- Optional live trade execution via Binance Spot API (disabled by default)
- Monitoring/status server for balances, bot tails, and recent trades

You will proceed in phases:
1. Clone & install
2. Configure environment (`.env`)
3. Run dry-run bots and status server
4. Launch UI and verify metrics
5. (Optional) Enable live trading with explicit safeguards
6. Set up process supervision & monitoring

---
## 2. System Requirements
| Component | Requirement |
|-----------|------------|
| OS | Ubuntu 20.04+ (tested 24.04) or macOS 13+ |
| Node.js | >= 18 (recommend 20 or 22 LTS) |
| npm | >= 9 |
| Python (optional analytics) | 3.12 (only for certain scripts) |
| Disk | ~1GB free (logs + simulations) |
| Network | Stable low-latency connection to Binance WebSocket |

Check current versions:
```bash
node -v
npm -v
python3 --version || true
```

---
## 3. Clone & Install
```bash
git clone git@github.com:RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-.git
cd AUREON-QUANTUM-TRADING-SYSTEM-AQTS-
# Install JS deps
npm install
```

Optional: If Python helpers needed:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# (Add any required Python packages here if a requirements file is added later)
```

---
## 4. Environment Configuration
Copy template:
```bash
cp .env.example .env
```
Edit `.env` and fill:
```bash
BINANCE_API_KEY=YOUR_KEY
BINANCE_API_SECRET=YOUR_SECRET
DRY_RUN=true                # Keep true initially
CONFIRM_LIVE_TRADING=yes    # Required gate for any live attempt
BINANCE_TESTNET=false       # Set true if you purposely route to testnet variant
MIN_COHERENCE=0.945
DECISION_THRESHOLD=0.15
POSITION_SIZE_FACTOR=0.98
KELLY_SAFETY_FACTOR=0.5
STATUS_MOCK=false
PORT=8787
```
Security notes:
- Do NOT enable withdrawals on the API key.
- Prefer IP whitelisting (Binance security settings).
- Keep `.env` out of version control.

---
## 5. Dry-Run Verification (Safe)
Start status server (mock first, then live):
```bash
# Mock (no real API touches)
STATUS_MOCK=true npm run status:server &
# Or real account snapshot (still DRY_RUN prevents orders)
npm run status:server &
```
Start UI:
```bash
npm run dev
```
Open browser: `http://localhost:3000` (or forwarded port). You should see the landing page → activate console.

Run a sample dry-run bot:
```bash
npm run hb:dry      # Hummingbird rotations (simulation)
# Or
npm run ants:dry    # Army Ants micro-diversification
```
Check logs for simulated trade events; console UI should reflect streaming data if connected.

---
## 6. Type Checking & Build
```bash
npm run typecheck   # Ensure TS surfaces no blocking issues
npm run build       # Production build (dist/)
```
If typecheck fails due to a script (e.g. experimental), you can isolate core system by temporarily moving offending script out of `scripts/` before CI, then restore.

---
## 7. Enabling Live Trading (Optional & Risky)
Prerequisites:
- Balance ≥ $15 (prefer $50+)
- Confirm min notional threshold (≈ $10 USDT) satisfied
- Validate environment variables: `DRY_RUN=false` + `CONFIRM_LIVE_TRADING=yes`

Procedure:
```bash
# Export env vars explicitly (optional if using .env loader elsewhere)
export DRY_RUN=false
export CONFIRM_LIVE_TRADING=yes

# Start status server (live)
npm run status:server &

# Launch a single conservative bot, monitor behavior for several cycles:
CONFIRM_LIVE_TRADING=yes DRY_RUN=false tsx scripts/loneWolf.ts
```
Monitoring:
- Watch P/L and fills via UI Recent Trades panel.
- Stop immediately if coherence < threshold yet trades occur (config mismatch).

Emergency stop:
```bash
# Simple kill
pkill -f tsx || pkill node
# If using PM2
pm2 stop all
```

Rollback to safe mode:
```bash
sed -i 's/DRY_RUN=false/DRY_RUN=true/' .env
```

---
## 8. Process Supervision (Production)
Using PM2:
```bash
npm install -g pm2
pm2 start ecosystem.config.js       # Should include status server & desired bots
pm2 save
pm2 startup                         # Generate startup script
```
Common PM2 commands:
```bash
pm2 status
pm2 logs --lines 100
pm2 restart <name>
pm2 delete <name>
```
Systemd alternative (minimal example `/etc/systemd/system/aqts-status.service`):
```ini
[Unit]
Description=AQTS Status Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/AQTS
Environment=PORT=8787 NODE_ENV=production
ExecStart=/usr/bin/npm run status:server
Restart=on-failure
User=aqts

[Install]
WantedBy=multi-user.target
```
Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aqts-status.service
```

---
## 9. Monitoring & Logging
Key surfaces:
- Status endpoint: `GET /api/status` → balances & trading readiness
- Bots endpoint: `GET /api/bots`
- Trades endpoint: `GET /api/trades`

Health checklist:
- Latency stable (< 250ms typical per update)
- No persistent 4xx/5xx from exchange
- Coherence metric present and above execution threshold for active trades

Log rotation (basic):
```bash
# Example using logrotate (/etc/logrotate.d/aqts)
/var/log/aqts/*.log {
  daily
  rotate 14
  compress
  missingok
  notifempty
  create 640 aqts aqts
}
```

---
## 10. Security Checklist (Pre-Live)
| Item | Status |
|------|--------|
| API key: trading only, no withdrawals | ☐ |
| IP whitelist configured | ☐ |
| `.env` permissions 600 | ☐ |
| DRY_RUN toggled only intentionally | ☐ |
| Confirm Kelly safety factor ≤ 0.5 | ☐ |
| Stop-loss logic validated in dry-run | ☐ |
| Drawdown guard (30%) documented | ☐ |

Quick hardening:
```bash
chmod 600 .env
# Optionally store secrets in systemd unit EnvironmentFile instead of .env for production
```

---
## 11. Common Pitfalls & Resolutions
| Symptom | Cause | Fix |
|---------|-------|-----|
| Trades not executing | DRY_RUN still true | Set `DRY_RUN=false` & restart script |
| "MIN_NOTIONAL" errors | Position size below exchange minimum | Increase capital or adjust sizing logic |
| Coherence always low | Threshold too high / miscalibration | Lower `MIN_COHERENCE` (e.g. 0.92) after analysis |
| API rate limit warnings | Excessive bot concurrency | Reduce simultaneous bots or add delays |
| Empty UI charts | WebSocket not connected | Check network/firewall; restart status server |

---
## 12. Upgrade & Maintenance
Update code:
```bash
git pull origin main
npm install
npm run typecheck
npm run build
```
Rolling restart (PM2):
```bash
pm2 restart all
```
Backup critical artifacts:
- `metrics/` directory (historical simulation summaries)
- `reports/` war room briefs & trade logs

---
## 13. Verification Script (Optional)
Create a quick verification script after deployment:
```bash
cat <<'EOF' > verify.sh
#!/usr/bin/env bash
set -euo pipefail
curl -sf http://localhost:8787/api/status | jq '.totalUsd, .canTrade'
ps -ef | grep -i tsx | grep -v grep || echo 'No bot processes found'
EOF
chmod +x verify.sh
./verify.sh
```

---
## 14. Safe Decommission
```bash
pm2 stop all || true
pm2 delete all || true
# Remove secrets
shred -u .env
# Archive logs
tar czf aqts-logs-$(date +%F).tar.gz logs/ metrics/ reports/
```

---
## 15. Glossary (Quick)
| Term | Meaning |
|------|---------|
| Coherence (Γ) | Agreement metric of node responses |
| Λ(t) | Master field value driving trade decisions |
| Auris Node | One of 9 perception functions |
| Lighthouse | Consensus voting layer (≥ 6/9) |
| DRY_RUN | Safe mode, disables actual order placement |
| Kelly Factor | Optimal fraction scaled by safety parameter |

---
## 16. Final Live Activation Checklist (All Must Be TRUE)
- [ ] Dry-run bots stable for ≥ 24h
- [ ] Risk parameters reviewed (Kelly, drawdown)
- [ ] Exchange key restricted & secured
- [ ] Monitoring alerts configured (optional)
- [ ] Capital threshold satisfied
- [ ] Manual single test trade validated

Then:
```bash
DRY_RUN=false CONFIRM_LIVE_TRADING=yes tsx scripts/loneWolf.ts
```
Monitor first trade; if metrics align, introduce additional bots gradually.

---
## 17. Disclaimer
Live trading involves substantial risk. This guide prioritizes operational clarity and safety but does **not** eliminate market, liquidity, or execution risks.

---
**Good luck, Loveable. Deploy safely.**
