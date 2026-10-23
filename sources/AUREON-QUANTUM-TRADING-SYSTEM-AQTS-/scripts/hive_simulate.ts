#!/usr/bin/env tsx
import { HiveController } from '../core/hiveController';
import { writeFileSync } from 'node:fs';

const NUM_AGENTS = Number(process.env.NUM_AGENTS ?? 100);
const PRIME_SCALE = Number(process.env.PRIME_SCALE ?? 0.01);
const MAX_STEPS = Number(process.env.MAX_STEPS ?? 10000);
const TARGET_EQUITY = Number(process.env.TARGET ?? 1_000_000);
const AGENT_START = Number(process.env.START ?? 100);

console.log('🐝 Hive Simulation');
console.log(`  Agents: ${NUM_AGENTS}`);
console.log(`  Start per agent: £${AGENT_START}`);
console.log(`  Prime scale: ${PRIME_SCALE}`);
console.log(`  Target per agent: £${TARGET_EQUITY}`);
console.log(`  Max steps: ${MAX_STEPS}`);

const hive = new HiveController(NUM_AGENTS, AGENT_START, PRIME_SCALE, TARGET_EQUITY);

const metrics: any[] = [];

for (let s = 0; s < MAX_STEPS; s++) {
  const state = hive.step();

  if ((s + 1) % 100 === 0 || s === 0) {
    const m = hive.getMetrics();
    console.log(
      `Step ${s + 1}: Agents=${m.activeAgents}/${NUM_AGENTS} | Successful=${m.successfulAgents} | Avg Equity=£${m.averageEquity.toFixed(2)} | Trades=${m.aggregateTradeCount}`
    );
    metrics.push(m);
  }

  // Early exit if all agents succeeded
  if (state.successfulAgents === NUM_AGENTS) {
    console.log(`\n✅ All agents reached target at step ${s + 1}!`);
    break;
  }
}

const finalMetrics = hive.getMetrics();
console.log('\n📊 Final Hive State');
console.log(`Successful agents: ${finalMetrics.successfulAgents}/${NUM_AGENTS}`);
console.log(`Success rate: ${(finalMetrics.successRate * 100).toFixed(2)}%`);
console.log(`Total aggregate equity: £${finalMetrics.totalEquity.toFixed(2)}`);
console.log(`Average equity per agent: £${finalMetrics.averageEquity.toFixed(2)}`);
console.log(`Total trades executed: ${finalMetrics.aggregateTradeCount}`);
console.log(`Aggregate win rate: ${(finalMetrics.winRate * 100).toFixed(2)}%`);
console.log(`Active agents: ${finalMetrics.activeAgents}`);

try {
  writeFileSync(
    'hive_results.json',
    JSON.stringify(
      {
        params: { NUM_AGENTS, PRIME_SCALE, MAX_STEPS, TARGET_EQUITY, AGENT_START },
        finalMetrics,
        metricsHistory: metrics,
      },
      null,
      2
    )
  );
  console.log('\nWrote hive_results.json');
} catch (err) {
  console.warn('Could not write results:', (err as Error).message);
}
