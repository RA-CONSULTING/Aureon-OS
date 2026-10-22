#!/usr/bin/env tsx
/**
 * Live Balance Monte Carlo Projection
 * Models path to £500k given current USDC balance, trade parameters, and win rate.
 * Assumptions:
 *  - Per trade: win => +WIN_PCT * POSITION_SIZE_PERCENT of capital, loss => -LOSS_PCT * POSITION_SIZE_PERCENT
 *  - Trades per day capped at TRADES_PER_DAY
 *  - Compounds after each trade
 *  - Stops when target or max days reached
 *  - Ignores fees/slippage (adjust with FEE_PCT if desired)
 *
 * Env overrides:
 *  WIN_RATE=0.8 (single scenario) or MULTI_WIN="0.65,0.7,0.75,0.8"
 *  PATHS=5000, TARGET=500000, TRADES_PER_DAY=50, DAYS_LIMIT=730
 *  WIN_PCT=0.003 (0.3%), LOSS_PCT=0.005 (0.5%), POSITION_SIZE_PERCENT=90
 *  FEE_PCT=0.0004 (0.04% per trade, applied to notional)
 */

import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

interface Params {
  startBalance: number;
  target: number;
  winRate: number;
  tradesPerDay: number;
  winPct: number; // raw % move captured on portion of capital deployed
  lossPct: number;
  positionSizePercent: number; // portion of capital put at risk each trade
  feePct: number; // per trade fee applied to deployed capital
  daysLimit: number;
}

function getLiveBalance(): Promise<number> {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
    // Explicit override takes precedence even if API keys exist
    if (process.env.START_BALANCE) {
      return Promise.resolve(Number(process.env.START_BALANCE));
  }
    const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
    return client.getAccount().then(acc => {
      const usdc = acc.balances.find(b => b.asset === 'USDC');
      return Number(usdc?.free || 0);
    }).catch(err => {
      console.warn('Failed to fetch live account balance:', err.message);
      return Promise.resolve(100);
  });
}

function simulatePath(p: Params): { days: number; trades: number; final: number; success: boolean } {
  let equity = p.startBalance;
  const tradeFrac = p.positionSizePercent / 100;
  const winGain = p.winPct * tradeFrac; // percent of total equity
  const lossLoss = p.lossPct * tradeFrac; // percent of total equity
  const feeFrac = p.feePct * tradeFrac; // percent drag
  let trades = 0;
  for (let day = 1; day <= p.daysLimit; day++) {
    for (let t = 0; t < p.tradesPerDay; t++) {
      const r = Math.random() < p.winRate;
      const deltaPct = r ? winGain - feeFrac : -lossLoss - feeFrac;
      equity *= (1 + deltaPct);
      trades++;
      if (equity >= p.target) return { days: day, trades, final: equity, success: true };
      if (equity <= 0) return { days: day, trades, final: equity, success: false };
    }
  }
  return { days: p.daysLimit, trades, final: equity, success: equity >= p.target };
}

function summarize(results: { days: number; trades: number; final: number; success: boolean }[]) {
  const successRuns = results.filter(r => r.success);
  const successRate = (successRuns.length / results.length) * 100;
  const sortByDays = successRuns.slice().sort((a,b)=>a.days-b.days);
  const pct = (p: number) => sortByDays.length ? sortByDays[Math.min(sortByDays.length-1, Math.floor(p * sortByDays.length))].days : null;
  const medianDays = pct(0.5);
  const p10 = pct(0.1);
  const p25 = pct(0.25);
  const p75 = pct(0.75);
  const p90 = pct(0.9);
  return { successRate, medianDays, p10, p25, p75, p90 };
}

async function main() {
  const startBalance = await getLiveBalance();
  const target = Number(process.env.TARGET ?? 500000);
  const tradesPerDay = Number(process.env.TRADES_PER_DAY ?? 50);
  const paths = Number(process.env.PATHS ?? 5000);
  const winPct = Number(process.env.WIN_PCT ?? 0.003);
  const lossPct = Number(process.env.LOSS_PCT ?? 0.005);
  const positionSizePercent = Number(process.env.POSITION_SIZE_PERCENT ?? 90);
  const feePct = Number(process.env.FEE_PCT ?? 0);
  const daysLimit = Number(process.env.DAYS_LIMIT ?? 730);
  const multiWin = (process.env.MULTI_WIN ?? '').split(',').map(s => s.trim()).filter(Boolean).map(Number);
  const singleWin = Number(process.env.WIN_RATE ?? 0.75);
  const scenarios = multiWin.length ? multiWin : [singleWin];

  console.log(`\n🔮 Monte Carlo Projection (paths=${paths})`);
  console.log(`Start Balance: £${startBalance.toFixed(2)} | Target: £${target}`);
  console.log(`Trades/Day: ${tradesPerDay} | Win% trade-level: ${winPct*100}% gain / ${lossPct*100}% loss on ${positionSizePercent}% capital`);
  console.log(`Position Size: ${positionSizePercent}% | FeePct: ${(feePct*100).toFixed(3)}% | Days Limit: ${daysLimit}`);

  const allOutputs: any[] = [];
  for (const winRate of scenarios) {
    console.log(`\nScenario winRate=${(winRate*100).toFixed(1)}% running...`);
    const results = [] as { days: number; trades: number; final: number; success: boolean }[];
    for (let i=0;i<paths;i++) {
      results.push(simulatePath({ startBalance, target, winRate, tradesPerDay, winPct, lossPct, positionSizePercent, feePct, daysLimit }));
    }
    const stats = summarize(results);
    console.log(`  Success Rate: ${stats.successRate.toFixed(2)}%`);
    console.log(`  Median Days: ${stats.medianDays ?? 'N/A'}`);
    console.log(`  10th Percentile Days: ${stats.p10 ?? 'N/A'}`);
    console.log(`  25th Percentile Days: ${stats.p25 ?? 'N/A'}`);
    console.log(`  75th Percentile Days: ${stats.p75 ?? 'N/A'}`);
    console.log(`  90th Percentile Days: ${stats.p90 ?? 'N/A'}`);
    const fastest = stats.p10 ?? stats.medianDays;
    if (fastest) {
      const fastestMonths = (fastest/30).toFixed(1);
      console.log(`  ⇒ Fast-path (p10) months: ${fastestMonths}`);
    }
    allOutputs.push({ winRate, stats });
  }

  // Persist JSON
  const out = { timestamp: new Date().toISOString(), params: { startBalance, target, tradesPerDay, paths, winPct, lossPct, positionSizePercent, feePct, daysLimit }, scenarios: allOutputs };
  try {
    await import('node:fs').then(fs => fs.writeFileSync('live_montecarlo_results.json', JSON.stringify(out, null, 2)));
    console.log('\n📝 Wrote live_montecarlo_results.json');
  } catch(err:any) {
    console.warn('Failed to write output:', err.message);
  }
}

main().catch(err => {
  console.error('Fatal error in Monte Carlo:', err.message);
  process.exit(1);
});
