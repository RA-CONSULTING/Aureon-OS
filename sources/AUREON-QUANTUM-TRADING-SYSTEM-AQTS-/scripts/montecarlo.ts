#!/usr/bin/env tsx
import { readFileSync, writeFileSync } from 'node:fs';

import fs from 'node:fs';

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  console.error(`${TRADE_CSV} not found. Run scripts/collect_trades.ts first.`);
  process.exit(1);
}

const csv = readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
const header = csv.shift()!;
const rows = csv.map(r => r.split(','));

type TradeRow = { ret: number; notional: number };
const trades: TradeRow[] = rows.map(r => ({ ret: Number(r[6]), notional: Number(r[5]) }));

const PATHS = Number(process.env.PATHS ?? 10000);
const MAX_TRADES = Number(process.env.MAX_TRADES ?? 20000);
const START_CAPS = (process.env.START_CAPS ?? '1,100').split(',').map(Number);
const FIXED_FRACTION = Number(process.env.FRACTION ?? 0.01);
const FEE = Number(process.env.FEE ?? 0); // absolute fraction subtracted from return, e.g. 0.0002
const SLIPPAGE = Number(process.env.SLIPPAGE ?? 0); // absolute fraction subtracted from return

console.log(`Monte Carlo: paths=${PATHS}, maxTrades=${MAX_TRADES}, startCaps=${START_CAPS}, fixedFraction=${FIXED_FRACTION}`);

function sampleTrade() {
  const i = Math.floor(Math.random() * trades.length);
  return trades[i];
}

function runPathFixed(start: number) {
  let eq = start;
  for (let t = 0; t < MAX_TRADES; t++) {
    const tr = sampleTrade();
    const f = FIXED_FRACTION;
    const pnl = eq * f * tr.ret;
    eq += pnl;
    if (eq >= 1_000_000) return t + 1;
    if (eq <= 0) return -1;
  }
  return -1;
}

function runPathEmpiricalFraction(start: number, baseEquity = 100000) {
  let eq = start;
  for (let t = 0; t < MAX_TRADES; t++) {
    const tr = sampleTrade();
    const frac = Math.min(1, Math.max(0, tr.notional / baseEquity));
    const pnl = eq * frac * tr.ret;
    eq += pnl;
    if (eq >= 1_000_000) return t + 1;
    if (eq <= 0) return -1;
  }
  return -1;
}

type ResultSummary = {
  start: number;
  fixed: { successRate: number; medianTrades: number | null };
  empirical: { successRate: number; medianTrades: number | null };
};

const out: ResultSummary[] = [];

for (const start of START_CAPS) {
  const fixedTimes: number[] = [];
  const empTimes: number[] = [];

  for (let p = 0; p < PATHS; p++) {
    const t1 = runPathFixed(start);
    if (t1 > 0) fixedTimes.push(t1);
    const t2 = runPathEmpiricalFraction(start);
    if (t2 > 0) empTimes.push(t2);
  }

  const fixedSuccess = (fixedTimes.length / PATHS) * 100;
  const empSuccess = (empTimes.length / PATHS) * 100;

  const median = (arr: number[]) => {
    if (arr.length === 0) return null;
    arr.sort((a, b) => a - b);
    const mid = Math.floor(arr.length / 2);
    return arr.length % 2 === 0 ? Math.round((arr[mid - 1] + arr[mid]) / 2) : arr[mid];
  };

  out.push({
    start,
    fixed: { successRate: fixedSuccess, medianTrades: median(fixedTimes) },
    empirical: { successRate: empSuccess, medianTrades: median(empTimes) },
  });
}

console.log('Results:');
for (const r of out) {
  console.log(`Start £${r.start}:`);
  console.log(`  Fixed ${FIXED_FRACTION * 100}% fraction -> success ${r.fixed.successRate.toFixed(2)}% | median trades: ${r.fixed.medianTrades ?? 'N/A'}`);
  console.log(`  Empirical fraction -> success ${r.empirical.successRate.toFixed(2)}% | median trades: ${r.empirical.medianTrades ?? 'N/A'}`);
}

try {
  writeFileSync('montecarlo_results.json', JSON.stringify({ params: { PATHS, MAX_TRADES, START_CAPS, FIXED_FRACTION }, results: out }, null, 2));
  console.log('Wrote montecarlo_results.json');
} catch (err) {
  console.warn('Unable to write results:', (err as Error).message);
}
