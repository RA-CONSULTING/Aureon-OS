#!/bin/bash
# 🔥 AUREON LIVE SWITCH: Testnet → Real Money Mode

echo "
╔════════════════════════════════════════════════════════════════╗
║         🔥 LIVE MONEY MODE ACTIVATION                        ║
╚════════════════════════════════════════════════════════════════╝
"

# Step 1: Get real Binance API credentials
echo "📝 Step 1: Real Money Credentials"
echo "   You need LIVE Binance API keys (not testnet)"
echo "   Get them at: https://www.binance.com/en/user/settings/api-management"
echo ""
read -p "   Enter LIVE Binance API Key: " LIVE_API_KEY
read -sp "   Enter LIVE Binance API Secret: " LIVE_API_SECRET
echo ""

# Step 2: Verify current credentials
echo ""
echo "📊 Step 2: Current Configuration"
TESTNET=$(grep "BINANCE_TESTNET" .env | cut -d'=' -f2)
echo "   Current mode: BINANCE_TESTNET=$TESTNET"
echo ""

# Step 3: Update .env to LIVE mode
echo "🔄 Step 3: Switching to LIVE mode..."
sed -i "s/BINANCE_TESTNET=.*/BINANCE_TESTNET=false/" .env
sed -i "s/^BINANCE_API_KEY=.*/BINANCE_API_KEY=$LIVE_API_KEY/" .env
sed -i "s/^BINANCE_API_SECRET=.*/BINANCE_API_SECRET=$LIVE_API_SECRET/" .env

echo "   ✅ Updated BINANCE_TESTNET=false"
echo "   ✅ Updated API credentials"

# Step 4: Set safety limits
echo ""
echo "⚙️  Step 4: Safety Configuration"
echo "   Current max order size: $(grep MAX_ORDER_SIZE .env | cut -d'=' -f2)"
echo "   Current max daily trades: $(grep MAX_DAILY_TRADES .env | cut -d'=' -f2)"
read -p "   Adjust max order size (USDT)? [n] " max_order
if [ ! -z "$max_order" ]; then
  sed -i "s/MAX_ORDER_SIZE=.*/MAX_ORDER_SIZE=$max_order/" .env
  echo "   ✅ Set MAX_ORDER_SIZE=$max_order"
fi

# Step 5: Confirmation
echo ""
echo "⚠️  WARNING: ABOUT TO TRADE WITH REAL MONEY"
echo "   Account balance will be determined at runtime"
echo "   Trades will execute on LIVE Binance"
echo ""
read -p "   Type 'YES I UNDERSTAND' to proceed: " confirmation

if [ "$confirmation" = "YES I UNDERSTAND" ]; then
  echo ""
  echo "🚀 LAUNCHING LIVE TRADING..."
  export CONFIRM_LIVE_TRADING=no
  export MAX_STEPS=100
  export LOG_INTERVAL=20
  
  npx tsx scripts/realMoneyLive.ts
else
  echo "❌ Cancelled - No changes made"
  exit 1
fi
