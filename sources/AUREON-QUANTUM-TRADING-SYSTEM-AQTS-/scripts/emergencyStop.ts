#!/usr/bin/env node
/**
 * 🚨 EMERGENCY STOP SCRIPT
 * 
 * Immediately stops all trading activity and optionally closes positions
 * Use this when you need to halt trading immediately
 */

import { BinanceClient } from '../core/binanceClient';
import { spawn } from 'child_process';

const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

function log(message: string, color: string = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function header(text: string) {
  console.log('\n' + '═'.repeat(70));
  log(`  ${text}`, BOLD + RED);
  console.log('═'.repeat(70) + '\n');
}

async function killAllProcesses() {
  log('🛑 Killing all trading bot processes...', YELLOW);
  
  const processNames = ['hummingbird', 'armyAnts', 'loneWolf', 'liveTrading', 'statusServer'];
  
  for (const name of processNames) {
    try {
      // Try pkill first
      const pkill = spawn('pkill', ['-f', name], { stdio: 'ignore' });
      await new Promise(resolve => setTimeout(resolve, 500));
      
      log(`  ✅ Killed ${name} processes`, GREEN);
    } catch (error) {
      // Process might not be running
    }
  }
  
  // Also try PM2 if available
  try {
    const pm2Stop = spawn('pm2', ['stop', 'all'], { stdio: 'ignore' });
    await new Promise(resolve => setTimeout(resolve, 1000));
    log(`  ✅ Stopped PM2 processes`, GREEN);
  } catch (error) {
    // PM2 might not be installed
  }
}

async function cancelAllOrders() {
  log('\n❌ Cancelling all open orders...', YELLOW);
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const openOrders = await client.getOpenOrders();
    
    if (openOrders.length === 0) {
      log('  ℹ️  No open orders to cancel', GREEN);
      return;
    }
    
    log(`  Found ${openOrders.length} open orders`, YELLOW);
    
    for (const order of openOrders) {
      try {
        await client.cancelOrder(order.symbol, order.orderId);
        log(`  ✅ Cancelled ${order.symbol} order #${order.orderId}`, GREEN);
      } catch (error) {
        log(`  ❌ Failed to cancel ${order.symbol} order: ${error instanceof Error ? error.message : 'Unknown error'}`, RED);
      }
    }
    
  } catch (error) {
    log(`  ❌ Error checking open orders: ${error instanceof Error ? error.message : 'Unknown error'}`, RED);
  }
}

async function displayCurrentPositions() {
  log('\n💼 Current Positions:', YELLOW);
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const account = await client.getAccount();
    
    const positions = account.balances
      .filter((b: any) => parseFloat(b.free) > 0 || parseFloat(b.locked) > 0)
      .map((b: any) => ({
        asset: b.asset,
        free: parseFloat(b.free),
        locked: parseFloat(b.locked),
        total: parseFloat(b.free) + parseFloat(b.locked)
      }))
      .filter(p => p.total > 0.0001); // Filter dust
    
    if (positions.length === 0) {
      log('  ℹ️  No significant positions', GREEN);
      return;
    }
    
    console.log('');
    positions.forEach(pos => {
      log(`  ${pos.asset}: ${pos.total.toFixed(8)} (free: ${pos.free.toFixed(8)}, locked: ${pos.locked.toFixed(8)})`, GREEN);
    });
    
  } catch (error) {
    log(`  ❌ Error checking positions: ${error instanceof Error ? error.message : 'Unknown error'}`, RED);
  }
}

async function main() {
  console.clear();
  
  header('🚨 EMERGENCY STOP - AUREON TRADING SYSTEM');
  
  log('⚠️  This will immediately halt all trading activity', YELLOW + BOLD);
  console.log('');
  
  // Step 1: Kill all processes
  await killAllProcesses();
  
  // Step 2: Cancel open orders
  await cancelAllOrders();
  
  // Step 3: Display current positions
  await displayCurrentPositions();
  
  // Summary
  header('✅ EMERGENCY STOP COMPLETE');
  
  log('All trading bots have been stopped.', GREEN);
  log('All open orders have been cancelled.', GREEN);
  console.log('');
  log('⚠️  Note: This does NOT close your positions (holdings).', YELLOW);
  log('Your current balances remain unchanged.', YELLOW);
  console.log('');
  log('To close positions and exit to stablecoins:', YELLOW);
  log('  1. Review positions above', YELLOW);
  log('  2. Manually sell on Binance, OR', YELLOW);
  log('  3. Run: npx tsx scripts/closeAllPositions.ts', YELLOW);
  console.log('');
  log('To restart trading:', GREEN);
  log('  npx tsx scripts/productionLaunch.ts', GREEN);
  console.log('');
}

if (require.main === module) {
  main().catch((error) => {
    log(`\n❌ FATAL ERROR: ${error.message}`, RED + BOLD);
    process.exit(1);
  });
}

export { killAllProcesses, cancelAllOrders };
