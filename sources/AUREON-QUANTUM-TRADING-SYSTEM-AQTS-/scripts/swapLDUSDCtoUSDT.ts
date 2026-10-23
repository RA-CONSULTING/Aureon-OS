#!/usr/bin/env node
/**
 * 🔄 AUREON: LDUSDC → USDT Swap
 * Uses Binance's smart routing to convert LDUSDC to USDT
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

async function swapLDUSDCtoUSDT() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔄 AUREON SMART SWAP: LDUSDC → USDT                  ║
╚════════════════════════════════════════════════════════════════╝
  `);

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  if (!apiKey || !apiSecret) {
    console.log(`❌ ERROR: Missing API credentials`);
    process.exit(1);
  }

  try {
    const client = new BinanceClient({ apiKey, apiSecret, testnet: isTestnet });

    console.log(`\n1️⃣  Fetching LDUSDC balance...`);
    const account = await client.getAccount();
    const ldusdcBal = account.balances.find((b) => b.asset === 'LDUSDC');
    const ldusdcAmount = Number(ldusdcBal?.free || 0);

    if (ldusdcAmount === 0) {
      console.log(`   ❌ No LDUSDC balance found`);
      process.exit(1);
    }

    console.log(`   💰 LDUSDC Balance: ${ldusdcAmount.toFixed(2)}`);

    // Strategy: LDUSDC → BTC → USDT (common routing)
    console.log(`\n2️⃣  Finding optimal swap route...`);
    
    // Check available pairs
    const possibleRoutes = [
      { route: 'LDUSDC → USDC → USDT', pairs: ['LDUSDCUSDC', 'USDCUSDT'] },
      { route: 'LDUSDC → BTC → USDT', pairs: ['LDUSDCBTC', 'BTCUSDT'] },
      { route: 'LDUSDC → ETH → USDT', pairs: ['LDUSDCETH', 'ETHUSDT'] },
      { route: 'LDUSDC → BNB → USDT', pairs: ['LDUSDCBNB', 'BNBUSDT'] },
    ];

    let selectedRoute = null;

    for (const route of possibleRoutes) {
      try {
        // Try to get price for first pair
        const price1 = await client.getPrice(route.pairs[0]);
        if (price1) {
          console.log(`   ✅ Route found: ${route.route}`);
          selectedRoute = route;
          break;
        }
      } catch {
        console.log(`   ⏭️  ${route.route} - Not available`);
      }
    }

    if (!selectedRoute) {
      console.log(`\n❌ No direct trading route found for LDUSDC`);
      console.log(`\n💡 MANUAL SOLUTION:`);
      console.log(`   1. Go to: https://www.binance.com/en/convert`);
      console.log(`   2. Convert ${ldusdcAmount.toFixed(2)} LDUSDC → USDT`);
      console.log(`   3. You'll get ~${ldusdcAmount.toFixed(2)} USDT (1:1 rate)`);
      console.log(`   4. Then run: npx tsx scripts/liveAccountCheck.ts`);
      process.exit(1);
    }

    console.log(`\n3️⃣  Executing swap via ${selectedRoute.route}...`);
    
    // Step 1: LDUSDC → Intermediate asset
    const pair1 = selectedRoute.pairs[0];
    console.log(`   🔄 Step 1: Selling ${ldusdcAmount.toFixed(6)} LDUSDC for ${pair1.replace('LDUSDC', '')}...`);
    
    const order1 = await client.placeOrder({
      symbol: pair1,
      side: 'SELL',
      type: 'MARKET',
      quantity: ldusdcAmount,
    });

    const intermediateAsset = pair1.replace('LDUSDC', '');
    const intermediateAmount = Number(order1.executedQty);
    
    console.log(`   ✅ Received: ${intermediateAmount} ${intermediateAsset}`);
    console.log(`   Order ID: ${order1.orderId}`);

    // Wait a moment for balance to update
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Step 2: Intermediate → USDT
    const pair2 = selectedRoute.pairs[1];
    console.log(`\n   🔄 Step 2: Selling ${intermediateAmount} ${intermediateAsset} for USDT...`);
    
    const order2 = await client.placeOrder({
      symbol: pair2,
      side: 'SELL',
      type: 'MARKET',
      quantity: intermediateAmount,
    });

    const usdtReceived = Number(order2.cummulativeQuoteQty);
    
    console.log(`   ✅ Received: ${usdtReceived.toFixed(2)} USDT`);
    console.log(`   Order ID: ${order2.orderId}`);

    console.log(`\n4️⃣  Swap Complete!`);
    console.log(`   Started with: ${ldusdcAmount.toFixed(2)} LDUSDC`);
    console.log(`   Ended with: ${usdtReceived.toFixed(2)} USDT`);
    console.log(`   Effective rate: ${(usdtReceived / ldusdcAmount).toFixed(4)}`);

    // Get final balance
    const finalAccount = await client.getAccount();
    const usdtBal = finalAccount.balances.find((b) => b.asset === 'USDT');
    const finalUSDT = Number(usdtBal?.free || 0);

    console.log(`\n💰 Total USDT Balance: £${finalUSDT.toFixed(2)}`);

    if (finalUSDT >= 10) {
      console.log(`\n✅ SUCCESS! Ready to trade!`);
      console.log(`\n🚀 Start trading with:`);
      console.log(`   export CONFIRM_LIVE_TRADING=yes`);
      console.log(`   npx tsx scripts/realMoneyLive.ts`);
    }

  } catch (err: any) {
    console.error(`\n❌ Swap failed:`, err.message);
    
    if (err.message.includes('LOT_SIZE') || err.message.includes('MIN_NOTIONAL')) {
      console.log(`\n💡 The amount is below minimum trading limits.`);
      console.log(`   Use Binance Convert instead:`);
      console.log(`   https://www.binance.com/en/convert`);
    }
    
    log('error', 'Swap failed', { error: err.message });
    process.exit(1);
  }
}

swapLDUSDCtoUSDT().catch(console.error);
