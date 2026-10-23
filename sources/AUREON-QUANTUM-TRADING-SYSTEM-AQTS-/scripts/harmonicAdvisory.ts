#!/usr/bin/env tsx
/**
 * HARMONIC ADVISORY - THE BLACK & WHITE KEYS
 * 
 * Paper trades on testnet while live systems (LION, HIVE, LIGHTHOUSE, etc.)
 * provide real-time guidance on when to strike.
 * 
 * Black Keys = Aggressive entries (momentum detected)
 * White Keys = Conservative holds (consolidation)
 * 
 * Generals & Lions run decision engines in parallel,
 * advising when conditions are optimal for each system.
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

// System definitions
interface TradingSystem {
  name: string;
  winRateTarget: number;
  posBase: number;
  winPct: number;
  lossPct: number;
  color: 'BLACK' | 'WHITE'; // Aggressive vs Conservative
}

const SYSTEMS: TradingSystem[] = [
  { name: 'LION', winRateTarget: 0.78, posBase: 0.75, winPct: 0.007, lossPct: 0.006, color: 'BLACK' },
  { name: 'HIVE', winRateTarget: 0.82, posBase: 0.70, winPct: 0.006, lossPct: 0.005, color: 'WHITE' },
  { name: 'LIGHTHOUSE', winRateTarget: 0.85, posBase: 0.80, winPct: 0.0065, lossPct: 0.0055, color: 'BLACK' },
  { name: 'QUANTUM', winRateTarget: 0.80, posBase: 0.72, winPct: 0.0070, lossPct: 0.0060, color: 'WHITE' },
  { name: 'SENTINEL', winRateTarget: 0.76, posBase: 0.68, winPct: 0.0065, lossPct: 0.0055, color: 'BLACK' }
];

interface MarketConditions {
  volatility: number; // Recent price volatility %
  momentum: number; // Directional bias -1 to +1
  spread: number; // Bid-ask spread %
  volume: number; // Recent volume spike factor
}

interface Advisory {
  system: TradingSystem;
  signal: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL';
  confidence: number; // 0-1
  reason: string;
}

interface HarmonicState {
  systemWeights: Map<string, number>;
  recentPerformance: Map<string, number[]>;
  equity: number;
  startEquity: number;
  trades: number;
  systemStats: Map<string, { trades: number; wins: number; pnl: number }>;
  advisories: Advisory[];
}

async function analyzeMarketConditions(
  client: BinanceClient,
  symbol: string
): Promise<MarketConditions> {
  try {
    // Get recent price data (use public endpoints)
    const currentPrice = await client.getPrice(symbol);
    
    // Get 24h stats (public)
    const url = `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`;
    const response = await fetch(url);
    const stats24h = await response.json() as any;
    
    const high = Number(stats24h.highPrice);
    const low = Number(stats24h.lowPrice);
    const volatility = ((high - low) / currentPrice) * 100;
    
    const priceChange = Number(stats24h.priceChangePercent);
    const momentum = Math.max(-1, Math.min(1, priceChange / 5)); // Normalize to -1 to +1
    
    // Get order book (public)
    const obUrl = `https://api.binance.com/api/v3/depth?symbol=${symbol}&limit=5`;
    const obResponse = await fetch(obUrl);
    const orderBook = await obResponse.json() as any;
    
    const bestBid = Number(orderBook.bids[0][0]);
    const bestAsk = Number(orderBook.asks[0][0]);
    const spread = ((bestAsk - bestBid) / currentPrice) * 100;
    
    const volume = 1.0; // Placeholder
    
    return { volatility, momentum, spread, volume };
  } catch (error: any) {
    console.error(`⚠️  Market analysis error: ${error.message}`);
    // Return neutral conditions on error
    return { volatility: 0.5, momentum: 0, spread: 0.05, volume: 1.0 };
  }
}

function generateAdvisories(
  systems: TradingSystem[],
  conditions: MarketConditions,
  state: HarmonicState
): Advisory[] {
  const advisories: Advisory[] = [];
  
  for (const system of systems) {
    let signal: Advisory['signal'] = 'HOLD';
    let confidence = 0.5;
    let reason = '';
    
    // Black key systems prefer high volatility + momentum
    if (system.color === 'BLACK') {
      if (conditions.volatility > 1.0 && Math.abs(conditions.momentum) > 0.3) {
        signal = conditions.momentum > 0 ? 'STRONG_BUY' : 'STRONG_SELL';
        confidence = 0.8 + conditions.volatility / 10;
        reason = `High volatility (${conditions.volatility.toFixed(2)}%) + momentum`;
      } else if (conditions.volatility > 0.5) {
        signal = conditions.momentum > 0 ? 'BUY' : 'SELL';
        confidence = 0.6;
        reason = `Moderate volatility (${conditions.volatility.toFixed(2)}%)`;
      } else {
        signal = 'HOLD';
        confidence = 0.3;
        reason = `Low volatility - BLACK key waiting`;
      }
    }
    
    // White key systems prefer stable conditions
    else {
      if (conditions.volatility < 0.5 && conditions.spread < 0.05) {
        signal = conditions.momentum > 0 ? 'BUY' : 'SELL';
        confidence = 0.75;
        reason = `Stable conditions, tight spread`;
      } else if (conditions.volatility > 1.5) {
        signal = 'HOLD';
        confidence = 0.3;
        reason = `Too volatile for WHITE key`;
      } else {
        signal = conditions.momentum > 0.1 ? 'BUY' : 'HOLD';
        confidence = 0.5;
        reason = `Neutral conditions`;
      }
    }
    
    // Factor in recent system performance
    const recentPerf = state.recentPerformance.get(system.name) || [];
    if (recentPerf.length > 0) {
      const winRate = recentPerf.reduce((s, v) => s + v, 0) / recentPerf.length;
      confidence *= (0.5 + winRate * 0.5); // Boost confidence if system performing well
    }
    
    advisories.push({ system, signal, confidence, reason });
  }
  
  return advisories;
}

function displayAdvisoryDashboard(state: HarmonicState, conditions: MarketConditions) {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`🎹 LIVE MARKET SIGNALS 🎹`);
  console.log(`${'='.repeat(80)}`);
  
  console.log(`\n📊 CONDITIONS: Vol ${conditions.volatility.toFixed(2)}% | Mom ${(conditions.momentum * 100).toFixed(0)}% | Spread ${(conditions.spread * 100).toFixed(3)}%`);
  
  console.log(`\n⚫ BLACK KEYS (Aggressive - High Volatility):`);
  state.advisories
    .filter(a => a.system.color === 'BLACK')
    .sort((a, b) => b.confidence - a.confidence)
    .forEach(adv => {
      const icon = adv.signal.includes('BUY') ? '📈' : adv.signal.includes('SELL') ? '📉' : '⏸️';
      const confBar = '█'.repeat(Math.floor(adv.confidence * 10));
      console.log(`   ${icon} ${adv.system.name.padEnd(12)} | ${adv.signal.padEnd(12)} | Conf: ${confBar.padEnd(10)} ${(adv.confidence * 100).toFixed(0)}%`);
      console.log(`      └─ ${adv.reason}`);
    });
  
  console.log(`\n⚪ WHITE KEYS (Conservative - Stable Conditions):`);
  state.advisories
    .filter(a => a.system.color === 'WHITE')
    .sort((a, b) => b.confidence - a.confidence)
    .forEach(adv => {
      const icon = adv.signal.includes('BUY') ? '📈' : adv.signal.includes('SELL') ? '📉' : '⏸️';
      const confBar = '█'.repeat(Math.floor(adv.confidence * 10));
      console.log(`   ${icon} ${adv.system.name.padEnd(12)} | ${adv.signal.padEnd(12)} | Conf: ${confBar.padEnd(10)} ${(adv.confidence * 100).toFixed(0)}%`);
      console.log(`      └─ ${adv.reason}`);
    });
  
  console.log(`\n💰 PORTFOLIO STATUS:`);
  console.log(`   Equity: $${state.equity.toFixed(2)} | Start: $${state.startEquity.toFixed(2)} | PnL: ${state.equity > state.startEquity ? '+' : ''}$${(state.equity - state.startEquity).toFixed(2)} (${((state.equity / state.startEquity - 1) * 100).toFixed(2)}%)`);
  console.log(`   Trades: ${state.trades}`);
  
  if (state.trades > 0) {
    console.log(`\n📈 SYSTEM PERFORMANCE:`);
    Array.from(state.systemStats.entries())
      .sort((a, b) => b[1].pnl - a[1].pnl)
      .forEach(([name, stats]) => {
        const winRate = stats.trades > 0 ? (stats.wins / stats.trades * 100).toFixed(0) : '0';
        const pnlColor = stats.pnl > 0 ? '+' : '';
        console.log(`   ${name.padEnd(12)}: ${stats.trades} trades | ${winRate}% wins | ${pnlColor}$${stats.pnl.toFixed(2)}`);
      });
  }
  
  console.log(`\n${'='.repeat(80)}\n`);
}

function initializeState(startEquity: number): HarmonicState {
  const weights = new Map<string, number>();
  const equalWeight = 1 / SYSTEMS.length;
  SYSTEMS.forEach(sys => weights.set(sys.name, equalWeight));
  
  return {
    systemWeights: weights,
    recentPerformance: new Map(SYSTEMS.map(s => [s.name, []])),
    equity: startEquity,
    startEquity,
    trades: 0,
    systemStats: new Map(SYSTEMS.map(s => [s.name, { trades: 0, wins: 0, pnl: 0 }])),
    advisories: []
  };
}

function selectSystemFromAdvisories(advisories: Advisory[]): TradingSystem {
  // Weight selection by confidence and signal strength
  const buyAdvisories = advisories.filter(a => 
    a.signal === 'STRONG_BUY' || a.signal === 'BUY'
  );
  
  if (buyAdvisories.length === 0) {
    // Fallback to any system
    return advisories[Math.floor(Math.random() * advisories.length)].system;
  }
  
  // Select weighted by confidence
  const totalConf = buyAdvisories.reduce((s, a) => s + a.confidence, 0);
  let rand = Math.random() * totalConf;
  
  for (const adv of buyAdvisories) {
    rand -= adv.confidence;
    if (rand <= 0) return adv.system;
  }
  
  return buyAdvisories[0].system;
}

async function executePaperTrade(
  client: BinanceClient,
  symbol: string,
  system: TradingSystem,
  state: HarmonicState,
  conditions: MarketConditions
): Promise<{ success: boolean; pnl: number }> {
  try {
    const price = await client.getPrice(symbol);
    
    // Calculate position (paper trade - no actual execution)
    const positionValue = state.equity * system.posBase;
    const quantity = positionValue / price;
    
    console.log(`\n🎯 PAPER TRADE (${system.color} KEY)`);
    console.log(`   System: ${system.name} | Entry: $${price.toFixed(2)} | Size: $${positionValue.toFixed(2)}`);
    
    // Simulate holding period (3-10 seconds)
    const holdTime = 3000 + Math.random() * 7000;
    // FULL SPEED MODE - instant execution, no delays
    const exitPrice = await client.getPrice(symbol);
    const actualHoldTime = holdTime; // Track for stats but don't wait
    const priceChange = (exitPrice - price) / price;
    
    // Determine outcome
    let success = false;
    let event = 'TIME';
    
    if (priceChange >= system.winPct) {
      success = true;
      event = 'TARGET';
    } else if (priceChange <= -system.lossPct) {
      success = false;
      event = 'STOP';
    } else {
      success = priceChange > 0;
      event = 'TIME';
    }
    
    // Calculate PnL (with simulated fees)
    const grossPnL = (exitPrice - price) * quantity;
    const fees = positionValue * 0.002; // 0.2% total (0.1% each side)
    const netPnL = grossPnL - fees;
    
    const icon = success ? '✅' : '❌';
    console.log(`   ${icon} ${event} | Δ: ${(priceChange * 100).toFixed(3)}% | Net: $${netPnL.toFixed(4)}`);
    
    return { success, pnl: netPnL };
    
  } catch (error: any) {
    console.error(`   ❌ Paper trade failed:`, error.message);
    return { success: false, pnl: 0 };
  }
}

async function main() {
  const bullets = Number(process.env.BULLETS ?? 100); // Default to 100 rapid-fire trades
  const symbol = process.env.SYMBOL || 'BTCUSDT';
  const lookbackWindow = Number(process.env.LOOKBACK_WINDOW ?? 10);
  const advisoryInterval = Number(process.env.ADVISORY_INTERVAL ?? 10); // Update advisory every N trades
  
  console.log(`\n🎹 HARMONIC ADVISORY - FULL SPEED DATA COLLECTION 🎹\n`);
  console.log(`"Testnet validates, live signals guide"\n`);
  
  // Always use testnet for paper trading
  const testnet = true;
  
  const apiKey = process.env.BINANCE_TESTNET_API_KEY || process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_TESTNET_API_SECRET || process.env.BINANCE_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    console.error('❌ API credentials required');
    process.exit(1);
  }
  
  const client = new BinanceClient({ apiKey, apiSecret, testnet });
  
  // Start with simulated equity (paper trading doesn't need real balance)
  const startEquity = Number(process.env.SIMULATED_EQUITY || 35.60);
  console.log(`📄 PAPER TRADING MODE - Using simulated balance (no real funds at risk)`);
  
  // Validate API can access market data (public endpoints)
  try {
    await client.getPrice(symbol);
  } catch (error: any) {
    console.error(`❌ Cannot access market data: ${error.message}`);
    console.error(`\nFor paper trading, we only need market data (no account access needed).`);
    console.error(`Check that symbol ${symbol} is valid.`);
    process.exit(1);
  }
  
  console.log(`💰 Starting Paper Equity: $${startEquity.toFixed(2)}`);
  console.log(`📊 Symbol: ${symbol} | Bullets: ${bullets}\n`);
  
  const state = initializeState(startEquity);
  
  // Initial market analysis
  let conditions = await analyzeMarketConditions(client, symbol);
  state.advisories = generateAdvisories(SYSTEMS, conditions, state);
  displayAdvisoryDashboard(state, conditions);
  
  // Trading loop with live advisory
  for (let i = 0; i < bullets; i++) {
    // Update advisories periodically
    if (i % advisoryInterval === 0 && i > 0) {
      conditions = await analyzeMarketConditions(client, symbol);
      state.advisories = generateAdvisories(SYSTEMS, conditions, state);
      displayAdvisoryDashboard(state, conditions);
    }
    
    // Select system based on current advisories
    const system = selectSystemFromAdvisories(state.advisories);
    
    // Execute paper trade
    const result = await executePaperTrade(client, symbol, system, state, conditions);
    
    // Update state
    state.equity += result.pnl;
    state.trades++;
    
    const systemStats = state.systemStats.get(system.name)!;
    systemStats.trades++;
    systemStats.pnl += result.pnl;
    if (result.success) systemStats.wins++;
    
    const recent = state.recentPerformance.get(system.name)!;
    recent.push(result.success ? 1 : 0);
    if (recent.length > lookbackWindow) recent.shift();
    
    // No delay - full speed execution
  }
  
  // Final advisory
  conditions = await analyzeMarketConditions(client, symbol);
  state.advisories = generateAdvisories(SYSTEMS, conditions, state);
  displayAdvisoryDashboard(state, conditions);
  
  console.log(`\n🎵 PAPER TRADING SESSION COMPLETE 🎵\n`);
}

main().catch(err => {
  console.error('Advisory system failed:', err);
  process.exit(1);
});
