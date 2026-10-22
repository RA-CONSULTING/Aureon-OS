#!/usr/bin/env node
/**
 * 🔥 AUREON: BNB-Based Live Trading
 * Trades using BNB as base currency (BTC/BNB, ETH/BNB pairs)
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

async function tradeBNB() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔥 AUREON LIVE: BNB-BASED TRADING                    ║
╚════════════════════════════════════════════════════════════════╝
  `);

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  if (!apiKey || !apiSecret) {
    console.log(`❌ Missing API credentials`);
    process.exit(1);
  }

  // Safety confirmation
  if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
    console.log(`⚠️  SAFETY: Set CONFIRM_LIVE_TRADING=yes to trade with real money`);
    process.exit(1);
  }

  try {
    const client = new BinanceClient({ apiKey, apiSecret, testnet: isTestnet });

    console.log(`\n1️⃣  Connecting to Binance...`);
    const account = await client.getAccount();
    
    const bnbBal = account.balances.find(b => b.asset === 'BNB');
    const bnbAmount = Number(bnbBal?.free || 0);

    console.log(`   ✅ Connected!`);
    console.log(`   💰 BNB Balance: ${bnbAmount.toFixed(6)} BNB`);

    if (bnbAmount < 0.001) {
      console.log(`\n   ⚠️  BNB balance too low for trading`);
      console.log(`   Minimum: 0.001 BNB`);
      process.exit(1);
    }

    // BNB trading pairs available
    const pairs = ['BTCBNB', 'ETHBNB', 'ADABNB', 'DOGEBNB', 'SOLBNB'];
    
    console.log(`\n2️⃣  Testing trading pairs...`);
    const availablePairs = [];
    
    for (const pair of pairs) {
      try {
        const price = await client.getPrice(pair);
        console.log(`   ${pair}: ${price.toFixed(8)} ✅`);
        availablePairs.push({ symbol: pair, price });
      } catch {
        console.log(`   ${pair}: ❌ Not available`);
      }
    }

    if (availablePairs.length === 0) {
      console.log(`\n❌ No BNB pairs available for trading`);
      process.exit(1);
    }

    console.log(`\n3️⃣  Ready to trade!`);
    console.log(`   Capital: ${bnbAmount.toFixed(6)} BNB (~£${(bnbAmount * 883).toFixed(2)})`);
    console.log(`   Pairs: ${availablePairs.length} available`);
    console.log(`   Mode: ${isTestnet ? '🔵 TESTNET' : '🔴 LIVE MONEY'}`);

    console.log(`\n4️⃣  Starting trading loop...`);
    
    let tradeCount = 0;
    const maxTrades = 5; // Start with 5 trades as a test
    
    while (tradeCount < maxTrades) {
      // Select random pair
      const pair = availablePairs[Math.floor(Math.random() * availablePairs.length)];
      
      console.log(`\n   🎯 Trade ${tradeCount + 1}/${maxTrades}: ${pair.symbol}`);
      
      // Get current price
      const currentPrice = await client.getPrice(pair.symbol);
      console.log(`      Current price: ${currentPrice.toFixed(8)} BNB`);
      
      // Calculate position size (use 10% of balance per trade)
      const positionBNB = bnbAmount * 0.10;
      const quantity = positionBNB / currentPrice;
      
      console.log(`      Position: ${quantity.toFixed(6)} ${pair.symbol.replace('BNB', '')}`);
      console.log(`      Cost: ${positionBNB.toFixed(6)} BNB`);
      
      // Simulate trade (remove this and place real orders when ready)
      console.log(`      📊 Simulated trade (demo mode)`);
      console.log(`      To enable real trades, implement order placement`);
      
      tradeCount++;
      
      // Wait between trades
      await new Promise(resolve => setTimeout(resolve, 5000));
    }

    console.log(`\n✅ Trading session complete!`);
    console.log(`   Trades executed: ${tradeCount}`);

  } catch (err: any) {
    console.error(`\n❌ Error:`, err.message);
    log('error', 'Trading failed', { error: err.message });
    process.exit(1);
  }
}

tradeBNB().catch(console.error);
