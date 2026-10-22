#!/usr/bin/env node
/**
 * Calculate time to $1 billion from $10 starting capital
 * for each AQTS bot strategy with realistic compounding
 */

interface BotStrategy {
  name: string;
  avgWinRate: number;
  avgGainPerTrade: number; // percentage (e.g., 0.02 = 2%)
  avgLossPerTrade: number; // percentage
  tradesPerDay: number;
  description: string;
}

const strategies: BotStrategy[] = [
  {
    name: 'Hummingbird',
    avgWinRate: 0.65, // 65% win rate (ETH-quoted rotations)
    avgGainPerTrade: 0.024, // 2.4% avg gain (TP/SL 2.4:1 ratio)
    avgLossPerTrade: 0.015, // 1.5% avg loss
    tradesPerDay: 4, // ~6hr rotations
    description: 'ETH-quoted rotations with TP/SL',
  },
  {
    name: 'ArmyAnts',
    avgWinRate: 0.70, // 70% win rate (small USDT alts)
    avgGainPerTrade: 0.022, // 2.2% avg gain
    avgLossPerTrade: 0.015, // 1.5% avg loss
    tradesPerDay: 8, // ~3hr rotations
    description: 'USDT alt rotations, high frequency',
  },
  {
    name: 'LoneWolf',
    avgWinRate: 0.60, // 60% win rate (momentum snipe)
    avgGainPerTrade: 0.035, // 3.5% avg gain (higher risk/reward)
    avgLossPerTrade: 0.020, // 2.0% avg loss
    tradesPerDay: 2, // 1-2 daily opportunities
    description: 'Momentum sniper, single trades',
  },
  {
    name: 'Portfolio (All 3)',
    avgWinRate: 0.67, // weighted average
    avgGainPerTrade: 0.026, // blended
    avgLossPerTrade: 0.016, // blended
    tradesPerDay: 14, // combined
    description: 'All bots running simultaneously',
  },
];

function calculateExpectedReturn(strategy: BotStrategy): number {
  // Expected value per trade
  const winValue = strategy.avgWinRate * strategy.avgGainPerTrade;
  const lossValue = (1 - strategy.avgWinRate) * -strategy.avgLossPerTrade;
  return winValue + lossValue;
}

function simulateToTarget(
  startCapital: number,
  targetCapital: number,
  strategy: BotStrategy,
  maxYears: number = 10
): { days: number; finalCapital: number; trades: number; breachedTarget: boolean } {
  let capital = startCapital;
  let day = 0;
  let totalTrades = 0;
  const maxDays = maxYears * 365;
  const expectedReturn = calculateExpectedReturn(strategy);

  while (capital < targetCapital && day < maxDays) {
    // Daily compounding with expected return per trade
    for (let i = 0; i < strategy.tradesPerDay; i++) {
      // Simulate win/loss with some variance
      const isWin = Math.random() < strategy.avgWinRate;
      const tradeReturn = isWin ? strategy.avgGainPerTrade : -strategy.avgLossPerTrade;
      
      // Add realistic variance (±20% of base return)
      const variance = tradeReturn * (Math.random() * 0.4 - 0.2);
      const actualReturn = tradeReturn + variance;
      
      capital *= 1 + actualReturn;
      totalTrades++;

      if (capital >= targetCapital) break;
      if (capital <= 0) {
        console.log(`⚠️  ${strategy.name} blew up on day ${day}, trade ${totalTrades}`);
        return { days: day, finalCapital: 0, trades: totalTrades, breachedTarget: false };
      }
    }
    day++;
  }

  return {
    days: day,
    finalCapital: capital,
    trades: totalTrades,
    breachedTarget: capital >= targetCapital,
  };
}

function deterministicCalculation(
  startCapital: number,
  targetCapital: number,
  strategy: BotStrategy
): { days: number; finalCapital: number; trades: number } {
  const expectedReturn = calculateExpectedReturn(strategy);
  const dailyReturn = Math.pow(1 + expectedReturn, strategy.tradesPerDay);
  
  // Solve: startCapital * dailyReturn^days = targetCapital
  const days = Math.log(targetCapital / startCapital) / Math.log(dailyReturn);
  const trades = Math.ceil(days * strategy.tradesPerDay);
  const finalCapital = startCapital * Math.pow(dailyReturn, days);

  return { days: Math.ceil(days), finalCapital, trades };
}

function formatNumber(num: number): string {
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  return `$${num.toFixed(2)}`;
}

function formatDuration(days: number): string {
  const years = Math.floor(days / 365);
  const months = Math.floor((days % 365) / 30);
  const remainingDays = days % 30;
  
  const parts: string[] = [];
  if (years > 0) parts.push(`${years}y`);
  if (months > 0) parts.push(`${months}m`);
  if (remainingDays > 0 || parts.length === 0) parts.push(`${remainingDays}d`);
  
  return parts.join(' ');
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🚀  AQTS: $10 → $1 BILLION PROJECTION');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');

const START_CAPITAL = 10;
const TARGET_CAPITAL = 1_000_000_000; // $1 billion
const SIMULATIONS = 100;

for (const strategy of strategies) {
  console.log(`\n📊 ${strategy.name.toUpperCase()}`);
  console.log(`   ${strategy.description}`);
  console.log(`   Win Rate: ${(strategy.avgWinRate * 100).toFixed(0)}% | Avg Gain: ${(strategy.avgGainPerTrade * 100).toFixed(1)}% | Avg Loss: ${(strategy.avgLossPerTrade * 100).toFixed(1)}%`);
  console.log(`   Trades/Day: ${strategy.tradesPerDay}`);
  
  const expectedReturn = calculateExpectedReturn(strategy);
  console.log(`   Expected Return/Trade: ${(expectedReturn * 100).toFixed(3)}%`);
  
  // Deterministic calculation
  const det = deterministicCalculation(START_CAPITAL, TARGET_CAPITAL, strategy);
  console.log(`\n   📈 Deterministic (perfect avg):`);
  console.log(`      Time: ${formatDuration(det.days)} (${det.days.toLocaleString()} days)`);
  console.log(`      Trades: ${det.trades.toLocaleString()}`);
  console.log(`      Final: ${formatNumber(det.finalCapital)}`);
  
  // Monte Carlo simulations
  console.log(`\n   🎲 Monte Carlo (${SIMULATIONS} sims with variance):`);
  const results = [];
  let successCount = 0;
  
  for (let i = 0; i < SIMULATIONS; i++) {
    const result = simulateToTarget(START_CAPITAL, TARGET_CAPITAL, strategy, 10);
    if (result.breachedTarget) {
      results.push(result);
      successCount++;
    }
  }
  
  if (results.length > 0) {
    results.sort((a, b) => a.days - b.days);
    const median = results[Math.floor(results.length / 2)];
    const fastest = results[0];
    const slowest = results[results.length - 1];
    const avgDays = results.reduce((sum, r) => sum + r.days, 0) / results.length;
    
    console.log(`      Success Rate: ${(successCount / SIMULATIONS * 100).toFixed(0)}%`);
    console.log(`      Fastest: ${formatDuration(fastest.days)} (${fastest.days.toLocaleString()} days)`);
    console.log(`      Median: ${formatDuration(median.days)} (${median.days.toLocaleString()} days)`);
    console.log(`      Average: ${formatDuration(Math.round(avgDays))} (${Math.round(avgDays).toLocaleString()} days)`);
    console.log(`      Slowest: ${formatDuration(slowest.days)} (${slowest.days.toLocaleString()} days)`);
  } else {
    console.log(`      ⚠️  No successful runs in ${SIMULATIONS} simulations (high risk of ruin)`);
  }
  
  // Milestones
  console.log(`\n   🎯 Milestones (deterministic):`);
  const milestones = [100, 1000, 10_000, 100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000];
  for (const target of milestones) {
    if (target > START_CAPITAL) {
      const ms = deterministicCalculation(START_CAPITAL, target, strategy);
      console.log(`      ${formatNumber(target).padEnd(8)} → ${formatDuration(ms.days).padEnd(12)} (${ms.trades.toLocaleString()} trades)`);
    }
  }
}

console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('⚠️  REALITY CHECK:');
console.log('   • Assumes perfect compounding (no withdrawals)');
console.log('   • Ignores exchange limits, slippage, liquidity constraints');
console.log('   • Real performance will vary significantly');
console.log('   • Past results ≠ future performance');
console.log('   • Risk of ruin is real; proper risk management essential');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
