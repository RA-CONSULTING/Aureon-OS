#!/usr/bin/env tsx
import { writeFileSync } from 'node:fs';
import { AQTSOrchestrator } from '../core/aqtsOrchestrator';
import { AQTSConfig, DeepPartial, defaultAQTSConfig, mergeConfig } from '../core/config';

const ITERATIONS = Number(process.env.ITERATIONS ?? process.env.AQTS_ITERATIONS ?? 50);
const STEPS = Number(process.env.STEPS ?? process.env.AQTS_STEPS ?? 2000);

console.log(`Collect trades: Iterations=${ITERATIONS}, Steps=${STEPS}`);

type TradeRecord = {
  iteration: number;
  step: number;
  direction: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  notional: number;
  return: number; // relative
  pnl: number; // absolute
};

const records: TradeRecord[] = [];

for (let it = 0; it < ITERATIONS; it++) {
  const orchestrator = new AQTSOrchestrator();
  for (let step = 0; step < STEPS; step++) {
    const out = orchestrator.next();
    if (out.order && out.execution) {
      const order = out.order;
      const exec = out.execution;
      const mark = out.snapshot.consolidatedOHLCV.close;
      const directionMultiplier = order.direction === 'long' ? 1 : -1;
      const entry = exec.averagePrice;
      const positionReturn = ((mark - entry) / entry) * directionMultiplier;
      const pnl = positionReturn * order.notional;
      records.push({
        iteration: it + 1,
        step: step + 1,
        direction: order.direction,
        entryPrice: entry,
        exitPrice: mark,
        notional: order.notional,
        return: positionReturn,
        pnl,
      });
    }
  }
}

console.log('Collected trades:', records.length);
try {
  const lines = ['iteration,step,direction,entryPrice,exitPrice,notional,return,pnl'];
  for (const r of records) {
    lines.push(`${r.iteration},${r.step},${r.direction},${r.entryPrice.toFixed(6)},${r.exitPrice.toFixed(6)},${r.notional.toFixed(6)},${r.return.toFixed(8)},${r.pnl.toFixed(6)}`);
  }
  writeFileSync('backtest_trades.csv', lines.join('\n'));
  console.log('Wrote backtest_trades.csv');
} catch (err) {
  console.warn('Unable to write CSV', (err as Error).message);
}
