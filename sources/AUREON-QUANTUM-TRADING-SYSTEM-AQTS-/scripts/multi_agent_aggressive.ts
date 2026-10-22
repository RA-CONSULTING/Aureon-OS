#!/usr/bin/env tsx
import fs from 'node:fs';

// Enhanced multi-agent: aggressive prime-based scaling + Fibonacci timing
// Goal: reach £1M from £100 per agent across 100 parallel agents

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  console.error('backtest_trades.csv missing');
  process.exit(1);
}

const csv = fs.readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
csv.shift();
const rows = csv.map(r => r.split(','));
const rets = rows.map(r => Number(r[6]));

console.log(`Loaded ${rets.length} empirical returns (mean: ${(rets.reduce((a, b) => a + b, 0) / rets.length).toExponential(6)})`);

function generatePrimes(n: number): number[] {
  const primes: number[] = [];
  let candidate = 2;
  while (primes.length < n) {
    let isPrime = true;
    for (let p of primes) {
      if (p * p > candidate) break;
      if (candidate % p === 0) {
        isPrime = false;
        break;
      }
    }
    if (isPrime) primes.push(candidate);
    candidate++;
  }
  return primes;
}

function generateFibonacci(n: number): number[] {
  const fib: number[] = [1, 1];
  while (fib.length < n) {
    fib.push(fib[fib.length - 1] + fib[fib.length - 2]);
  }
  return fib;
}

const primes = generatePrimes(100);
const fibs = generateFibonacci(30);

// Aggressive scaling: use prime * scale_factor
const PRIME_SCALE = Number(process.env.PRIME_SCALE ?? 0.001); // 0.1% per unit prime => 0.2%, 0.3%, 0.5%, etc.

class AgentV2 {
  id: number;
  equity: number;
  trades: number = 0;
  primeIdx: number = 0;
  fibIdx: number = 0;
  targetTrades: number = 1; // Fibonacci-scheduled trades

  constructor(id: number, startEquity: number) {
    this.id = id;
    this.equity = startEquity;
  }

  executeTrade(): boolean {
    if (this.equity <= 0) return false;

    const prime = primes[this.primeIdx % primes.length];
    const fraction = prime * PRIME_SCALE;
    this.primeIdx++;

    const ret = rets[Math.floor(Math.random() * rets.length)];
    const pnl = this.equity * fraction * ret;
    this.equity += pnl;
    this.trades++;

    return this.equity > 0;
  }

  scheduleNextBatch(): number {
    // Next batch of trades scheduled by Fibonacci
    const nextFibCount = fibs[this.fibIdx % fibs.length];
    this.fibIdx++;
    return nextFibCount;
  }

  hasReachedTarget(): boolean {
    return this.equity >= 1_000_000;
  }
}

const NUM_AGENTS = 100;
const START_PER_AGENT = 100;
const MAX_GLOBAL_TRADES = 1_000_000; // 1M global trades

console.log(`\nMulti-Agent Simulation (Aggressive):`);
console.log(`  Agents: ${NUM_AGENTS}`);
console.log(`  Start per agent: £${START_PER_AGENT}`);
console.log(`  Prime scale: ${PRIME_SCALE}`);
console.log(`  Max global trades: ${MAX_GLOBAL_TRADES}`);

const agents: AgentV2[] = [];
for (let i = 0; i < NUM_AGENTS; i++) {
  agents.push(new AgentV2(i, START_PER_AGENT));
}

let globalTrades = 0;
let successCount = 0;
const successTimes: number[] = [];
const agentTradeCount: number[] = new Array(NUM_AGENTS).fill(0);

// Round-robin: each agent trades in sequence
for (let step = 0; step < MAX_GLOBAL_TRADES && successCount < NUM_AGENTS; step++) {
  for (let agentIdx = 0; agentIdx < NUM_AGENTS; agentIdx++) {
    const agent = agents[agentIdx];
    if (!agent.hasReachedTarget() && agent.equity > 0) {
      if (agent.executeTrade()) {
        globalTrades++;
        agentTradeCount[agentIdx]++;
        if (agent.hasReachedTarget()) {
          successCount++;
          successTimes.push(globalTrades);
          console.log(`  Agent ${agentIdx} reached £1M at trade ${globalTrades}`);
        }
      }
    }
  }

  if ((step + 1) % 100000 === 0) {
    console.log(`    Step ${step + 1}: ${successCount}/${NUM_AGENTS} agents at target`);
  }
}

console.log(`\n📊 Results (Aggressive Multi-Agent)`);
console.log(`Success rate: ${(successCount / NUM_AGENTS * 100).toFixed(2)}%`);
console.log(`Agents reaching £1M: ${successCount}/${NUM_AGENTS}`);
console.log(`Total global trades: ${globalTrades}`);

const equities = agents.map(a => a.equity);
const avgEquity = equities.reduce((a, b) => a + b, 0) / NUM_AGENTS;
const maxEquity = Math.max(...equities);
const totalEquity = equities.reduce((a, b) => a + b, 0);

console.log(`Avg equity per agent: £${avgEquity.toFixed(2)}`);
console.log(`Max equity: £${maxEquity.toFixed(2)}`);
console.log(`Total aggregate: £${totalEquity.toFixed(2)}`);

if (successTimes.length > 0) {
  successTimes.sort((a, b) => a - b);
  const med = successTimes[Math.floor(successTimes.length / 2)];
  const min = successTimes[0];
  const max = successTimes[successTimes.length - 1];
  console.log(`Success trades: min=${min}, median=${med}, max=${max}`);

  const medDays = Math.ceil(med / 100); // assume 100 trades/day total
  console.log(`Median calendar days to 1M (at 100 trades/day): ~${medDays}`);
}

try {
  fs.writeFileSync('multi_agent_aggressive_results.json', JSON.stringify(
    {
      params: { NUM_AGENTS, START_PER_AGENT, PRIME_SCALE, MAX_GLOBAL_TRADES },
      successRate: successCount / NUM_AGENTS,
      successfulAgents: successCount,
      totalGlobalTrades: globalTrades,
      avgEquity,
      maxEquity,
      totalEquity,
      successTimes,
    },
    null,
    2
  ));
  console.log('Wrote multi_agent_aggressive_results.json');
} catch (err) {
  console.warn('Could not write:', (err as Error).message);
}
