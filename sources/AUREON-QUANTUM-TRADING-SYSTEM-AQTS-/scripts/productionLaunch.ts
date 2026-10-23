#!/usr/bin/env node
/**
 * 🚀 PRODUCTION LAUNCH ORCHESTRATOR
 * 
 * Comprehensive pre-flight checks and safe production launch
 * - Validates environment configuration
 * - Checks account balance and API connectivity
 * - Performs safety checks before live trading
 * - Launches all bots with monitoring
 */

import { spawn, ChildProcess } from 'child_process';
import { BinanceClient } from '../core/binanceClient';

const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

interface PreFlightCheck {
  name: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
}

const checks: PreFlightCheck[] = [];
const botProcesses: ChildProcess[] = [];

function log(message: string, color: string = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function header(text: string) {
  console.log('\n' + '═'.repeat(70));
  log(`  ${text}`, BOLD + BLUE);
  console.log('═'.repeat(70) + '\n');
}

function checkItem(name: string, status: 'pass' | 'fail' | 'warning', message: string) {
  const icon = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
  const color = status === 'pass' ? GREEN : status === 'fail' ? RED : YELLOW;
  log(`${icon} ${name}: ${message}`, color);
  checks.push({ name, status, message });
}

async function performPreFlightChecks(): Promise<boolean> {
  header('🛫 PRE-FLIGHT CHECKS');

  // 1. Environment Configuration
  log('📋 Checking environment configuration...', BLUE);
  
  const apiKey = process.env.BINANCE_API_KEY || '';
  const apiSecret = process.env.BINANCE_API_SECRET || '';
  const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
  
  if (!apiKey || apiKey === 'your_api_key_here') {
    checkItem('API Key', 'fail', 'Binance API key not configured');
    return false;
  } else {
    checkItem('API Key', 'pass', 'API key configured');
  }

  if (!apiSecret || apiSecret === 'your_api_secret_here') {
    checkItem('API Secret', 'fail', 'Binance API secret not configured');
    return false;
  } else {
    checkItem('API Secret', 'pass', 'API secret configured');
  }

  // 2. Trading Mode Verification
  log('\n🎯 Verifying trading mode...', BLUE);
  
  if (process.env.DRY_RUN === 'true') {
    checkItem('Dry Run', 'warning', 'DRY_RUN is enabled - no real trades will execute');
  } else {
    checkItem('Dry Run', 'pass', 'DRY_RUN disabled - ready for live trading');
  }

  if (process.env.CONFIRM_LIVE_TRADING !== 'true') {
    checkItem('Live Trading Confirmation', 'fail', 'CONFIRM_LIVE_TRADING must be "true" for production');
    return false;
  } else {
    checkItem('Live Trading Confirmation', 'pass', 'Live trading confirmed');
  }

  if (testnet) {
    checkItem('Network', 'warning', 'Testnet mode enabled - using testnet.binance.vision');
  } else {
    checkItem('Network', 'pass', 'Production network - using api.binance.com');
  }


  // 3. API Connectivity
  log('\n🔌 Testing API connectivity...', BLUE);
  
  try {
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const serverTime = await client.getServerTime();
    checkItem('Binance API', 'pass', `Connected - Server time: ${new Date(serverTime).toISOString()}`);
  } catch (error) {
    checkItem('Binance API', 'fail', `Cannot connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return false;
  }

  // 4. Account Balance
  log('\n💰 Checking account balance...', BLUE);
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const account = await client.getAccount();
    
    // Find balances with non-zero free amounts
    const balances = account.balances
      .filter((b: any) => parseFloat(b.free) > 0)
      .map((b: any) => `${b.asset}: ${parseFloat(b.free).toFixed(8)}`);
    
    if (balances.length === 0) {
      checkItem('Account Balance', 'fail', 'No funds available in account');
      return false;
    }
    
    checkItem('Account Balance', 'pass', `${balances.length} assets with balance`);
    balances.forEach(bal => log(`    ${bal}`, GREEN));
    
    // Check for minimum viable balance (rough estimate)
    const btcBalance = account.balances.find((b: any) => b.asset === 'BTC');
    const ethBalance = account.balances.find((b: any) => b.asset === 'ETH');
    const usdtBalance = account.balances.find((b: any) => b.asset === 'USDT');
    
    const btcValue = btcBalance ? parseFloat(btcBalance.free) * 95000 : 0; // ~$95k per BTC
    const ethValue = ethBalance ? parseFloat(ethBalance.free) * 3100 : 0;  // ~$3.1k per ETH
    const usdtValue = usdtBalance ? parseFloat(usdtBalance.free) : 0;
    
    const totalValue = btcValue + ethValue + usdtValue;
    
    if (totalValue < 10) {
      checkItem('Minimum Notional', 'warning', `Total value ~$${totalValue.toFixed(2)} - close to $10 minimum`);
    } else {
      checkItem('Minimum Notional', 'pass', `Total value ~$${totalValue.toFixed(2)} - above $10 minimum`);
    }
    
  } catch (error) {
    checkItem('Account Balance', 'fail', `Cannot retrieve: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return false;
  }

  // 5. Trading Permissions
  log('\n🔓 Verifying trading permissions...', BLUE);
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const account = await client.getAccount();
    
    const canTrade = account.canTrade;
    const canWithdraw = account.canWithdraw;
    const canDeposit = account.canDeposit;
    
    if (!canTrade) {
      checkItem('Trading Permission', 'fail', 'Account does not have trading permission');
      return false;
    } else {
      checkItem('Trading Permission', 'pass', 'Trading enabled');
    }
    
    checkItem('Withdraw Permission', canWithdraw ? 'pass' : 'warning', canWithdraw ? 'Enabled' : 'Disabled');
    checkItem('Deposit Permission', canDeposit ? 'pass' : 'warning', canDeposit ? 'Enabled' : 'Disabled');
    
  } catch (error) {
    checkItem('Trading Permissions', 'fail', `Cannot verify: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return false;
  }

  // 6. Market Data Access
  log('\n📊 Testing market data access...', BLUE);
  
  try {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    const client = new BinanceClient({ apiKey, apiSecret, testnet });
    const ticker = await client.get24hStats('BTCUSDT');
    
    checkItem('Market Data', 'pass', `BTCUSDT: $${parseFloat(ticker.lastPrice).toFixed(2)}`);
  } catch (error) {
    checkItem('Market Data', 'fail', `Cannot retrieve: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return false;
  }

  return true;
}

function displaySummary() {
  header('📋 PRE-FLIGHT SUMMARY');
  
  const passed = checks.filter(c => c.status === 'pass').length;
  const failed = checks.filter(c => c.status === 'fail').length;
  const warnings = checks.filter(c => c.status === 'warning').length;
  
  log(`✅ Passed: ${passed}`, GREEN);
  log(`❌ Failed: ${failed}`, RED);
  log(`⚠️  Warnings: ${warnings}`, YELLOW);
  
  if (failed > 0) {
    log('\n❌ LAUNCH ABORTED - Fix failed checks before proceeding', RED + BOLD);
    return false;
  }
  
  if (warnings > 0) {
    log('\n⚠️  Some warnings detected - review before proceeding', YELLOW + BOLD);
  } else {
    log('\n✅ ALL SYSTEMS GO!', GREEN + BOLD);
  }
  
  return true;
}

async function confirmLaunch(): Promise<boolean> {
  header('⚠️  FINAL CONFIRMATION');
  
  log('You are about to start LIVE TRADING with REAL MONEY.', YELLOW + BOLD);
  log('Please review the following:', YELLOW);
  console.log('');
  log('  • All bots will execute trades automatically', YELLOW);
  log('  • Real money will be spent on each trade', YELLOW);
  log('  • Trading fees will be charged', YELLOW);
  log('  • Market conditions may result in losses', YELLOW);
  log('  • You are responsible for monitoring the system', YELLOW);
  console.log('');
  
  // In production, you'd use readline or similar for interactive confirmation
  // For now, we'll check environment variable
  const confirmed = process.env.CONFIRM_LIVE_TRADING === 'true';
  
  if (confirmed) {
    log('✅ Live trading confirmation: CONFIRMED', GREEN + BOLD);
    return true;
  } else {
    log('❌ Live trading confirmation: NOT CONFIRMED', RED + BOLD);
    log('Set CONFIRM_LIVE_TRADING=true in .env to proceed', RED);
    return false;
  }
}

function launchBot(name: string, script: string): ChildProcess {
  log(`🚀 Launching ${name}...`, BLUE);
  
  const bot = spawn('npx', ['tsx', script], {
    cwd: process.cwd(),
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env }
  });
  
  bot.stdout?.on('data', (data) => {
    const lines = data.toString().split('\n').filter((l: string) => l.trim());
    lines.forEach((line: string) => {
      log(`[${name}] ${line}`, GREEN);
    });
  });
  
  bot.stderr?.on('data', (data) => {
    const lines = data.toString().split('\n').filter((l: string) => l.trim());
    lines.forEach((line: string) => {
      log(`[${name}] ERROR: ${line}`, RED);
    });
  });
  
  bot.on('exit', (code) => {
    if (code !== 0) {
      log(`[${name}] ❌ Exited with code ${code}`, RED);
    } else {
      log(`[${name}] ✅ Exited gracefully`, GREEN);
    }
  });
  
  return bot;
}

function launchAllBots() {
  header('🤖 LAUNCHING TRADING BOTS');
  
  const bots = [
    { name: 'Hummingbird', script: './scripts/hummingbird.ts', delay: 0 },
    { name: 'ArmyAnts', script: './scripts/armyAnts.ts', delay: 2000 },
    { name: 'LoneWolf', script: './scripts/loneWolf.ts', delay: 4000 },
  ];
  
  bots.forEach((bot, index) => {
    setTimeout(() => {
      const process = launchBot(bot.name, bot.script);
      botProcesses.push(process);
    }, bot.delay);
  });
}

function setupShutdownHandlers() {
  const shutdown = () => {
    header('🛑 SHUTTING DOWN');
    
    log('Stopping all bots...', YELLOW);
    
    botProcesses.forEach((bot, index) => {
      if (bot && !bot.killed) {
        bot.kill('SIGTERM');
      }
    });
    
    setTimeout(() => {
      log('✅ All bots stopped', GREEN);
      process.exit(0);
    }, 2000);
  };
  
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

function displayLiveMonitoring() {
  header('📊 LIVE MONITORING');
  
  log('✅ Bots are now running', GREEN + BOLD);
  console.log('');
  log('Monitor your trading:', BLUE);
  log('  • Status API: http://localhost:3001/api/status', BLUE);
  log('  • Bot States: http://localhost:3001/api/bots', BLUE);
  log('  • Recent Trades: http://localhost:3001/api/trades', BLUE);
  log('  • UI Dashboard: http://localhost:5173', BLUE);
  console.log('');
  log('Logs:', BLUE);
  log('  • Trading logs: ./logs/', BLUE);
  log('  • Performance: ./artifacts/', BLUE);
  console.log('');
  log('Press Ctrl+C to stop all bots', YELLOW + BOLD);
  console.log('');
}

async function main() {
  console.clear();
  
  header('🚀 AUREON PRODUCTION LAUNCH ORCHESTRATOR');
  
  log('Initializing production launch sequence...', BLUE);
  log('This will perform safety checks before starting live trading.', BLUE);
  
  // Perform all pre-flight checks
  const checksPass = await performPreFlightChecks();
  
  // Display summary
  const summaryPass = displaySummary();
  
  if (!checksPass || !summaryPass) {
    process.exit(1);
  }
  
  // Final confirmation
  const confirmed = await confirmLaunch();
  
  if (!confirmed) {
    log('\n❌ Launch cancelled', RED);
    process.exit(1);
  }
  
  // Setup shutdown handlers
  setupShutdownHandlers();
  
  // Launch all bots
  launchAllBots();
  
  // Display monitoring info
  setTimeout(() => {
    displayLiveMonitoring();
  }, 5000);
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    log(`\n❌ FATAL ERROR: ${error.message}`, RED + BOLD);
    process.exit(1);
  });
}

export { performPreFlightChecks };
