#!/usr/bin/env node
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

function ts() { return new Date().toISOString(); }

async function main() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) {
    console.error('Missing BINANCE_API_KEY/SECRET');
    process.exit(1);
  }
  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  const intervalMs = Number(process.env.BAL_INTERVAL_MS || 60000);

  for (;;) {
    try {
      const acct = await client.getAccount();
      const eth = Number(acct.balances.find(b=>b.asset==='ETH')?.free || 0);
      const usdt = Number(acct.balances.find(b=>b.asset==='USDT')?.free || 0);
      const ethPx = await client.getPrice('ETHUSDT');
      const totalUsd = usdt + eth*ethPx;
      console.log(`${ts()} | ETH=${eth.toFixed(8)} | USDT=$${usdt.toFixed(2)} | Total=$${totalUsd.toFixed(2)} (ETHUSDT=$${ethPx.toFixed(2)})`);
    } catch (e:any) {
      console.error(`${ts()} | Watcher error: ${e.message}`);
    }
    await new Promise(r=>setTimeout(r, intervalMs));
  }
}

main().catch(e=>{console.error('Fatal:', e); process.exit(1);});
