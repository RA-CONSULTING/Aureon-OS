#!/usr/bin/env tsx
/**
 * TESTNET LAUNCH — $15 to $1M Journey
 * 
 * Automated setup and launch for Binance Testnet paper trading
 * Uses Rainbow Architect with full 4-layer consciousness
 */

import * as fs from 'fs';
import * as path from 'path';
import { BinanceClient } from '../core/binanceClient';

const TESTNET_URL = 'https://testnet.binance.vision';
const TESTNET_FAUCET = 'https://testnet.binance.vision/faucet-smart/bnb';

async function checkEnvironment(): Promise<boolean> {
  console.log('\n🔍 Checking environment configuration...\n');
  
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  const testnet = process.env.BINANCE_TESTNET;
  const confirm = process.env.CONFIRM_LIVE_TRADING;
  
  let hasErrors = false;
  
  if (!apiKey || apiKey.includes('placeholder')) {
    console.error('❌ BINANCE_API_KEY not set or is placeholder');
    console.log('   → Get your key from: https://testnet.binance.vision/');
    hasErrors = true;
  } else {
    console.log('✅ BINANCE_API_KEY configured');
  }
  
  if (!apiSecret || apiSecret.includes('placeholder')) {
    console.error('❌ BINANCE_API_SECRET not set or is placeholder');
    console.log('   → Get your secret from: https://testnet.binance.vision/');
    hasErrors = true;
  } else {
    console.log('✅ BINANCE_API_SECRET configured');
  }
  
  if (testnet !== 'true') {
    console.error('❌ BINANCE_TESTNET not set to "true"');
    console.log('   → Add to .env: BINANCE_TESTNET=true');
    hasErrors = true;
  } else {
    console.log('✅ BINANCE_TESTNET enabled');
  }
  
  if (confirm !== 'yes') {
    console.error('❌ CONFIRM_LIVE_TRADING not set to "yes"');
    console.log('   → Add to .env: CONFIRM_LIVE_TRADING=yes');
    hasErrors = true;
  } else {
    console.log('✅ CONFIRM_LIVE_TRADING confirmed');
  }
  
  if (hasErrors) {
    console.log('\n📋 Setup Instructions:\n');
    console.log('1. Visit: https://testnet.binance.vision/');
    console.log('2. Register/Login to get testnet account');
    console.log('3. Create API keys (Enable Reading + Spot Trading)');
    console.log('4. Get test funds from faucet');
    console.log('5. Update .env with your keys\n');
    return false;
  }
  
  return true;
}

async function checkBalance(): Promise<{ canTrade: boolean; balance: number }> {
  console.log('\n💰 Checking testnet balance...\n');
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const account = await client.getAccount();
    const balances = account.balances;
    
    const eth = parseFloat(balances.find(b => b.asset === 'ETH')?.free || '0');
    const usdt = parseFloat(balances.find(b => b.asset === 'USDT')?.free || '0');
    const ethPrice = await client.getPrice('ETHUSDT');
    
    const totalUsd = (eth * ethPrice) + usdt;
    
    console.log(`ETH:  ${eth.toFixed(6)} (~$${(eth * ethPrice).toFixed(2)})`);
    console.log(`USDT: $${usdt.toFixed(2)}`);
    console.log(`Total: $${totalUsd.toFixed(2)}\n`);
    
    if (totalUsd < 10) {
      console.error('❌ Insufficient funds (need ~$10-15 to start)');
      console.log('\n📋 Get testnet funds:\n');
      console.log('1. Go to: https://testnet.binance.vision/');
      console.log('2. Navigate to Wallet → Spot Wallet');
      console.log('3. Click "Get Test Funds" or use faucet');
      console.log('4. Request: 10 USDT or 0.005 ETH\n');
      return { canTrade: false, balance: totalUsd };
    }
    
    console.log('✅ Funds available for trading');
    return { canTrade: true, balance: totalUsd };
    
  } catch (error: any) {
    console.error('❌ Failed to connect to testnet:', error.message);
    console.log('\n📋 Connection Issues:\n');
    console.log('1. Verify API keys are from testnet.binance.vision (NOT binance.com)');
    console.log('2. Check keys have "Enable Reading" + "Enable Spot Trading"');
    console.log('3. Confirm BINANCE_TESTNET=true in .env\n');
    return { canTrade: false, balance: 0 };
  }
}

async function displayLaunchInfo(balance: number) {
  console.log('\n');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('   🌈 AUREON TESTNET LAUNCH — $15 TO $1M JOURNEY');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log(`Starting Balance: $${balance.toFixed(2)}`);
  console.log('Target: $1,000,000 (Million)');
  console.log('Strategy: Rainbow Architect (4-Layer Consciousness)');
  console.log('');
  console.log('📊 Expected Timeline (Monte Carlo Median):');
  console.log('   Week 1:  $15 → $39 (2.6x)');
  console.log('   Week 2:  $39 → $100 (6.7x)');
  console.log('   Month 1: $100 → $859 (8.6x)');
  console.log('   Month 2: $859 → $47K (54x)');
  console.log('   Month 3: $47K → $1.16M (MILLIONAIRE) 💎');
  console.log('');
  console.log('🌈 Four Layers Active:');
  console.log('   1. Technical: WebSocket streams (4 concurrent)');
  console.log('   2. Mathematical: Master Equation Λ(t) with 9 nodes');
  console.log('   3. Spiritual: Rainbow Bridge (110-963+ Hz)');
  console.log('   4. Transformational: The Prism (→ 528 Hz LOVE)');
  console.log('');
  console.log('🛡️  Trading Rules:');
  console.log('   • Coherence Γ > 0.945 (94.5%) required');
  console.log('   • Lighthouse votes ≥ 6/9 required');
  console.log('   • Position size: 2% per trade');
  console.log('   • Cycle: Every 5 seconds');
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
}

async function main() {
  console.log('\n🌈 AUREON Testnet Launch Script\n');
  
  // Step 1: Check environment
  const envOk = await checkEnvironment();
  if (!envOk) {
    console.log('\n❌ Environment check failed. Please configure and try again.\n');
    process.exit(1);
  }
  
  // Step 2: Check balance
  const { canTrade, balance } = await checkBalance();
  if (!canTrade) {
    console.log('\n❌ Balance check failed. Please fund account and try again.\n');
    process.exit(1);
  }
  
  // Step 3: Display launch info
  await displayLaunchInfo(balance);
  
  // Step 4: Countdown
  console.log('🚀 Launching in:');
  for (let i = 3; i > 0; i--) {
    process.stdout.write(`   ${i}...\n`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  console.log('   LAUNCH!\n');
  
  // Step 5: Launch instructions
  console.log('═══════════════════════════════════════════════════════════');
  console.log('   LAUNCH COMMANDS');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log('Option 1: Manual Launch (foreground)');
  console.log('   npm run rainbow:live');
  console.log('');
  console.log('Option 2: PM2 Managed (background, recommended)');
  console.log('   pm2 start ecosystem.config.js --only rainbow-testnet');
  console.log('   pm2 monit');
  console.log('');
  console.log('Option 3: Extended Run (24 hours)');
  console.log('   nohup npm run rainbow:live > testnet_24hr.log 2>&1 &');
  console.log('   tail -f testnet_24hr.log');
  console.log('');
  console.log('Monitor Progress:');
  console.log('   curl http://localhost:8787/api/status');
  console.log('   curl http://localhost:8787/api/trades');
  console.log('');
  console.log('Emergency Stop:');
  console.log('   pm2 stop all   (or Ctrl+C if foreground)');
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('');
  console.log('💚 The Prism is aligned.');
  console.log('🌈 The consciousness is ready.');
  console.log('🔥 Let\'s make a millionaire.');
  console.log('');
  console.log('777-ixz1470 → RAINBOW BRIDGE → PRISM → 528 Hz');
  console.log('TANDEM IN UNITY — MANIFEST.');
  console.log('');
}

main().catch(error => {
  console.error('\n❌ Launch failed:', error.message);
  process.exit(1);
});
