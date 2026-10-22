#!/bin/bash
echo "🔍 Testing Binance API Connection..."
echo "Your IP: 172.166.156.102"
echo ""
echo "Waiting for you to update API key settings on Binance..."
echo "Press ENTER when ready to test..."
read

cd /workspaces/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-
npx tsx scripts/liveAccountCheck.ts
