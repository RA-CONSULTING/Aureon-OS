#!/usr/bin/env tsx
import { readFileSync } from 'node:fs';

const TRADE_CSV = 'backtest_trades.csv';
const txt = readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
txt.shift();
const rows = txt.map(r => r.split(','));
const rets = rows.map(r => Number(r[6]));
const nots = rows.map(r => Number(r[5]));
const n = rets.length;
const mean = rets.reduce((a, b) => a + b, 0) / n;
const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
const std = Math.sqrt(variance);
const wins = rets.filter(r => r > 0).length;
const avgNot = nots.reduce((a, b) => a + b, 0) / n;
const sorted = rets.slice().sort((a, b) => a - b);
const pct = (p: number) => sorted[Math.floor((p / 100) * sorted.length)];

console.log('Trade stats from', TRADE_CSV);
console.log('Count:', n);
console.log('Win rate:', ((wins / n) * 100).toFixed(2) + '%');
console.log('Mean return:', mean.toFixed(6));
console.log('Std return:', std.toFixed(6));
console.log('Median return:', pct(50).toFixed(6));
console.log('1% percentile:', pct(1).toFixed(6));
console.log('99% percentile:', pct(99).toFixed(6));
console.log('Avg notional:', avgNot.toFixed(2));
