#!/usr/bin/env node
/**
 * 🔥 LIVE TRADING QUICK START
 * 
 * You now have 3 deployment options:
 * 
 * 1. 🧪 TESTNET (Current - Safe Practice)
 *    npx tsx scripts/liveWalletDeploy.ts
 *    - Uses testnet balance: £10,784.95
 *    - No real money involved
 *    - Full Queen-Hive deployment
 *    - Perfect for testing
 * 
 * 2. 🔍 LIVE VERIFICATION (Before Real Trading)
 *    npx tsx scripts/liveAccountCheck.ts
 *    - Verifies your LIVE Binance account
 *    - Confirms API credentials work
 *    - Shows real account balance
 *    - Checks trading permissions
 * 
 * 3. 🔥 REAL MONEY MODE (Full Production)
 *    export CONFIRM_LIVE_TRADING=yes
 *    npx tsx scripts/realMoneyLive.ts
 *    - Connects to your LIVE Binance account
 *    - Uses your ACTUAL wallet balance
 *    - Executes REAL trades with real capital
 *    - Auto-spawns hives on 5x growth
 *    - Real-time P&L tracking
 * 
 * ════════════════════════════════════════════════════════════════
 * 
 * TO GO LIVE WITH REAL MONEY:
 * 
 * Step 1: Get your LIVE Binance API keys
 *         https://www.binance.com/en/user/settings/api-management
 * 
 * Step 2: Update .env file
 *         BINANCE_TESTNET=false
 *         BINANCE_API_KEY=your_live_key_here
 *         BINANCE_API_SECRET=your_live_secret_here
 * 
 * Step 3: Run safety check
 *         npx tsx scripts/liveAccountCheck.ts
 * 
 * Step 4: Launch with confirmation
 *         export CONFIRM_LIVE_TRADING=yes
 *         npx tsx scripts/realMoneyLive.ts
 * 
 * ════════════════════════════════════════════════════════════════
 * 
 * WHAT HAPPENS WHEN YOU GO LIVE:
 * 
 * ✅ Connects to your real Binance account
 * ✅ Fetches your actual USDT balance
 * ✅ Creates initial Queen-Hive with all capital
 * ✅ Deploys 5 agents per hive
 * ✅ Each agent trades on: BTC, ETH, BNB, ADA, DOGE
 * ✅ Executes REAL limit orders on live market
 * ✅ Tracks real P&L from actual trades
 * ✅ Auto-spawns new hives when equity grows 5x
 * ✅ Closes all positions on shutdown
 * 
 * ════════════════════════════════════════════════════════════════
 * 
 * SAFETY FEATURES:
 * 
 * 🛡️  Position size limits (max £100 per trade by default)
 * 🛡️  Daily trade limits (max 50 trades per day by default)
 * 🛡️  Risk percentage limits (0.5% per trade)
 * 🛡️  Minimum balance checks (requires £10)
 * 🛡️  Graceful shutdown (closes all positions cleanly)
 * 🛡️  Emergency stop (Ctrl+C will halt trading)
 * 
 * ════════════════════════════════════════════════════════════════
 * 
 * RIGHT NOW YOU CAN:
 * 
 * 1. Continue with TESTNET (your balance: £10,784.95)
 *    Perfect for seeing the system work without risk
 * 
 * 2. Switch to LIVE when ready
 *    Your actual account balance will be used
 *    Real trades = real gains/losses
 * 
 * The system is PRODUCTION READY.
 * All infrastructure is in place.
 * Just need your live API keys to deploy. 🚀
 * 
 * 🍯 Let's bring in the honey! 🔥
 */

console.log(require('fs').readFileSync(__filename, 'utf-8').split('*/')[0].substring(4));
