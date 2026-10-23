#!/usr/bin/env node
/**
 * AUREON Live Binance Test - Execute real trades on testnet
 */

import { liveTradingService } from '../core/liveTradingService';
import { log } from '../core/environment';

async function testLiveTrading() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║       AUREON LIVE BINANCE TEST - Real Testnet Trading        ║
║              Account: Fully Connected & Authenticated         ║
╚════════════════════════════════════════════════════════════════╝
`);

  await liveTradingService.initialize();

  if (!liveTradingService.isInitialized()) {
    console.error('❌ Failed to initialize live trading service');
    process.exit(1);
  }

  // Get account balance
  const account = await liveTradingService.getAccountInfo();
  if (account) {
    const btcBalance = account.balances.find((b) => b.asset === 'BTC');
    const usdtBalance = account.balances.find((b) => b.asset === 'USDT');
    console.log(`\n💼 Account Summary:`);
    console.log(`  BTC: ${btcBalance?.free || '0'} (locked: ${btcBalance?.locked || '0'})`);
    console.log(`  USDT: ${usdtBalance?.free || '0'} (locked: ${usdtBalance?.locked || '0'})`);
  }

  // Get current prices
  console.log(`\n📊 Current Market Prices:`);
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT'];
  for (const symbol of symbols) {
    const price = await liveTradingService.getPrice(symbol);
    if (price) {
      console.log(`  ${symbol}: $${price.toFixed(2)}`);
    }
  }

  // Execute test trades
  console.log(`\n🎯 Executing Test Trades:`);

  const trades = [
    { symbol: 'BTCUSDT', side: 'BUY' as const, quantity: 0.001 },
    { symbol: 'ETHUSDT', side: 'BUY' as const, quantity: 0.01 },
    { symbol: 'BNBUSDT', side: 'BUY' as const, quantity: 0.1 },
  ];

  for (const trade of trades) {
    console.log(`\n  → ${trade.side} ${trade.quantity} ${trade.symbol}...`);
    const result = await liveTradingService.executeTrade(trade);

    if (result.success) {
      console.log(`    ✅ Order ${result.orderId}: ${result.message}`);
      console.log(`       Executed: ${result.executedQty} @ $${result.avgPrice?.toFixed(2)}`);
    } else {
      console.log(`    ❌ Failed: ${result.error || result.message}`);
    }
  }

  // Get final positions
  const positions = liveTradingService.getPositions();
  if (positions.length > 0) {
    console.log(`\n📈 Open Positions:`);
    for (const pos of positions) {
      console.log(
        `  ${pos.symbol}: ${pos.side} ${pos.quantity} @ $${pos.entryPrice.toFixed(2)} (P&L: ${pos.unrealizedPnLPercent.toFixed(2)}%)`
      );
    }
  }

  console.log(`\n✨ Test Complete!`);
}

testLiveTrading().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
