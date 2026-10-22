#!/usr/bin/env node
/**
 * Convert existing assets to USDT for trading
 * Consolidates ETH, BNB, and other assets into USDT
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

async function convertToUSDT() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         💱 ASSET CONVERSION TO USDT                          ║
║         Consolidating assets for trading                     ║
╚════════════════════════════════════════════════════════════════╝
  `);

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  if (!apiKey || !apiSecret) {
    console.log(`❌ ERROR: Missing API credentials in .env`);
    process.exit(1);
  }

  try {
    const client = new BinanceClient({
      apiKey,
      apiSecret,
      testnet: isTestnet,
    });

    console.log(`\n1️⃣  Fetching account balances...`);
    const account = await client.getAccount();

    // Get non-zero balances
    const balances = account.balances
      .filter((b) => Number(b.free) > 0 && b.asset !== 'USDT')
      .map((b) => ({ asset: b.asset, free: Number(b.free) }));

    console.log(`\n2️⃣  Current Holdings (excluding USDT):`);
    for (const bal of balances) {
      console.log(`   ${bal.asset}: ${bal.free}`);
    }

    if (balances.length === 0) {
      console.log(`\n✅ No assets to convert (only USDT found or zero balance)`);
      return;
    }

    // Assets we can convert to USDT
    const convertibleAssets = ['ETH', 'BNB', 'BTC', 'SOL', 'ADA', 'DOGE', 'XRP', 'DOT', 'MATIC', 'LDUSDC'];
    const toConvert = balances.filter((b) => convertibleAssets.includes(b.asset));

    console.log(`\n3️⃣  Assets to convert to USDT:`);
    let totalEstimatedUSDT = 0;

    for (const bal of toConvert) {
      try {
        const symbol = `${bal.asset}USDT`;
        const price = await client.getPrice(symbol);
        const estimatedUSDT = bal.free * price;
        totalEstimatedUSDT += estimatedUSDT;
        console.log(`   ${bal.asset}: ${bal.free} × £${price.toFixed(2)} = £${estimatedUSDT.toFixed(2)} USDT`);
      } catch (err) {
        console.log(`   ${bal.asset}: Cannot find ${bal.asset}USDT pair, skipping...`);
      }
    }

    console.log(`\n   📊 Estimated Total: £${totalEstimatedUSDT.toFixed(2)} USDT`);

    console.log(`\n4️⃣  Executing conversions...`);
    let successCount = 0;
    let totalReceived = 0;

    for (const bal of toConvert) {
      try {
        const symbol = `${bal.asset}USDT`;
        
        // Get current price to calculate quantity
        const currentPrice = await client.getPrice(symbol);
        const estimatedUSDT = bal.free * currentPrice;
        
        // Skip if estimated value is too small (less than $1)
        if (estimatedUSDT < 1) {
          console.log(`   ⏭️  Skipping ${bal.asset} (value < $1)`);
          continue;
        }

        console.log(`\n   🔄 Converting ${bal.asset} to USDT...`);
        console.log(`      Amount: ${bal.free} ${bal.asset}`);
        console.log(`      Symbol: ${symbol}`);
        console.log(`      Type: MARKET SELL`);

        // Place market sell order to convert to USDT
        const order = await client.placeOrder({
          symbol,
          side: 'SELL',
          type: 'MARKET',
          quantity: bal.free,
        });

        const receivedUSDT = Number(order.cummulativeQuoteQty);
        totalReceived += receivedUSDT;
        successCount++;

        console.log(`      ✅ Success!`);
        console.log(`      Order ID: ${order.orderId}`);
        console.log(`      Received: £${receivedUSDT.toFixed(2)} USDT`);

        // Wait a bit between orders
        await new Promise((resolve) => setTimeout(resolve, 500));
      } catch (err: any) {
        console.log(`      ❌ Failed to convert ${bal.asset}: ${err.message}`);
        
        // Check if it's a minimum notional error
        if (err.message.includes('MIN_NOTIONAL') || err.message.includes('LOT_SIZE')) {
          console.log(`      ℹ️  Amount too small for trading`);
        }
      }
    }

    console.log(`\n5️⃣  Conversion Summary:`);
    console.log(`   Conversions attempted: ${toConvert.length}`);
    console.log(`   Successful: ${successCount}`);
    console.log(`   Failed/Skipped: ${toConvert.length - successCount}`);
    console.log(`   Total USDT received: £${totalReceived.toFixed(2)}`);

    // Get final USDT balance
    console.log(`\n6️⃣  Fetching final USDT balance...`);
    const finalAccount = await client.getAccount();
    const usdtBalance = finalAccount.balances.find((b) => b.asset === 'USDT');
    const finalUSDT = Number(usdtBalance?.free || 0);

    console.log(`   💰 Current USDT Balance: £${finalUSDT.toFixed(2)}`);

    if (finalUSDT >= 10) {
      console.log(`\n✅ SUCCESS! You now have sufficient USDT to start trading!`);
      console.log(`\n🚀 Ready to launch trading system with £${finalUSDT.toFixed(2)} USDT`);
    } else if (finalUSDT > 0) {
      console.log(`\n⚠️  USDT balance is still below recommended minimum (£10)`);
      console.log(`   Consider depositing more USDT for better trading opportunities`);
    } else {
      console.log(`\n⚠️  No USDT balance after conversion`);
      console.log(`   All assets were either too small or couldn't be converted`);
    }

  } catch (err: any) {
    console.error(`\n❌ Error during conversion:`, err.message);
    log('error', 'Conversion failed', { error: err.message });
    process.exit(1);
  }
}

convertToUSDT().catch(console.error);
