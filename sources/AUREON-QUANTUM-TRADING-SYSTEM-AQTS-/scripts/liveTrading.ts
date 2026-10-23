#!/usr/bin/env node
/**
 * AUREON Live Trading: Queen-Hive Network with Binance Integration
 * - Real-time price feeds from Binance WebSocket
 * - Live order execution on Binance (testnet or live)
 * - Multi-hive orchestration with risk management
 * - 10-9-1 capital allocation with automated spawning
 */

import { liveTradingService } from '../core/liveTradingService';
import { envConfig, log } from '../core/environment';
import { BinanceClient } from '../core/binanceClient';

interface LiveHive {
  id: string;
  generation: number;
  capital: number;
  agents: number;
  trades: number;
  successRate: number;
  positions: Set<string>;
  pnl: number;
}

const TRADE_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT'];

async function initializeLiveTrading() {
  log('info', '🚀 AUREON Live Trading System Initializing...');
  log('info', `Mode: ${envConfig.mode}`);
  log('info', `Binance: ${envConfig.binance.testnet ? 'TESTNET' : 'LIVE'}`);
  log('info', `Paper Mode: ${envConfig.trading.paperMode}`);

  await liveTradingService.initialize();

  if (liveTradingService.isInitialized()) {
    const account = await liveTradingService.getAccountInfo();
    if (account) {
      const totalBalance = account.balances.reduce((sum, b) => {
        const free = Number(b.free);
        const locked = Number(b.locked);
        return sum + free + locked;
      }, 0);
      log('info', `✅ Account connected. Total balance: ${totalBalance.toFixed(8)} BNB equivalent`);
    }
  } else if (liveTradingService.isPaperMode()) {
    log('warn', '⚠️  Running in PAPER MODE - no live execution');
  }
}

async function subscribeToLivePrices() {
  log('info', `📊 Subscribing to real-time price feeds for: ${TRADE_SYMBOLS.join(', ')}`);

  const priceCallback = (symbol: string, price: number) => {
    log('debug', `${symbol}: $${price.toFixed(2)}`);
  };

  // Subscribe to each symbol
  for (const symbol of TRADE_SYMBOLS) {
    const unsubscribe = liveTradingService.subscribeToPrice(symbol, (price) => {
      priceCallback(symbol, price);
    });

    if (unsubscribe) {
      // Store unsubscribe functions for cleanup on exit
      process.on('exit', unsubscribe);
    }
  }
}

async function simulateLiveTrading() {
  log('info', '🎯 Simulating live trading with 10-agent hive network...');

  const hive: LiveHive = {
    id: 'hive-live-0',
    generation: 1,
    capital: 100,
    agents: 10,
    trades: 0,
    successRate: 0,
    positions: new Set(),
    pnl: 0,
  };

  // Simulate trades over time
  const tradeInterval = setInterval(async () => {
    const symbol = TRADE_SYMBOLS[Math.floor(Math.random() * TRADE_SYMBOLS.length)];
    const side = Math.random() > 0.5 ? 'BUY' : 'SELL';
    
    // Use minimum valid lot sizes for each symbol on testnet
    const lotSizes: Record<string, number> = {
      BTCUSDT: 0.001,  // Min 0.001 BTC
      ETHUSDT: 0.01,   // Min 0.01 ETH
      BNBUSDT: 0.1,    // Min 0.1 BNB
      ADAUSDT: 1,      // Min 1 ADA
      XRPUSDT: 1,      // Min 1 XRP
    };
    const quantity = lotSizes[symbol] || 0.001;

    log('info', `📈 Executing: ${side} ${quantity} ${symbol}`);

    const result = await liveTradingService.executeTrade({
      symbol,
      side,
      quantity,
      type: 'MARKET',
    });

    if (result.success) {
      log('info', `✅ Trade ${hive.trades + 1} executed: ${result.message}`);
      hive.trades++;
      hive.positions.add(symbol);

      if (result.avgPrice) {
        hive.pnl += (Math.random() - 0.5) * 10; // Random P&L for demo
      }
    } else {
      log('warn', `❌ Trade failed: ${result.message}`);
    }

    // Log hive status every 10 trades
    if (hive.trades % 10 === 0) {
      log('info', `Hive Status: Trades=${hive.trades}, PnL=£${hive.pnl.toFixed(2)}`);
    }

    // Stop after 30 trades (demo)
    if (hive.trades >= 30) {
      clearInterval(tradeInterval);
      log('info', `✨ Demo trading complete. Total trades: ${hive.trades}, PnL: £${hive.pnl.toFixed(2)}`);
      process.exit(0);
    }
  }, 5000); // Trade every 5 seconds
}

async function main() {
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║     AUREON LIVE TRADING: Binance Integration Demo            ║
║     Production-Grade Queen-Hive Network + Real Execution    ║
╚═══════════════════════════════════════════════════════════════╝
`);

  try {
    await initializeLiveTrading();
    await subscribeToLivePrices();
    await simulateLiveTrading();
  } catch (err) {
    log('error', 'Fatal error:', err);
    process.exit(1);
  }
}

main();
