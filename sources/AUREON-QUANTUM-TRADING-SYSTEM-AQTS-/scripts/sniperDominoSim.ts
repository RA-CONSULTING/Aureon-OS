#!/usr/bin/env tsx
/**
 * Sniper Domino Simulation
 * Models multiple "commanders" each with a fixed number of bullets (trades).
 * Dynamic position sizing compounds on wins and diminishes on losses within bounds.
 * Optional domino gating: next commander only fires if previous ends net-positive.
 * All commanders share the same underlying wallet (single equity pool) so capital truly compounds.
 *
 * Env Params:
 *  START_BALANCE=120.98          // override initial equity (else fallback to live USDC if keys provided)
 *  COMMANDERS=8                  // number of commanders (default: derive from accounts.json length or 1)
 *  BULLETS_PER=50                // trades per commander
 *  PATHS=1000                    // Monte Carlo paths
 *  WIN_RATE=0.8                  // per-trade probability of win (or MULTI_WIN="0.6,0.7,0.8")
 *  WIN_PCT=0.004                 // percent move captured on deployed slice when win (0.4%)
 *  LOSS_PCT=0.006                // percent loss on deployed slice when loss (0.6%)
 *  POSITION_SIZE_BASE=0.75       // base fraction of equity deployed per trade (75%)
 *  GROWTH_ON_WIN=0.02            // multiplicative increase of size fraction after each win
 *  SHRINK_ON_LOSS=0.04           // multiplicative decrease of size fraction after each loss
 *  MIN_SIZE_PERCENT=0.50         // floor on position size fraction
 *  MAX_SIZE_PERCENT=0.95         // cap on position size fraction
 *  FEE_PCT=0.001                 // fee applied to deployed notional each trade (0.1%)
 *  DOMINO_GATE=true              // if true, commander n+1 only begins if n net-positive cluster PnL
 *  CLUSTER_RESET=false           // if true, position size resets to base for each new commander
 *  REPORT_JSON=sniper_domino_results.json // output file name
 *
 * Output: Console summary + JSON with path distributions.
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';
import { loadAccountsFromJson } from './utils/accountLoader';
import fs from 'fs';

interface SimParams {
  startBalance: number;
  commanders: number;
  bulletsPer: number;
  winRate: number;
  winPct: number;
  lossPct: number;
  posBase: number; // fraction 0-1
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
  commanderStats: CommanderStat[];
}
interface CommanderStat {
  commanderIndex: number;
  startEquity: number;
  endEquity: number;
  trades: number;
  wins: number;
  losses: number;
  netPct: number; // (end - start)/start
}

function fetchStartBalance(): Promise<number> {
  if (process.env.START_BALANCE) return Promise.resolve(Number(process.env.START_BALANCE));
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) return Promise.resolve(100); // fallback
  const client = new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
  return client.getAccount().then(acc => {
    const usdc = acc.balances.find(b => b.asset === 'USDC');
    return Number(usdc?.free || 0);
  }).catch(() => 100);
}

function simulatePath(p: SimParams): PathResult {
  let equity = p.startBalance;
  let posFrac = p.posBase;
  const commanderStats: CommanderStat[] = [];
  for (let c = 0; c < p.commanders; c++) {
    const startEquity = equity;
    let wins = 0, losses = 0;
    if (p.clusterReset) posFrac = p.posBase;
    for (let b = 0; b < p.bulletsPer; b++) {
      const win = Math.random() < p.winRate;
      const deployed = equity * posFrac;
      const fee = deployed * p.feePct;
      if (win) {
        const gain = deployed * p.winPct - fee;
        equity += gain;
        wins++;
        posFrac = Math.min(p.maxSize, posFrac * (1 + p.growthOnWin));
      } else {
        const loss = deployed * p.lossPct + fee;
        equity -= loss;
        losses++;
        posFrac = Math.max(p.minSize, posFrac * (1 - p.shrinkOnLoss));
        if (equity <= 0) {
          commanderStats.push({ commanderIndex: c, startEquity, endEquity: equity, trades: wins + losses, wins, losses, netPct: (equity - startEquity)/startEquity });
          return { finalEquity: 0, ruined: true, commanderStats };
        }
      }
    }
    const endEquity = equity;
    commanderStats.push({ commanderIndex: c, startEquity, endEquity, trades: p.bulletsPer, wins, losses, netPct: (endEquity - startEquity)/startEquity });
    // Domino gate: stop if cluster negative
    if (p.dominoGate && endEquity < startEquity) break;
  }
  return { finalEquity: equity, ruined: equity <= 0, commanderStats };
}

function summarize(paths: PathResult[]) {
  const finals = paths.map(r => r.finalEquity);
  const ruined = paths.filter(r => r.ruined).length;
  const ruinRate = ruined / paths.length * 100;
  const sorted = finals.slice().sort((a,b)=>a-b);
  const pct = (q:number) => sorted[Math.min(sorted.length-1, Math.floor(q*sorted.length))];
  const commanderAverages: Record<number,{count:number; avgNetPct:number; winRate:number}> = {};
  paths.forEach(r => r.commanderStats.forEach(cs => {
    if (!commanderAverages[cs.commanderIndex]) commanderAverages[cs.commanderIndex] = { count:0, avgNetPct:0, winRate:0 };
    commanderAverages[cs.commanderIndex].count++;
    commanderAverages[cs.commanderIndex].avgNetPct += cs.netPct;
    commanderAverages[cs.commanderIndex].winRate += cs.wins / cs.trades;
  }));
  const commanderSummary = Object.entries(commanderAverages).map(([idx,obj]) => ({
    commander: Number(idx),
    avgNetPct: obj.avgNetPct / obj.count,
    avgWinRate: obj.winRate / obj.count
  }));
  return {
    ruinRate,
    p10: pct(0.1),
    median: pct(0.5),
    p90: pct(0.9),
    commanderSummary
  };
}

async function main() {
  const startBalance = await fetchStartBalance();
  const accounts = loadAccountsFromJson();
  const commanders = Number(process.env.COMMANDERS ?? (accounts.length || 1));
  const bulletsPer = Number(process.env.BULLETS_PER ?? 50);
  const paths = Number(process.env.PATHS ?? 1000);
  const winPct = Number(process.env.WIN_PCT ?? 0.004);
  const lossPct = Number(process.env.LOSS_PCT ?? 0.006);
  const winRates = (process.env.MULTI_WIN ? process.env.MULTI_WIN.split(',').map(s=>Number(s.trim())) : [Number(process.env.WIN_RATE ?? 0.8)]).filter(n=>!isNaN(n) && n>0 && n<1.0);
  const posBase = Number(process.env.POSITION_SIZE_BASE ?? 0.75);
  const growthOnWin = Number(process.env.GROWTH_ON_WIN ?? 0.02);
  const shrinkOnLoss = Number(process.env.SHRINK_ON_LOSS ?? 0.04);
  const minSize = Number(process.env.MIN_SIZE_PERCENT ?? 0.50);
  const maxSize = Number(process.env.MAX_SIZE_PERCENT ?? 0.95);
  const feePct = Number(process.env.FEE_PCT ?? 0.001);
  const dominoGate = String(process.env.DOMINO_GATE ?? 'true').toLowerCase() === 'true';
  const clusterReset = String(process.env.CLUSTER_RESET ?? 'false').toLowerCase() === 'true';
  const reportFile = process.env.REPORT_JSON || 'sniper_domino_results.json';

  console.log(`\n🎯 Sniper Domino Simulation | startBalance=${startBalance.toFixed(2)} commanders=${commanders} bulletsEach=${bulletsPer} paths=${paths}`);
  console.log(`WinPct=${(winPct*100).toFixed(2)}% LossPct=${(lossPct*100).toFixed(2)}% BaseSize=${(posBase*100).toFixed(1)}% Min=${(minSize*100).toFixed(1)}% Max=${(maxSize*100).toFixed(1)}% Fee=${(feePct*100).toFixed(3)}%`);
  console.log(`GrowthOnWin=${(growthOnWin*100).toFixed(1)}% ShrinkOnLoss=${(shrinkOnLoss*100).toFixed(1)}% DominoGate=${dominoGate} ClusterReset=${clusterReset}`);

  const scenarioOutputs: any[] = [];
  for (const winRate of winRates) {
    console.log(`\nScenario WIN_RATE=${(winRate*100).toFixed(2)}% running...`);
    const pathResults: PathResult[] = [];
    for (let i=0;i<paths;i++) {
      pathResults.push(simulatePath({ startBalance, commanders, bulletsPer, winRate, winPct, lossPct, posBase, growthOnWin, shrinkOnLoss, minSize, maxSize, feePct, dominoGate, clusterReset }));
    }
    const stats = summarize(pathResults);
    console.log(`  RuinRate: ${stats.ruinRate.toFixed(2)}% | Median Final: ${stats.median.toFixed(2)} | p10: ${stats.p10.toFixed(2)} | p90: ${stats.p90.toFixed(2)}`);
    console.log(`  Commander Avg Net%:`);
    stats.commanderSummary.forEach(cs => {
      console.log(`    Commander ${cs.commander}: Net ${(cs.avgNetPct*100).toFixed(2)}% | WinRate ${(cs.avgWinRate*100).toFixed(2)}%`);
    });
    scenarioOutputs.push({ winRate, stats });
  }

  const out = { timestamp: new Date().toISOString(), params: { startBalance, commanders, bulletsPer, winPct, lossPct, posBase, growthOnWin, shrinkOnLoss, minSize, maxSize, feePct, dominoGate, clusterReset }, scenarios: scenarioOutputs };
  fs.writeFileSync(reportFile, JSON.stringify(out, null, 2));
  console.log(`\n📝 Wrote ${reportFile}`);
}

main().catch(err => { console.error('Simulation failed:', err); process.exit(1); });
