#!/usr/bin/env tsx
/**
 * Quick BNB to USDT Converter
 * Converts all available BNB to USDT for trading
 */

import { BinanceClient } from '../core/binanceClient';

async function convertBNBtoUSDT() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const testnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  if (!apiKey || !apiSecret) {
    console.log(`❌ Missing API credentials`);
    process.exit(1);
  }

  console.log(`\n🔄 BNB → USDT Converter\n`);

  try {
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    
    // Get account
    const account = await client.getAccount();
    const bnbBalance = account.balances.find(b => b.asset === 'BNB');
    const bnbFree = parseFloat(bnbBalance?.free || '0');

    if (bnbFree < 0.01) {
      console.log(`❌ Insufficient BNB balance: ${bnbFree.toFixed(8)}`);
      console.log(`   Minimum: 0.01 BNB`);
      process.exit(1);
    }

    // Get BNB price
    const bnbPrice = await client.getPrice('BNBUSDT');
    const bnbValue = bnbFree * bnbPrice;

    console.log(`Current BNB: ${bnbFree.toFixed(4)} BNB`);
    console.log(`BNB Price: $${bnbPrice.toFixed(2)}`);
    console.log(`Value: $${bnbValue.toFixed(2)} USDT\n`);

    // Confirm
    const confirm = process.env.CONFIRM_CONVERSION;
    if (confirm !== 'YES') {
      console.log(`⚠️  To convert, run:`);
      console.log(`   export CONFIRM_CONVERSION=YES`);
      console.log(`   npx tsx scripts/quickConvert.ts\n`);
      process.exit(0);
    }

    console.log(`🔥 Converting ${bnbFree.toFixed(4)} BNB to USDT...\n`);

    // Place sell order (sell all BNB for USDT)
    const order = await client.placeOrder({
      symbol: 'BNBUSDT',
      side: 'SELL',
      type: 'MARKET',
      quantity: parseFloat(bnbFree.toFixed(5)), // Round to 5 decimals
    });

    console.log(`✅ Conversion complete!`);
    console.log(`   Order ID: ${order.orderId}`);
    console.log(`   Sold: ${order.executedQty} BNB`);
    console.log(`   Received: ~$${order.cummulativeQuoteQty} USDT\n`);

    // Check new balance
    await new Promise(resolve => setTimeout(resolve, 2000));
    const newAccount = await client.getAccount();
    const usdtBalance = newAccount.balances.find(b => b.asset === 'USDT');
    const usdtFree = parseFloat(usdtBalance?.free || '0');

    console.log(`💰 New USDT Balance: $${usdtFree.toFixed(2)}\n`);
    console.log(`✅ Ready to trade! Run:`);
    console.log(`   export CONFIRM_LIVE_TRADING=yes`);
    console.log(`   npx tsx scripts/smartSmallCapital.ts\n`);

  } catch (err: any) {
    console.log(`❌ Conversion failed: ${err.message}`);
    process.exit(1);
  }
}

convertBNBtoUSDT();
