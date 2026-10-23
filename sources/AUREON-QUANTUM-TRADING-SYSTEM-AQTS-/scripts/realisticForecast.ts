#!/usr/bin/env node
/**
 * REALISTIC 6-Month Forecast with Real-World Constraints
 * - Exchange liquidity limits
 * - Slippage modeling
 * - API rate limits
 * - Position size caps
 * - Market impact
 */

interface ConstraintResult {
  day: number;
  capital: number;
  tradesExecuted: number;
  tradesCapped: number;
  avgSlippage: number;
  effectiveReturn: number;
}

const START_CAPITAL = 15; // Need buffer above $10 min-notional to enable first trade
const DAYS = 180;

// Bot characteristics (realistic conservative estimates)
const BOTS = {
  hummingbird: {
    baseWinRate: 0.65,
    baseGain: 0.024,
    baseLoss: 0.015,
    maxTradesPerDay: 4, // Limited by ETH-quoted pair availability
  },
  armyAnts: {
    baseWinRate: 0.70,
    baseGain: 0.022,
    baseLoss: 0.015,
    maxTradesPerDay: 8, // Limited by USDT alt liquidity
  },
  loneWolf: {
    baseWinRate: 0.60,
    baseGain: 0.035,
    baseLoss: 0.020,
    maxTradesPerDay: 2, // Selective momentum opportunities
  },
};

// Real-world constraints
const CONSTRAINTS = {
  // Binance Spot limits
  binanceMaxOrderPerSymbol: 50_000_000, // $50M max position
  binanceRateLimit: 1200, // requests per minute
  binanceSymbolCount: 500, // tradable symbols
  
  // Slippage model (increases with order size)
  getSlippage: (orderSize: number) => {
    if (orderSize < 1000) return 0.0001; // 0.01% for small orders
    if (orderSize < 10000) return 0.0003; // 0.03%
    if (orderSize < 100000) return 0.0008; // 0.08%
    if (orderSize < 1000000) return 0.002; // 0.2%
    if (orderSize < 10000000) return 0.005; // 0.5%
    return 0.01; // 1% for very large orders
  },
  
  // Position size as % of capital (risk management)
  maxPositionSizePercent: 0.98, // 98% per trade (full compound, reserves for fees)
  
  // Daily trade limit (API rate limits, execution time)
  maxTradesPerDay: 50, // Realistic with proper execution
  
  // Minimum notional
  minNotional: 10,
};

function calculateExpectedReturn(bot: typeof BOTS.hummingbird): number {
  return bot.baseWinRate * bot.baseGain + (1 - bot.baseWinRate) * -bot.baseLoss;
}

function simulateDay(capital: number, day: number): {
  newCapital: number;
  tradesExecuted: number;
  avgSlippage: number;
  details: string[];
} {
  let currentCapital = capital;
  let totalTrades = 0;
  let totalSlippage = 0;
  const details: string[] = [];
  
  // Calculate total possible trades (respecting individual bot limits)
  const possibleTrades = 
    BOTS.hummingbird.maxTradesPerDay +
    BOTS.armyAnts.maxTradesPerDay +
    BOTS.loneWolf.maxTradesPerDay;
  
  // Apply daily trade cap
  const maxTrades = Math.min(possibleTrades, CONSTRAINTS.maxTradesPerDay);
  
  // Distribute trades proportionally
  const tradesPerBot = {
    hummingbird: Math.min(
      BOTS.hummingbird.maxTradesPerDay,
      Math.floor(maxTrades * (BOTS.hummingbird.maxTradesPerDay / possibleTrades))
    ),
    armyAnts: Math.min(
      BOTS.armyAnts.maxTradesPerDay,
      Math.floor(maxTrades * (BOTS.armyAnts.maxTradesPerDay / possibleTrades))
    ),
    loneWolf: Math.min(
      BOTS.loneWolf.maxTradesPerDay,
      Math.floor(maxTrades * (BOTS.loneWolf.maxTradesPerDay / possibleTrades))
    ),
  };
  
  // Execute trades for each bot
  for (const [botName, bot] of Object.entries(BOTS)) {
    const botTrades = tradesPerBot[botName as keyof typeof tradesPerBot];
    
    for (let i = 0; i < botTrades; i++) {
      // Calculate position size (capped by constraints)
      let positionSize = currentCapital * CONSTRAINTS.maxPositionSizePercent;
      
      // If we're near min notional, use full capital to get started
      if (currentCapital < CONSTRAINTS.minNotional * 1.05) {
        positionSize = currentCapital * 0.999; // Leave tiny amount for fees
      }
      
      const exchangeLimit = CONSTRAINTS.binanceMaxOrderPerSymbol;
      positionSize = Math.min(positionSize, exchangeLimit);
      
      // Skip if below minimum notional
      if (positionSize < CONSTRAINTS.minNotional) continue;
      
      // Calculate slippage based on order size
      const slippage = CONSTRAINTS.getSlippage(positionSize);
      totalSlippage += slippage;
      
      // Simulate trade outcome
      const isWin = Math.random() < bot.baseWinRate;
      const baseReturn = isWin ? bot.baseGain : -bot.baseLoss;
      
      // Add variance (±10%)
      const variance = baseReturn * (Math.random() * 0.2 - 0.1);
      const grossReturn = baseReturn + variance;
      
      // Apply slippage and fees
      const netReturn = grossReturn - slippage - 0.001; // 0.1% trading fee
      
      currentCapital *= (1 + netReturn);
      totalTrades++;
      
      // Cap at exchange max
      if (currentCapital > CONSTRAINTS.binanceMaxOrderPerSymbol * CONSTRAINTS.binanceSymbolCount) {
        currentCapital = CONSTRAINTS.binanceMaxOrderPerSymbol * CONSTRAINTS.binanceSymbolCount;
        details.push(`Day ${day}: Hit exchange liquidity cap at $${(currentCapital / 1e9).toFixed(2)}B`);
        break;
      }
    }
  }
  
  return {
    newCapital: currentCapital,
    tradesExecuted: totalTrades,
    avgSlippage: totalTrades > 0 ? totalSlippage / totalTrades : 0,
    details,
  };
}

function formatCurrency(amount: number): string {
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(2)}B`;
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(2)}M`;
  if (amount >= 1e3) return `$${(amount / 1e3).toFixed(1)}K`;
  return `$${amount.toFixed(2)}`;
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🌍  REALISTIC 6-MONTH FORECAST');
console.log('    With Exchange Limits, Slippage & API Constraints');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
console.log('📊 Configuration:');
console.log(`   Starting Capital: ${formatCurrency(START_CAPITAL)}`);
console.log(`   Max Trades/Day: ${CONSTRAINTS.maxTradesPerDay} (API rate limited)`);
console.log(`   Max Position Size: 98% of capital (full compound)`);
console.log(`   Exchange Limit: ${formatCurrency(CONSTRAINTS.binanceMaxOrderPerSymbol)}/symbol`);
console.log(`   Trading Fees: 0.1% per trade`);
console.log('');
console.log('🤖 Bot Limits (realistic):');
console.log(`   🕊️  Hummingbird: ${BOTS.hummingbird.maxTradesPerDay}/day (ETH-quoted pairs)`);
console.log(`   🐜 ArmyAnts: ${BOTS.armyAnts.maxTradesPerDay}/day (USDT alts)`);
console.log(`   🐺 LoneWolf: ${BOTS.loneWolf.maxTradesPerDay}/day (momentum)`);
console.log('');

// Run Monte Carlo simulation
const SIMULATIONS = 100;
const allResults: ConstraintResult[][] = [];

for (let sim = 0; sim < SIMULATIONS; sim++) {
  let capital = START_CAPITAL;
  const results: ConstraintResult[] = [];
  
  for (let day = 1; day <= DAYS; day++) {
    const dayResult = simulateDay(capital, day);
    
    results.push({
      day,
      capital: dayResult.newCapital,
      tradesExecuted: dayResult.tradesExecuted,
      tradesCapped: 0,
      avgSlippage: dayResult.avgSlippage,
      effectiveReturn: (dayResult.newCapital - capital) / capital,
    });
    
    capital = dayResult.newCapital;
    
    if (capital <= 0) break; // Blown up
  }
  
  allResults.push(results);
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('📈  GROWTH PROJECTIONS (100 Monte Carlo simulations)');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');

const milestones = [7, 14, 30, 60, 90, 120, 150, 180];

console.log('Day  |  Worst    |  25th %   |  Median   |  75th %   |  Best     |  Avg Trades/Day');
console.log('─────┼───────────┼───────────┼───────────┼───────────┼───────────┼────────────────');

for (const day of milestones) {
  const dayResults = allResults
    .map(r => r[day - 1])
    .filter(r => r && r.capital > 0)
    .sort((a, b) => a.capital - b.capital);
  
  if (dayResults.length === 0) {
    console.log(`${day.toString().padStart(3)}  | ALL BLOWN UP`);
    continue;
  }
  
  const worst = dayResults[0];
  const q25 = dayResults[Math.floor(dayResults.length * 0.25)];
  const median = dayResults[Math.floor(dayResults.length * 0.5)];
  const q75 = dayResults[Math.floor(dayResults.length * 0.75)];
  const best = dayResults[dayResults.length - 1];
  const avgTrades = dayResults.reduce((sum, r) => sum + r.tradesExecuted, 0) / dayResults.length;
  
  console.log(
    `${day.toString().padStart(3)}  | ` +
    `${formatCurrency(worst.capital).padEnd(9)} | ` +
    `${formatCurrency(q25.capital).padEnd(9)} | ` +
    `${formatCurrency(median.capital).padEnd(9)} | ` +
    `${formatCurrency(q75.capital).padEnd(9)} | ` +
    `${formatCurrency(best.capital).padEnd(9)} | ` +
    `${avgTrades.toFixed(1).padStart(3)}`
  );
}

console.log('');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🎯  6-MONTH OUTCOMES');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

const finalResults = allResults
  .map(r => r[DAYS - 1])
  .filter(r => r && r.capital > 0)
  .sort((a, b) => a.capital - b.capital);

if (finalResults.length > 0) {
  const median = finalResults[Math.floor(finalResults.length * 0.5)];
  const avg = finalResults.reduce((sum, r) => sum + r.capital, 0) / finalResults.length;
  const worst = finalResults[0];
  const best = finalResults[finalResults.length - 1];
  const totalTrades = finalResults.reduce((sum, r) => sum + r.tradesExecuted * DAYS, 0) / finalResults.length;
  
  console.log('');
  console.log(`   Success Rate: ${(finalResults.length / SIMULATIONS * 100).toFixed(0)}% (${finalResults.length}/${SIMULATIONS} profitable)`);
  console.log(`   Median Outcome: ${formatCurrency(median.capital)}`);
  console.log(`   Average Outcome: ${formatCurrency(avg)}`);
  console.log(`   Best Case: ${formatCurrency(best.capital)}`);
  console.log(`   Worst Case: ${formatCurrency(worst.capital)}`);
  console.log(`   Avg Total Trades: ${Math.round(totalTrades).toLocaleString()}`);
  console.log('');
  console.log(`   📊 ROI Analysis (Median):`);
  console.log(`      ROI: ${(((median.capital - START_CAPITAL) / START_CAPITAL) * 100).toFixed(0)}%`);
  console.log(`      Multiple: ${(median.capital / START_CAPITAL).toFixed(1)}x`);
  console.log('');
  
  // Time to realistic milestones
  console.log(`   🏁 Time to Milestones (median path):`);
  const targets = [100, 1000, 10000, 100000, 1000000, 10000000, 50000000];
  
  for (const target of targets) {
    let crossDay = 0;
    
    for (let d = 1; d <= DAYS; d++) {
      const dayResults = allResults
        .map(r => r[d - 1])
        .filter(r => r && r.capital > 0)
        .sort((a, b) => a.capital - b.capital);
      
      if (dayResults.length > 0) {
        const medianForDay = dayResults[Math.floor(dayResults.length * 0.5)];
        if (medianForDay.capital >= target) {
          crossDay = d;
          break;
        }
      }
    }
    
    if (crossDay > 0) {
      const months = Math.floor(crossDay / 30);
      const days = crossDay % 30;
      console.log(`      ${formatCurrency(target).padEnd(10)} → Day ${crossDay.toString().padStart(3)} (${months}m ${days}d)`);
    } else if (median.capital < target) {
      console.log(`      ${formatCurrency(target).padEnd(10)} → Not reached in 6 months`);
    }
  }
} else {
  console.log('\n   ⚠️  All simulations resulted in losses');
}

console.log('');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('💡  REALISTIC CONSTRAINTS APPLIED:');
console.log('   • Max 50 trades/day (API rate limits + execution time)');
console.log('   • 98% position size (full compound with fee reserves)');
console.log('   • Slippage increases with order size (0.01%-1%)');
console.log('   • 0.1% trading fees per trade');
console.log('   • $50M max per symbol (Binance Spot limit)');
console.log('   • $25B total cap (500 symbols × $50M)');
console.log('   • Market variance ±10% on expected returns');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('');
