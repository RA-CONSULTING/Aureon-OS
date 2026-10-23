#!/usr/bin/env node
/**
 * 6-month forecast: All 3 bots working together
 * with 999 trades/day cap distributed between them
 */

interface DailySnapshot {
  day: number;
  capital: number;
  tradesTotal: number;
  hbTrades: number;
  antsTrades: number;
  wolfTrades: number;
  dailyReturn: number;
}

// Bot characteristics
const BOTS = {
  hummingbird: {
    winRate: 0.65,
    avgGain: 0.024,
    avgLoss: 0.015,
    baseTradesPerDay: 4,
    weight: 0.286, // 4/(4+8+2) = proportional to base frequency
  },
  armyAnts: {
    winRate: 0.70,
    avgGain: 0.022,
    avgLoss: 0.015,
    baseTradesPerDay: 8,
    weight: 0.571, // 8/14
  },
  loneWolf: {
    winRate: 0.60,
    avgGain: 0.035,
    avgLoss: 0.020,
    baseTradesPerDay: 2,
    weight: 0.143, // 2/14
  },
};

const START_CAPITAL = 10;
const DAYS = 180; // 6 months
const MAX_TRADES_PER_DAY = 999;

// Distribute trades proportionally
const tradesPerBot = {
  hummingbird: Math.floor(MAX_TRADES_PER_DAY * BOTS.hummingbird.weight),
  armyAnts: Math.floor(MAX_TRADES_PER_DAY * BOTS.armyAnts.weight),
  loneWolf: Math.floor(MAX_TRADES_PER_DAY * BOTS.loneWolf.weight),
};

// Adjust to exactly 999
const totalAllocated = tradesPerBot.hummingbird + tradesPerBot.armyAnts + tradesPerBot.loneWolf;
tradesPerBot.armyAnts += MAX_TRADES_PER_DAY - totalAllocated;

function expectedReturn(bot: typeof BOTS.hummingbird): number {
  return bot.winRate * bot.avgGain + (1 - bot.winRate) * -bot.avgLoss;
}

function simulateTrade(bot: typeof BOTS.hummingbird): number {
  const isWin = Math.random() < bot.winRate;
  const baseReturn = isWin ? bot.avgGain : -bot.avgLoss;
  // Add ±15% variance
  const variance = baseReturn * (Math.random() * 0.3 - 0.15);
  return baseReturn + variance;
}

function formatNumber(num: number): string {
  if (num >= 1e9) return `$${(num / 1e9).toFixed(3)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  return `$${num.toFixed(2)}`;
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🚀  AQTS: 6-MONTH FORECAST (All Bots @ 999 Trades/Day Cap)');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
console.log(`📊 Configuration:`);
console.log(`   Starting Capital: ${formatNumber(START_CAPITAL)}`);
console.log(`   Duration: ${DAYS} days (6 months)`);
console.log(`   Max Trades/Day: ${MAX_TRADES_PER_DAY}`);
console.log('');
console.log(`🤖 Trade Distribution:`);
console.log(`   🕊️  Hummingbird: ${tradesPerBot.hummingbird}/day (${(BOTS.hummingbird.weight * 100).toFixed(1)}%)`);
console.log(`      Win: ${(BOTS.hummingbird.winRate * 100).toFixed(0)}% | Gain: ${(BOTS.hummingbird.avgGain * 100).toFixed(1)}% | Loss: ${(BOTS.hummingbird.avgLoss * 100).toFixed(1)}%`);
console.log(`      Expected Return/Trade: ${(expectedReturn(BOTS.hummingbird) * 100).toFixed(3)}%`);
console.log(`   🐜 ArmyAnts: ${tradesPerBot.armyAnts}/day (${(BOTS.armyAnts.weight * 100).toFixed(1)}%)`);
console.log(`      Win: ${(BOTS.armyAnts.winRate * 100).toFixed(0)}% | Gain: ${(BOTS.armyAnts.avgGain * 100).toFixed(1)}% | Loss: ${(BOTS.armyAnts.avgLoss * 100).toFixed(1)}%`);
console.log(`      Expected Return/Trade: ${(expectedReturn(BOTS.armyAnts) * 100).toFixed(3)}%`);
console.log(`   🐺 LoneWolf: ${tradesPerBot.loneWolf}/day (${(BOTS.loneWolf.weight * 100).toFixed(1)}%)`);
console.log(`      Win: ${(BOTS.loneWolf.winRate * 100).toFixed(0)}% | Gain: ${(BOTS.loneWolf.avgGain * 100).toFixed(1)}% | Loss: ${(BOTS.loneWolf.avgLoss * 100).toFixed(1)}%`);
console.log(`      Expected Return/Trade: ${(expectedReturn(BOTS.loneWolf) * 100).toFixed(3)}%`);
console.log('');

// Monte Carlo simulation
const SIMULATIONS = 50;
const allResults: DailySnapshot[][] = [];

for (let sim = 0; sim < SIMULATIONS; sim++) {
  let capital = START_CAPITAL;
  let totalTrades = 0;
  const snapshots: DailySnapshot[] = [];

  for (let day = 1; day <= DAYS; day++) {
    const startDayCapital = capital;
    let hbTrades = 0;
    let antsTrades = 0;
    let wolfTrades = 0;

    // Hummingbird trades
    for (let i = 0; i < tradesPerBot.hummingbird; i++) {
      const tradeReturn = simulateTrade(BOTS.hummingbird);
      capital *= 1 + tradeReturn;
      hbTrades++;
      totalTrades++;
    }

    // ArmyAnts trades
    for (let i = 0; i < tradesPerBot.armyAnts; i++) {
      const tradeReturn = simulateTrade(BOTS.armyAnts);
      capital *= 1 + tradeReturn;
      antsTrades++;
      totalTrades++;
    }

    // LoneWolf trades
    for (let i = 0; i < tradesPerBot.loneWolf; i++) {
      const tradeReturn = simulateTrade(BOTS.loneWolf);
      capital *= 1 + tradeReturn;
      wolfTrades++;
      totalTrades++;
    }

    const dailyReturn = (capital - startDayCapital) / startDayCapital;

    snapshots.push({
      day,
      capital,
      tradesTotal: totalTrades,
      hbTrades,
      antsTrades,
      wolfTrades,
      dailyReturn,
    });

    if (capital <= 0) break; // Blown up
  }

  allResults.push(snapshots);
}

// Calculate statistics
function getStats(day: number) {
  const dayCapitals = allResults
    .map((r) => r[day - 1]?.capital || 0)
    .filter((c) => c > 0)
    .sort((a, b) => a - b);

  if (dayCapitals.length === 0) return null;

  return {
    min: dayCapitals[0],
    q25: dayCapitals[Math.floor(dayCapitals.length * 0.25)],
    median: dayCapitals[Math.floor(dayCapitals.length * 0.5)],
    q75: dayCapitals[Math.floor(dayCapitals.length * 0.75)],
    max: dayCapitals[dayCapitals.length - 1],
    avg: dayCapitals.reduce((sum, c) => sum + c, 0) / dayCapitals.length,
    successRate: dayCapitals.length / SIMULATIONS,
  };
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('📈  GROWTH PROJECTIONS (Monte Carlo, 50 simulations)');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');

const milestones = [7, 14, 30, 60, 90, 120, 150, 180];

console.log('Day  |  Min     |  25th %ile |  Median  |  75th %ile |  Max     |  Avg     | Success');
console.log('─────┼──────────┼────────────┼──────────┼────────────┼──────────┼──────────┼────────');

for (const day of milestones) {
  const stats = getStats(day);
  if (!stats) {
    console.log(`${day.toString().padStart(3)}  | BLOWN UP - All simulations failed`);
    continue;
  }

  const successPct = (stats.successRate * 100).toFixed(0);
  console.log(
    `${day.toString().padStart(3)}  | ` +
      `${formatNumber(stats.min).padEnd(8)} | ` +
      `${formatNumber(stats.q25).padEnd(10)} | ` +
      `${formatNumber(stats.median).padEnd(8)} | ` +
      `${formatNumber(stats.q75).padEnd(10)} | ` +
      `${formatNumber(stats.max).padEnd(8)} | ` +
      `${formatNumber(stats.avg).padEnd(8)} | ` +
      `${successPct.padStart(3)}%`
  );
}

console.log('');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🎯  6-MONTH FINAL RESULTS');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

const finalStats = getStats(180);
if (finalStats) {
  console.log('');
  console.log(`   Success Rate: ${(finalStats.successRate * 100).toFixed(0)}% (${Math.round(finalStats.successRate * SIMULATIONS)}/${SIMULATIONS} simulations)`);
  console.log(`   Median Outcome: ${formatNumber(finalStats.median)}`);
  console.log(`   Average Outcome: ${formatNumber(finalStats.avg)}`);
  console.log(`   Best Case: ${formatNumber(finalStats.max)}`);
  console.log(`   Worst Case: ${formatNumber(finalStats.min)}`);
  console.log(`   Total Trades: ${(MAX_TRADES_PER_DAY * 180).toLocaleString()}`);
  console.log('');
  console.log(`   📊 ROI Analysis:`);
  const medianROI = ((finalStats.median - START_CAPITAL) / START_CAPITAL) * 100;
  const avgROI = ((finalStats.avg - START_CAPITAL) / START_CAPITAL) * 100;
  console.log(`      Median ROI: ${medianROI.toFixed(0)}%`);
  console.log(`      Average ROI: ${avgROI.toFixed(0)}%`);
  console.log(`      Median Multiple: ${(finalStats.median / START_CAPITAL).toFixed(1)}x`);
  console.log(`      Average Multiple: ${(finalStats.avg / START_CAPITAL).toFixed(1)}x`);
  
  // Time to milestones
  console.log('');
  console.log(`   🏁 Time to Milestones (median outcome):`);
  const targets = [100, 1000, 10000, 100000, 1000000, 10000000];
  for (const target of targets) {
    if (finalStats.median < target) break;
    
    // Find day when median crosses target
    let crossDay = 0;
    for (let d = 1; d <= 180; d++) {
      const dayStats = getStats(d);
      if (dayStats && dayStats.median >= target) {
        crossDay = d;
        break;
      }
    }
    
    if (crossDay > 0) {
      console.log(`      ${formatNumber(target).padEnd(9)} → Day ${crossDay.toString().padStart(3)} (${Math.floor(crossDay / 30)}m ${crossDay % 30}d)`);
    }
  }
} else {
  console.log('\n   ⚠️  All simulations resulted in account blow-up');
}

console.log('');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('⚠️  IMPORTANT NOTES:');
console.log('   • 999 trades/day assumes 24/7 operation with <90 sec/trade avg');
console.log('   • Real execution will face API rate limits, network latency');
console.log('   • Exchange liquidity may constrain larger position sizes');
console.log('   • Slippage increases with order frequency and size');
console.log('   • These projections assume perfect market conditions');
console.log('   • Past performance ≠ future results');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
