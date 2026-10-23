#!/usr/bin/env node
/**
 * Quick API Key Test - verify live Binance connection
 */

import { BinanceClient } from '../core/binanceClient';
import 'dotenv/config';

async function testKeys() {
  console.log('\n🔍 Testing Live Binance API Keys...\n');
  
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const isTestnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
  
  console.log('API Key (first 15 chars):', apiKey?.substring(0, 15) + '...');
  console.log('Mode:', isTestnet ? 'TESTNET' : 'LIVE');
  console.log('');
  
  if (!apiKey || !apiSecret) {
    console.error('❌ Missing API credentials in .env');
    process.exit(1);
  }
  
  const client = new BinanceClient({
    apiKey,
    apiSecret,
    testnet: isTestnet,
  });
  
  try {
    // Test 1: Get account info
    console.log('Test 1: Fetching account info...');
    const account = await client.getAccount();
    console.log('✅ Account fetch successful!');
    console.log('   Can trade:', account.canTrade);
    console.log('   Can withdraw:', account.canWithdraw);
    console.log('   Can deposit:', account.canDeposit);
    
    // Test 2: Get ETH balance
    const ethBal = account.balances.find(b => b.asset === 'ETH');
    console.log('\nTest 2: ETH Balance');
    console.log('   Free:', ethBal?.free || '0');
    console.log('   Locked:', ethBal?.locked || '0');
    
    // Test 3: Get price (public endpoint)
    console.log('\nTest 3: Fetching BTC price...');
    const btcPrice = await client.getPrice('BTCUSDT');
    console.log('✅ BTC/USDT:', btcPrice);
    
    // Test 4: Get ETH price
    console.log('\nTest 4: Fetching ETH price...');
    const ethPrice = await client.getPrice('ETHUSDT');
    console.log('✅ ETH/USDT:', ethPrice);
    
    // Test 5: Try getting ADAETH price
    console.log('\nTest 5: Fetching ADA/ETH price...');
    try {
      const adaEthPrice = await client.getPrice('ADAETH');
      console.log('✅ ADA/ETH:', adaEthPrice);
    } catch (err: any) {
      console.log('❌ ADA/ETH not available:', err.message);
    }
    
    console.log('\n✅ All API tests passed! Keys are working correctly.\n');
    
  } catch (err: any) {
    console.error('\n❌ API Test Failed!');
    console.error('Error:', err.message || err);
    
    if (err.message?.includes('Invalid API-key')) {
      console.error('\n💡 This means your API keys are not valid for live Binance.');
      console.error('   - If these are testnet keys, set BINANCE_TESTNET=true in .env');
      console.error('   - If you want live trading, get NEW keys from: https://www.binance.com/en/my/settings/api-management');
    }
    
    process.exit(1);
  }
}

testKeys();
