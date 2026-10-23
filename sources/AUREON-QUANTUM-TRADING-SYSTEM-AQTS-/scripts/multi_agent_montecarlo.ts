#!/usr/bin/env tsx
import fs from 'node:fs';

// Multi-agent system: 100 agents, each with prime-based position scaling and Fibonacci timing
// Goal: compound from starting capital to £1M via many small trades

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  console.error('backtest_trades.csv missing — run collect_trades.ts first');
  process.exit(1);
}

const csv = fs.readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
csv.shift();
const rows = csv.map(r => r.split(','));
const rets = rows.map(r => Number(r[6]));

console.log(`Loaded ${rets.length} empirical trade returns`);

// Prime number generator for position scaling
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

// Fibonacci sequence for timing
function generateFibonacci(n: number): number[] {
  const fib: number[] = [1, 1];
  while (fib.length < n) {
    fib.push(fib[fib.length - 1] + fib[fib.length - 2]);
  }
  return fib;
}

const primes = generatePrimes(50);
const fibs = generateFibonacci(50);

console.log('Primes (first 10):', primes.slice(0, 10));
console.log('Fibonacci (first 10):', fibs.slice(0, 10));

// Single agent: uses prime-scaled fractions and Fibonacci-timed entries
class Agent {
  id: number;
  equity: number;
  trades: number = 0;
  primeIdx: number = 0;
  fibIdx: number = 0;
  targetTrades: number = 0; // set by fibonacci timing

  constructor(id: number, startEquity: number) {
    this.id = id;
    this.equity = startEquity;
  }

  nextTrade(): boolean {
    // Check if it's time to trade (Fibonacci-timed)
    if (this.trades >= this.targetTrades) {
      const nextFib = fibs[this.fibIdx % fibs.length];
      this.targetTrades = this.trades + nextFib;
      this.fibIdx++;
    }

    if (this.trades < this.targetTrades) {
      // Execute trade with prime-scaled position
      const prime = primes[this.primeIdx % primes.length];
      const baseFraction = prime / 10000; // scale primes to small fractions (e.g., 2/10k, 3/10k, etc.)
      this.primeIdx++;

      // Sample random trade from empirical data
      const ret = rets[Math.floor(Math.random() * rets.length)];
      const pnl = this.equity * baseFraction * ret;
      this.equity += pnl;
      this.trades++;

      if (this.equity <= 0) {
        return false; // agent ruined
      }
      return true;
    }
    return false; // not yet scheduled for trade
  }

  hasReachedTarget(): boolean {
    return this.equity >= 1_000_000;
  }
}

// Multi-agent simulation
const NUM_AGENTS = 100;
const START_PER_AGENT = 100;
const MAX_GLOBAL_TRADES = 500_000; // global trade budget

const agents: Agent[] = [];
for (let i = 0; i < NUM_AGENTS; i++) {
  agents.push(new Agent(i, START_PER_AGENT));
}

console.log(`\nStarting multi-agent simulation:`);
console.log(`  Agents: ${NUM_AGENTS}`);
console.log(`  Start per agent: £${START_PER_AGENT}`);
console.log(`  Max global trades: ${MAX_GLOBAL_TRADES}`);

let globalTrades = 0;
let successCount = 0;
const successTimes: number[] = [];

for (let step = 0; step < MAX_GLOBAL_TRADES; step++) {
  for (let agentIdx = 0; agentIdx < NUM_AGENTS; agentIdx++) {
    const agent = agents[agentIdx];
    if (!agent.hasReachedTarget() && agent.equity > 0) {
      agent.nextTrade();
      globalTrades++;
      if (agent.hasReachedTarget()) {
        successCount++;
        successTimes.push(globalTrades);
      }
    }
  }
  if (step % 50000 === 0 && step > 0) {
    console.log(`  Step ${step}: ${successCount}/${NUM_AGENTS} agents reached target (${(successCount / NUM_AGENTS * 100).toFixed(2)}%)`);
  }
}

console.log(`\n📊 Multi-Agent Simulation Results`);
console.log(`Success rate: ${(successCount / NUM_AGENTS * 100).toFixed(2)}%`);
console.log(`Agents reaching £1M: ${successCount}/${NUM_AGENTS}`);
console.log(`Total trades executed: ${globalTrades}`);

if (successTimes.length > 0) {
  successTimes.sort((a, b) => a - b);
  const median = successTimes[Math.floor(successTimes.length / 2)];
  const p95 = successTimes[Math.floor(successTimes.length * 0.95)];
  const p99 = successTimes[Math.floor(successTimes.length * 0.99)];
  console.log(`Median trades to target (successful agents): ${median}`);
  console.log(`95th percentile trades: ${p95}`);
  console.log(`99th percentile trades: ${p99}`);

  const medianDays = Math.ceil(median / 10); // assume ~10 trades per day per agent
  const p95Days = Math.ceil(p95 / 10);
  console.log(`Median days to target (at 10 trades/day): ${medianDays}`);
  console.log(`95th percentile days: ${p95Days}`);
}

const finalEquities = agents.map(a => a.equity);
const avgFinalEquity = finalEquities.reduce((a, b) => a + b, 0) / NUM_AGENTS;
const totalAggregateEquity = finalEquities.reduce((a, b) => a + b, 0);
console.log(`Average final equity per agent: £${avgFinalEquity.toFixed(2)}`);
console.log(`Total aggregate equity (100 agents): £${totalAggregateEquity.toFixed(2)}`);

try {
  const results = {
    params: { NUM_AGENTS, START_PER_AGENT, MAX_GLOBAL_TRADES },
    successRate: successCount / NUM_AGENTS,
    totalAgents: NUM_AGENTS,
    successfulAgents: successCount,
    totalTrades: globalTrades,
    medianTradesToTarget: successTimes.length > 0 ? successTimes[Math.floor(successTimes.length / 2)] : null,
    successTimes: successTimes.slice(0, 20), // first 20 for reference
    avgFinalEquity,
    totalAggregateEquity,
  };
  fs.writeFileSync('multi_agent_results.json', JSON.stringify(results, null, 2));
  console.log('\nWrote multi_agent_results.json');
} catch (err) {
  console.warn('Could not write results:', (err as Error).message);
}
