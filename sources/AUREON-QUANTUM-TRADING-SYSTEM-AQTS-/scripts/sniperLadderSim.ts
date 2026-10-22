#!/usr/bin/env tsx
/**
 * Sniper Ladder Simulation (Snakes & Ladders)
 * Progressively unlock aggressive parameters as equity grows.
 * 
 * LADDERS (unlock higher aggression):
 *  - 1.0x-1.3x: Conservative (70% win assumed, 65% position, 0.4%/0.6% asymmetry)
 *  - 1.3x-1.6x: Moderate (75% win, 72% position, 0.5%/0.55%)
 *  - 1.6x-2.0x: Aggressive (80% win, 78% position, 0.55%/0.5%)
 *  - 2.0x+: Beast Mode (85% win, 80% position, 0.6%/0.5%)
 * 
 * SNAKES (drawdown protection):
 *  - If equity drops 15% from tier peak → fall back one tier
 *  - Reset to tier 1 if drop below 1.1x start
 * 
 * Dynamic position sizing continues within each tier.
 */
import 'dotenv/config';
import fs from 'fs';

interface Tier {
  name: string;
  minMultiple: number;
  winRate: number;
  posBase: number;
  winPct: number;
  lossPct: number;
  growthOnWin: number;
  shrinkOnLoss: number;
}

const TIERS: Tier[] = [
  { name: 'Conservative', minMultiple: 1.0, winRate: 0.70, posBase: 0.65, winPct: 0.004, lossPct: 0.006, growthOnWin: 0.02, shrinkOnLoss: 0.04 },
  { name: 'Moderate', minMultiple: 1.3, winRate: 0.75, posBase: 0.72, winPct: 0.005, lossPct: 0.0055, growthOnWin: 0.03, shrinkOnLoss: 0.04 },
  { name: 'Aggressive', minMultiple: 1.6, winRate: 0.80, posBase: 0.78, winPct: 0.0055, lossPct: 0.005, growthOnWin: 0.035, shrinkOnLoss: 0.03 },
  { name: 'Beast', minMultiple: 2.0, winRate: 0.85, posBase: 0.80, winPct: 0.006, lossPct: 0.005, growthOnWin: 0.04, shrinkOnLoss: 0.03 }
];

interface SimParams {
  startBalance: number;
  commanders: number;
  bulletsPer: number;
  feePct: number;
  minSize: number;
  maxSize: number;
  snakeThreshold: number; // drawdown % to trigger tier downgrade
}

interface PathResult {
  finalEquity: number;
  ruined: boolean;
  tierProgression: { commander: number; tier: string; startEquity: number; endEquity: number }[];
}

function getTier(equity: number, startBalance: number, currentTierIndex: number, peakEquity: number, params: SimParams): number {
  const multiple = equity / startBalance;
  
  // Snake check: fell 15% from peak
  if (equity < peakEquity * (1 - params.snakeThreshold)) {
    // Drop one tier, minimum tier 0
    return Math.max(0, currentTierIndex - 1);
  }
  
  // Reset to tier 0 if below 1.1x
  if (multiple < 1.1) return 0;
  
  // Ladder climb: find highest unlocked tier
  for (let i = TIERS.length - 1; i >= 0; i--) {
    if (multiple >= TIERS[i].minMultiple) return i;
  }
  
  return 0;
}

function simulatePath(params: SimParams): PathResult {
  let equity = params.startBalance;
  let posFrac = TIERS[0].posBase;
  let tierIndex = 0;
  let peakEquity = equity;
  const tierProgression: { commander: number; tier: string; startEquity: number; endEquity: number }[] = [];
  
  for (let c = 0; c < params.commanders; c++) {
    const startEquity = equity;
    tierIndex = getTier(equity, params.startBalance, tierIndex, peakEquity, params);
    const tier = TIERS[tierIndex];
    posFrac = tier.posBase; // reset to tier base
    
    for (let b = 0; b < params.bulletsPer; b++) {
      const win = Math.random() < tier.winRate;
      const deployed = equity * posFrac;
      const fee = deployed * params.feePct;
      
      if (win) {
        const gain = deployed * tier.winPct - fee;
        equity += gain;
        posFrac = Math.min(params.maxSize, posFrac * (1 + tier.growthOnWin));
      } else {
        const loss = deployed * tier.lossPct + fee;
        equity -= loss;
        posFrac = Math.max(params.minSize, posFrac * (1 - tier.shrinkOnLoss));
        if (equity <= 0) {
          tierProgression.push({ commander: c, tier: tier.name, startEquity, endEquity: 0 });
          return { finalEquity: 0, ruined: true, tierProgression };
        }
      }
      
      peakEquity = Math.max(peakEquity, equity);
    }
    
    tierProgression.push({ commander: c, tier: tier.name, startEquity, endEquity: equity });
  }
  
  return { finalEquity: equity, ruined: false, tierProgression };
}

function summarize(paths: PathResult[], startBalance: number) {
  const finals = paths.map(r => r.finalEquity);
  const ruined = paths.filter(r => r.ruined).length;
  const ruinRate = ruined / paths.length;
  const sorted = finals.slice().sort((a, b) => a - b);
  const pct = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  
  // Tier reach stats
  const tierReached = { Conservative: 0, Moderate: 0, Aggressive: 0, Beast: 0 };
  paths.forEach(p => {
    const maxTier = p.tierProgression.reduce((max, tp) => 
      TIERS.findIndex(t => t.name === tp.tier) > TIERS.findIndex(t => t.name === max) ? tp.tier : max
    , 'Conservative');
    tierReached[maxTier as keyof typeof tierReached]++;
  });
  
  return {
    median: pct(0.5),
    p10: pct(0.1),
    p90: pct(0.9),
    ruinRate,
    tierReached: Object.entries(tierReached).map(([name, count]) => ({ name, pct: count / paths.length * 100 }))
  };
}

async function main() {
  const startBalance = Number(process.env.START_BALANCE ?? 120.98);
  const commanders = Number(process.env.COMMANDERS ?? 5);
  const bulletsPer = Number(process.env.BULLETS_PER ?? 50);
  const paths = Number(process.env.PATHS ?? 1000);
  const feePct = Number(process.env.FEE_PCT ?? 0.001);
  const snakeThreshold = Number(process.env.SNAKE_THRESHOLD ?? 0.15);
  const minSize = 0.50;
  const maxSize = 0.95;
  
  console.log(`\n🎲 Sniper Ladder Simulation (Snakes & Ladders)`);
  console.log(`Start: $${startBalance.toFixed(2)} | Commanders: ${commanders} | Bullets: ${bulletsPer} | Paths: ${paths}`);
  console.log(`Snake Threshold: ${(snakeThreshold*100).toFixed(0)}% drawdown\n`);
  
  console.log(`Tier Structure:`);
  TIERS.forEach(t => {
    console.log(`  ${t.name.padEnd(12)} (${t.minMultiple}x+): WinRate=${(t.winRate*100).toFixed(0)}% Pos=${(t.posBase*100).toFixed(0)}% Win/Loss=${(t.winPct*100).toFixed(2)}%/${(t.lossPct*100).toFixed(2)}%`);
  });
  console.log();
  
  const pathResults: PathResult[] = [];
  for (let i = 0; i < paths; i++) {
    pathResults.push(simulatePath({ startBalance, commanders, bulletsPer, feePct, minSize, maxSize, snakeThreshold }));
  }
  
  const stats = summarize(pathResults, startBalance);
  const gainPct = ((stats.median - startBalance) / startBalance * 100).toFixed(2);
  
  console.log(`\n📊 Results:`);
  console.log(`  Median Final: $${stats.median.toFixed(2)} (+${gainPct}%)`);
  console.log(`  p10: $${stats.p10.toFixed(2)} | p90: $${stats.p90.toFixed(2)}`);
  console.log(`  Ruin Rate: ${(stats.ruinRate*100).toFixed(2)}%`);
  console.log(`\n  Tier Reached Distribution:`);
  stats.tierReached.forEach(tr => {
    console.log(`    ${tr.name.padEnd(12)}: ${tr.pct.toFixed(1)}% of paths`);
  });
  
  // Compare to static strategies
  console.log(`\n🔬 Comparison to Static Strategies:\n`);
  
  // Static conservative (70% win)
  const staticConservative = Array.from({ length: paths }, () => {
    let eq = startBalance;
    let pos = 0.65;
    for (let c = 0; c < commanders; c++) {
      for (let b = 0; b < bulletsPer; b++) {
        const win = Math.random() < 0.70;
        const deployed = eq * pos;
        const fee = deployed * feePct;
        if (win) {
          eq += deployed * 0.004 - fee;
          pos = Math.min(maxSize, pos * 1.02);
        } else {
          eq -= deployed * 0.006 + fee;
          pos = Math.max(minSize, pos * 0.96);
          if (eq <= 0) return 0;
        }
      }
    }
    return eq;
  });
  const staticConsMed = staticConservative.slice().sort((a,b)=>a-b)[Math.floor(staticConservative.length/2)];
  console.log(`  Static Conservative (70%): Median $${staticConsMed.toFixed(2)} (+${((staticConsMed/startBalance-1)*100).toFixed(2)}%)`);
  
  // Static aggressive (80% win)
  const staticAggressive = Array.from({ length: paths }, () => {
    let eq = startBalance;
    let pos = 0.78;
    for (let c = 0; c < commanders; c++) {
      for (let b = 0; b < bulletsPer; b++) {
        const win = Math.random() < 0.80;
        const deployed = eq * pos;
        const fee = deployed * feePct;
        if (win) {
          eq += deployed * 0.0055 - fee;
          pos = Math.min(maxSize, pos * 1.035);
        } else {
          eq -= deployed * 0.005 + fee;
          pos = Math.max(minSize, pos * 0.97);
          if (eq <= 0) return 0;
        }
      }
    }
    return eq;
  });
  const staticAggMed = staticAggressive.slice().sort((a,b)=>a-b)[Math.floor(staticAggressive.length/2)];
  console.log(`  Static Aggressive (80%): Median $${staticAggMed.toFixed(2)} (+${((staticAggMed/startBalance-1)*100).toFixed(2)}%)`);
  
  console.log(`\n  Ladder Advantage: ${stats.median > staticAggMed ? '+' : ''}${(stats.median - staticAggMed).toFixed(2)} vs Static Aggressive`);
  
  const out = {
    timestamp: new Date().toISOString(),
    params: { startBalance, commanders, bulletsPer, paths, feePct, snakeThreshold },
    ladderStats: stats,
    staticComparison: {
      conservative: { median: staticConsMed },
      aggressive: { median: staticAggMed }
    }
  };
  fs.writeFileSync('sniper_ladder_results.json', JSON.stringify(out, null, 2));
  console.log(`\n📝 Wrote sniper_ladder_results.json\n`);
}

main().catch(err => {
  console.error('Ladder simulation failed:', err);
  process.exit(1);
});
