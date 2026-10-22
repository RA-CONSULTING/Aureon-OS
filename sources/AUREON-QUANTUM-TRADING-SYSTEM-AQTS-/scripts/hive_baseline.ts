#!/usr/bin/env tsx
import fs from 'node:fs';
import { AQTSOrchestrator } from '../core/aqtsOrchestrator';

// Hybrid Hive: uses empirical trade returns + Lighthouse signals from AQTSOrchestrator
// Each agent: boots with empirical trade distribution, scales by Fibonacci + prime, gated by Lighthouse confidence

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  console.error('backtest_trades.csv missing');
  process.exit(1);
}

const csv = fs.readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
csv.shift();
const rows = csv.map(r => r.split(','));
const rets = rows.map(r => Number(r[6]));

const PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97];
const FIBS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144];

const NUM_AGENTS = Number(process.env.NUM_AGENTS ?? 100);
const PRIME_SCALE = Number(process.env.PRIME_SCALE ?? 0.005);
const MAX_TRADES = Number(process.env.MAX_TRADES ?? 100000);
const TARGET = Number(process.env.TARGET ?? 1_000_000);
const START = Number(process.env.START ?? 100);
const CONFIDENCE_GATE = Number(process.env.CONFIDENCE_GATE ?? 0.0); // Lighthouse confidence threshold

console.log('🐝 Hive Baseline (Hybrid: Empirical + Lighthouse)');
console.log(`  Agents: ${NUM_AGENTS}`);
console.log(`  Start: £${START}`);
console.log(`  Prime scale: ${PRIME_SCALE}`);
console.log(`  Confidence gate: ${CONFIDENCE_GATE}`);
console.log(`  Target: £${TARGET}`);

class HiveAgent {
  id: number;
  equity: number;
  trades: number = 0;
  wins: number = 0;
  primeIdx: number;
  fibIdx: number = 0;
  orchestrator: AQTSOrchestrator;

  constructor(id: number) {
    this.id = id;
    this.equity = START;
    this.primeIdx = id % PRIMES.length;
    this.orchestrator = new AQTSOrchestrator();
  }

  trade(): boolean {
    if (this.equity <= 0 || this.equity >= TARGET) return false;

    // Get Lighthouse signal
    const out = this.orchestrator.next();
    const confidence = out.lighthouseEvent?.confidence ?? 0;

    // Gate: only trade if Lighthouse confidence exceeds threshold
    if (confidence < CONFIDENCE_GATE) return false;

    // Sample empirical trade return
    const ret = rets[Math.floor(Math.random() * rets.length)];

    // Prime-scaled fraction
    const prime = PRIMES[this.primeIdx % PRIMES.length];
    this.primeIdx++;
    const frac = prime * PRIME_SCALE;

    // Apply trade
    const pnl = this.equity * frac * ret;
    this.equity += pnl;
    this.trades++;
    if (ret > 0) this.wins++;

    return true;
  }

  hasReachedTarget(): boolean {
    return this.equity >= TARGET;
  }
}

const agents: HiveAgent[] = [];
for (let i = 0; i < NUM_AGENTS; i++) {
  agents.push(new HiveAgent(i));
}

let globalTrades = 0;
let successCount = 0;
const successTrades: number[] = [];

for (let t = 0; t < MAX_TRADES; t++) {
  for (let a = 0; a < NUM_AGENTS; a++) {
    const agent = agents[a];
    if (!agent.hasReachedTarget()) {
      if (agent.trade()) {
        globalTrades++;
        if (agent.hasReachedTarget()) {
          successCount++;
          successTrades.push(globalTrades);
          console.log(`  Agent ${a} reached target at trade ${globalTrades}`);
        }
      }
    }
  }

  if ((t + 1) % 10000 === 0) {
    console.log(`Step ${t + 1}: ${successCount}/${NUM_AGENTS} successful (${globalTrades} global trades)`);
  }

  if (successCount === NUM_AGENTS) {
    console.log(`✅ All agents succeeded at trade ${globalTrades}`);
    break;
  }
}

const equities = agents.map(a => a.equity);
const totalEq = equities.reduce((a, b) => a + b, 0);
const avgEq = totalEq / NUM_AGENTS;
const totalTrades = agents.reduce((a, b) => a + b.trades, 0);
const totalWins = agents.reduce((a, b) => a + b.wins, 0);

console.log('\n📊 Hive Baseline Results');
console.log(`Success rate: ${(successCount / NUM_AGENTS * 100).toFixed(2)}%`);
console.log(`Successful agents: ${successCount}/${NUM_AGENTS}`);
console.log(`Avg equity: £${avgEq.toFixed(2)}`);
console.log(`Total equity: £${totalEq.toFixed(2)}`);
console.log(`Total trades: ${totalTrades}`);
console.log(`Global trades: ${globalTrades}`);
console.log(`Aggregate win rate: ${(totalWins / totalTrades * 100).toFixed(2)}%`);

if (successTrades.length > 0) {
  successTrades.sort((a, b) => a - b);
  const med = successTrades[Math.floor(successTrades.length / 2)];
  console.log(`Median trades to target: ${med}`);
}

try {
  fs.writeFileSync('hive_baseline.json', JSON.stringify(
    { params: { NUM_AGENTS, PRIME_SCALE, MAX_TRADES, TARGET, START }, successCount, successRate: successCount / NUM_AGENTS, avgEq, totalEq },
    null, 2
  ));
  console.log('Wrote hive_baseline.json');
} catch (err) {
  console.warn('Could not write:', (err as Error).message);
}
