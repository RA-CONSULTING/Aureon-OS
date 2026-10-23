#!/usr/bin/env tsx
/**
 * LIVE SIGNAL DASHBOARD
 * 
 * Real-time market monitoring with BLACK/WHITE key signals
 * Updates every 5 seconds to guide manual trading decisions
 * 
 * Use this alongside the testnet validator to know WHEN to strike
 */
import 'dotenv/config';

interface MarketConditions {
  volatility: number;
  momentum: number;
  spread: number;
  price: number;
  priceChange24h: number;
  volume24h: number;
}

interface Signal {
  system: string;
  color: 'BLACK' | 'WHITE';
  action: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL';
  confidence: number;
  reason: string;
}

async function fetchMarketData(symbol: string): Promise<MarketConditions> {
  try {
    // Price
    const priceResp = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`);
    const priceData = await priceResp.json() as any;
    const price = Number(priceData.price);
    
    // 24h stats
    const statsResp = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`);
    const stats = await statsResp.json() as any;
    
    const high = Number(stats.highPrice);
    const low = Number(stats.lowPrice);
    const volatility = ((high - low) / price) * 100;
    
    const priceChange24h = Number(stats.priceChangePercent);
    const momentum = Math.max(-1, Math.min(1, priceChange24h / 5));
    
    const volume24h = Number(stats.volume);
    
    // Order book
    const obResp = await fetch(`https://api.binance.com/api/v3/depth?symbol=${symbol}&limit=5`);
    const ob = await obResp.json() as any;
    
    const bestBid = Number(ob.bids[0][0]);
    const bestAsk = Number(ob.asks[0][0]);
    const spread = ((bestAsk - bestBid) / price) * 100;
    
    return { volatility, momentum, spread, price, priceChange24h, volume24h };
  } catch (error: any) {
    throw new Error(`Market data fetch failed: ${error.message}`);
  }
}

function generateSignals(conditions: MarketConditions): Signal[] {
  const signals: Signal[] = [];
  
  // BLACK KEY SYSTEMS (Aggressive - High Vol)
  const blackSystems = [
    { name: 'LION', target: 0.78, winPct: 0.007 },
    { name: 'LIGHTHOUSE', target: 0.85, winPct: 0.0065 },
    { name: 'SENTINEL', target: 0.76, winPct: 0.0065 }
  ];
  
  for (const sys of blackSystems) {
    let action: Signal['action'] = 'HOLD';
    let confidence = 0.5;
    let reason = '';
    
    if (conditions.volatility > 1.5 && Math.abs(conditions.momentum) > 0.4) {
      action = conditions.momentum > 0 ? 'STRONG_BUY' : 'STRONG_SELL';
      confidence = 0.85 + Math.min(conditions.volatility / 10, 0.15);
      reason = `⚡ STRIKE NOW - Vol ${conditions.volatility.toFixed(2)}%, Mom ${(conditions.momentum * 100).toFixed(0)}%`;
    } else if (conditions.volatility > 1.0 && Math.abs(conditions.momentum) > 0.2) {
      action = conditions.momentum > 0 ? 'BUY' : 'SELL';
      confidence = 0.65;
      reason = `Ready - Vol ${conditions.volatility.toFixed(2)}%`;
    } else {
      action = 'HOLD';
      confidence = 0.3;
      reason = `Waiting for volatility`;
    }
    
    signals.push({ system: sys.name, color: 'BLACK', action, confidence, reason });
  }
  
  // WHITE KEY SYSTEMS (Conservative - Stable)
  const whiteSystems = [
    { name: 'HIVE', target: 0.82, winPct: 0.006 },
    { name: 'QUANTUM', target: 0.80, winPct: 0.007 }
  ];
  
  for (const sys of whiteSystems) {
    let action: Signal['action'] = 'HOLD';
    let confidence = 0.5;
    let reason = '';
    
    if (conditions.volatility < 0.5 && conditions.spread < 0.05) {
      action = conditions.momentum > 0 ? 'BUY' : 'HOLD';
      confidence = 0.75;
      reason = `Stable conditions, tight spread`;
    } else if (conditions.volatility > 2.0) {
      action = 'HOLD';
      confidence = 0.2;
      reason = `Too volatile - stand down`;
    } else {
      action = 'HOLD';
      confidence = 0.4;
      reason = `Neutral - watching`;
    }
    
    signals.push({ system: sys.name, color: 'WHITE', action, confidence, reason });
  }
  
  return signals;
}

function displayDashboard(symbol: string, conditions: MarketConditions, signals: Signal[]) {
  console.clear();
  
  const timestamp = new Date().toLocaleTimeString();
  
  console.log(`\n${'═'.repeat(90)}`);
  console.log(`🎹 LIVE TRADING SIGNALS - ${symbol} - ${timestamp} 🎹`);
  console.log(`${'═'.repeat(90)}\n`);
  
  // Price & Market
  const priceColor = conditions.priceChange24h > 0 ? '📈' : '📉';
  console.log(`💰 PRICE: $${conditions.price.toFixed(2)} ${priceColor} ${conditions.priceChange24h > 0 ? '+' : ''}${conditions.priceChange24h.toFixed(2)}% (24h)`);
  console.log(`📊 VOLATILITY: ${conditions.volatility.toFixed(2)}% | MOMENTUM: ${(conditions.momentum * 100).toFixed(0)}% | SPREAD: ${(conditions.spread * 100).toFixed(3)}%`);
  console.log(`📦 VOLUME: ${(conditions.volume24h / 1000).toFixed(1)}K BTC\n`);
  
  // Overall Market Bias
  let marketBias = '⚪ NEUTRAL';
  if (conditions.volatility > 1.5 && Math.abs(conditions.momentum) > 0.4) {
    marketBias = conditions.momentum > 0 ? '🟢 STRONG BULLISH - BLACK KEYS ACTIVE' : '🔴 STRONG BEARISH';
  } else if (conditions.volatility < 0.5) {
    marketBias = '⚪ CALM - WHITE KEYS ACTIVE';
  }
  console.log(`🎯 MARKET STATE: ${marketBias}\n`);
  
  console.log(`${'─'.repeat(90)}\n`);
  
  // BLACK KEYS
  const blackSignals = signals.filter(s => s.color === 'BLACK').sort((a, b) => b.confidence - a.confidence);
  console.log(`⚫ BLACK KEYS (Aggressive - Volatility Plays):\n`);
  
  for (const sig of blackSignals) {
    const actionIcon = sig.action.includes('BUY') ? '🚀' : sig.action.includes('SELL') ? '⬇️' : '⏸️';
    const confBar = '█'.repeat(Math.floor(sig.confidence * 20));
    const actionColor = sig.action === 'STRONG_BUY' ? '\x1b[32m' : sig.action === 'BUY' ? '\x1b[33m' : '\x1b[37m';
    const reset = '\x1b[0m';
    
    console.log(`   ${actionIcon} ${actionColor}${sig.system.padEnd(12)}${reset} | ${sig.action.padEnd(12)} | ${confBar} ${(sig.confidence * 100).toFixed(0)}%`);
    console.log(`      └─ ${sig.reason}`);
  }
  
  console.log(`\n⚪ WHITE KEYS (Conservative - Stable Plays):\n`);
  
  const whiteSignals = signals.filter(s => s.color === 'WHITE').sort((a, b) => b.confidence - a.confidence);
  
  for (const sig of whiteSignals) {
    const actionIcon = sig.action.includes('BUY') ? '📈' : sig.action.includes('SELL') ? '📉' : '⏸️';
    const confBar = '█'.repeat(Math.floor(sig.confidence * 20));
    const actionColor = sig.action === 'BUY' ? '\x1b[33m' : '\x1b[37m';
    const reset = '\x1b[0m';
    
    console.log(`   ${actionIcon} ${actionColor}${sig.system.padEnd(12)}${reset} | ${sig.action.padEnd(12)} | ${confBar} ${(sig.confidence * 100).toFixed(0)}%`);
    console.log(`      └─ ${sig.reason}`);
  }
  
  console.log(`\n${'═'.repeat(90)}`);
  
  // Trading Recommendation
  const topSignal = signals.sort((a, b) => b.confidence - a.confidence)[0];
  if (topSignal.confidence > 0.75 && topSignal.action.includes('BUY')) {
    console.log(`\n🎯 RECOMMENDED ACTION: ${topSignal.system} ${topSignal.action} (Confidence: ${(topSignal.confidence * 100).toFixed(0)}%)`);
    console.log(`   ${topSignal.reason}`);
  } else {
    console.log(`\n⏸️  NO STRONG SIGNALS - Continue monitoring`);
  }
  
  console.log(`\n${'═'.repeat(90)}\n`);
  console.log(`Updating in 5 seconds... Press Ctrl+C to stop\n`);
}

async function main() {
  const symbol = process.env.SYMBOL || 'BTCUSDT';
  const updateInterval = Number(process.env.UPDATE_INTERVAL || 5000); // 5 seconds default
  
  console.log(`\n🎹 Starting live signal dashboard for ${symbol}...\n`);
  
  // Continuous monitoring loop
  while (true) {
    try {
      const conditions = await fetchMarketData(symbol);
      const signals = generateSignals(conditions);
      displayDashboard(symbol, conditions, signals);
      
      await new Promise(resolve => setTimeout(resolve, updateInterval));
    } catch (error: any) {
      console.error(`\n❌ Error: ${error.message}`);
      console.log(`Retrying in 10 seconds...\n`);
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
}

main().catch(err => {
  console.error('Dashboard failed:', err);
  process.exit(1);
});
