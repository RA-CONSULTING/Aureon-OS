#!/usr/bin/env npx tsx
/**
 * 🎯 SINGLE LIVE TRADE (CONTROLLED EXECUTION)
 * Places ONE MARKET order using existing balance (BNB preferred) with proper lot sizing.
 * - Fetches account & exchange filters
 * - Computes safe quantity (positionPercent of free balance, capped by maxUsd)
 * - Adjusts to LOT_SIZE step & min quantity
 * - Executes MARKET SELL (if base asset held) or MARKET BUY (if sufficient USDT)
 * - Re-fetches account after short delay to show balance changes
 *
 * IMPORTANT: REAL MONEY on MAINNET if BINANCE_TESTNET != true.
 */

import { BinanceClient } from '../core/binanceClient';
import * as dotenv from 'dotenv';

dotenv.config();

interface TradePlan {
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  quoteEstimate: number; // USD equivalent
}

async function sleep(ms: number) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
  if (!apiKey || !apiSecret) {
    console.error('❌ Missing API credentials in environment.');
    process.exit(1);
  }
  const client = new BinanceClient({ apiKey, apiSecret, testnet });

  console.log('\n══════════════════════════════════════════════');
  console.log('  🎯 SINGLE LIVE TRADE INIT');
  console.log('  Network:', testnet ? 'TESTNET' : 'LIVE MAINNET');
  console.log('══════════════════════════════════════════════\n');

  const accountBefore = await client.getAccount();
  const balances = accountBefore.balances.reduce<Record<string, number>>((map, b) => { const v = parseFloat(b.free); if (v > 0) map[b.asset] = v; return map; }, {});
  console.log('📦 Free Balances:');
  Object.entries(balances).forEach(([asset,val]) => console.log(`   ${asset}: ${val}`));

  // Prefer selling some BNB (larger balance) else BTC else ETH else buying BTC with USDT.
  const candidatesSell = ['BNB','BTC','ETH'];
  let selectedBase: string | undefined = candidatesSell.find(a => balances[a] && balances[a] > 0);
  let side: 'BUY' | 'SELL' = 'SELL';
  let symbol: string;

  if (selectedBase) {
    symbol = selectedBase + 'USDT';
  } else if (balances['USDT'] && balances['USDT'] >= 11) {
    // fallback: buy BTC
    symbol = 'BTCUSDT';
    side = 'BUY';
    selectedBase = 'BTC';
  } else {
    console.error('❌ No suitable asset to trade (need BNB/BTC/ETH or >=11 USDT).');
    process.exit(1);
  }

  console.log(`\n🔍 Target Symbol: ${symbol} (side: ${side})`);

  // Fetch exchange info to get LOT_SIZE & MIN_NOTIONAL
  const exInfo = await client.getExchangeInfo([symbol]);
  const symbolInfo = exInfo.symbols?.[0];
  if (!symbolInfo) {
    console.error('❌ Could not load symbol info for', symbol);
    process.exit(1);
  }
  const lotFilter = symbolInfo.filters.find((f: any) => f.filterType === 'LOT_SIZE');
  const notionalFilter = symbolInfo.filters.find((f: any) => f.filterType === 'MIN_NOTIONAL');
  const stepSize = lotFilter ? parseFloat(lotFilter.stepSize) : 0.000001;
  const minQty = lotFilter ? parseFloat(lotFilter.minQty) : 0.000001;
  const minNotional = notionalFilter ? parseFloat(notionalFilter.minNotional) : 10;

  const price = await client.getPrice(symbol);
  console.log(`💵 Current Price: $${price.toFixed(2)}`);

  const positionPercent = 5; // risk 5% of free base
  const maxUsd = 20; // safety cap
  let rawQty: number;

  if (side === 'SELL') {
    const freeBase = balances[selectedBase!] || 0;
    rawQty = freeBase * (positionPercent / 100);
  } else { // BUY
    const freeUsdt = balances['USDT'] || 0;
    const targetUsd = Math.min(freeUsdt * (positionPercent / 100), maxUsd);
    rawQty = targetUsd / price;
  }

  // Enforce cap by USD
  const usdEquivalent = rawQty * price;
  if (usdEquivalent > maxUsd) {
    rawQty = maxUsd / price;
  }

  // Adjust to step size and minQty (floor)
  const adjust = (q: number) => {
    const floored = Math.floor(q / stepSize) * stepSize;
    return parseFloat(floored.toFixed(8));
  };
  let quantity = adjust(rawQty);
  if (quantity < minQty) quantity = minQty;
  const finalUsd = quantity * price;

  if (finalUsd < minNotional) {
    console.error(`❌ Final notional $${finalUsd.toFixed(2)} below min notional $${minNotional}. Increase balances or adjust config.`);
    process.exit(1);
  }

  const plan: TradePlan = { symbol, side, quantity, quoteEstimate: finalUsd };
  console.log('\n🧪 Trade Plan:');
  console.log(`   Side:        ${plan.side}`);
  console.log(`   Quantity:    ${plan.quantity}`);
  console.log(`   Est USD:     $${plan.quoteEstimate.toFixed(2)}`);
  console.log(`   MinQty:      ${minQty}  StepSize: ${stepSize}`);
  console.log(`   MinNotional: $${minNotional}`);

  if (!testnet) {
    console.log('\n⚠️ LIVE MAINNET — REAL ORDER WILL BE SENT.');
  } else {
    console.log('\n🧪 TESTNET MODE — safe simulation environment.');
  }

  console.log('\n🚀 Placing MARKET order...');
  const order = await client.placeOrder({ symbol, side, type: 'MARKET', quantity });
  console.log('✅ Order Accepted:');
  console.log(`   OrderId: ${order.orderId}`);
  console.log(`   Executed Qty: ${order.executedQty}`);
  console.log(`   Status: ${order.status}`);
  if (order.fills && order.fills.length) {
    const avgFill = order.fills.reduce((sum, f) => sum + parseFloat(f.price) * parseFloat(f.qty), 0) / order.fills.reduce((s,f)=>s+parseFloat(f.qty),0);
    console.log(`   Avg Fill Price: $${avgFill.toFixed(2)}`);
  }

  console.log('\n⏳ Waiting for balance update...');
  await sleep(4000);
  const accountAfter = await client.getAccount();
  const afterBalances = accountAfter.balances.reduce<Record<string, number>>((m,b)=>{const v=parseFloat(b.free);if(v>0)m[b.asset]=v;return m;},{});

  const beforeVal = balances[selectedBase!] || 0;
  const afterVal = afterBalances[selectedBase!] || 0;
  const delta = afterVal - beforeVal;
  console.log('\n📊 Balance Change:');
  console.log(`   ${selectedBase} before: ${beforeVal}`);
  console.log(`   ${selectedBase} after:  ${afterVal}`);
  console.log(`   Δ ${selectedBase}: ${delta.toFixed(8)}`);

  console.log('\n✅ Single trade complete. You can inspect further with:');
  console.log('   npx tsx -e "import {showHoney} from ./core/honeyPot; showHoney()"');
  console.log('\n──────────────────────────────────────────────');
}

main().catch(e => {
  console.error('💥 ERROR:', e.message);
  process.exit(1);
});
