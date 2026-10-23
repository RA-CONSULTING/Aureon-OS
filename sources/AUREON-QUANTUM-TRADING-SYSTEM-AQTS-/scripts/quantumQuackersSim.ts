
/**
 * ⚡🦆🔥 QUANTUM QUACKERS: TARGET PRACTICE SIMULATION 🔥🦆⚡
 * 
 * "We are snipers. We make sure we know the targets."
 * "The Elephant doesn't forget."
 * "Domino Effect: Chainlink awareness."
 * 
 * OBJECTIVE:
 * - Run 10 Agents (Quackers 1-10).
 * - 50 Trades per Agent.
 * - Compounding Profits (Honey Pot).
 * - Shared Hive Awareness (Domino Effect).
 * - Elephant Memory Integration.
 */

import { ElephantMemory } from '../core/elephantMemory';
import * as fs from 'fs';
import * as path from 'path';

// --- CONFIGURATION ---
const NUM_AGENTS = 10;
const TRADES_PER_AGENT = 50;
const STARTING_BALANCE = 100; // $100 per agent
const FEE_RATE = 0.001; // 0.1% per side
const SLIPPAGE = 0.0005; // 0.05% slippage
const WIN_RATE_BASE = 0.65; // Base win rate (Snipers are good)
const DOMINO_BOOST = 0.15; // Boost when hive is winning
const COMPOUND_RATE = 1.0; // 100% reinvestment

// --- SYMBOLS ---
const TARGETS = [
  'BTCUSDC', 'ETHUSDC', 'BNBUSDC', 'SOLUSDC', 
  'XRPUSDC', 'DOGEUSDC', 'ADAUSDC', 'AVAXUSDC', 
  'LINKUSDC', 'DOTUSDC', 'MATICUSDC', 'SHIBUSDC'
];

// --- HIVE MIND (SHARED STATE) ---
interface HiveState {
  recentWins: number;
  recentLosses: number;
  momentum: number; // -1 to 1
  lastKill: string | null;
}

const hive: HiveState = {
  recentWins: 0,
  recentLosses: 0,
  momentum: 0,
  lastKill: null
};

// --- AGENT CLASS ---
class QuantumQuacker {
  id: number;
  balance: number;
  trades: number;
  wins: number;
  losses: number;
  history: any[];

  constructor(id: number, startBalance: number) {
    this.id = id;
    this.balance = startBalance;
    this.trades = 0;
    this.wins = 0;
    this.losses = 0;
    this.history = [];
  }

  async hunt(memory: ElephantMemory) {
    if (this.trades >= TRADES_PER_AGENT) return;

    // 1. Select Target (Elephant Memory Influence)
    const symbol = TARGETS[Math.floor(Math.random() * TARGETS.length)];
    const stats = memory.getSymbolStats(symbol);
    
    // Elephant Memory: If we have a good history, boost confidence
    let memoryBoost = 0;
    if (stats && stats.wins > stats.losses) {
      memoryBoost = 0.05;
    }

    // 2. Check Hive Momentum (Domino Effect)
    // If the hive is winning, we are more likely to win (correlated market)
    const hiveBoost = hive.momentum * DOMINO_BOOST;

    // 3. Simulate Trade Outcome
    // "Quantum" probability: Base + Memory + Hive
    const winProbability = WIN_RATE_BASE + memoryBoost + hiveBoost;
    const isWin = Math.random() < winProbability;

    // 4. Calculate PnL
    // Win: +0.5% to +1.5%
    // Loss: -0.3% to -0.8%
    let pnlPercent = 0;
    if (isWin) {
      pnlPercent = (Math.random() * 1.0) + 0.5; // 0.5% to 1.5%
    } else {
      pnlPercent = -((Math.random() * 0.5) + 0.3); // -0.3% to -0.8%
    }

    // Apply Fees & Slippage
    pnlPercent -= (FEE_RATE * 2 * 100); // Round trip fees
    pnlPercent -= (SLIPPAGE * 100);

    // 5. Execute Trade (Compounding)
    const tradeSize = this.balance * 0.95; // Use 95% of balance
    const pnlAmount = tradeSize * (pnlPercent / 100);
    this.balance += pnlAmount;

    // 6. Update Stats
    this.trades++;
    if (pnlAmount > 0) {
      this.wins++;
      hive.recentWins++;
      hive.momentum = Math.min(1, hive.momentum + 0.1);
      hive.lastKill = symbol;
    } else {
      this.losses++;
      hive.recentLosses++;
      hive.momentum = Math.max(-1, hive.momentum - 0.1);
    }

    // 7. Log to Elephant Memory
    memory.rememberResult(symbol, { 
      trades: 1, 
      profit: pnlAmount 
    });

    // 8. Log to Agent History
    this.history.push({
      trade: this.trades,
      symbol,
      result: isWin ? 'WIN' : 'LOSS',
      pnl: pnlAmount,
      balance: this.balance,
      hiveMomentum: hive.momentum
    });

    // 9. Broadcast to Hive (Console)
    const icon = isWin ? '🎯' : '❌';
    const pnlStr = pnlAmount >= 0 ? `+$${pnlAmount.toFixed(2)}` : `-$${Math.abs(pnlAmount).toFixed(2)}`;
    console.log(`   🦆 Q${this.id} | ${symbol.padEnd(8)} | ${icon} ${pnlStr} | Bal: $${this.balance.toFixed(2)} | 🧠 Mem: ${(memoryBoost*100).toFixed(0)}% | 🔗 Hive: ${(hiveBoost*100).toFixed(0)}%`);
  }
}

// --- MAIN SIMULATION LOOP ---
async function runSimulation() {
  console.log('\n' + '⚡'.repeat(60));
  console.log('  🦆 QUANTUM QUACKERS: TARGET PRACTICE (SIMULATION) 🦆');
  console.log('  "The Elephant Never Forgets. The Hive is One."');
  console.log('⚡'.repeat(60) + '\n');

  const memory = new ElephantMemory({ storePath: 'artifacts/sim_elephant.json' });
  const agents: QuantumQuacker[] = [];

  // Initialize Agents
  for (let i = 1; i <= NUM_AGENTS; i++) {
    agents.push(new QuantumQuacker(i, STARTING_BALANCE));
  }

  console.log(`📋 DEPLOYING ${NUM_AGENTS} AGENTS.`);
  console.log(`🎯 MISSION: ${TRADES_PER_AGENT} TRADES PER AGENT.`);
  console.log(`💰 STARTING AMMO: $${STARTING_BALANCE} per agent.`);
  console.log(`🔗 DOMINO LINK: ACTIVE.`);
  console.log('─'.repeat(60) + '\n');

  // Run Rounds
  let active = true;
  let round = 0;

  while (active) {
    round++;
    active = false;
    
    // Shuffle agents for random execution order (Quantum Chaos)
    const shuffledAgents = agents.sort(() => Math.random() - 0.5);

    for (const agent of shuffledAgents) {
      if (agent.trades < TRADES_PER_AGENT) {
        await agent.hunt(memory);
        active = true; // Keep going if at least one agent is active
      }
    }

    // Decay Hive Momentum slightly each round
    hive.momentum *= 0.95;
    
    if (round % 10 === 0) {
        console.log(`\n--- 🔄 ROUND ${round} COMPLETE ---\n`);
    }
    
    await new Promise(r => setTimeout(r, 50)); // Fast simulation
  }

  // --- REPORT CARD ---
  console.log('\n' + '🏆'.repeat(60));
  console.log('  🏁 MISSION COMPLETE: DEBRIEFING 🏁');
  console.log('🏆'.repeat(60) + '\n');

  let totalProfit = 0;
  let totalTrades = 0;
  let totalWins = 0;

  console.log('📊 AGENT PERFORMANCE:');
  console.log('─'.repeat(60));
  console.log('ID  | TRADES | WINS | LOSS | WIN RATE | FINAL BAL | PROFIT');
  console.log('─'.repeat(60));

  for (const agent of agents.sort((a, b) => a.id - b.id)) {
    const profit = agent.balance - STARTING_BALANCE;
    const winRate = (agent.wins / agent.trades) * 100;
    
    totalProfit += profit;
    totalTrades += agent.trades;
    totalWins += agent.wins;

    console.log(
      `Q${agent.id.toString().padEnd(2)} | ` +
      `${agent.trades.toString().padEnd(6)} | ` +
      `${agent.wins.toString().padEnd(4)} | ` +
      `${agent.losses.toString().padEnd(4)} | ` +
      `${winRate.toFixed(1)}%    | ` +
      `$${agent.balance.toFixed(2).padEnd(8)} | ` +
      `${profit >= 0 ? '+' : ''}$${profit.toFixed(2)}`
    );
  }

  console.log('─'.repeat(60));
  
  const globalWinRate = (totalWins / totalTrades) * 100;
  const totalStart = NUM_AGENTS * STARTING_BALANCE;
  const totalEnd = totalStart + totalProfit;
  const growth = ((totalEnd - totalStart) / totalStart) * 100;

  console.log(`\n🌍 GLOBAL STATS:`);
  console.log(`   💰 Total Starting Capital: $${totalStart.toFixed(2)}`);
  console.log(`   💰 Total Ending Capital:   $${totalEnd.toFixed(2)}`);
  console.log(`   📈 Net Profit:             $${totalProfit.toFixed(2)} (+${growth.toFixed(2)}%)`);
  console.log(`   🎯 Global Win Rate:        ${globalWinRate.toFixed(2)}%`);
  console.log(`   🐘 Elephant Memory:        UPDATED (artifacts/sim_elephant.json)`);

  console.log('\n🦆 General Quackers: "Target practice complete. The swarm is ready."');
}

runSimulation();
