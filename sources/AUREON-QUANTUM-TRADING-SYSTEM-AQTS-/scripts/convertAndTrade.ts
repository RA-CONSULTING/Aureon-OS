#!/usr/bin/env tsx
/**
 * 🔥 CONVERT ASSETS & START LIVE TRADING 🔥
 * 
 * This script will:
 * 1. Convert your BNB/ETH to USDT
 * 2. Launch the ultra-aggressive mission with REAL money
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';

async function convertAndTrade() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔥 AUREON LIVE TRADING LAUNCHER 🍯                   ║
║         Converting Assets → Starting Mission                 ║
╚════════════════════════════════════════════════════════════════╝
  `);

  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = process.env.BINANCE_TESTNET?.toLowerCase() === 'true';

  if (!apiKey || !apiSecret) {
    console.log(`❌ ERROR: Missing credentials in .env`);
    process.exit(1);
  }

  try {
    console.log(`\n1️⃣  Connecting to Binance...`);
    const client = new BinanceClient({
      apiKey,
      apiSecret,
      testnet: isTestnet,
    });

    // Get account info
    const account = await client.getAccount();
    console.log(`   ✅ Connected to ${isTestnet ? 'TESTNET' : 'LIVE'} account\n`);

    // Check balances
    const bnbBalance = account.balances.find((b) => b.asset === 'BNB');
    const ethBalance = account.balances.find((b) => b.asset === 'ETH');
    const usdtBalance = account.balances.find((b) => b.asset === 'USDT');

    const bnbFree = Number(bnbBalance?.free || 0);
    const ethFree = Number(ethBalance?.free || 0);
    const usdtFree = Number(usdtBalance?.free || 0);

    console.log(`2️⃣  Current Balances:`);
    console.log(`   BNB: ${bnbFree.toFixed(8)}`);
    console.log(`   ETH: ${ethFree.toFixed(8)}`);
    console.log(`   USDT: ${usdtFree.toFixed(2)}\n`);

    // Get current prices
    const bnbPrice = await client.getPrice('BNBUSDT');
    const ethPrice = await client.getPrice('ETHUSDT');

    const bnbValue = bnbFree * bnbPrice;
    const ethValue = ethFree * ethPrice;
    const totalValue = bnbValue + ethValue + usdtFree;

    console.log(`3️⃣  Portfolio Value:`);
    console.log(`   BNB: $${bnbValue.toFixed(2)} (${bnbFree.toFixed(4)} BNB @ $${bnbPrice.toFixed(2)})`);
    console.log(`   ETH: $${ethValue.toFixed(2)} (${ethFree.toFixed(6)} ETH @ $${ethPrice.toFixed(2)})`);
    console.log(`   USDT: $${usdtFree.toFixed(2)}`);
    console.log(`   TOTAL: $${totalValue.toFixed(2)}\n`);

    // Ask for confirmation
    console.log(`4️⃣  Conversion Plan:`);
    
    let willConvert = false;
    let conversionPlan: { asset: string; amount: number; value: number }[] = [];

    if (bnbFree > 0.01) {  // Only convert if > 0.01 BNB to avoid dust
      console.log(`   • Convert ${bnbFree.toFixed(4)} BNB → ~$${bnbValue.toFixed(2)} USDT`);
      conversionPlan.push({ asset: 'BNB', amount: bnbFree, value: bnbValue });
      willConvert = true;
    }

    if (ethFree > 0.001) {  // Only convert if > 0.001 ETH to avoid dust
      console.log(`   • Convert ${ethFree.toFixed(6)} ETH → ~$${ethValue.toFixed(2)} USDT`);
      conversionPlan.push({ asset: 'ETH', amount: ethFree, value: ethValue });
      willConvert = true;
    }

    if (!willConvert && usdtFree < 10) {
      console.log(`\n❌ ERROR: No assets to convert and insufficient USDT balance`);
      console.log(`   You need at least $10 USDT to start trading`);
      console.log(`\n   Options:`);
      console.log(`   1. Deposit USDT to your Binance account`);
      console.log(`   2. Buy BNB/ETH on Binance and run this script again`);
      process.exit(1);
    }

    if (willConvert) {
      const expectedUSDT = totalValue;
      console.log(`\n   Expected USDT after conversion: ~$${expectedUSDT.toFixed(2)}\n`);

      // Require explicit confirmation
      const confirm = process.env.CONFIRM_CONVERSION === 'YES';
      if (!confirm) {
        console.log(`⚠️  CONVERSION REQUIRES CONFIRMATION!`);
        console.log(`\nTo proceed, run:`);
        console.log(`   export CONFIRM_CONVERSION=YES`);
        console.log(`   npx tsx scripts/convertAndTrade.ts\n`);
        process.exit(1);
      }

      console.log(`5️⃣  Converting assets to USDT...\n`);

      // Convert BNB to USDT
      if (bnbFree > 0.01) {
        try {
          console.log(`   Converting BNB...`);
          const bnbOrder = await client.placeOrder({
            symbol: 'BNBUSDT',
            side: 'SELL',
            type: 'MARKET',
            quantity: parseFloat(bnbFree.toFixed(5)),
          });
          console.log(`   ✅ BNB → USDT: Order ID ${bnbOrder.orderId}`);
          await new Promise(resolve => setTimeout(resolve, 2000));
        } catch (err: any) {
          console.log(`   ⚠️  BNB conversion error: ${err.message}`);
        }
      }

      // Convert ETH to USDT
      if (ethFree > 0.001) {
        try {
          console.log(`   Converting ETH...`);
          const ethOrder = await client.placeOrder({
            symbol: 'ETHUSDT',
            side: 'SELL',
            type: 'MARKET',
            quantity: parseFloat(ethFree.toFixed(6)),
          });
          console.log(`   ✅ ETH → USDT: Order ID ${ethOrder.orderId}`);
          await new Promise(resolve => setTimeout(resolve, 2000));
        } catch (err: any) {
          console.log(`   ⚠️  ETH conversion error: ${err.message}`);
        }
      }

      // Check final USDT balance
      console.log(`\n6️⃣  Checking final USDT balance...`);
      const finalAccount = await client.getAccount();
      const finalUSDT = Number(finalAccount.balances.find((b) => b.asset === 'USDT')?.free || 0);
      console.log(`   Final USDT: $${finalUSDT.toFixed(2)}\n`);

      if (finalUSDT < 10) {
        console.log(`⚠️  WARNING: USDT balance still below $10`);
        console.log(`   Cannot start trading with less than $10`);
        process.exit(1);
      }
    } else {
      console.log(`   No conversion needed, using existing USDT: $${usdtFree.toFixed(2)}\n`);
    }

    // Final USDT balance
    const readyAccount = await client.getAccount();
    const readyUSDT = Number(readyAccount.balances.find((b) => b.asset === 'USDT')?.free || 0);

    console.log(`${'═'.repeat(64)}`);
    console.log(`\n🔥 READY TO TRADE! 🔥`);
    console.log(`\n   Trading Capital: $${readyUSDT.toFixed(2)} USDT`);
    console.log(`\n   To launch LIVE TRADING:\n`);
    console.log(`   export CONFIRM_LIVE_TRADING=YES`);
    console.log(`   export STARTING_CAPITAL=${readyUSDT.toFixed(2)}`);
    console.log(`   npx tsx scripts/realMoneyLive.ts\n`);
    console.log(`${'═'.repeat(64)}\n`);

  } catch (err: any) {
    console.log(`\n❌ ERROR: ${err.message}`);
    log('error', 'Conversion failed', err);
    process.exit(1);
  }
}

convertAndTrade();
