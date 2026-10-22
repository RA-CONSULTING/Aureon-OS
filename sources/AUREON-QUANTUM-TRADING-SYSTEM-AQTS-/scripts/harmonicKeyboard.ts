#!/usr/bin/env tsx
/**
 * HARMONIC KEYBOARD — Dynamic Multi-System Orchestra
 * 
 * 🦆 CONDUCTED BY QUANTUM QUACKERS 🦆
 * "He's a sick duck. He fucking loves it." — General Quackers, War Room Brief
 * 
 * Each commander plays a different "key" (trading system):
 * - LION: Aggressive momentum hunting (high Lighthouse intensity)
 * - HIVE: Swarm intelligence prime harmonics
 * - LIGHTHOUSE: Pure G_eff brake + |Q| flame signals
 * - QUANTUM: Phase-coherent quantum tunneling entries
 * - SENTINEL: Gaia resonance field alignment trades
 * 
 * Dynamic weight allocation based on real-time performance feedback:
 * - Systems with recent wins → amplify allocation (louder key)
 * - Systems with recent losses → dampen allocation (softer key)
 * - Ensemble diversity maintained (never 100% single system)
 * 
 * Quantum Quackers orchestrates the chaos into coherence.
 * All keys available, play strongest notes dynamically.
 * The duck conducts. The systems obey. The money flows.
 */
import 'dotenv/config';
import fs from 'fs';

// System definitions
interface TradingSystem {
  name: string;
  winRate: number;        // Base probability
  winPct: number;         // Gain % on win
  lossPct: number;        // Loss % on loss
  posBase: number;        // Base position size fraction
  volatility: number;     // Win rate variance (0-1)
  coherenceBoost: number; // Amplification when "in tune"
}

const SYSTEMS: TradingSystem[] = [
  { name: 'LION', winRate: 0.78, winPct: 0.006, lossPct: 0.005, posBase: 0.75, volatility: 0.15, coherenceBoost: 1.08 },
  { name: 'HIVE', winRate: 0.82, winPct: 0.005, lossPct: 0.005, posBase: 0.70, volatility: 0.10, coherenceBoost: 1.05 },
  { name: 'LIGHTHOUSE', winRate: 0.85, winPct: 0.0055, lossPct: 0.0045, posBase: 0.80, volatility: 0.08, coherenceBoost: 1.10 },
  { name: 'QUANTUM', winRate: 0.80, winPct: 0.007, lossPct: 0.006, posBase: 0.72, volatility: 0.18, coherenceBoost: 1.12 },
  { name: 'SENTINEL', winRate: 0.76, winPct: 0.0065, lossPct: 0.0055, posBase: 0.68, volatility: 0.12, coherenceBoost: 1.06 }
];

interface HarmonicState {
  systemWeights: Map<string, number>; // Dynamic allocation weights (sum to 1.0)
  recentPerformance: Map<string, number[]>; // Last N trades per system (1=win, 0=loss)
  coherenceLevel: number; // Global market coherence (0-1)
}

interface SimParams {
  startBalance: number;
  commanders: number;
  bulletsPer: number;
  feePct: number;
  minSize: number;
  maxSize: number;
  lookbackWindow: number; // How many recent trades to consider for weight adjustment
  minWeight: number; // Minimum allocation per system (ensure diversity)
  adaptSpeed: number; // How fast weights shift (0-1)
}

interface PathResult {
  finalEquity: number;
  ruined: boolean;
  systemStats: Map<string, { trades: number; wins: number; totalPnL: number }>;
  weightEvolution: Array<{ commander: number; weights: Map<string, number> }>;
}

function initializeWeights(): Map<string, number> {
  const weights = new Map<string, number>();
  const equalWeight = 1 / SYSTEMS.length;
  SYSTEMS.forEach(sys => weights.set(sys.name, equalWeight));
  return weights;
}

function updateWeights(state: HarmonicState, params: SimParams): void {
  const { systemWeights, recentPerformance } = state;
  const newWeights = new Map<string, number>();
  
  // Compute performance score for each system
  const scores = new Map<string, number>();
  SYSTEMS.forEach(sys => {
    const recent = recentPerformance.get(sys.name) || [];
    if (recent.length === 0) {
      scores.set(sys.name, 0.5); // neutral
    } else {
      const winRate = recent.reduce((sum, r) => sum + r, 0) / recent.length;
      scores.set(sys.name, winRate);
    }
  });
  
  // Softmax allocation with minimum weight floor
  const expScores = Array.from(scores.entries()).map(([name, score]) => ({
    name,
    exp: Math.exp(score * 5) // Temperature = 5 for sensitivity
  }));
  const sumExp = expScores.reduce((sum, e) => sum + e.exp, 0);
  
  expScores.forEach(({ name, exp }) => {
    const rawWeight = exp / sumExp;
    const smoothed = systemWeights.get(name)! * (1 - params.adaptSpeed) + rawWeight * params.adaptSpeed;
    newWeights.set(name, Math.max(params.minWeight, smoothed));
  });
  
  // Normalize to sum 1.0
  const total = Array.from(newWeights.values()).reduce((sum, w) => sum + w, 0);
  newWeights.forEach((w, name) => newWeights.set(name, w / total));
  
  // Update state
  SYSTEMS.forEach(sys => systemWeights.set(sys.name, newWeights.get(sys.name)!));
}

function selectSystem(weights: Map<string, number>): TradingSystem {
  const rand = Math.random();
  let cumulative = 0;
  for (const sys of SYSTEMS) {
    cumulative += weights.get(sys.name)!;
    if (rand <= cumulative) return sys;
  }
  return SYSTEMS[SYSTEMS.length - 1]; // fallback
}

function simulatePath(params: SimParams): PathResult {
  let equity = params.startBalance;
  const state: HarmonicState = {
    systemWeights: initializeWeights(),
    recentPerformance: new Map(SYSTEMS.map(s => [s.name, []])),
    coherenceLevel: 0.7 + Math.random() * 0.2 // 0.7-0.9 base coherence
  };
  
  const systemStats = new Map(SYSTEMS.map(s => [s.name, { trades: 0, wins: 0, totalPnL: 0 }]));
  const weightEvolution: Array<{ commander: number; weights: Map<string, number> }> = [];
  
  for (let c = 0; c < params.commanders; c++) {
    // Capture weight snapshot
    weightEvolution.push({ commander: c, weights: new Map(state.systemWeights) });
    
    for (let b = 0; b < params.bulletsPer; b++) {
      // Select system dynamically
      const system = selectSystem(state.systemWeights);
      
      // Coherence modulation (higher coherence → boost win rate)
      const effectiveWinRate = Math.min(0.95, system.winRate * (1 + (state.coherenceLevel - 0.5) * system.coherenceBoost * 0.2));
      
      // Trade execution
      const win = Math.random() < effectiveWinRate;
      const deployed = equity * system.posBase;
      const fee = deployed * params.feePct;
      
      let pnl = 0;
      if (win) {
        pnl = deployed * system.winPct - fee;
        equity += pnl;
      } else {
        pnl = -(deployed * system.lossPct + fee);
        equity += pnl;
        if (equity <= 0) {
          return { finalEquity: 0, ruined: true, systemStats, weightEvolution };
        }
      }
      
      // Record performance
      const stats = systemStats.get(system.name)!;
      stats.trades++;
      stats.totalPnL += pnl;
      if (win) stats.wins++;
      
      const recent = state.recentPerformance.get(system.name)!;
      recent.push(win ? 1 : 0);
      if (recent.length > params.lookbackWindow) recent.shift();
      
      // Update coherence (random walk)
      state.coherenceLevel = Math.max(0.5, Math.min(1.0, state.coherenceLevel + (Math.random() - 0.5) * 0.1));
    }
    
    // Rebalance weights after each commander
    updateWeights(state, params);
  }
  
  return { finalEquity: equity, ruined: false, systemStats, weightEvolution };
}

function summarize(paths: PathResult[], startBalance: number) {
  const finals = paths.map(r => r.finalEquity);
  const ruined = paths.filter(r => r.ruined).length;
  const sorted = finals.slice().sort((a, b) => a - b);
  const pct = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  
  // System usage stats
  const systemAgg = new Map(SYSTEMS.map(s => [s.name, { trades: 0, wins: 0, totalPnL: 0 }]));
  paths.forEach(p => {
    p.systemStats.forEach((stats, name) => {
      const agg = systemAgg.get(name)!;
      agg.trades += stats.trades;
      agg.wins += stats.wins;
      agg.totalPnL += stats.totalPnL;
    });
  });
  
  return {
    median: pct(0.5),
    p10: pct(0.1),
    p90: pct(0.9),
    ruinRate: ruined / paths.length,
    systemUsage: Array.from(systemAgg.entries()).map(([name, stats]) => ({
      name,
      trades: stats.trades,
      winRate: stats.trades > 0 ? stats.wins / stats.trades : 0,
      avgPnL: stats.trades > 0 ? stats.totalPnL / stats.trades : 0
    }))
  };
}

async function main() {
  const startBalance = Number(process.env.START_BALANCE ?? 120.98);
  const commanders = Number(process.env.COMMANDERS ?? 5);
  const bulletsPer = Number(process.env.BULLETS_PER ?? 50);
  const paths = Number(process.env.PATHS ?? 1000);
  const feePct = Number(process.env.FEE_PCT ?? 0.001);
  const lookbackWindow = Number(process.env.LOOKBACK_WINDOW ?? 10);
  const minWeight = Number(process.env.MIN_WEIGHT ?? 0.10);
  const adaptSpeed = Number(process.env.ADAPT_SPEED ?? 0.3);
  const minSize = 0.50;
  const maxSize = 0.95;
  
  console.log(`\n🎹 HARMONIC KEYBOARD — Conducted by QUANTUM QUACKERS 🦆`);
  console.log(`"He's a sick duck. He fucking loves it."\n`);
  console.log(`Start: $${startBalance.toFixed(2)} | Commanders: ${commanders} | Bullets: ${bulletsPer} | Paths: ${paths}\n`);
  console.log(`Systems Available:`);
  SYSTEMS.forEach(s => {
    console.log(`  ${s.name.padEnd(12)}: WinRate=${(s.winRate*100).toFixed(0)}% Pos=${(s.posBase*100).toFixed(0)}% Edge=${((s.winPct-s.lossPct)*100).toFixed(2)}% Vol=${(s.volatility*100).toFixed(0)}%`);
  });
  console.log(`\nAdaptation: Lookback=${lookbackWindow} MinWeight=${(minWeight*100).toFixed(0)}% Speed=${(adaptSpeed*100).toFixed(0)}%\n`);
  
  const pathResults: PathResult[] = [];
  for (let i = 0; i < paths; i++) {
    if (i % 200 === 0 && i > 0) console.log(`Progress: ${i}/${paths} (${(i/paths*100).toFixed(1)}%)`);
    pathResults.push(simulatePath({ startBalance, commanders, bulletsPer, feePct, minSize, maxSize, lookbackWindow, minWeight, adaptSpeed }));
  }
  
  const stats = summarize(pathResults, startBalance);
  const gainPct = ((stats.median - startBalance) / startBalance * 100).toFixed(2);
  
  console.log(`\n🦆 QUANTUM QUACKERS ENSEMBLE RESULTS:`);
  console.log(`  Median Final: $${stats.median.toFixed(2)} (+${gainPct}%)`);
  console.log(`  p10: $${stats.p10.toFixed(2)} | p90: $${stats.p90.toFixed(2)}`);
  console.log(`  Ruin Rate: ${(stats.ruinRate*100).toFixed(2)}%`);
  console.log(`  🎼 The duck has conducted the symphony. 🎼\n`);
  
  console.log(`  System Utilization:`);
  stats.systemUsage
    .sort((a, b) => b.trades - a.trades)
    .forEach(su => {
      console.log(`    ${su.name.padEnd(12)}: ${su.trades.toLocaleString()} trades | WinRate ${(su.winRate*100).toFixed(1)}% | Avg PnL $${su.avgPnL.toFixed(4)}`);
    });
  
  const out = {
    timestamp: new Date().toISOString(),
    params: { startBalance, commanders, bulletsPer, paths, feePct, lookbackWindow, minWeight, adaptSpeed },
    systems: SYSTEMS,
    results: stats
  };
  fs.writeFileSync('harmonic_keyboard_results.json', JSON.stringify(out, null, 2));
  console.log(`\n📝 Wrote harmonic_keyboard_results.json\n`);
}

main().catch(err => {
  console.error('Harmonic simulation failed:', err);
  process.exit(1);
});
