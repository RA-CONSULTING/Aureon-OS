#!/usr/bin/env node
/**
 * Consolidate all assets to USDT, then report full balance
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

function roundDown(v: number, d: number) {
  const p = Math.pow(10, d);
  return Math.floor(v * p) / p;
}

async function main() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) {
    console.error('Missing API credentials');
    process.exit(1);
  }

  const client = new BinanceClient({ 
    apiKey, 
    apiSecret, 
    testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") 
  });

  console.log('🔄 Consolidating all assets to USDT...\n');

  const account = await client.getAccount();
  const balances = account.balances.filter(b => Number(b.free) > 0 && b.asset !== 'USDT');

  let totalUSDTBefore = Number(account.balances.find(b => b.asset === 'USDT')?.free || 0);
  console.log(`Starting USDT: $${totalUSDTBefore.toFixed(2)}\n`);

  for (const bal of balances) {
    const asset = bal.asset;
    const amount = Number(bal.free);
    
    if (amount === 0) continue;

    const symbol = `${asset}USDT`;
    
    try {
      // Check if pair exists
      const price = await client.getPrice(symbol);
      const valueUSDT = amount * price;
      
      if (valueUSDT < 10) {
        console.log(`⏭️  Skipping ${asset}: $${valueUSDT.toFixed(2)} (below $10 min)`);
        continue;
      }

      // Sell to USDT
      const sellQty = roundDown(amount * 0.99, 6);
      console.log(`🔴 Selling ${sellQty} ${asset} (~$${valueUSDT.toFixed(2)}) → USDT`);
      
      const order = await client.placeOrder({
        symbol,
        side: 'SELL',
        type: 'MARKET',
        quantity: sellQty
      });

      const receivedUSDT = Number(order.cummulativeQuoteQty);
      console.log(`✅ Received $${receivedUSDT.toFixed(2)} USDT\n`);
      
    } catch (e: any) {
      console.log(`❌ Failed to sell ${asset}: ${e.message}\n`);
    }
  }

  // Get final balance
  const finalAcct = await client.getAccount();
  const finalUSDT = Number(finalAcct.balances.find(b => b.asset === 'USDT')?.free || 0);
  const finalETH = Number(finalAcct.balances.find(b => b.asset === 'ETH')?.free || 0);
  
  let totalValueUSD = finalUSDT;
  if (finalETH > 0) {
    try {
      const ethPrice = await client.getPrice('ETHUSDT');
      totalValueUSD += finalETH * ethPrice;
    } catch {}
  }

  console.log('\n' + '='.repeat(60));
  console.log('💰 FINAL CONSOLIDATED BALANCE');
  console.log('='.repeat(60));
  console.log(`USDT: $${finalUSDT.toFixed(2)}`);
  if (finalETH > 0) console.log(`ETH: ${finalETH.toFixed(8)}`);
  console.log(`Total Value: $${totalValueUSD.toFixed(2)}`);
  console.log('='.repeat(60) + '\n');
}

main().catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});
