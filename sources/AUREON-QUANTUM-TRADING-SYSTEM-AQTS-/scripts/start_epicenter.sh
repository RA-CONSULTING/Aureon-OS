#!/bin/bash
set -e
cd /workspaces/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-

# Safety defaults
export EPICENTER_LIVE=${EPICENTER_LIVE:-NO}
export CONFIRM_EPICENTER=YES
export EPICENTER_COOLDOWN_SEC=${EPICENTER_COOLDOWN_SEC:-10}
export EPICENTER_POSITION_PCT=${EPICENTER_POSITION_PCT:-0.2}
# Choose symbols explicitly or let discovery pick top 20 by volume
# export EPICENTER_SYMBOLS="BNBBTC,ETHBTC,BTCUSDT,BNBUSDT,ETHUSDT"

python3 -u scripts/epicenter/engine.py
