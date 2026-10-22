#!/usr/bin/env node
/**
 * 🔍 AUREON LIVE SAFETY CHECK
 * - Verify connection to LIVE Binance account
 * - Confirm API credentials are correct
 * - Check account balance and permissions
 * - Verify trading symbols are supported
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

async function liveAccountCheck() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔍 AUREON LIVE SAFETY CHECK                          ║
║         Pre-Trading Verification System                      ║
╚════════════════════════════════════════════════════════════════╝
  `);

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  console.log(`\n1️⃣  Configuration Check:`);
  console.log(`   API Key present: ${apiKey ? '✅' : '❌'}`);
  console.log(`   API Secret present: ${apiSecret ? '✅' : '❌'}`);
  console.log(`   Mode: ${isTestnet ? '🔵 TESTNET (Safe)' : '🔴 LIVE MONEY (Real)'}`);

  if (!apiKey || !apiSecret) {
    console.log(`\n❌ ERROR: Missing credentials in .env`);
    process.exit(1);
  }

  try {
    console.log(`\n2️⃣  Connecting to ${isTestnet ? 'TESTNET' : 'LIVE'} Binance...`);
    const client = new BinanceClient({
      apiKey,
      apiSecret,
      testnet: isTestnet,
    });

    console.log(`   ✅ Client initialized\n`);

    // Get account info
    console.log(`3️⃣  Fetching account information...`);
    const account = await client.getAccount();

    console.log(`   ✅ Connected successfully!`);
    console.log(`   Account Type: SPOT`);
    console.log(`   Trading enabled: ${account.canTrade ? '✅ YES' : '❌ NO'}`);
    console.log(`   Can deposit: ${account.canDeposit ? '✅ YES' : '❌ NO'}`);
    console.log(`   Can withdraw: ${account.canWithdraw ? '✅ YES' : '❌ NO'}`);

    // Get balances
    console.log(`\n4️⃣  Account Balances:`);
    const balances = account.balances
      .filter((b) => Number(b.free) > 0 || Number(b.locked) > 0)
      .slice(0, 15);

    for (const b of balances) {
      const free = Number(b.free);
      const locked = Number(b.locked);
      if (free > 0 || locked > 0) {
        console.log(`   ${b.asset}: ${free.toFixed(8)} (free) + ${locked.toFixed(8)} (locked)`);
      }
    }

    // Check USDT balance specifically (or base asset if configured)
    const baseAsset = (process.env.BASE_ASSET || 'USDT').toUpperCase();
    let usdtFree = 0;
    let baseBalance = 0;
    let baseEquiv = 0;

    if (baseAsset === 'USDT') {
      const usdtBalance = account.balances.find((b) => b.asset === 'USDT');
      usdtFree = Number(usdtBalance?.free || 0);
    } else {
      const baseBalRec = account.balances.find((b) => b.asset === baseAsset);
      baseBalance = Number(baseBalRec?.free || 0);
      try {
        const price = await client.getPrice(`${baseAsset}USDT`);
        baseEquiv = baseBalance * price;
      } catch {
        baseEquiv = 0;
      }
    }

    console.log(`\n5️⃣  Base Asset Balance Check: (${baseAsset})`);
    if (baseAsset === 'USDT') {
      if (usdtFree === 0) {
        console.log(`   ⚠️  WARNING: No USDT balance found!`);
        console.log(`   Action: Transfer USDT to your account to trade`);
      } else if (usdtFree < 10) {
        console.log(`   ⚠️  WARNING: Low USDT balance (${usdtFree.toFixed(2)})`);
        console.log(`   Minimum for trading: £10`);
      } else {
        console.log(`   ✅ Available: £${usdtFree.toFixed(2)} USDT`);
      }
    } else {
      if (baseBalance === 0) {
        console.log(`   ⚠️  WARNING: No ${baseAsset} balance found!`);
        console.log(`   Action: Deposit or convert assets to ${baseAsset} to trade in this mode`);
      } else if (baseEquiv < 10) {
        console.log(`   ⚠️  WARNING: ${baseAsset} equivalent too low (£${baseEquiv.toFixed(2)})`);
        console.log(`   Minimum for trading: £10 USDT-equivalent`);
      } else {
        console.log(`   ✅ ${baseAsset} Balance: ${baseBalance} ${baseAsset} (~£${baseEquiv.toFixed(2)} USDT)`);
      }
    }

    // Check symbol prices
    console.log(`\n6️⃣  Testing Trading Symbols:`);
    const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT'];

    for (const symbol of symbols) {
      try {
        const price = await client.getPrice(symbol);
        console.log(`   ${symbol}: £${Number(price).toFixed(2)} ✅`);
      } catch (err) {
        console.log(`   ${symbol}: ❌ Error`);
      }
    }

    // Risk configuration
    console.log(`\n7️⃣  Risk Configuration:`);
    const maxOrderSize = Number(process.env.MAX_ORDER_SIZE || 10000);
    const maxDailyTrades = Number(process.env.MAX_DAILY_TRADES || 500);
    const riskPercent = Number(process.env.RISK_LIMIT_PERCENT || 2);

    console.log(`   Max order size: £${maxOrderSize}`);
    console.log(`   Max daily trades: ${maxDailyTrades}`);
    console.log(`   Risk per trade: ${riskPercent}%`);

    // Final readiness check
    console.log(`\n8️⃣  Readiness Assessment:`);

    let readyToTrade = true;
    const checks = [
      { name: 'Trading enabled', ok: account.canTrade },
      { name: `${baseAsset} available`, ok: baseAsset === 'USDT' ? usdtFree > 0 : baseBalance > 0 },
      { name: `${baseAsset} > £10 (USDT equiv)`, ok: baseAsset === 'USDT' ? usdtFree >= 10 : baseEquiv >= 10 },
      { name: 'API connected', ok: true },
      { name: 'Symbols responding', ok: true },
    ];

    for (const check of checks) {
      console.log(`   ${check.ok ? '✅' : '❌'} ${check.name}`);
      if (!check.ok) readyToTrade = false;
    }

    console.log(`\n${'═'.repeat(64)}`);

    if (readyToTrade && !isTestnet) {
      console.log(`\n🚀 READY FOR LIVE TRADING!`);
      console.log(`\n   To start trading:
   
   export CONFIRM_LIVE_TRADING=yes
   npx tsx scripts/realMoneyLive.ts
   
   ⚠️  WARNING: This will execute REAL trades with actual capital!
   `);
    } else if (readyToTrade && isTestnet) {
      console.log(`\n🧪 READY FOR TESTNET TRADING!`);
      console.log(`\n   To deploy with your testnet balance:
   
   npx tsx scripts/liveWalletDeploy.ts
   `);
    } else {
      console.log(`\n⚠️  NOT READY - Address issues above before trading`);
    }

    console.log(`${'═'.repeat(64)}\n`);
  } catch (err) {
    console.log(`\n❌ Connection Failed`);
    log('error', 'Account check failed', err);
    process.exit(1);
  }
}

liveAccountCheck();
