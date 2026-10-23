#!/usr/bin/env node
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

async function main() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) {
    console.error('Missing BINANCE_API_KEY/SECRET');
    process.exit(1);
  }
  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  const ethPx = await client.getPrice('ETHUSDT');

  // Fetch full exchange info and filter ETH-quoted symbols
  const info = await client.getExchangeInfo();
  const myEth = Number((await client.getAccount()).balances.find(b => b.asset === 'ETH')?.free || 0);
  const myUsd = myEth * ethPx;

  console.log(`ETH balance: ${myEth} (~$${myUsd.toFixed(2)}) | ETHUSDT: $${ethPx.toFixed(2)}`);
  console.log('Checking MIN_NOTIONAL filters (quote is ETH)...');

  const viable: { symbol: string; minNotionalETH: number; minUsd: number }[] = [];

  for (const sym of info.symbols || []) {
    if (sym.quoteAsset !== 'ETH') continue;
    const mn = sym.filters?.find((f: any) => f.filterType === 'MIN_NOTIONAL');
    if (!mn) continue;
    const minNotionalETH = Number(mn.minNotional || mn.notional || 0);
    if (!minNotionalETH) continue;
    const minUsd = minNotionalETH * ethPx;
    if (minUsd <= myUsd + 1e-8) {
      viable.push({ symbol: sym.symbol, minNotionalETH, minUsd });
    }
  }

  viable.sort((a,b) => a.minUsd - b.minUsd);
  if (viable.length === 0) {
    console.log('No ETH-quoted symbols with MIN_NOTIONAL <= your balance.');
  } else {
    console.log('Viable ETH-quoted symbols you can trade with current balance:');
    for (const v of viable) {
      console.log(`- ${v.symbol}: min ~${v.minNotionalETH} ETH (~$${v.minUsd.toFixed(2)})`);
    }
  }
}

main().catch(e => { console.error('Scan failed:', e); process.exit(1); });
