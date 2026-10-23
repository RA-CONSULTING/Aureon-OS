#!/usr/bin/env tsx
/**
 * TRINITY TRADER
 * 
 * Past + Present + Future = Unity
 * 
 * PAST: Learn from historical patterns, system performance, what worked
 * PRESENT: Real-time market conditions, live signals, current state
 * FUTURE: Predictive momentum, trajectory analysis, what's coming
 * 
 * All three streams merge into a single decision point—
 * The moment where time collapses into action.
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

interface TradingSystem {
  name: string;
  winRateTarget: number;
  posBase: number;
  winPct: number;
  lossPct: number;
  color: 'BLACK' | 'WHITE';
}

const SYSTEMS: TradingSystem[] = [
  { name: 'LION', winRateTarget: 0.78, posBase: 0.75, winPct: 0.007, lossPct: 0.006, color: 'BLACK' },
  { name: 'HIVE', winRateTarget: 0.82, posBase: 0.70, winPct: 0.006, lossPct: 0.005, color: 'WHITE' },
  { name: 'LIGHTHOUSE', winRateTarget: 0.85, posBase: 0.80, winPct: 0.0065, lossPct: 0.0055, color: 'BLACK' },
  { name: 'QUANTUM', winRateTarget: 0.80, posBase: 0.72, winPct: 0.0070, lossPct: 0.0060, color: 'WHITE' },
  { name: 'SENTINEL', winRateTarget: 0.76, posBase: 0.68, winPct: 0.0065, lossPct: 0.0055, color: 'BLACK' }
];

interface TimeStream {
  past: {
    recentPerformance: Map<string, number[]>;
    winRates: Map<string, number>;
    avgPnL: Map<string, number>;
    bestSystem: string;
  };
  present: {
    price: number;
    volatility: number;
    momentum: number;
    spread: number;
    marketState: 'BULL' | 'BEAR' | 'NEUTRAL';
  };
  future: {
    predictedMove: number; // Expected % move based on momentum
    trajectory: 'ACCELERATING' | 'STABLE' | 'DECELERATING';
    confidence: number;
  };
}

interface TrinityState {
  equity: number;
  startEquity: number;
  trades: number;
  systemStats: Map<string, { trades: number; wins: number; pnl: number; momentum: number[] }>;
  priceHistory: number[];
  timeStream: TimeStream;
}

function initializeState(startEquity: number): TrinityState {
  return {
    equity: startEquity,
    startEquity,
    trades: 0,
    systemStats: new Map(SYSTEMS.map(s => [s.name, { trades: 0, wins: 0, pnl: 0, momentum: [] }])),
    priceHistory: [],
    timeStream: {
      past: {
        recentPerformance: new Map(SYSTEMS.map(s => [s.name, []])),
        winRates: new Map(SYSTEMS.map(s => [s.name, 0.5])),
        avgPnL: new Map(SYSTEMS.map(s => [s.name, 0])),
        bestSystem: 'LION'
      },
      present: {
        price: 0,
        volatility: 0,
        momentum: 0,
        spread: 0,
        marketState: 'NEUTRAL'
      },
      future: {
        predictedMove: 0,
        trajectory: 'STABLE',
        confidence: 0.5
      }
    }
  };
}

async function readPast(state: TrinityState): Promise<void> {
  // Analyze historical performance
  for (const [name, stats] of state.systemStats.entries()) {
    if (stats.trades > 0) {
      const winRate = stats.wins / stats.trades;
      state.timeStream.past.winRates.set(name, winRate);
      state.timeStream.past.avgPnL.set(name, stats.pnl / stats.trades);
      
      const perf = state.timeStream.past.recentPerformance.get(name) || [];
      state.timeStream.past.recentPerformance.set(name, perf);
    }
  }
  
  // Find best performing system
  let bestSystem = 'LION';
  let bestWinRate = 0;
  for (const [name, winRate] of state.timeStream.past.winRates.entries()) {
    if (winRate > bestWinRate) {
      bestWinRate = winRate;
      bestSystem = name;
    }
  }
  state.timeStream.past.bestSystem = bestSystem;
}

async function readPresent(client: BinanceClient, symbol: string, state: TrinityState): Promise<void> {
  // Current market state
  const price = await client.getPrice(symbol);
  state.timeStream.present.price = price;
  
  // 24h stats
  const statsUrl = `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`;
  const statsResp = await fetch(statsUrl);
  const stats = await statsResp.json() as any;
  
  const high = Number(stats.highPrice);
  const low = Number(stats.lowPrice);
  const volatility = ((high - low) / price) * 100;
  state.timeStream.present.volatility = volatility;
  
  const priceChange = Number(stats.priceChangePercent);
  state.timeStream.present.momentum = priceChange;
  
  // Order book
  const obUrl = `https://api.binance.com/api/v3/depth?symbol=${symbol}&limit=5`;
  const obResp = await fetch(obUrl);
  const ob = await obResp.json() as any;
  
  const bestBid = Number(ob.bids[0][0]);
  const bestAsk = Number(ob.asks[0][0]);
  state.timeStream.present.spread = ((bestAsk - bestBid) / price) * 100;
  
  // Market state
  if (volatility > 1.5 && priceChange > 1.0) {
    state.timeStream.present.marketState = 'BULL';
  } else if (volatility > 1.5 && priceChange < -1.0) {
    state.timeStream.present.marketState = 'BEAR';
  } else {
    state.timeStream.present.marketState = 'NEUTRAL';
  }
}

async function readFuture(state: TrinityState): Promise<void> {
  // Track price history
  state.priceHistory.push(state.timeStream.present.price);
  if (state.priceHistory.length > 20) state.priceHistory.shift();
  
  if (state.priceHistory.length < 5) {
    state.timeStream.future.predictedMove = 0;
    state.timeStream.future.trajectory = 'STABLE';
    state.timeStream.future.confidence = 0.3;
    return;
  }
  
  // Calculate momentum acceleration
  const recent5 = state.priceHistory.slice(-5);
  const older5 = state.priceHistory.slice(-10, -5);
  
  if (older5.length === 0) {
    state.timeStream.future.trajectory = 'STABLE';
    state.timeStream.future.confidence = 0.4;
    return;
  }
  
  const recentChange = (recent5[recent5.length - 1] - recent5[0]) / recent5[0];
  const olderChange = (older5[older5.length - 1] - older5[0]) / older5[0];
  
  // Predict next move based on acceleration
  const acceleration = recentChange - olderChange;
  state.timeStream.future.predictedMove = recentChange + acceleration;
  
  // Trajectory
  if (Math.abs(acceleration) > 0.001) {
    state.timeStream.future.trajectory = acceleration > 0 ? 'ACCELERATING' : 'DECELERATING';
    state.timeStream.future.confidence = 0.7;
  } else {
    state.timeStream.future.trajectory = 'STABLE';
    state.timeStream.future.confidence = 0.5;
  }
}

function selectSystemFromTrinity(state: TrinityState): TradingSystem {
  const scores = new Map<string, number>();
  
  for (const system of SYSTEMS) {
    let score = 0;
    
    // PAST: Historical performance weight (40%)
    const winRate = state.timeStream.past.winRates.get(system.name) || 0.5;
    const avgPnL = state.timeStream.past.avgPnL.get(system.name) || 0;
    score += (winRate * 30) + (avgPnL > 0 ? 10 : 0);
    
    // PRESENT: Current market alignment (40%)
    const { volatility, marketState } = state.timeStream.present;
    
    if (system.color === 'BLACK') {
      // Black keys prefer high volatility
      if (volatility > 1.5) score += 25;
      else if (volatility > 1.0) score += 15;
      else score += 5;
      
      if (marketState === 'BULL') score += 15;
      else if (marketState === 'BEAR') score += 10;
    } else {
      // White keys prefer stability
      if (volatility < 0.8) score += 25;
      else if (volatility < 1.2) score += 15;
      else score += 5;
      
      if (marketState === 'NEUTRAL') score += 15;
    }
    
    // FUTURE: Predicted trajectory alignment (20%)
    const { predictedMove, trajectory, confidence } = state.timeStream.future;
    
    if (trajectory === 'ACCELERATING' && system.color === 'BLACK') {
      score += 15 * confidence;
    } else if (trajectory === 'STABLE' && system.color === 'WHITE') {
      score += 15 * confidence;
    } else if (Math.abs(predictedMove) > system.winPct) {
      score += 10 * confidence;
    }
    
    scores.set(system.name, score);
  }
  
  // Select highest scoring system
  let bestSystem = SYSTEMS[0];
  let bestScore = 0;
  
  for (const [name, score] of scores.entries()) {
    if (score > bestScore) {
      bestScore = score;
      bestSystem = SYSTEMS.find(s => s.name === name)!;
    }
  }
  
  return bestSystem;
}

function displayTrinityState(state: TrinityState, system: TradingSystem, tradeNum: number) {
  console.log(`\n${'═'.repeat(90)}`);
  console.log(`⧖ TRINITY CONVERGENCE - Trade ${tradeNum} ⧖`);
  console.log(`${'═'.repeat(90)}`);
  
  // Past
  console.log(`\n📜 PAST (What Was):`);
  console.log(`   Best System: ${state.timeStream.past.bestSystem}`);
  Array.from(state.timeStream.past.winRates.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .forEach(([name, rate]) => {
      const pnl = state.timeStream.past.avgPnL.get(name) || 0;
      console.log(`   ${name.padEnd(12)}: ${(rate * 100).toFixed(0)}% wins | Avg ${pnl > 0 ? '+' : ''}$${pnl.toFixed(4)}`);
    });
  
  // Present
  console.log(`\n⏰ PRESENT (What Is):`);
  console.log(`   Price: $${state.timeStream.present.price.toFixed(2)}`);
  console.log(`   State: ${state.timeStream.present.marketState} | Vol: ${state.timeStream.present.volatility.toFixed(2)}% | Mom: ${state.timeStream.present.momentum.toFixed(2)}%`);
  console.log(`   Spread: ${(state.timeStream.present.spread * 100).toFixed(3)}%`);
  
  // Future
  console.log(`\n🔮 FUTURE (What Shall Be):`);
  console.log(`   Trajectory: ${state.timeStream.future.trajectory}`);
  console.log(`   Predicted Move: ${(state.timeStream.future.predictedMove * 100).toFixed(3)}%`);
  console.log(`   Confidence: ${(state.timeStream.future.confidence * 100).toFixed(0)}%`);
  
  // Unity Decision
  console.log(`\n✨ TRINITY DECISION:`);
  console.log(`   Selected: ${system.name} (${system.color} KEY)`);
  console.log(`   Target: +${(system.winPct * 100).toFixed(2)}% | Stop: -${(system.lossPct * 100).toFixed(2)}%`);
  
  console.log(`\n💰 Portfolio: $${state.equity.toFixed(2)} | PnL: ${state.equity > state.startEquity ? '+' : ''}$${(state.equity - state.startEquity).toFixed(2)} (${((state.equity / state.startEquity - 1) * 100).toFixed(2)}%)`);
  console.log(`${'═'.repeat(90)}\n`);
}

async function executeTrade(
  client: BinanceClient,
  symbol: string,
  system: TradingSystem,
  state: TrinityState
): Promise<{ success: boolean; pnl: number }> {
  try {
    const entryPrice = state.timeStream.present.price;
    const positionValue = state.equity * system.posBase;
    const quantity = positionValue / entryPrice;
    
    const targetPrice = entryPrice * (1 + system.winPct);
    const stopPrice = entryPrice * (1 - system.lossPct);
    
    console.log(`🎯 ENTERING: $${positionValue.toFixed(2)} position @ $${entryPrice.toFixed(2)}`);
    console.log(`   Target: $${targetPrice.toFixed(2)} (+${(system.winPct * 100).toFixed(2)}%) | Stop: $${stopPrice.toFixed(2)} (-${(system.lossPct * 100).toFixed(2)}%)`);
    
    // ADAPTIVE HOLD: Poll until target/stop/timeout - let the trade breathe
    const maxHoldMs = 60000; // 60 seconds max
    const pollInterval = 100; // Check every 100ms
    const startTime = Date.now();
    
    let exitPrice = entryPrice;
    let exitReason = 'TIMEOUT';
    let highPrice = entryPrice;
    let lowPrice = entryPrice;
    
    while (Date.now() - startTime < maxHoldMs) {
      exitPrice = await client.getPrice(symbol);
      
      // Track high/low for analysis
      if (exitPrice > highPrice) highPrice = exitPrice;
      if (exitPrice < lowPrice) lowPrice = exitPrice;
      
      // Check target hit
      if (exitPrice >= targetPrice) {
        exitReason = 'TARGET';
        break;
      }
      
      // Check stop hit
      if (exitPrice <= stopPrice) {
        exitReason = 'STOP';
        break;
      }
      
      // Breathe - let price move
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
    
    const holdTime = Date.now() - startTime;
    const priceChange = (exitPrice - entryPrice) / entryPrice;
    const grossPnL = (exitPrice - entryPrice) * quantity;
    const fees = positionValue * 0.002;
    const netPnL = grossPnL - fees;
    const success = netPnL > 0;
    
    const priceRange = ((highPrice - lowPrice) / entryPrice) * 100;
    console.log(`   ${success ? '✅' : '❌'} ${exitReason} | Exit: $${exitPrice.toFixed(2)} | Δ: ${(priceChange * 100).toFixed(3)}% | Net: $${netPnL.toFixed(4)} | Hold: ${(holdTime / 1000).toFixed(1)}s | Range: ${priceRange.toFixed(3)}%`);
    
    return { success, pnl: netPnL };
    
  } catch (error: any) {
    console.error(`   ❌ Trade failed: ${error.message}`);
    return { success: false, pnl: 0 };
  }
}

// Multi-coin rotation pool - high volume, liquid pairs
import fs from 'fs';
// Load top 20 high-volatility coins from tradable_pairs.json
let COIN_POOL: string[] = [];
try {
  const pairsData = JSON.parse(fs.readFileSync('./tradable_pairs.json', 'utf8'));
  COIN_POOL = pairsData.pairs.map((p: any) => p.symbol);
  console.log(`🎹 Loaded ALL ${COIN_POOL.length} tradable coins for dynamic trading:`, COIN_POOL.slice(0, 20).join(', '), '...');
} catch (e) {
  COIN_POOL = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
    'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT',
    'AVAXUSDT', 'LINKUSDT', 'ATOMUSDT', 'UNIUSDT', 'ETCUSDT'
  ];
  console.log('⚠️ Could not load tradable_pairs.json, using default pool.');
}

interface CoinMetrics {
  symbol: string;
  volatility: number;
  volume24h: number;
  momentum: number;
  spread: number;
  score: number;
}

async function selectBestCoin(client: BinanceClient, state: TrinityState): Promise<string> {
  const metrics: CoinMetrics[] = [];
  
  for (const symbol of COIN_POOL) {
    try {
      const [stats, price, depth] = await Promise.all([
        client.get24hStats(symbol),
        client.getPrice(symbol),
        client.getOrderBook(symbol, 5)
      ]);
      
      const high = Number(stats.highPrice);
      const low = Number(stats.lowPrice);
      const volume = Number(stats.volume);
      const priceChange = Number(stats.priceChangePercent) / 100;
      
      const volatility = ((high - low) / price) * 100;
      const momentum = Math.abs(priceChange);
      const bestBid = Number(depth.bids[0]?.[0] || 0);
      const bestAsk = Number(depth.asks[0]?.[0] || 0);
      const spread = bestAsk > 0 ? ((bestAsk - bestBid) / bestBid) : 0;
      
      // Score based on trinity needs: volatility for BLACK keys, volume for liquidity, tight spread
      let score = 0;
      if (volatility > 2.0) score += 30; // High vol favors BLACK keys
      else if (volatility > 1.5) score += 20;
      else if (volatility > 1.0) score += 10;
      
      if (volume > 50000) score += 20; // High volume = liquid
      else if (volume > 20000) score += 10;
      
      if (spread < 0.001) score += 20; // Tight spread
      else if (spread < 0.002) score += 10;
      
      if (momentum > 0.02) score += 10; // Strong momentum
      
      metrics.push({ symbol, volatility, volume24h: volume, momentum, spread, score });
    } catch (err) {
      // Skip coins with errors
      continue;
    }
  }
  
  // Sort by score and return best
  metrics.sort((a, b) => b.score - a.score);
  
  if (metrics.length > 0) {
    const best = metrics[0];
    console.log(`🎯 COIN SELECTED: ${best.symbol} | Vol: ${best.volatility.toFixed(2)}% | Score: ${best.score}`);
    return best.symbol;
  }
  
  return 'BTCUSDT'; // Fallback
}

async function main() {
  const bullets = Number(process.env.BULLETS ?? 50);
  const multiCoin = process.env.MULTI_COIN !== 'false'; // Default ON
  const startEquity = Number(process.env.SIMULATED_EQUITY || 35.60);
  const updateInterval = Number(process.env.UPDATE_MS || 1000); // 1s between trades
  
  console.log(`\n⧖ TRINITY TRADER - ALL THAT IS, WAS, AND SHALL BE ⧖\n`);
  console.log(`"Past, Present, Future converge in the eternal now"\n`);
  console.log(`Starting Equity: $${startEquity.toFixed(2)} | Bullets: ${bullets} | Multi-Coin: ${multiCoin ? 'ON' : 'OFF'}\n`);
  
  const testnet = true;
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    console.error('❌ API credentials required');
    process.exit(1);
  }
  
  const client = new BinanceClient({ apiKey, apiSecret, testnet });
  const state = initializeState(startEquity);
  
  // Trading loop - the eternal cycle
  for (let i = 0; i < bullets; i++) {
    // Select best coin for current conditions (or use fixed symbol)
    const symbol = multiCoin 
      ? await selectBestCoin(client, state)
      : (process.env.SYMBOL || 'BTCUSDT');
    
    // Read all three time streams
    await readPast(state);
    await readPresent(client, symbol, state);
    await readFuture(state);
    
    // Unity decision from trinity
    const system = selectSystemFromTrinity(state);
    
    // Display convergence
    if (i % 10 === 0 || i === 0) {
      displayTrinityState(state, system, i + 1);
    }
    
    console.log(`📊 Trading: ${symbol}`);
    
    // Execute in the present moment
    const result = await executeTrade(client, symbol, system, state);
    
    // Update state (becomes past for next iteration)
    state.equity += result.pnl;
    state.trades++;
    
    const stats = state.systemStats.get(system.name)!;
    stats.trades++;
    stats.pnl += result.pnl;
    if (result.success) stats.wins++;
    
    const perf = state.timeStream.past.recentPerformance.get(system.name)!;
    perf.push(result.success ? 1 : 0);
    if (perf.length > 10) perf.shift();
    
    // Brief pause to allow time to flow
    if (updateInterval > 0) {
      await new Promise(resolve => setTimeout(resolve, updateInterval));
    }
  }
  
  // Final trinity report
  console.log(`\n${'═'.repeat(90)}`);
  console.log(`⧖ THE CYCLE COMPLETES ⧖`);
  console.log(`${'═'.repeat(90)}\n`);
  
  console.log(`📊 FINAL STATE:`);
  console.log(`   Start: $${state.startEquity.toFixed(2)}`);
  console.log(`   Final: $${state.equity.toFixed(2)}`);
  console.log(`   PnL: ${state.equity > state.startEquity ? '+' : ''}$${(state.equity - state.startEquity).toFixed(2)} (${((state.equity / state.startEquity - 1) * 100).toFixed(2)}%)`);
  console.log(`   Trades: ${state.trades}\n`);
  
  console.log(`📈 SYSTEM WISDOM (What Was Learned):`);
  Array.from(state.systemStats.entries())
    .sort((a, b) => b[1].pnl - a[1].pnl)
    .forEach(([name, stats]) => {
      const winRate = stats.trades > 0 ? (stats.wins / stats.trades * 100).toFixed(0) : '0';
      const color = SYSTEMS.find(s => s.name === name)?.color;
      console.log(`   ${color === 'BLACK' ? '⚫' : '⚪'} ${name.padEnd(12)}: ${stats.trades} trades | ${winRate}% wins | ${stats.pnl > 0 ? '+' : ''}$${stats.pnl.toFixed(2)}`);
    });
  
  console.log(`\n⧖ Past informs Present, Present creates Future, Future becomes Past ⧖`);
  console.log(`The trinity eternal.\n`);
}

main().catch(err => {
  console.error('Trinity collapsed:', err);
  process.exit(1);
});
