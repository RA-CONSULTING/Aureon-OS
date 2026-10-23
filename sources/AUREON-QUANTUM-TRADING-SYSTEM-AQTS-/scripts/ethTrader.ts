#!/usr/bin/env node
/**
 * 🔥 ETH TRADER - Buy Low, Sell High Strategy
 * - Uses your existing ETH balance
 * - Sells ETH for USDT when price goes up
 * - Buys ETH with USDT when price goes down
 * - Accumulates more ETH over time
 */

import { BinanceClient } from '../core/binanceClient';
import { log } from '../core/environment';
import 'dotenv/config';

interface TradeStats {
  totalTrades: number;
  successfulTrades: number;
  failedTrades: number;
  ethStart: number;
  ethCurrent: number;
  usdtBalance: number;
  totalValue: number;
}

class ETHTrader {
  private client: BinanceClient;
  private stats: TradeStats;
  private lastETHPrice = 0;
  private priceHistory: number[] = [];
  
  constructor() {
    const apiKey = process.env.BINANCE_API_KEY!;
    const apiSecret = process.env.BINANCE_API_SECRET!;
    
    this.client = new BinanceClient({
      apiKey,
      apiSecret,
      testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false"),
    });
    
    this.stats = {
      totalTrades: 0,
      successfulTrades: 0,
      failedTrades: 0,
      ethStart: 0,
      ethCurrent: 0,
      usdtBalance: 0,
      totalValue: 0,
    };
  }
  
  async initialize(): Promise<void> {
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🔥 ETH TRADER - Accumulation Strategy                 ║
╚════════════════════════════════════════════════════════════════╝
    `);
    
    const account = await this.client.getAccount();
    const ethBal = Number(account.balances.find(b => b.asset === 'ETH')?.free || 0);
    const usdtBal = Number(account.balances.find(b => b.asset === 'USDT')?.free || 0);
    
    this.stats.ethStart = ethBal;
    this.stats.ethCurrent = ethBal;
    this.stats.usdtBalance = usdtBal;
    
    const ethPrice = await this.client.getPrice('ETHUSDT');
    this.lastETHPrice = ethPrice;
    this.stats.totalValue = (ethBal * ethPrice) + usdtBal;
    
    console.log(`💰 Starting Balance:`);
    console.log(`   ETH: ${ethBal.toFixed(8)} ($${(ethBal * ethPrice).toFixed(2)})`);
    console.log(`   USDT: $${usdtBal.toFixed(2)}`);
    console.log(`   Total Value: $${this.stats.totalValue.toFixed(2)}`);
    console.log(`   ETH Price: $${ethPrice.toFixed(2)}`);
    console.log(``);
    console.log(`⚡ Starting trading loop...`);
    console.log(``);
  }
  
  async executeTrade(): Promise<void> {
    try {
      // Get current price
      const currentPrice = await this.client.getPrice('ETHUSDT');
      this.priceHistory.push(currentPrice);
      
      // Keep last 20 prices for trend analysis
      if (this.priceHistory.length > 20) {
        this.priceHistory.shift();
      }
      
      // Get current balances
      const account = await this.client.getAccount();
      const ethBal = Number(account.balances.find(b => b.asset === 'ETH')?.free || 0);
      const usdtBal = Number(account.balances.find(b => b.asset === 'USDT')?.free || 0);
      
      this.stats.ethCurrent = ethBal;
      this.stats.usdtBalance = usdtBal;
      
      // Calculate price change
      const priceChange = ((currentPrice - this.lastETHPrice) / this.lastETHPrice) * 100;
      
      // Strategy: Sell if price went up 0.5%, Buy if price went down 0.5%
      let shouldSell = priceChange > 0.5 && ethBal > 0.001;
      let shouldBuy = priceChange < -0.5 && usdtBal > 10;
      
      // Alternative: Use all ETH to sell, use all USDT to buy
      if (shouldSell && ethBal >= 0.001) {
        // SELL: Convert ETH to USDT
        const sellAmount = Math.floor(ethBal * 1000) / 1000; // Round to 3 decimals
        
        console.log(`🔴 SELL SIGNAL: Price up ${priceChange.toFixed(2)}%`);
        console.log(`   Selling ${sellAmount} ETH @ $${currentPrice.toFixed(2)}`);
        
        try {
          const order = await this.client.placeOrder({
            symbol: 'ETHUSDT',
            side: 'SELL',
            type: 'MARKET',
            quantity: sellAmount,
          });
          
          this.stats.totalTrades++;
          this.stats.successfulTrades++;
          
          console.log(`✅ SOLD ${order.executedQty} ETH for ~$${(Number(order.executedQty) * currentPrice).toFixed(2)}`);
          this.lastETHPrice = currentPrice;
          
        } catch (err: any) {
          this.stats.totalTrades++;
          this.stats.failedTrades++;
          console.log(`❌ Sell failed: ${err.message}`);
        }
        
      } else if (shouldBuy && usdtBal >= 10) {
        // BUY: Convert USDT to ETH
        const buyAmountUSDT = Math.min(usdtBal * 0.95, usdtBal - 1); // Leave $1 for fees
        const buyAmountETH = Math.floor((buyAmountUSDT / currentPrice) * 1000) / 1000;
        
        console.log(`🟢 BUY SIGNAL: Price down ${priceChange.toFixed(2)}%`);
        console.log(`   Buying ${buyAmountETH} ETH with $${buyAmountUSDT.toFixed(2)}`);
        
        try {
          const order = await this.client.placeOrder({
            symbol: 'ETHUSDT',
            side: 'BUY',
            type: 'MARKET',
            quantity: buyAmountETH,
          });
          
          this.stats.totalTrades++;
          this.stats.successfulTrades++;
          
          console.log(`✅ BOUGHT ${order.executedQty} ETH for ~$${(Number(order.executedQty) * currentPrice).toFixed(2)}`);
          this.lastETHPrice = currentPrice;
          
        } catch (err: any) {
          this.stats.totalTrades++;
          this.stats.failedTrades++;
          console.log(`❌ Buy failed: ${err.message}`);
        }
        
      } else {
        console.log(`⏸️  Price: $${currentPrice.toFixed(2)} (${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%) - Waiting for signal...`);
      }
      
    } catch (err) {
      log('error', 'Trade execution failed', err);
    }
  }
  
  printStatus(): void {
    const ethValue = this.stats.ethCurrent * this.lastETHPrice;
    const totalValue = ethValue + this.stats.usdtBalance;
    const profitUSDT = totalValue - this.stats.totalValue;
    const profitPercent = ((totalValue - this.stats.totalValue) / this.stats.totalValue) * 100;
    const ethGained = this.stats.ethCurrent - this.stats.ethStart;
    
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║            ETH TRADER STATUS                                   ║
╚════════════════════════════════════════════════════════════════╝

Current Holdings:
  ETH: ${this.stats.ethCurrent.toFixed(8)} ($${ethValue.toFixed(2)})
  USDT: $${this.stats.usdtBalance.toFixed(2)}
  Total Value: $${totalValue.toFixed(2)}
  
Performance:
  Starting Value: $${this.stats.totalValue.toFixed(2)}
  Current Value: $${totalValue.toFixed(2)}
  Profit/Loss: $${profitUSDT.toFixed(2)} (${profitPercent >= 0 ? '+' : ''}${profitPercent.toFixed(2)}%)
  
ETH Accumulated:
  Started with: ${this.stats.ethStart.toFixed(8)} ETH
  Current: ${this.stats.ethCurrent.toFixed(8)} ETH
  Gained: ${ethGained >= 0 ? '+' : ''}${ethGained.toFixed(8)} ETH (${((ethGained / this.stats.ethStart) * 100).toFixed(2)}%)
  
Trading Stats:
  Total Trades: ${this.stats.totalTrades}
  Successful: ${this.stats.successfulTrades}
  Failed: ${this.stats.failedTrades}
  Success Rate: ${this.stats.totalTrades > 0 ? ((this.stats.successfulTrades / this.stats.totalTrades) * 100).toFixed(1) : 0}%
    `);
  }
}

async function main() {
  const trader = new ETHTrader();
  
  try {
    await trader.initialize();
    
    const MAX_ITERATIONS = Number(process.env.MAX_STEPS || 200);
    const LOG_INTERVAL = Number(process.env.LOG_INTERVAL || 20);
    const TRADE_DELAY = 5000; // 5 seconds between checks
    
    for (let i = 0; i < MAX_ITERATIONS; i++) {
      await trader.executeTrade();
      
      if ((i + 1) % LOG_INTERVAL === 0) {
        trader.printStatus();
      }
      
      // Wait before next trade check
      await new Promise(r => setTimeout(r, TRADE_DELAY));
    }
    
    console.log(`\n✅ Trading session complete!`);
    trader.printStatus();
    
  } catch (err) {
    log('error', '❌ Fatal error', err);
    process.exit(1);
  }
}

main();
