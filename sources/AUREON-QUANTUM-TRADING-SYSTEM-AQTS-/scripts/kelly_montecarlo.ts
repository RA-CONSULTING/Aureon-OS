#!/usr/bin/env tsx
import fs from 'node:fs';

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  console.error('backtest_trades.csv missing — run collect_trades.ts first');
  process.exit(1);
}

const csv = fs.readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
csv.shift();
const rows = csv.map(r => r.split(','));
const rets = rows.map(r => Number(r[6]));

const wins = rets.filter(r => r > 0);
const losses = rets.filter(r => r <= 0).map(r => Math.abs(r));
const p = wins.length / rets.length;
const avgWin = wins.reduce((a, b) => a + b, 0) / (wins.length || 1);
const avgLoss = losses.reduce((a, b) => a + b, 0) / (losses.length || 1);
const b = avgWin / (avgLoss || 1e-9);
const kelly = (b * p - (1 - p)) / b;

console.log('Empirical stats:');
console.log('  Trades:', rets.length);
console.log('  Win rate p:', p.toFixed(4));
console.log('  Avg win:', avgWin.toExponential(6));
console.log('  Avg loss:', avgLoss.toExponential(6));
console.log('  b (win/loss ratio):', b.toFixed(4));
console.log('  Kelly fraction:', kelly.toFixed(6));

// Monte Carlo using Kelly fraction (and capped variants)
const PATHS = Number(process.env.PATHS ?? 10000);
const MAX_TRADES = Number(process.env.MAX_TRADES ?? 20000);
const START = Number(process.env.START ?? 100);
const baseEquity = 100000; // used for empirical fraction baseline

function sampleReturn() {
  const i = Math.floor(Math.random() * rets.length);
  return rets[i];
}

function runPath(fraction: number) {
  let eq = START;
  for (let t = 0; t < MAX_TRADES; t++) {
    const r = sampleReturn();
    const pnl = eq * fraction * r;
    eq += pnl;
    if (eq >= 1_000_000) return t + 1;
    if (eq <= 0) return -1;
  }
  return -1;
}

function statsForFraction(frac: number) {
  const times: number[] = [];
  for (let pth = 0; pth < PATHS; pth++) {
    const t = runPath(frac);
    if (t > 0) times.push(t);
  }
  const success = (times.length / PATHS) * 100;
  times.sort((a, b) => a - b);
  const median = times.length ? times[Math.floor(times.length / 2)] : null;
  return { success, median };
}

const caps = [0.10, 0.05];
const mults = [1.0, 0.5];
const results: any[] = [];

for (const m of mults) {
  const raw = Math.max(0, kelly * m);
  for (const cap of caps) {
    const frac = Math.min(raw, cap);
    const res = statsForFraction(frac);
    console.log(`Fraction scenario: multiplier=${m}, cap=${cap} => frac=${(frac * 100).toFixed(2)}% -> success ${res.success.toFixed(2)}% medianTrades ${res.median ?? 'N/A'}`);
    results.push({ multiplier: m, cap, frac, res });
  }
}

try {
  fs.writeFileSync('kelly_montecarlo_results.json', JSON.stringify({ kelly, results }, null, 2));
  console.log('Wrote kelly_montecarlo_results.json');
} catch (err) {
  console.warn('Could not write results:', (err as Error).message);
}
