#!/usr/bin/env tsx
/**
 * Sniper Domino Optimization Sweep
 * Runs 100+ parameter combinations to find optimal configuration.
 * Tests combinations of:
 *  - WIN_RATE: [0.70, 0.75, 0.80, 0.85]
 *  - POSITION_SIZE_BASE: [0.60, 0.70, 0.75, 0.80, 0.85]
 *  - WIN_PCT/LOSS_PCT asymmetry ratios
 *  - GROWTH_ON_WIN / SHRINK_ON_LOSS tuning
 *
 * Output: Ranked results by median final equity, filtered by acceptable ruin rate.
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';
import fs from 'fs';

interface SimParams {
  startBalance: number;
  commanders: number;
  bulletsPer: number;
  winRate: number;
  winPct: number;
  lossPct: number;
  posBase: number;
  growthOnWin: number;
  shrinkOnLoss: number;
  minSize: number;
  maxSize: number;
  feePct: number;
  dominoGate: boolean;
  clusterReset: boolean;
}

interface PathResult {
  finalEquity: number;
  ruined: boolean;
}

function fetchStartBalance(): Promise<number> {
  if (process.env.START_BALANCE) return Promise.resolve(Number(process.env.START_BALANCE));
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) return Promise.resolve(120.98);
  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  return client.getAccount().then(acc => {
    const usdc = acc.balances.find(b => b.asset === 'USDC');
    return Number(usdc?.free || 0);
  }).catch(() => 120.98);
}

function simulatePath(p: SimParams): PathResult {
  let equity = p.startBalance;
  let posFrac = p.posBase;
  for (let c = 0; c < p.commanders; c++) {
    const startEquity = equity;
    if (p.clusterReset) posFrac = p.posBase;
    for (let b = 0; b < p.bulletsPer; b++) {
      const win = Math.random() < p.winRate;
      const deployed = equity * posFrac;
      const fee = deployed * p.feePct;
      if (win) {
        const gain = deployed * p.winPct - fee;
        equity += gain;
        posFrac = Math.min(p.maxSize, posFrac * (1 + p.growthOnWin));
      } else {
        const loss = deployed * p.lossPct + fee;
        equity -= loss;
        posFrac = Math.max(p.minSize, posFrac * (1 - p.shrinkOnLoss));
        if (equity <= 0) return { finalEquity: 0, ruined: true };
      }
    }
    const endEquity = equity;
    if (p.dominoGate && endEquity < startEquity) break;
  }
  return { finalEquity: equity, ruined: equity <= 0 };
}

function runScenario(p: SimParams, paths: number) {
  const results: PathResult[] = [];
  for (let i = 0; i < paths; i++) {
    results.push(simulatePath(p));
  }
  const finals = results.map(r => r.finalEquity);
  const ruined = results.filter(r => r.ruined).length;
  const ruinRate = ruined / results.length;
  const sorted = finals.slice().sort((a, b) => a - b);
  const pct = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  return {
    median: pct(0.5),
    p10: pct(0.1),
    p90: pct(0.9),
    ruinRate,
    avgFinal: finals.reduce((a, b) => a + b, 0) / finals.length
  };
}

async function main() {
  const startBalance = await fetchStartBalance();
  const commanders = Number(process.env.COMMANDERS ?? 5);
  const bulletsPer = Number(process.env.BULLETS_PER ?? 50);
  const paths = Number(process.env.PATHS ?? 300); // lower for speed
  const feePct = Number(process.env.FEE_PCT ?? 0.001);
  const dominoGate = String(process.env.DOMINO_GATE ?? 'true').toLowerCase() === 'true';
  const clusterReset = false; // keep position sizing persistent
  const minSize = 0.50;
  const maxSize = 0.95;

  console.log(`\n🔬 Sniper Optimization Sweep | startBalance=${startBalance.toFixed(2)} commanders=${commanders} bullets=${bulletsPer} paths=${paths}\n`);

  // Parameter grid
  const winRates = [0.70, 0.75, 0.80, 0.85];
  const positionBases = [0.60, 0.70, 0.75, 0.80, 0.85];
  const winPcts = [0.004, 0.005, 0.006];
  const lossPcts = [0.005, 0.006, 0.007];
  const growthOnWinRates = [0.02, 0.03, 0.04];
  const shrinkOnLossRates = [0.03, 0.04, 0.05];

  const scenarios: any[] = [];
  let count = 0;
  const total = winRates.length * positionBases.length * winPcts.length * lossPcts.length * growthOnWinRates.length * shrinkOnLossRates.length;

  console.log(`Total combinations: ${total}\n`);

  for (const winRate of winRates) {
    for (const posBase of positionBases) {
      for (const winPct of winPcts) {
        for (const lossPct of lossPcts) {
          for (const growthOnWin of growthOnWinRates) {
            for (const shrinkOnLoss of shrinkOnLossRates) {
              count++;
              if (count % 50 === 0) console.log(`Progress: ${count}/${total} (${(count/total*100).toFixed(1)}%)`);
              const stats = runScenario({
                startBalance,
                commanders,
                bulletsPer,
                winRate,
                winPct,
                lossPct,
                posBase,
                growthOnWin,
                shrinkOnLoss,
                minSize,
                maxSize,
                feePct,
                dominoGate,
                clusterReset
              }, paths);
              scenarios.push({
                params: { winRate, posBase, winPct, lossPct, growthOnWin, shrinkOnLoss },
                stats
              });
            }
          }
        }
      }
    }
  }

  console.log(`\nCompleted ${scenarios.length} scenarios\n`);

  // Filter by acceptable ruin rate (<10%)
  const viable = scenarios.filter(s => s.stats.ruinRate < 0.10);
  console.log(`Viable scenarios (ruin < 10%): ${viable.length}\n`);

  // Rank by median final equity
  const ranked = viable.slice().sort((a, b) => b.stats.median - a.stats.median);

  console.log(`\n🏆 Top 20 Configurations:\n`);
  ranked.slice(0, 20).forEach((s, idx) => {
    const p = s.params;
    const st = s.stats;
    const gainPct = ((st.median - startBalance) / startBalance * 100).toFixed(2);
    console.log(`${idx+1}. WinRate=${(p.winRate*100).toFixed(0)}% PosBase=${(p.posBase*100).toFixed(0)}% WinPct=${(p.winPct*100).toFixed(2)}% LossPct=${(p.lossPct*100).toFixed(2)}% Growth=${(p.growthOnWin*100).toFixed(0)}% Shrink=${(p.shrinkOnLoss*100).toFixed(0)}%`);
    console.log(`   → Median: ${st.median.toFixed(2)} (+${gainPct}%) | Ruin: ${(st.ruinRate*100).toFixed(2)}% | p10: ${st.p10.toFixed(2)} | p90: ${st.p90.toFixed(2)}\n`);
  });

  // Save full results
  const out = {
    timestamp: new Date().toISOString(),
    baseParams: { startBalance, commanders, bulletsPer, paths, feePct, dominoGate },
    totalScenarios: scenarios.length,
    viableScenarios: viable.length,
    topConfigs: ranked.slice(0, 50)
  };
  fs.writeFileSync('sniper_optimization_results.json', JSON.stringify(out, null, 2));
  console.log(`\n📝 Wrote sniper_optimization_results.json\n`);

  // Summary stats
  if (ranked.length > 0) {
    const best = ranked[0];
    console.log(`\n✨ OPTIMAL CONFIGURATION:`);
    console.log(`   WIN_RATE=${best.params.winRate}`);
    console.log(`   POSITION_SIZE_BASE=${best.params.posBase}`);
    console.log(`   WIN_PCT=${best.params.winPct}`);
    console.log(`   LOSS_PCT=${best.params.lossPct}`);
    console.log(`   GROWTH_ON_WIN=${best.params.growthOnWin}`);
    console.log(`   SHRINK_ON_LOSS=${best.params.shrinkOnLoss}`);
    console.log(`   Expected Median: ${best.stats.median.toFixed(2)} (${((best.stats.median/startBalance - 1)*100).toFixed(2)}% gain)`);
    console.log(`   Ruin Risk: ${(best.stats.ruinRate*100).toFixed(2)}%\n`);
  }
}

main().catch(err => {
  console.error('Optimization sweep failed:', err);
  process.exit(1);
});
