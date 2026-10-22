#!/usr/bin/env node
/**
 * 🦆 VALIDATE QUACKER ARMY - Test all commander accounts
 */

import { BinanceClient } from '../core/binanceClient';
import { loadAccountsFromJson, AccountRecord } from './utils/accountLoader';

async function validateQuackerArmy() {
  console.log('\n' + '═'.repeat(70));
  console.log('  🦆⚡ VALIDATING QUACKER ARMY - TESTING ALL COMMANDERS ⚡🦆');
  console.log('═'.repeat(70) + '\n');

  const accounts: AccountRecord[] = loadAccountsFromJson();
  if (accounts.length === 0) {
    console.error('❌ accounts.json not found or empty.');
    process.exit(1);
  }
  console.log(`📋 Found ${accounts.length} Quacker Commanders to validate\n`);

  const results: Array<{
    name: string;
    status: 'ACTIVE' | 'FAILED';
    balance: number;
    assets: string[];
    error?: string;
  }> = [];

  let totalBalance = 0;
  let activeCount = 0;

  for (const account of accounts) {
    process.stdout.write(`🦆 Testing ${account.name}... `);

    try {
      const client = new BinanceClient({
        apiKey: account.apiKey,
        apiSecret: account.apiSecret,
        testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false"), // All are live accounts
      });

      const accountInfo = await client.getAccount();

      if (!accountInfo.canTrade) {
        throw new Error('Trading not enabled');
      }

      // Calculate total balance
      let accountBalance = 0;
      const assetList: string[] = [];

      for (const bal of accountInfo.balances) {
        const free = parseFloat(bal.free);
        if (free > 0.0001) {
          assetList.push(bal.asset);
          
          // Try to get USDT value
          try {
            if (bal.asset === 'USDT' || bal.asset === 'USDC') {
              accountBalance += free;
            } else if (bal.asset === 'BTC') {
              const btcPrice = await client.getPrice('BTCUSDT');
              accountBalance += free * btcPrice;
            } else if (bal.asset === 'ETH') {
              const ethPrice = await client.getPrice('ETHUSDT');
              accountBalance += free * ethPrice;
            } else if (bal.asset === 'BNB') {
              const bnbPrice = await client.getPrice('BNBUSDT');
              accountBalance += free * bnbPrice;
            } else {
              // Try to get price for other assets
              try {
                const price = await client.getPrice(`${bal.asset}USDT`);
                accountBalance += free * price;
              } catch {
                // Can't price this asset, skip it
              }
            }
          } catch {
            // Pricing failed for this asset
          }
        }
      }

      console.log(`✅ ACTIVE | $${accountBalance.toFixed(2)} | Assets: ${assetList.join(', ')}`);

      results.push({
        name: account.name,
        status: 'ACTIVE',
        balance: accountBalance,
        assets: assetList,
      });

      totalBalance += accountBalance;
      activeCount++;

      // Small delay to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 200));

    } catch (err: any) {
      console.log(`❌ FAILED | ${err.message}`);
      
      results.push({
        name: account.name,
        status: 'FAILED',
        balance: 0,
        assets: [],
        error: err.message,
      });
    }
  }

  // Summary
  console.log('\n' + '═'.repeat(70));
  console.log('  📊 QUACKER ARMY VALIDATION SUMMARY');
  console.log('═'.repeat(70) + '\n');

  console.log(`🦆 Total Commanders: ${accounts.length}`);
  console.log(`✅ Active & Ready: ${activeCount}`);
  console.log(`❌ Failed/Inactive: ${accounts.length - activeCount}`);
  console.log(`💰 Combined War Chest: $${totalBalance.toFixed(2)}`);
  console.log('');

  console.log('Individual Commander Status:\n');
  for (const result of results) {
    if (result.status === 'ACTIVE') {
      console.log(`  ✅ ${result.name}: $${result.balance.toFixed(2)} (${result.assets.length} assets)`);
    } else {
      console.log(`  ❌ ${result.name}: ${result.error}`);
    }
  }

  console.log('\n' + '═'.repeat(70));
  console.log('  🦆 VALIDATION COMPLETE');
  console.log('═'.repeat(70) + '\n');

  if (activeCount === 0) {
    console.log('⚠️  WARNING: NO ACTIVE ACCOUNTS! Cannot deploy army.\n');
  } else if (activeCount < accounts.length) {
    console.log(`⚠️  WARNING: ${accounts.length - activeCount} commanders failed validation.\n`);
  } else {
    console.log('🎉 ALL COMMANDERS VALIDATED AND READY FOR DEPLOYMENT!\n');
  }
}

validateQuackerArmy().catch(err => {
  console.error('\n❌ Fatal error:', err.message);
  process.exit(1);
});
