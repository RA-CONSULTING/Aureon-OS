#!/usr/bin/env node
/**
 * ArmyAnts: Pick from the floor, bring back to the hive
 * - Ensures >= $11 USDT by selling a slice of ETH if needed
 * - Sequentially buys small amounts ($11) of liquid USDT alts using quoteOrderQty
 * - Takes quick profit or small loss, sells back to USDT
 * - At the end, converts USDT back to ETH (unless RETAIN_USDT=yes)
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function roundDown(v: number, d: number) {
  const p = Math.pow(10, d);
  return Math.floor(v * p) / p;
}

function toStep(value: number, stepSize: number): number {
  if (!stepSize || stepSize <= 0) return value;
  const steps = Math.floor(value / stepSize);
  return steps * stepSize;
}

async function getSymbolConstraints(client: BinanceClient, symbol: string): Promise<{ minQty: number; stepSize: number; minNotional: number; price: number }> {
  const info = await client.getExchangeInfo([symbol]);
  const sym = info.symbols?.find((s: any) => s.symbol === symbol) || {};
  const filters = sym.filters || [];
  const find = (t: string) => filters.find((f: any) => f.filterType === t || f.type === t) || {};
  const lot = find('LOT_SIZE');
  const mlot = find('MARKET_LOT_SIZE');
  const notional = find('NOTIONAL') || find('MIN_NOTIONAL');
  const minQty = parseFloat(mlot.minQty || lot.minQty || '0');
  const stepSize = parseFloat(lot.stepSize || '0');
  const minNotional = parseFloat(notional.minNotional || '0');
  const price = await client.getPrice(symbol);
  return { minQty: isFinite(minQty) ? minQty : 0, stepSize: isFinite(stepSize) ? stepSize : 0, minNotional: isFinite(minNotional) ? minNotional : 0, price };
}

async function getBalance(client: BinanceClient, asset: string): Promise<number> {
  const acct = await client.getAccount();
  return Number(acct.balances.find((b) => b.asset === asset)?.free || 0);
}

async function ensureUsdt(client: BinanceClient, minUsdt = 11, wait = false): Promise<void> {
  const DRY_RUN = process.env.DRY_RUN === 'true';
  const usdt = await getBalance(client, 'USDT');
  if (usdt >= minUsdt) return;
  const ethPrice = await client.getPrice('ETHUSDT');
  const need = minUsdt + 1 - usdt; // buffer for fees
  const qtyEth = roundDown(need / ethPrice + 0.0002, 6);
  const ethBal = await getBalance(client, 'ETH');
  if (qtyEth * ethPrice < 10 || qtyEth > ethBal) {
    if (DRY_RUN) {
      console.log(`DRY_RUN: would sell ${qtyEth} ETH -> USDT to raise ~$${minUsdt}`);
      return;
    }
    if (!wait) {
      throw new Error(`ETH insufficient to raise USDT >= $${minUsdt}. Have ${ethBal.toFixed(8)} ETH; need ${(qtyEth).toFixed(6)} ETH.`);
    }
    process.stdout.write(`Waiting for funds (need ~$${minUsdt} USDT min)...`);
    for (;;) {
      await sleep(5000);
      const curUsdt = await getBalance(client, 'USDT');
      if (curUsdt >= minUsdt) break;
      const curEth = await getBalance(client, 'ETH');
      const px = await client.getPrice('ETHUSDT');
      const minEth = (minUsdt + 1 - curUsdt) / px + 0.0002;
      if (minEth <= curEth && minEth * px >= 10) break;
      process.stdout.write('.');
    }
    console.log('\nFunds available. Proceeding.');
  }
  console.log(`🔄 Selling ${qtyEth} ETH -> USDT to reach ~$${minUsdt}+`);
  if (DRY_RUN) {
    console.log(`DRY_RUN: simulate SELL ETHUSDT qty=${qtyEth}`);
  } else {
    await client.placeOrder({ symbol: 'ETHUSDT', side: 'SELL', type: 'MARKET', quantity: qtyEth });
  }
}

async function buyUsdtAlt(
  client: BinanceClient,
  symbol: string,
  spendUSDT: number
): Promise<{ baseBought: number; avgPrice: number }> {
  const { minQty, stepSize, minNotional, price } = await getSymbolConstraints(client, symbol);
  const requiredQuote = Math.max(minQty * price, minNotional);
  if (spendUSDT < requiredQuote) {
    throw new Error(`Spend $${spendUSDT.toFixed(2)} < exchange min $${requiredQuote.toFixed(2)} — skip ${symbol}`);
  }
  // Liquidity/depth pre-check: ensure order book can satisfy at least min base
  try {
    const ob = await client.getOrderBook(symbol, 10);
    const minBaseNeeded = Math.max(minQty, minNotional > 0 ? (minNotional / price) : 0);
    let sumAsk = 0;
    for (const [askPxStr, askQtyStr] of ob.asks) {
      const askQty = Number(askQtyStr);
      sumAsk += askQty;
      if (sumAsk >= minBaseNeeded) break;
    }
    if (sumAsk < minBaseNeeded) {
      throw new Error(`Insufficient depth for ${symbol}: book ask qty ${sumAsk.toFixed(6)} < minBase ${minBaseNeeded.toFixed(6)}`);
    }
  } catch (e: any) {
    throw new Error(`Depth check failed for ${symbol}: ${e.message || e}`);
  }

  console.log(`🟢 Buying ~$${spendUSDT.toFixed(2)} of ${symbol}`);
  console.log(`📡 Source: Army Ants (USDT rotations, small alt spends)`);
  const DRY_RUN = process.env.DRY_RUN === 'true';
  let order: any;
  if (DRY_RUN) {
    const px = await client.getPrice(symbol);
    let qty = spendUSDT / px;
    if (stepSize > 0) qty = toStep(qty, stepSize);
    order = { executedQty: String(qty), cummulativeQuoteQty: String(qty * px) };
    console.log(`DRY_RUN: simulate BUY ${symbol} spend $${spendUSDT.toFixed(2)} (~${qty.toFixed(6)} units @ $${px.toFixed(6)})`);
  } else {
    try {
      order = await client.placeOrder({ symbol, side: 'BUY', type: 'MARKET', quoteOrderQty: spendUSDT, quantity: 0 });
    } catch (err: any) {
      const msg = String(err?.message || '');
      // Fallback: compute quantity with LOT_SIZE stepping
      if (msg.includes('LOT_SIZE') || msg.includes('-2010') || msg.includes('-1013')) {
        const px = await client.getPrice(symbol);
        let qty = spendUSDT / px;
        if (stepSize > 0) qty = toStep(qty, stepSize);
        if (qty < minQty) throw new Error(`Fallback qty ${qty} < minQty ${minQty} for ${symbol}`);
        console.log(`↩️  Fallback: placing MARKET by quantity ${qty} (stepped)`);
        order = await client.placeOrder({ symbol, side: 'BUY', type: 'MARKET', quantity: qty });
      } else {
        throw err;
      }
    }
  }
  const qty = Number(order.executedQty);
  const cost = Number(order.cummulativeQuoteQty);
  const avg = qty > 0 ? cost / qty : 0;
  console.log(`✅ Bought ${qty} ${symbol.replace('USDT','')} @ ~$${avg.toFixed(6)}`);
  return { baseBought: qty, avgPrice: avg };
}

async function sellUsdtAlt(
  client: BinanceClient,
  symbol: string,
  qty: number
): Promise<void> {
  const { stepSize, minQty } = await getSymbolConstraints(client, symbol);
  let q = roundDown(qty * 0.99, 6);
  if (stepSize > 0) q = toStep(q, stepSize);
  if (q <= 0) return;
  if (q < minQty) { console.log(`Skip sell ${symbol}: qty ${q} < minQty ${minQty}`); return; }
  console.log(`🔴 Selling ${q} ${symbol.replace('USDT','')} back to USDT`);
  const DRY_RUN = process.env.DRY_RUN === 'true';
  if (DRY_RUN) {
    console.log(`DRY_RUN: simulate SELL ${symbol} qty=${q}`);
  } else {
    await client.placeOrder({ symbol, side: 'SELL', type: 'MARKET', quantity: q });
  }
}

async function rotateSymbol(
  client: BinanceClient,
  symbol: string,
  spendUSDT = 11,
  tp = 0.006, // +0.6%
  sl = -0.005, // -0.5%
  maxMinutes = 3
): Promise<void> {
  try {
    const wait = process.env.ANTS_WAIT_FOR_FUNDS === 'yes';
    await ensureUsdt(client, spendUSDT, wait);
  } catch (e: any) {
    console.log(`⏭️  Skip: ${e.message}`);
    return;
  }
  // Pre-check constraints to skip illiquid/minimum-violating pairs
  try {
    const { minQty, minNotional, price } = await getSymbolConstraints(client, symbol);
    const requiredQuote = Math.max(minQty * price, minNotional);
    if (spendUSDT < requiredQuote) {
      console.log(`⏭️  Skip ${symbol}: spend $${spendUSDT.toFixed(2)} < min $${requiredQuote.toFixed(2)}`);
      return;
    }
  } catch (err: any) {
    console.log(`⏭️  Skip ${symbol}: cannot fetch constraints (${err.message})`);
    return;
  }
  const { baseBought, avgPrice } = await buyUsdtAlt(client, symbol, spendUSDT);
  if (baseBought <= 0) return;

  for (let i = 0; i < maxMinutes * 12; i++) {
    await sleep(5000);
    let price: number;
    try {
      price = await client.getPrice(symbol);
    } catch {
      continue;
    }
    const change = (price - avgPrice) / avgPrice;
    const sign = change >= 0 ? '+' : '';
    process.stdout.write(`\r${symbol} $${price.toFixed(6)} (${sign}${(change * 100).toFixed(2)}%)   `);
    if (change >= tp || change <= sl) {
      console.log(`\nTrigger ${(change * 100).toFixed(2)}% — exiting...`);
      await sellUsdtAlt(client, symbol, baseBought);
      break;
    }
  }
}

async function convertBackToEth(client: BinanceClient, retainUsdt = false): Promise<void> {
  const usdt = await getBalance(client, 'USDT');
  if (usdt < 10) return;
  let toSpend = retainUsdt ? Math.max(0, usdt - 12) : usdt * 0.98;
  if (toSpend < 10) return;
  // Round quote to QUOTE_LOT_SIZE step
  try {
    const info = await client.getExchangeInfo(['ETHUSDT']);
    const sym = info.symbols?.find((s: any) => s.symbol === 'ETHUSDT') || {};
    const qlot = (sym.filters || []).find((f: any) => f.filterType === 'QUOTE_LOT_SIZE' || f.type === 'QUOTE_LOT_SIZE') || {};
    const qStep = parseFloat(qlot.stepSize || '0');
    if (isFinite(qStep) && qStep > 0) {
      const steps = Math.floor(toSpend / qStep);
      toSpend = steps * qStep;
    }
  } catch {}
  if (toSpend < 10) return;
  console.log(`🧭 Converting $${toSpend.toFixed(2)} USDT -> ETH`);
  await client.placeOrder({ symbol: 'ETHUSDT', side: 'BUY', type: 'MARKET', quoteOrderQty: toSpend, quantity: 0 });
}

async function main() {
  if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
    console.error('Safety abort: set CONFIRM_LIVE_TRADING=yes');
    process.exit(1);
  }
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) {
    console.error('Missing BINANCE_API_KEY/SECRET');
    process.exit(1);
  }
  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });

  const retain = process.env.RETAIN_USDT === 'yes';
  const universe = (process.env.ANTS_UNIVERSE || 'ADAUSDT,DOGEUSDT,XRPUSDT,SOLUSDT,MATICUSDT,LTCUSDT,LINKUSDT,ATOMUSDT,AVAXUSDT,NEARUSDT').split(',');
  const maxRotations = Number(process.env.ANTS_ROTATIONS || 4);
  const spend = Number(process.env.ANTS_SPEND_USDT || 11);
  const tp = Number(process.env.ANTS_TP || 0.006);
  const sl = Number(process.env.ANTS_SL || -0.005);
  const minutes = Number(process.env.ANTS_MAX_MIN || 3);

  const startEth = await getBalance(client, 'ETH');
  const ethPrice = await client.getPrice('ETHUSDT');
  console.log(`🐜 The Ants begin their work — workers of the earth`);
  console.log(`   Starting with ${startEth.toFixed(8)} ETH (~$${(startEth * ethPrice).toFixed(2)})`);
  console.log(`   Gathering from ${Math.min(maxRotations, universe.length)} USDT sources...`);

  for (let i = 0; i < Math.min(maxRotations, universe.length); i++) {
    const sym = universe[i].trim();
    try {
      await rotateSymbol(client, sym, spend, tp, sl, minutes);
    } catch (e: any) {
      console.log(`⚠️  Rotation error on ${sym}: ${e.message}`);
    }
  }

  await convertBackToEth(client, retain);
  const endEth = await getBalance(client, 'ETH');
  const delta = endEth - startEth;
  const deltaSign = delta >= 0 ? '+' : '';
  const profitUSD = delta * ethPrice;
  
  // Save profit for Garden orchestrator
  try {
    const artifactPath = require('path').join(process.cwd(), 'artifacts', 'ants_profit.json');
    await require('fs/promises').writeFile(artifactPath, JSON.stringify({ profitUSD, deltaETH: delta, timestamp: Date.now() }, null, 2));
  } catch {}
  
  console.log(`\n🐜 The Ants have completed their work`);
  console.log(`🏁 ETH: ${endEth.toFixed(8)} (${deltaSign}${delta.toFixed(8)} ETH)`);
  console.log(`💰 Profit: ${deltaSign}$${profitUSD.toFixed(2)} USD`);
  console.log(`🌍 The earth is richer for their labor`);
}

main().catch((e) => {
  console.error('Fatal:', e);
  process.exit(1);
});
