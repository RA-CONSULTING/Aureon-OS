#!/usr/bin/env node
/**
 * Hummingbird Strategy: "Pollinate and Extract"
 * - Uses small ETH to buy one ETH-quoted alt with sufficient notional (>= $10)
 * - Targets quick rotations: take-profit and stop-loss
 * - Sells back to ETH to grow the hive's ETH
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

const SLEEP = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function getNumberBalance(client: BinanceClient, asset: string): Promise<number> {
  const acct = await client.getAccount();
  return Number(acct.balances.find((b) => b.asset === asset)?.free || 0);
}

function roundDown(value: number, decimals: number): number {
  const p = Math.pow(10, decimals);
  return Math.floor(value * p) / p;
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

async function pickAltSymbol(client: BinanceClient, candidates: string[]): Promise<string | null> {
  // Prefer symbol with highest quote volume (ETH) if available
  let best: { sym: string; vol: number } | null = null;
  for (const sym of candidates) {
    try {
      const stats = await client.get24hStats(sym);
      const vol = Number(stats.quoteAssetVolume);
      if (!isNaN(vol) && (!best || vol > best.vol)) best = { sym, vol };
    } catch {
      // try next
    }
  }
  if (best) return best.sym;

  // Fallback: first symbol that has a price endpoint
  for (const sym of candidates) {
    try {
      const p = await client.getPrice(sym);
      if (p > 0) return sym;
    } catch {
      // continue
    }
  }
  return null;
}

async function main() {
  const DRY_RUN = process.env.DRY_RUN === 'true';
  if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
    console.error('Safety abort: set CONFIRM_LIVE_TRADING=yes to proceed.');
    process.exit(1);
  }

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) {
    console.error('Missing BINANCE_API_KEY or BINANCE_API_SECRET');
    process.exit(1);
  }

  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });

  console.log('🐝 The Bee begins its work — pollinator of the sky');

  const ethPrice = await client.getPrice('ETHUSDT');
  const ethBal = await getNumberBalance(client, 'ETH');
  console.log(`   ETH balance: ${ethBal.toFixed(8)} (~$${(ethBal * ethPrice).toFixed(2)}) | ETHUSDT: $${ethPrice.toFixed(2)}`);

  const minUSDT = 10.2; // buffer above $10
  const minETHNeeded = minUSDT / ethPrice;
  let spendETH = Math.min(roundDown(ethBal * 0.9, 6), roundDown(minETHNeeded + 0.0002, 6));

  if (spendETH * ethPrice < 10) {
    if (DRY_RUN) {
      // In dry-run, allow simulation below min-notional by capping spend to available
      spendETH = Math.min(roundDown(ethBal * 0.9, 6), roundDown((10 / ethPrice), 6));
      console.log(`DRY_RUN: proceeding with simulated spend ${spendETH} ETH (<$10 notional possible)`);
    } else if (process.env.HB_WAIT_FOR_FUNDS === 'yes') {
      process.stdout.write(`Waiting for ETH to reach ~$10 notional...`);
      for (;;) {
        await SLEEP(5000);
        const e = await getNumberBalance(client, 'ETH');
        const px = await client.getPrice('ETHUSDT');
        const minNeed = minUSDT / px + 0.0002;
        spendETH = Math.min(roundDown(e * 0.9, 6), roundDown(minNeed, 6));
        if (spendETH * px >= 10) break;
        process.stdout.write('.');
      }
      console.log('\nFunds available. Proceeding.');
    } else {
      console.error(`Not enough ETH to meet Binance $10 minimum. Need at least ${(minETHNeeded).toFixed(6)} ETH.`);
      process.exit(1);
    }
  }

  const forced = (process.env.HB_SYMBOL || '').trim();
  if (forced) {
    try {
      const p = await client.getPrice(forced);
      if (p > 0) {
        console.log(`HB_SYMBOL override: ${forced}`);
      } else {
        console.log(`HB_SYMBOL not tradable, falling back to universe.`);
      }
    } catch {
      // ignore and fall back to universe
    }
  }

  const envList = (process.env.HB_UNIVERSE || '').trim();
  const universe = envList ? envList.split(',').map(s => s.trim()).filter(Boolean) : ['BNBETH','SOLETH','ADAETH','XRPETH','DOGEETH','MATICETH','LTCETH'];
  const candidates = universe;

  const symbol = forced || await pickAltSymbol(client, candidates);
  if (!symbol) {
    console.error('No viable ETH-quoted symbols found.');
    process.exit(1);
  }

  console.log(`Selected: ${symbol} | Spending ${spendETH} ETH (~$${(spendETH * ethPrice).toFixed(2)})`);
  console.log(`📡 Source: Hummingbird (ETH-quoted rotations with TP/SL)`);

  // BUY via quoteOrderQty (amount of ETH to spend)
  const simulateOrder = async (sym: string, side: 'BUY'|'SELL', opts: { quantity?: number; quoteOrderQty?: number }) => {
    if (!DRY_RUN) return client.placeOrder({ symbol: sym, side, type: 'MARKET', quantity: opts.quantity || 0, quoteOrderQty: opts.quoteOrderQty });
    const px = await client.getPrice(sym);
    let executedQty = 0; let quote = 0;
    if (opts.quoteOrderQty && opts.quoteOrderQty > 0) { executedQty = opts.quoteOrderQty / px; quote = opts.quoteOrderQty; }
    else if (opts.quantity && opts.quantity > 0) { executedQty = opts.quantity; quote = opts.quantity * px; }
    return {
      symbol: sym, orderId: 0, clientOrderId: 'dry', transactTime: Date.now(), price: String(px),
      origQty: String(executedQty), executedQty: String(executedQty), cummulativeQuoteQty: String(quote),
      status: 'FILLED', timeInForce: 'GTC', type: 'MARKET', side, fills: []
    } as any;
  };

  // Filter-aware precheck for ETH-quoted pair
  try {
    const { minQty, stepSize, minNotional, price } = await getSymbolConstraints(client, symbol);
    const requiredQuoteETH = Math.max(minQty * price, minNotional); // both in ETH for *ETH pairs
    if (spendETH < requiredQuoteETH) {
      console.error(`Spend ${spendETH} ETH < exchange min ${requiredQuoteETH} ETH — skipping ${symbol}`);
      process.exit(0);
    }
    // Liquidity/depth pre-check: ensure asks cover minimum base
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
        console.error(`Insufficient depth for ${symbol}: ask qty ${sumAsk.toFixed(6)} < minBase ${minBaseNeeded.toFixed(6)} — skipping`);
        process.exit(0);
      }
    } catch (e: any) {
      console.error(`Depth check failed for ${symbol}: ${e.message || e}`);
      process.exit(1);
    }
  } catch (err: any) {
    console.error(`Cannot fetch constraints for ${symbol}: ${err.message}`);
    process.exit(1);
  }

  let buy: any;
  if (DRY_RUN) {
    buy = await simulateOrder(symbol, 'BUY', { quoteOrderQty: spendETH });
  } else {
    try {
      buy = await client.placeOrder({ symbol, side: 'BUY', type: 'MARKET', quoteOrderQty: spendETH, quantity: 0 });
    } catch (err: any) {
      const msg = String(err?.message || '');
      if (msg.includes('LOT_SIZE') || msg.includes('-2010') || msg.includes('-1013')) {
        // Fallback: compute quantity based on spendETH and step to LOT_SIZE
        const px = await client.getPrice(symbol);
        let qty = spendETH / px; // base units
        try {
          const { stepSize, minQty } = await getSymbolConstraints(client, symbol);
          if (stepSize > 0) qty = toStep(qty, stepSize);
          if (qty < minQty) {
            console.error(`Fallback qty ${qty} < minQty ${minQty} — skipping ${symbol}`);
            process.exit(0);
          }
        } catch {}
        console.log(`↩️  Fallback: placing MARKET by quantity ${qty} (stepped)`);
        buy = await client.placeOrder({ symbol, side: 'BUY', type: 'MARKET', quantity: qty });
      } else {
        throw err;
      }
    }
  }
  const baseQty = Number(buy.executedQty);
  const spentETH = Number(buy.cummulativeQuoteQty); // quote asset amount
  const avgPriceETH = spentETH / baseQty; // price in ETH
  console.log(`✅ Bought ${baseQty} ${symbol.replace('ETH','')} spending ${spentETH} ETH @ ${avgPriceETH} ETH`);

  // Monitor for TP/SL and sell back to ETH
  const target = 0.015; // +1.5%
  const stop = -0.010;  // -1.0%
  const MAX_MINUTES = Number(process.env.MAX_MINUTES || process.env.HB_MAX_MINUTES || 30);
  const baseAsset = symbol.replace('ETH','');

  for (let i = 0; i < MAX_MINUTES * 12; i++) { // check every 5s
    await SLEEP(5000);
    let priceETH: number;
    try {
      priceETH = await client.getPrice(symbol);
    } catch {
      continue;
    }
    const change = (priceETH - avgPriceETH) / avgPriceETH;
    const side = change >= 0 ? '+' : '';
    process.stdout.write(`\r${symbol} price: ${priceETH.toFixed(8)} ETH (${side}${(change*100).toFixed(2)}%)   `);

    if (change >= target || change <= stop) {
      console.log(`\nTrigger hit: ${(change*100).toFixed(2)}% — selling back to ETH...`);

      // Refresh actual base balance, sell 99% to avoid dust/precision issues
      const acct = await client.getAccount();
      const held = Number(acct.balances.find(b => b.asset === baseAsset)?.free || 0);
      // Round to exchange step size
      let sellQty = roundDown(held * 0.99, 6);
      try {
        const { stepSize, minQty } = await getSymbolConstraints(client, symbol);
        if (stepSize > 0) sellQty = toStep(sellQty, stepSize);
        if (sellQty < minQty) {
          console.error(`Sell qty ${sellQty} below minQty ${minQty} — skipping sell.`);
          break;
        }
      } catch {}
      if (sellQty <= 0) {
        console.error('No quantity to sell.');
        break;
      }

      try {
        const sell = await simulateOrder(symbol, 'SELL', { quantity: sellQty });
        console.log(`✅ Sold ${sell.executedQty} ${baseAsset} back to ETH`);
      } catch (e: any) {
        console.error(`❌ Sell failed: ${e.message}`);
        // Try with a slightly smaller qty
        sellQty = roundDown(sellQty * 0.95, 6);
        if (sellQty * priceETH * ethPrice < 10) {
          console.error('Sell would be below $10; skipping.');
          break;
        }
        try {
          const sell2 = await simulateOrder(symbol, 'SELL', { quantity: sellQty });
          console.log(`✅ Sold ${sell2.executedQty} ${baseAsset} back to ETH (retry)`);
        } catch (e2: any) {
          console.error(`❌ Sell retry failed: ${e2.message}`);
        }
      }
      break;
    }
  }

  // Print final balances and save profit
  const ethAfter = await getNumberBalance(client, 'ETH');
  const ethPriceEnd = await client.getPrice('ETHUSDT');
  const delta = ethAfter - ethBal;
  const deltaSign = delta >= 0 ? '+' : '';
  const profitUSD = delta * ethPriceEnd;

  // Save profit for Garden orchestrator
  try {
    const path = require('path');
    const fs = require('fs/promises');
    const artifactPath = path.join(process.cwd(), 'artifacts', 'bee_profit.json');
    await fs.writeFile(artifactPath, JSON.stringify({ profitUSD, deltaETH: delta, timestamp: Date.now() }, null, 2));
  } catch {}

  console.log(`\n🐝 The Bee has completed its work`);
  console.log(`🏁 ETH: ${ethAfter.toFixed(8)} (${deltaSign}${delta.toFixed(8)} ETH)`);
  console.log(`💰 Profit: ${deltaSign}$${profitUSD.toFixed(2)} USD`);
  console.log(`☁️  The sky is fuller for its flight`);
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});
