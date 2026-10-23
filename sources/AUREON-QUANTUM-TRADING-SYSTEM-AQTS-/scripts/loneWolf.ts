#!/usr/bin/env node
/**
 * LoneWolf: Stalks momentum, makes a single clean kill, returns to base
 * - Base AUTO: prefers USDT if >= $10, else ETH if >= $10 notional
 * - Scans liquid symbols, picks high momentum, buys with exact quote notional
 * - Tight TP/SL; exits back to base
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function roundDown(v: number, d: number) {
  const p = Math.pow(10, d);
  return Math.floor(v * p) / p;
}

function toStep(v: number, stepSize: number): number {
  if (!stepSize || stepSize <= 0) return v;
  const steps = Math.floor(v / stepSize);
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

type BaseMode = 'USDT' | 'ETH';

async function chooseBase(client: BinanceClient, modeEnv?: string): Promise<{ base: BaseMode; spendQuote: number } | null> {
  const ethPrice = await client.getPrice('ETHUSDT');
  const usdt = await getBalance(client, 'USDT');
  const eth = await getBalance(client, 'ETH');
  const minUSDT = Number(process.env.WOLF_SPEND_USDT || 12);
  const minETH = Number(process.env.WOLF_SPEND_USD || 12) / ethPrice + 0.0002;

  const mode = (modeEnv || 'AUTO').toUpperCase();
  if (mode === 'USDT') {
    if (usdt >= 10) return { base: 'USDT', spendQuote: Math.min(usdt * 0.95, Math.max(11, Number(process.env.WOLF_SPEND_USDT || 12))) };
    return null;
  }
  if (mode === 'ETH') {
    if (eth * ethPrice >= 10) return { base: 'ETH', spendQuote: Math.max(minETH, 10 / ethPrice + 0.0002) };
    return null;
  }
  // AUTO
  if (usdt >= 10) return { base: 'USDT', spendQuote: Math.min(usdt * 0.95, Math.max(11, Number(process.env.WOLF_SPEND_USDT || 12))) };
  if (eth * ethPrice >= 10) return { base: 'ETH', spendQuote: Math.max(minETH, 10 / ethPrice + 0.0002) };
  return null;
}

async function pickMomentumSymbol(client: BinanceClient, base: BaseMode): Promise<string | null> {
  const universeUSDT = (process.env.WOLF_UNIVERSE_USDT || 'BTCUSDT,ETHUSDT,SOLUSDT,LINKUSDT,AVAXUSDT,NEARUSDT,MATICUSDT,XRPUSDT,DOGEUSDT,ADAUSDT').split(',');
  const universeETH = (process.env.WOLF_UNIVERSE_ETH || 'BNBETH,SOLETH,LINKETH,ADAETH,MATICETH').split(',');
  const list = base === 'USDT' ? universeUSDT : universeETH;

  let best: { sym: string; score: number } | null = null;
  for (const sym of list) {
    try {
      const s = await client.get24hStats(sym);
      const pct = Number(s.priceChangePercent); // momentum
      const vol = Number(s.quoteAssetVolume);   // liquidity
      // Simple score: momentum weighted by log(volume)
      const score = pct * Math.log(1 + Math.max(1, vol));
      if (!best || score > best.score) best = { sym, score };
    } catch {
      // ignore
    }
  }
  if (best) return best.sym;

  // Fallback: first with a price
  for (const sym of list) {
    try { const p = await client.getPrice(sym); if (p > 0) return sym; } catch {}
  }
  return null;
}

async function tradeOnce(client: BinanceClient, base: BaseMode, symbol: string, spendQuote: number, tp=0.008, sl=-0.006, maxMinutes=5): Promise<void> {
  const DRY_RUN = process.env.DRY_RUN === 'true';
  console.log(`🐺 LoneWolf hunting ${symbol} with spend ${base==='USDT' ? '$'+spendQuote.toFixed(2) : spendQuote.toFixed(6)+' ETH'}`);
  console.log(`📡 Source: Lone Wolf (momentum snipe, single trade)`);

  // Pre-check constraints and skip if spend insufficient
  try {
    const { minQty, minNotional, price } = await getSymbolConstraints(client, symbol);
    const requiredQuote = Math.max(minQty * price, minNotional);
    if (spendQuote < requiredQuote) {
      console.log(`⏭️  Skip ${symbol}: spend ${base==='USDT'?'$'+spendQuote.toFixed(2):spendQuote.toFixed(6)+' ETH'} < min ${base==='USDT'?'$'+requiredQuote.toFixed(2):requiredQuote.toFixed(6)+' ETH'}`);
      return;
    }
  } catch (err: any) {
    console.log(`⏭️  Skip ${symbol}: cannot fetch constraints (${err.message})`);
    return;
  }

  // Buy using quoteOrderQty (spend amount in base quote)
  let buy: any;
  if (DRY_RUN) {
    const px = await client.getPrice(symbol);
    let qty = spendQuote / px;
    try { const { stepSize } = await getSymbolConstraints(client, symbol); if (stepSize > 0) qty = toStep(qty, stepSize); } catch {}
    buy = { executedQty: String(qty), cummulativeQuoteQty: String(spendQuote) };
    console.log(`DRY_RUN: simulate BUY ${symbol} spend ${base==='USDT' ? '$'+spendQuote.toFixed(2) : spendQuote.toFixed(6)+' ETH'} (~${qty.toFixed(6)} units @ ${base==='USDT' ? '$'+px.toFixed(6) : (px.toFixed(8)+' ETH')})`);
  } else {
    // Place MARKET order using quantity (LOT_SIZE stepped) to avoid LOT_SIZE errors
    const { stepSize, minQty } = await getSymbolConstraints(client, symbol);
    const px = await client.getPrice(symbol);
    let qty = spendQuote / px;
    if (stepSize > 0) qty = toStep(qty, stepSize);
    if (qty < minQty || qty <= 0) {
      console.log(`⏭️  Skip ${symbol}: computed qty ${qty} < minQty ${minQty}`);
      return;
    }
    buy = await client.placeOrder({ symbol, side: 'BUY', type: 'MARKET', quantity: qty });
  }
  const baseQty = Number(buy.executedQty);
  const cost = Number(buy.cummulativeQuoteQty);
  const avg = baseQty > 0 ? cost / baseQty : 0;
  console.log(`✅ Entry ${baseQty} ${symbol.replace(base,'')} @ ~${base==='USDT' ? '$'+avg.toFixed(6) : avg.toFixed(8)+' ETH'}`);

  // Monitor
  for (let i = 0; i < maxMinutes * 12; i++) {
    await sleep(5000);
    let px: number; try { px = await client.getPrice(symbol); } catch { continue; }
    const ch = (px - avg) / avg;
    const sign = ch >= 0 ? '+' : '';
    process.stdout.write(`\r${symbol} ${base==='USDT' ? '$'+px.toFixed(6) : px.toFixed(8)+' ETH'} (${sign}${(ch*100).toFixed(2)}%)   `);
    if (ch >= tp || ch <= sl) {
      console.log(`\nTrigger ${(ch*100).toFixed(2)}% — exiting...`);
      let sellQty = roundDown(baseQty * 0.99, 6);
      try { const { stepSize, minQty } = await getSymbolConstraints(client, symbol); if (stepSize > 0) sellQty = toStep(sellQty, stepSize); if (sellQty < minQty) { console.log(`Skip sell ${symbol}: qty ${sellQty} < minQty ${minQty}`); break; } } catch {}
      if (sellQty > 0) {
        if (DRY_RUN) {
          console.log(`DRY_RUN: simulate SELL ${symbol} qty=${sellQty}`);
        } else {
          await client.placeOrder({ symbol, side: 'SELL', type: 'MARKET', quantity: sellQty });
        }
      }
      break;
    }
  }
}

async function main() {
  if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
    console.error('Safety abort: set CONFIRM_LIVE_TRADING=yes');
    process.exit(1);
  }
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) { console.error('Missing BINANCE_API_KEY/SECRET'); process.exit(1); }

  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  const waitForFunds = process.env.WOLF_WAIT_FOR_FUNDS === 'yes';
  const tp = Number(process.env.WOLF_TP || 0.008);
  const sl = Number(process.env.WOLF_SL || -0.006);
  const maxMin = Number(process.env.WOLF_MAX_MIN || 5);

  let chooser = await chooseBase(client, process.env.WOLF_BASE);
  if (!chooser) {
    if (!waitForFunds) {
      console.error('Insufficient funds to meet $10 min-notional in USDT or ETH.');
      process.exit(1);
    }
    console.log('Waiting for funds to reach $10 min-notional...');
    for (;;) {
      await sleep(5000);
      chooser = await chooseBase(client, process.env.WOLF_BASE);
      if (chooser) break;
      process.stdout.write('.');
    }
    console.log('\nFunds available. Starting.');
  }
  const { base, spendQuote } = chooser;
  const symbol = await pickMomentumSymbol(client, base);
  if (!symbol) { console.error('No symbol available.'); process.exit(1); }
  await tradeOnce(client, base, symbol, spendQuote, tp, sl, maxMin);

  // Return to ETH if base was USDT and RETAIN_USDT != yes
  if (base === 'USDT' && process.env.WOLF_RETAIN_USDT !== 'yes') {
    const usdt = await getBalance(client, 'USDT');
    if (usdt >= 10) {
      let spend = usdt * 0.98;
      // Round quoteOrderQty to QUOTE_LOT_SIZE step to avoid precision errors
      try {
        const info = await client.getExchangeInfo(['ETHUSDT']);
        const sym = info.symbols?.find((s: any) => s.symbol === 'ETHUSDT') || {};
        const qlot = (sym.filters || []).find((f: any) => f.filterType === 'QUOTE_LOT_SIZE' || f.type === 'QUOTE_LOT_SIZE') || {};
        const qStep = parseFloat(qlot.stepSize || '0');
        const toStepQuote = (v: number, step: number) => (step > 0 ? Math.floor(v / step) * step : v);
        spend = toStepQuote(spend, isFinite(qStep) ? qStep : 0);
      } catch {}
      if (spend >= 10) {
        console.log(`🔁 Converting $${spend.toFixed(2)} USDT -> ETH`);
        await client.placeOrder({ symbol: 'ETHUSDT', side: 'BUY', type: 'MARKET', quoteOrderQty: spend, quantity: 0 });
      }
    }
  }

  const eth = await getBalance(client, 'ETH');
  const ethPx = await client.getPrice('ETHUSDT');
  console.log(`\n🏁 LoneWolf done. ETH: ${eth.toFixed(8)} (~$${(eth*ethPx).toFixed(2)})`);
}

main().catch((e) => { console.error('Fatal:', e); process.exit(1); });
