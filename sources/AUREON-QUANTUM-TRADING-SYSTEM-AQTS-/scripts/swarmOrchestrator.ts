#!/usr/bin/env node
/**
 * 🌟 SWARM ORCHESTRATOR: Coordinated Multi-Agent Trading
 * 
 * Hierarchy & Coordination:
 * - 🐝 Bees (Queen-Hive): Provide capital pool, spawn new agents
 * - 🐜 ArmyAnts: Forage small USDT profits, deposit back to capital pool
 * - 🐺 LoneWolf: Scout market for high-momentum opportunities, signal direction
 * - 🐦 Hummingbird: Execute ETH rotations based on wolf's signals
 * 
 * Flow:
 * 1. Bees maintain capital pool and allocate to ants
 * 2. Ants execute small rotations, return profits to pool
 * 3. Wolf analyzes market momentum, broadcasts signals
 * 4. Hummingbird listens to wolf signals and executes larger ETH trades
 * 5. All profits flow back to bee hive for compounding
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

interface CapitalPool {
  totalETH: number;
  totalUSDT: number;
  totalValueUSD: number;
  allocated: { agent: string; amount: number; asset: string }[];
}

interface MarketSignal {
  symbol: string;
  direction: 'BUY' | 'SELL';
  strength: number; // 0-1
  momentum: number; // % change
  timestamp: number;
}

class SwarmOrchestrator {
  private client: BinanceClient;
  private capitalPool: CapitalPool = { totalETH: 0, totalUSDT: 0, totalValueUSD: 0, allocated: [] };
  private latestSignal: MarketSignal | null = null;
  private stats = { 
    beeCapital: 0, 
    antProfits: 0, 
    wolfSignals: 0, 
    hummingbirdTrades: 0,
    totalProfits: 0,
    cyclesCompleted: 0
  };

  constructor() {
    const apiKey = process.env.BINANCE_API_KEY!;
    const apiSecret = process.env.BINANCE_API_SECRET!;
    this.client = new BinanceClient({ 
      apiKey, 
      apiSecret, 
      testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") 
    });
  }

  private roundDown(v: number, d: number) {
    const p = Math.pow(10, d);
    return Math.floor(v * p) / p;
  }

  private async getBalance(asset: string): Promise<number> {
    const acct = await this.client.getAccount();
    return Number(acct.balances.find(b => b.asset === asset)?.free || 0);
  }

  async initializeBeeHive(): Promise<void> {
    console.log('🐝 Initializing Bee Hive (Capital Pool)...');
    const eth = await this.getBalance('ETH');
    const usdt = await this.getBalance('USDT');
    const ethPrice = await this.client.getPrice('ETHUSDT');
    
    this.capitalPool.totalETH = eth;
    this.capitalPool.totalUSDT = usdt;
    this.capitalPool.totalValueUSD = (eth * ethPrice) + usdt;
    this.stats.beeCapital = this.capitalPool.totalValueUSD;

    console.log(`🐝 Hive initialized: ${eth.toFixed(8)} ETH + $${usdt.toFixed(2)} USDT = $${this.capitalPool.totalValueUSD.toFixed(2)}`);
  }

  async wolfScout(): Promise<MarketSignal | null> {
    console.log('\n🐺 Wolf scouting for opportunities...');
    const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT'];
    
    let best: { symbol: string; momentum: number; strength: number } | null = null;

    for (const symbol of symbols) {
      try {
        const stats = await this.client.get24hStats(symbol);
        const momentum = Number(stats.priceChangePercent);
        const volume = Number(stats.quoteAssetVolume);
        const strength = Math.min(1, Math.abs(momentum) / 10) * Math.log10(1 + volume / 1e9);

        if (!best || strength > best.strength) {
          best = { symbol, momentum, strength };
        }
      } catch (e) {
        // skip
      }
    }

    if (!best) return null;

    const signal: MarketSignal = {
      symbol: best.symbol,
      direction: best.momentum > 0 ? 'BUY' : 'SELL',
      strength: best.strength,
      momentum: best.momentum,
      timestamp: Date.now()
    };

    this.latestSignal = signal;
    this.stats.wolfSignals++;
    console.log(`🐺 Signal: ${signal.direction} ${signal.symbol} (momentum: ${signal.momentum.toFixed(2)}%, strength: ${signal.strength.toFixed(2)})`);
    return signal;
  }

  async antForage(): Promise<number> {
    console.log('\n🐜 Ants foraging for small profits...');
    const DRY_RUN = process.env.DRY_RUN === 'true';
    
    // Check if we have enough capital to allocate to ants
    const ethPrice = await this.client.getPrice('ETHUSDT');
    const availableUSD = this.capitalPool.totalValueUSD;
    
    if (availableUSD < 11) {
      console.log('🐜 Not enough capital for ant foraging (need $11+)');
      return 0;
    }

    // Allocate small amount to ants
    const allocateUSDT = Math.min(11, this.capitalPool.totalUSDT * 0.3);
    const allocateETH = allocateUSDT > 10 ? 0 : Math.min(0.004, this.capitalPool.totalETH * 0.3);
    
    if (allocateUSDT < 10 && allocateETH * ethPrice < 10) {
      console.log('🐜 Insufficient allocation for ant foraging');
      return 0;
    }

    // Simulate a quick USDT rotation
    const symbol = 'ADAUSDT';
    const spendUSDT = allocateUSDT > 10 ? allocateUSDT : 11;

    if (DRY_RUN) {
      console.log(`🐜 DRY_RUN: Would forage with $${spendUSDT.toFixed(2)} on ${symbol}`);
      const simulatedProfit = spendUSDT * (Math.random() * 0.02 - 0.005); // -0.5% to +1.5%
      this.stats.antProfits += simulatedProfit;
      return simulatedProfit;
    }

    try {
      const price = await this.client.getPrice(symbol);
      const buy = await this.client.placeOrder({ 
        symbol, 
        side: 'BUY', 
        type: 'MARKET', 
        quoteOrderQty: spendUSDT,
        quantity: 0
      });
      
      const qty = Number(buy.executedQty);
      const avgPrice = Number(buy.cummulativeQuoteQty) / qty;
      console.log(`🐜 Bought ${qty} ${symbol.replace('USDT','')} @ $${avgPrice.toFixed(6)}`);

      // Wait a bit and sell for quick profit
      await sleep(3000);
      const currentPrice = await this.client.getPrice(symbol);
      const sellQty = this.roundDown(qty * 0.99, 6);
      
      const sell = await this.client.placeOrder({
        symbol,
        side: 'SELL',
        type: 'MARKET',
        quantity: sellQty
      });

      const profit = Number(sell.cummulativeQuoteQty) - spendUSDT;
      this.stats.antProfits += profit;
      console.log(`🐜 Sold back, profit: $${profit.toFixed(4)}`);
      return profit;
    } catch (e: any) {
      console.log(`🐜 Foraging failed: ${e.message}`);
      return 0;
    }
  }

  async hummingbirdExecute(signal: MarketSignal | null): Promise<number> {
    if (!signal) {
      console.log('\n🐦 Hummingbird: No signal from wolf, skipping');
      return 0;
    }

    console.log(`\n🐦 Hummingbird executing based on wolf signal: ${signal.direction} ${signal.symbol}`);
    const DRY_RUN = process.env.DRY_RUN === 'true';

    // Check if we have enough ETH capital
    const ethPrice = await this.client.getPrice('ETHUSDT');
    const availableETH = this.capitalPool.totalETH;
    
    if (availableETH * ethPrice < 10) {
      console.log('🐦 Not enough ETH capital for hummingbird (need $10+)');
      return 0;
    }

    const spendETH = this.roundDown(Math.min(availableETH * 0.4, 0.01), 6);
    
    if (DRY_RUN) {
      console.log(`🐦 DRY_RUN: Would execute ${signal.direction} with ${spendETH} ETH on ETH-quoted pairs`);
      const simulatedProfit = spendETH * ethPrice * (Math.random() * 0.03 - 0.01); // -1% to +2%
      this.stats.hummingbirdTrades++;
      return simulatedProfit;
    }

    // For simplicity, trade on ETHUSDT based on signal
    try {
      if (signal.direction === 'SELL' && signal.symbol === 'ETHUSDT') {
        // Sell some ETH
        const sell = await this.client.placeOrder({
          symbol: 'ETHUSDT',
          side: 'SELL',
          type: 'MARKET',
          quantity: spendETH
        });
        console.log(`🐦 Sold ${sell.executedQty} ETH @ $${Number(sell.cummulativeQuoteQty)/Number(sell.executedQty)}`);
        
        // Buy back after a moment
        await sleep(5000);
        const buyback = await this.client.placeOrder({
          symbol: 'ETHUSDT',
          side: 'BUY',
          type: 'MARKET',
          quoteOrderQty: Number(sell.cummulativeQuoteQty) * 0.99,
          quantity: 0
        });
        
        const profit = (Number(buyback.executedQty) - spendETH) * ethPrice;
        this.stats.hummingbirdTrades++;
        console.log(`🐦 Bought back, profit: $${profit.toFixed(4)}`);
        return profit;
      } else {
        console.log(`🐦 Signal not actionable for current strategy`);
        return 0;
      }
    } catch (e: any) {
      console.log(`🐦 Execution failed: ${e.message}`);
      return 0;
    }
  }

  async coordinatedCycle(): Promise<void> {
    console.log('\n' + '='.repeat(70));
    console.log(`🌟 SWARM CYCLE #${this.stats.cyclesCompleted + 1}`);
    console.log('='.repeat(70));

    // 1. Refresh capital pool
    await this.initializeBeeHive();

    // 2. Wolf scouts
    const signal = await this.wolfScout();

    // 3. Ants forage
    const antProfit = await this.antForage();

    // 4. Hummingbird executes based on wolf signal
    const hbProfit = await this.hummingbirdExecute(signal);

    // 5. Update stats
    this.stats.totalProfits += antProfit + hbProfit;
    this.stats.cyclesCompleted++;

    console.log('\n' + '='.repeat(70));
    console.log('📊 SWARM STATS');
    console.log('='.repeat(70));
    console.log(`🐝 Bee Capital: $${this.stats.beeCapital.toFixed(2)}`);
    console.log(`🐜 Ant Profits: $${this.stats.antProfits.toFixed(4)}`);
    console.log(`🐺 Wolf Signals: ${this.stats.wolfSignals}`);
    console.log(`🐦 Hummingbird Trades: ${this.stats.hummingbirdTrades}`);
    console.log(`💰 Total Profits: $${this.stats.totalProfits.toFixed(4)}`);
    console.log(`🔄 Cycles: ${this.stats.cyclesCompleted}`);
    console.log('='.repeat(70) + '\n');
  }

  async run(): Promise<void> {
    const maxCycles = Number(process.env.SWARM_CYCLES || 100);
    const cycleDelay = Number(process.env.SWARM_CYCLE_MS || 30000); // 30s between cycles

    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🌟 SWARM ORCHESTRATOR                                 ║
║         Coordinated Multi-Agent Trading System                ║
╚════════════════════════════════════════════════════════════════╝

Starting ${maxCycles} cycles with ${cycleDelay/1000}s delay...
    `);

    for (let i = 0; i < maxCycles; i++) {
      await this.coordinatedCycle();
      
      if (i < maxCycles - 1) {
        console.log(`⏳ Waiting ${cycleDelay/1000}s before next cycle...\n`);
        await sleep(cycleDelay);
      }
    }

    console.log('\n✅ Swarm orchestration complete!');
  }
}

async function main() {
  if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
    console.error('Safety: Set CONFIRM_LIVE_TRADING=yes');
    process.exit(1);
  }

  const orchestrator = new SwarmOrchestrator();
  await orchestrator.run();
}

main().catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});
