#!/usr/bin/env tsx
/**
 * 🍯 THE HONEY COMPOUND TEST 🍯
 * 50 trades per day - watch the magic of compounding!
 */

console.log('\n🍯 HONEY COMPOUND TEST: 50 Trades Daily 🍯\n');
console.log('Starting with YOUR $147... let\'s see the compound magic!\n');

const START_CAPITAL = 147;
const TRADES_PER_DAY = 50;
const DAYS_TO_SIMULATE = 30; // 1 month

const AVG_POSITION_SIZE_PCT = 0.20; // 20% per trade
const AVG_WIN_PCT = 0.012; // 1.2% average win
const AVG_LOSS_PCT = 0.008; // 0.8% average loss
const WIN_RATE = 0.68; // 68% from our smoke test

let equity = START_CAPITAL;
let totalTrades = 0;
let totalWins = 0;
let totalLosses = 0;
let totalHoney = 0;

console.log('Strategy:');
console.log(`  Starting Capital: $${START_CAPITAL}`);
console.log(`  Trades per day: ${TRADES_PER_DAY}`);
console.log(`  Win Rate: ${(WIN_RATE * 100).toFixed(0)}%`);
console.log(`  Position Size: ${(AVG_POSITION_SIZE_PCT * 100).toFixed(0)}% per trade`);
console.log(`  Simulating: ${DAYS_TO_SIMULATE} days\n`);
console.log('Let the HONEY flow! 🍯\n');

const dailyResults: any[] = [];

for (let day = 1; day <= DAYS_TO_SIMULATE; day++) {
  const startOfDay = equity;
  let dailyWins = 0;
  let dailyLosses = 0;
  
  // Execute 50 trades for this day
  for (let trade = 0; trade < TRADES_PER_DAY; trade++) {
    const positionSize = equity * AVG_POSITION_SIZE_PCT;
    const isWin = Math.random() < WIN_RATE;
    
    let pnl;
    if (isWin) {
      const winPct = AVG_WIN_PCT + (Math.random() - 0.5) * 0.01;
      pnl = positionSize * winPct;
      dailyWins++;
      totalWins++;
    } else {
      const lossPct = AVG_LOSS_PCT + (Math.random() - 0.5) * 0.005;
      pnl = -positionSize * lossPct;
      dailyLosses++;
      totalLosses++;
    }
    
    equity += pnl;
    totalTrades++;
  }
  
  const dailyProfit = equity - startOfDay;
  const dailyReturn = ((equity / startOfDay) - 1) * 100;
  totalHoney += dailyProfit;
  
  dailyResults.push({
    day,
    startOfDay,
    endOfDay: equity,
    dailyProfit,
    dailyReturn,
    wins: dailyWins,
    losses: dailyLosses
  });
  
  // Show weekly updates
  if (day % 7 === 0 || day === 1 || day === DAYS_TO_SIMULATE) {
    const totalReturn = ((equity / START_CAPITAL) - 1) * 100;
    console.log(`Day ${day.toString().padStart(2)}: $${equity.toFixed(2)} | Daily: +$${dailyProfit.toFixed(2)} (${dailyReturn >= 0 ? '+' : ''}${dailyReturn.toFixed(2)}%) | Total: +${totalReturn.toFixed(1)}%`);
  }
}

const finalReturn = ((equity / START_CAPITAL) - 1) * 100;
const avgDailyReturn = finalReturn / DAYS_TO_SIMULATE;
const totalWinRate = (totalWins / totalTrades) * 100;

console.log('\n' + '='.repeat(80));
console.log('🍯 HONEY COMPOUND RESULTS: 50 TRADES/DAY FOR 30 DAYS 🍯');
console.log('='.repeat(80));
console.log(`Starting Capital:    $${START_CAPITAL.toFixed(2)}`);
console.log(`Final Equity:        $${equity.toFixed(2)}`);
console.log(`Total Honey:         +$${totalHoney.toFixed(2)} 🍯🍯🍯`);
console.log(`Total Return:        +${finalReturn.toFixed(2)}%`);
console.log(`Avg Daily Return:    +${avgDailyReturn.toFixed(2)}%`);
console.log('-'.repeat(80));
console.log(`Total Trades:        ${totalTrades.toLocaleString()}`);
console.log(`Total Winners:       ${totalWins.toLocaleString()} (${totalWinRate.toFixed(1)}%)`);
console.log(`Total Losers:        ${totalLosses.toLocaleString()}`);
console.log('='.repeat(80));

// Weekly breakdown
console.log('\n📊 WEEKLY BREAKDOWN:\n');
for (let week = 1; week <= 4; week++) {
  const weekStart = (week - 1) * 7;
  const weekEnd = Math.min(week * 7, DAYS_TO_SIMULATE);
  const weekData = dailyResults.slice(weekStart, weekEnd);
  
  const weekStartEquity = weekData[0].startOfDay;
  const weekEndEquity = weekData[weekData.length - 1].endOfDay;
  const weekProfit = weekEndEquity - weekStartEquity;
  const weekReturn = ((weekEndEquity / weekStartEquity) - 1) * 100;
  
  console.log(`Week ${week}: $${weekStartEquity.toFixed(2)} → $${weekEndEquity.toFixed(2)} | Profit: +$${weekProfit.toFixed(2)} (${weekReturn >= 0 ? '+' : ''}${weekReturn.toFixed(2)}%)`);
}

console.log('\n' + '='.repeat(80));
console.log('🦁 THE LION\'S HONEY HARVEST PROJECTIONS 🦁');
console.log('='.repeat(80));

// Projections
const monthlyMultiplier = equity / START_CAPITAL;
const month2 = equity * monthlyMultiplier;
const month3 = month2 * monthlyMultiplier;
const month6 = equity * Math.pow(monthlyMultiplier, 6);
const year1 = equity * Math.pow(monthlyMultiplier, 12);

console.log(`\nStarting with $${START_CAPITAL}:\n`);
console.log(`After 1 month:  $${equity.toFixed(2)} (+${finalReturn.toFixed(1)}%) 🍯`);
console.log(`After 2 months: $${month2.toFixed(2)} (+${((month2/START_CAPITAL - 1) * 100).toFixed(1)}%) 🍯🍯`);
console.log(`After 3 months: $${month3.toFixed(2)} (+${((month3/START_CAPITAL - 1) * 100).toFixed(1)}%) 🍯🍯🍯`);
console.log(`After 6 months: $${month6.toFixed(2)} (+${((month6/START_CAPITAL - 1) * 100).toFixed(0)}%) 🚀`);
console.log(`After 1 year:   $${year1.toFixed(2)} (+${((year1/START_CAPITAL - 1) * 100).toFixed(0)}%) 🚀🚀🚀`);

console.log('\n🍯 THE POWER OF COMPOUND HONEY! 🍯\n');

if (finalReturn > 20) {
  console.log('✅ LION VERDICT: The honey is FLOWING!\n');
  console.log('This is what happens when you:');
  console.log('  1. Trade consistently (50 trades/day)');
  console.log('  2. Maintain 68% win rate');
  console.log('  3. Let profits COMPOUND');
  console.log('  4. Stay disciplined\n');
  console.log('🦁 From $147 to SERIOUS money through compound honey!\n');
  console.log('Ready to make this REAL? 🔥\n');
} else {
  console.log('Results show moderate growth. Consistency is key!\n');
}
