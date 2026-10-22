// Hive Controller: orchestrates 100+ trading agents (magets)
// Each agent uses prime-based position scaling and Fibonacci timing
// Aggregate tracking and risk management across all agents

import { AQTSOrchestrator } from './aqtsOrchestrator';
import { DeepPartial, AQTSConfig } from './config';

export interface HiveAgent {
  id: number;
  equity: number;
  startEquity: number;
  trades: number;
  wins: number;
  losses: number;
  maxDrawdown: number;
  primeIdx: number;
  fibIdx: number;
  orchestrator: AQTSOrchestrator;
  active: boolean;
}

export interface HiveState {
  timestamp: number;
  agents: HiveAgent[];
  totalEquity: number;
  averageEquity: number;
  aggregateTradeCount: number;
  successfulAgents: number; // agents that have reached target
  targetEquity: number;
}

const PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97];
const FIBS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377];

export class HiveController {
  agents: HiveAgent[] = [];
  numAgents: number;
  primeScale: number;
  targetEquity: number;
  agentStartEquity: number;
  stepCount: number = 0;

  constructor(
    numAgents: number = 100,
    agentStartEquity: number = 100,
    primeScale: number = 0.01,
    targetEquity: number = 1_000_000,
    configOverrides?: DeepPartial<AQTSConfig>
  ) {
    this.numAgents = numAgents;
    this.agentStartEquity = agentStartEquity;
    this.primeScale = primeScale;
    this.targetEquity = targetEquity;

    for (let i = 0; i < numAgents; i++) {
      const agent: HiveAgent = {
        id: i,
        equity: agentStartEquity,
        startEquity: agentStartEquity,
        trades: 0,
        wins: 0,
        losses: 0,
        maxDrawdown: 0,
        primeIdx: i % PRIMES.length, // stagger prime sequence
        fibIdx: 0,
        orchestrator: new AQTSOrchestrator(configOverrides),
        active: true,
      };
      this.agents.push(agent);
    }
  }

  // Execute one trading step for all active agents
  step(): HiveState {
    for (const agent of this.agents) {
      if (!agent.active || agent.equity <= 0) {
        agent.active = false;
        continue;
      }

      if (agent.equity >= this.targetEquity) {
        agent.active = false;
        continue;
      }

      // Get next orchestrator output (QGITA signal, risk-adjusted order, execution)
      const output = agent.orchestrator.next();

      if (output.order && output.execution) {
        const order = output.order;
        const exec = output.execution;
        const mark = output.snapshot.consolidatedOHLCV.close;

        // Prime-scaled position sizing amplifies orchestrator's order notional
        const prime = PRIMES[agent.primeIdx % PRIMES.length];
        agent.primeIdx++;
        const primeMultiplier = prime * this.primeScale; // e.g., 2*0.01=0.02, 3*0.01=0.03

        // Scale the orchestrator's recommended notional by prime multiplier
        const scaledNotional = order.notional * primeMultiplier;

        // Compute trade return using executed price vs mark
        const directionMultiplier = order.direction === 'long' ? 1 : -1;
        const entry = exec.averagePrice;
        const positionReturn = ((mark - entry) / entry) * directionMultiplier;
        const pnl = scaledNotional * positionReturn / entry; // pnl = position_value * return

        agent.equity += pnl;
        agent.trades++;

        if (positionReturn > 0) {
          agent.wins++;
        } else {
          agent.losses++;
        }

        // Track drawdown
        const dd = Math.abs(Math.min(0, positionReturn));
        agent.maxDrawdown = Math.max(agent.maxDrawdown, dd);
      }
    }

    this.stepCount++;
    return this.getState();
  }

  getState(): HiveState {
    const totalEquity = this.agents.reduce((acc, a) => acc + a.equity, 0);
    const averageEquity = totalEquity / Math.max(1, this.agents.length);
    const aggregateTradeCount = this.agents.reduce((acc, a) => acc + a.trades, 0);
    const successfulAgents = this.agents.filter(a => a.equity >= this.targetEquity).length;

    return {
      timestamp: Date.now(),
      agents: this.agents,
      totalEquity,
      averageEquity,
      aggregateTradeCount,
      successfulAgents,
      targetEquity: this.targetEquity,
    };
  }

  getMetrics() {
    const state = this.getState();
    const activeAgents = this.agents.filter(a => a.active).length;
    const winRate = this.agents.reduce((acc, a) => acc + a.wins, 0) / Math.max(1, state.aggregateTradeCount);

    return {
      ...state,
      activeAgents,
      winRate,
      successRate: state.successfulAgents / this.numAgents,
    };
  }

  reset() {
    for (const agent of this.agents) {
      agent.equity = agent.startEquity;
      agent.trades = 0;
      agent.wins = 0;
      agent.losses = 0;
      agent.maxDrawdown = 0;
      agent.active = true;
      agent.orchestrator.reset();
    }
    this.stepCount = 0;
  }
}
