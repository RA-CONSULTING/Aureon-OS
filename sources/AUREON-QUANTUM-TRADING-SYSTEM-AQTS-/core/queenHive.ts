// Queen-Hive with 10-9-1 Revenue Sharing
// 100% profit → 90% stays in hive (compound growth), 10% harvested for spawning new hives
// Exponential hive multiplication with controlled capital allocation

import fs from 'node:fs';

export interface HiveMetrics {
  id: string;
  generation: number;
  agents: number;
  equity: number;
  harvestedCapital: number;
  trades: number;
  successfulAgents: number;
  stage: string;
  age: number;
  profitMultiplier: number;
}

export interface QueenHiveState {
  timestamp: number;
  totalHives: number;
  totalAgents: number;
  totalEquity: number;
  totalHarvested: number;
  hives: HiveMetrics[];
  generation: number;
  splitEvents: Array<{ step: number; newHiveId: string; spawnCapital: number }>;
}

const TRADE_CSV = 'backtest_trades.csv';
if (!fs.existsSync(TRADE_CSV)) {
  throw new Error('backtest_trades.csv missing');
}

const csv = fs.readFileSync(TRADE_CSV, 'utf-8').trim().split('\n');
csv.shift();
const rets = csv.map(r => Number(r.split(',')[6]));

const PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97];

class Agent {
  id: number;
  equity: number;
  startEquity: number;
  trades: number = 0;
  wins: number = 0;
  primeIdx: number;

  constructor(id: number, start: number, primeIdxOffset: number = 0) {
    this.id = id;
    this.equity = start;
    this.startEquity = start;
    this.primeIdx = (id + primeIdxOffset) % PRIMES.length;
  }

  trade(): { pnl: number; return: number } {
    if (this.equity <= 0) return { pnl: 0, return: 0 };
    const ret = rets[Math.floor(Math.random() * rets.length)];
    const prime = PRIMES[this.primeIdx % PRIMES.length];
    this.primeIdx++;
    const frac = prime * 0.01;
    const pnl = this.equity * frac * ret;
    this.equity += pnl;
    this.trades++;
    if (ret > 0) this.wins++;
    return { pnl, return: ret };
  }

  getProfitSinceStart(): number {
    return this.equity - this.startEquity;
  }
}

class Hive {
  id: string;
  generation: number;
  agents: Agent[];
  trades: number = 0;
  harvestedCapital: number = 0;
  age: number = 0;
  agentPerHive: number;
  startEquityPerAgent: number;
  targetPerAgent: number;
  successfulAgents: number = 0;

  constructor(
    id: string,
    generation: number,
    agentCount: number,
    startEquityPerAgent: number,
    targetPerAgent: number
  ) {
    this.id = id;
    this.generation = generation;
    this.agentPerHive = agentCount;
    this.startEquityPerAgent = startEquityPerAgent;
    this.targetPerAgent = targetPerAgent;

    this.agents = [];
    for (let i = 0; i < agentCount; i++) {
      this.agents.push(new Agent(i, startEquityPerAgent, generation * 1000 + i));
    }
  }

  step(): void {
    for (const agent of this.agents) {
      if (agent.equity > 0 && agent.equity < this.targetPerAgent) {
        agent.trade();
        this.trades++;
        if (agent.equity >= this.targetPerAgent) {
          this.successfulAgents++;
        }
      }
    }
    this.age++;
  }

  // 10-9-1 allocation: extract 10% of profit for new hive spawning
  harvestCapital(): number {
    const totalEquity = this.getTotalEquity();
    const startTotal = this.startEquityPerAgent * this.agentPerHive;
    const totalProfit = Math.max(0, totalEquity - startTotal);
    const harvestAmount = totalProfit * 0.1;
    this.harvestedCapital += harvestAmount;

    for (const agent of this.agents) {
      const agentProfit = agent.getProfitSinceStart();
      const agentHarvest = agentProfit * 0.1;
      agent.equity -= agentHarvest;
    }

    return harvestAmount;
  }

  getTotalEquity(): number {
    return this.agents.reduce((sum, a) => sum + a.equity, 0);
  }

  getProfitMultiplier(): number {
    const startTotal = this.startEquityPerAgent * this.agentPerHive;
    return this.getTotalEquity() / startTotal;
  }

  canSplit(): boolean {
    return this.successfulAgents >= this.agentPerHive * 0.5;
  }

  getMetrics(): HiveMetrics {
    const stage = this.successfulAgents === this.agentPerHive ? 'mature' : this.canSplit() ? 'ready_to_split' : 'growing';
    return {
      id: this.id,
      generation: this.generation,
      agents: this.agentPerHive,
      equity: this.getTotalEquity(),
      harvestedCapital: this.harvestedCapital,
      trades: this.trades,
      successfulAgents: this.successfulAgents,
      stage,
      age: this.age,
      profitMultiplier: this.getProfitMultiplier(),
    };
  }
}

export class QueenHive {
  hives: Map<string, Hive> = new Map();
  harvestPool: number = 0;
  maxGeneration: number = 0;
  agentPerHive: number;
  startEquityPerAgent: number;
  targetPerAgent: number;
  splitEvents: Array<{ step: number; newHiveId: string; spawnCapital: number }> = [];
  globalStep: number = 0;

  constructor(agentPerHive: number = 100, startEquity: number = 100, targetPerAgent: number = 1_000_000) {
    this.agentPerHive = agentPerHive;
    this.startEquityPerAgent = startEquity;
    this.targetPerAgent = targetPerAgent;

    const firstHive = new Hive('hive-0', 0, agentPerHive, startEquity, targetPerAgent);
    this.hives.set(firstHive.id, firstHive);
  }

  step(): QueenHiveState {
    // Execute trading for all hives
    for (const hive of this.hives.values()) {
      hive.step();
    }

    // Harvest 10% from hives when they've doubled their starting capital
    for (const hive of this.hives.values()) {
      if (hive.getProfitMultiplier() >= 2) {
        const harvestedThisHive = hive.harvestCapital();
        this.harvestPool += harvestedThisHive;
      }
    }

    // Check for splits: if harvest pool >= cost of new hive, spawn new hive
    const newHiveCost = this.startEquityPerAgent * this.agentPerHive;
    while (this.harvestPool >= newHiveCost) {
      const hivesToSplit = Array.from(this.hives.values()).filter(h => h.getProfitMultiplier() >= 1.5);
      if (hivesToSplit.length > 0) {
        const newHiveId = `hive-${this.hives.size}`;
        const parentGen = hivesToSplit[0].generation;
        const newGeneration = parentGen + 1;
        const newHive = new Hive(newHiveId, newGeneration, this.agentPerHive, this.startEquityPerAgent, this.targetPerAgent);
        this.hives.set(newHiveId, newHive);
        this.harvestPool -= newHiveCost;
        this.splitEvents.push({ step: this.globalStep, newHiveId, spawnCapital: newHiveCost });
        this.maxGeneration = Math.max(this.maxGeneration, newGeneration);
      } else {
        break;
      }
    }

    this.globalStep++;
    return this.getState();
  }

  getState(): QueenHiveState {
    const hiveMetrics = Array.from(this.hives.values()).map(h => h.getMetrics());
    const totalEquity = hiveMetrics.reduce((sum, m) => sum + m.equity, 0);
    const totalAgents = hiveMetrics.reduce((sum, m) => sum + m.agents, 0);
    const totalHarvested = hiveMetrics.reduce((sum, m) => sum + m.harvestedCapital, 0) + this.harvestPool;

    return {
      timestamp: Date.now(),
      totalHives: this.hives.size,
      totalAgents,
      totalEquity,
      totalHarvested,
      hives: hiveMetrics,
      generation: this.maxGeneration,
      splitEvents: this.splitEvents,
    };
  }

  run(maxSteps: number, logInterval: number = 1000): QueenHiveState {
    for (let s = 0; s < maxSteps; s++) {
      const state = this.step();

      if ((s + 1) % logInterval === 0) {
        const harvestPercent = (state.totalHarvested / (state.totalEquity + state.totalHarvested) * 100).toFixed(1);
        console.log(
          `Step ${s + 1}: Hives=${state.totalHives} | Agents=${state.totalAgents} | Equity=£${state.totalEquity.toFixed(0)} | Harvested=£${state.totalHarvested.toFixed(0)} (${harvestPercent}%)`
        );
      }
    }

    return this.getState();
  }
}
