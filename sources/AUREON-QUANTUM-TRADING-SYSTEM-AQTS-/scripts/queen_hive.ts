#!/usr/bin/env tsx
import { QueenHive } from '../core/queenHive';
import fs from 'node:fs';

const AGENTS_PER_HIVE = Number(process.env.AGENTS_PER_HIVE ?? 100);
const START_PER_AGENT = Number(process.env.START ?? 100);
const TARGET_PER_AGENT = Number(process.env.TARGET ?? 1_000_000);
const MAX_STEPS = Number(process.env.MAX_STEPS ?? 100_000);
const LOG_INTERVAL = Number(process.env.LOG_INTERVAL ?? 5000);

console.log('👑 Queen-Hive Meta-Controller');
console.log(`  Agents per hive: ${AGENTS_PER_HIVE}`);
console.log(`  Start per agent: £${START_PER_AGENT}`);
console.log(`  Target per agent: £${TARGET_PER_AGENT}`);
console.log(`  Max steps: ${MAX_STEPS}`);
console.log('');

const queenHive = new QueenHive(AGENTS_PER_HIVE, START_PER_AGENT, TARGET_PER_AGENT);

const finalState = queenHive.run(MAX_STEPS, LOG_INTERVAL);

console.log('\n📊 Final Queen-Hive State');
console.log(`Total hives spawned: ${finalState.totalHives}`);
console.log(`Total agents: ${finalState.totalAgents}`);
console.log(`Total aggregate equity: £${finalState.totalEquity.toFixed(2)}`);
console.log(`Max generation: ${finalState.generation}`);
console.log(`Split events: ${finalState.splitEvents.length}`);

console.log('\n🐝 Hive Breakdown:');
const byStage: Record<string, number> = { growing: 0, ready_to_split: 0, splitting: 0, mature: 0 };
for (const hive of finalState.hives) {
  byStage[hive.stage]++;
  console.log(
    `  ${hive.id} (gen ${hive.generation}): £${hive.equity.toFixed(2)} (${hive.successfulAgents}/${hive.agents} agents, mult=${hive.profitMultiplier.toFixed(2)}x)`
  );
}

console.log('\n📈 Stage Summary:');
console.log(`  Growing: ${byStage.growing}`);
console.log(`  Ready to split: ${byStage.ready_to_split}`);
console.log(`  Splitting: ${byStage.splitting}`);
console.log(`  Mature: ${byStage.mature}`);

console.log('\n🔄 Split Timeline:');
for (const event of finalState.splitEvents) {
  console.log(`  Step ${event.step}: spawned ${event.newHiveId}`);
}

try {
  fs.writeFileSync('queen_hive_results.json', JSON.stringify(finalState, null, 2));
  console.log('\nWrote queen_hive_results.json');
} catch (err) {
  console.warn('Could not write results:', (err as Error).message);
}
