#!/usr/bin/env tsx
import '../core/environment';
import { spawn, ChildProcess } from 'child_process';
import fs from 'node:fs';
import path from 'node:path';
import PrideScanner from './prideScanner';

interface McConfig {
  rounds: number;
  hunters: number; // concurrent symbols per round
  cyclesPerHunt: number;
  cycleMs: number;
  minVolatility: number;
  minVolume: number; // USD
  dreamMode?: string; // dream|sweet|custom
  dreamAlpha?: number;
  dreamBeta?: number;
  testnet: boolean;
}

interface HunterResult { symbol: string; trades: number; profit: number; }
interface RoundResult { round: number; results: HunterResult[]; }

class TestnetMonteCarlo {
  private cfg: McConfig;
  private apiKey: string;
  private apiSecret: string;
  private scanner: PrideScanner;
  private artifactsDir: string;

  constructor(cfg: Partial<McConfig> = {}) {
    this.apiKey = process.env.BINANCE_API_KEY || '';
    this.apiSecret = process.env.BINANCE_API_SECRET || '';
    if (!this.apiKey || !this.apiSecret) throw new Error('BINANCE_API_KEY/SECRET required');

    this.cfg = {
      rounds: cfg.rounds ?? 10,
      hunters: cfg.hunters ?? 8,
      cyclesPerHunt: cfg.cyclesPerHunt ?? 10,
      cycleMs: cfg.cycleMs ?? 5000,
      minVolatility: cfg.minVolatility ?? 2.0,
      minVolume: cfg.minVolume ?? 100000,
      dreamMode: cfg.dreamMode,
      dreamAlpha: cfg.dreamAlpha,
      dreamBeta: cfg.dreamBeta,
      testnet: cfg.testnet ?? (!(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false")),
    };

    this.scanner = new PrideScanner(this.apiKey, this.apiSecret, this.cfg.testnet);
    this.artifactsDir = path.resolve(process.cwd(), 'artifacts');
    try { fs.mkdirSync(this.artifactsDir, { recursive: true }); } catch {}
  }

  async run(): Promise<void> {
    const summary: RoundResult[] = [];

    console.log('\n🧪 TESTNET MONTE CARLO — Rainbow Architect');
    console.log(`   Rounds: ${this.cfg.rounds}`);
    console.log(`   Hunters/round: ${this.cfg.hunters}`);
    console.log(`   Cycles/hunt: ${this.cfg.cyclesPerHunt}`);
    console.log(`   Cycle: ${this.cfg.cycleMs} ms`);
    console.log(`   Volatility ≥ ${this.cfg.minVolatility}% | Volume ≥ $${this.cfg.minVolume}`);
    if (this.cfg.dreamMode || (this.cfg.dreamAlpha !== undefined && this.cfg.dreamBeta !== undefined)) {
      console.log(`   Dream: ${this.cfg.dreamMode ?? 'custom'} α=${this.cfg.dreamAlpha ?? '—'} β=${this.cfg.dreamBeta ?? '—'}`);
    }
    console.log(`   Testnet: ${this.cfg.testnet ? 'YES' : 'NO'}`);

    for (let r = 1; r <= this.cfg.rounds; r++) {
      console.log(`\n${'='.repeat(60)}\n🎲 ROUND ${r}/${this.cfg.rounds}\n${'='.repeat(60)}`);
      await this.scanner.scanPride();
      let targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, this.cfg.minVolatility);
      if (targets.length < this.cfg.hunters) {
        // expand by lowering volatility threshold
        targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, Math.max(0.5, this.cfg.minVolatility / 2));
      }
      if (!targets.length) {
        console.log('⚠️ No targets found; skipping round');
        summary.push({ round: r, results: [] });
        continue;
      }

      const chosen = targets.slice(0, this.cfg.hunters);
      console.log('🎯 Targets:', chosen.map(t => t.symbol).join(', '));

      const results = await this.launchHunters(chosen.map(t => t.symbol));
      summary.push({ round: r, results });
      this.reportRound(r, results);
    }

    this.finish(summary);
  }

  private async launchHunters(symbols: string[]): Promise<HunterResult[]> {
    const children: ChildProcess[] = [];
    const results: Record<string, HunterResult> = {};

    const envBase: NodeJS.ProcessEnv = {
      ...process.env,
      BINANCE_API_KEY: this.apiKey,
      BINANCE_API_SECRET: this.apiSecret,
      BINANCE_TESTNET: this.cfg.testnet.toString(),
      CONFIRM_LIVE_TRADING: 'no',
      DRY_RUN: 'false',
      RAINBOW_CYCLES: this.cfg.cyclesPerHunt.toString(),
    };
    if (this.cfg.dreamMode) envBase.DREAM_MODE = this.cfg.dreamMode;
    if (this.cfg.dreamAlpha !== undefined) envBase.DREAM_ALPHA = String(this.cfg.dreamAlpha);
    if (this.cfg.dreamBeta !== undefined) envBase.DREAM_BETA = String(this.cfg.dreamBeta);

    await Promise.all(symbols.map(async (sym) => new Promise<void>((resolve) => {
      const args = ['tsx', 'scripts/rainbowArch.ts', sym, '--live', `--interval=${this.cfg.cycleMs}`];
      const child = spawn('npx', args, { env: envBase, stdio: 'pipe', cwd: process.cwd() });
      children.push(child);
      results[sym] = { symbol: sym, trades: 0, profit: 0 };

      child.stdout?.on('data', (buf) => {
        const s = buf.toString();
        if (s.includes('TRADE SIGNAL')) results[sym].trades++;
        const tradesMatch = s.match(/Total Trades:\s*(\d+)/i);
        if (tradesMatch) results[sym].trades = parseInt(tradesMatch[1] || '0');
        const profitMatch = s.match(/Total Profit:\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*USDT/i);
        if (profitMatch) results[sym].profit = parseFloat(profitMatch[1] || '0');
      });

      child.on('close', () => resolve());
      child.on('error', () => resolve());
    })));

    return Object.values(results);
  }

  private reportRound(round: number, results: HunterResult[]) {
    const totalTrades = results.reduce((a, r) => a + (r.trades || 0), 0);
    const totalProfit = results.reduce((a, r) => a + (r.profit || 0), 0);
    console.log(`\n📊 Round ${round} summary: ${totalTrades} trades | $${totalProfit.toFixed(2)} profit`);
  }

  private finish(summary: RoundResult[]) {
    const flat = summary.flatMap(r => r.results);
    const totalTrades = flat.reduce((a, r) => a + (r.trades || 0), 0);
    const totalProfit = flat.reduce((a, r) => a + (r.profit || 0), 0);

    const bySymbol: Record<string, { trades: number; profit: number }> = {};
    for (const r of flat) {
      if (!bySymbol[r.symbol]) bySymbol[r.symbol] = { trades: 0, profit: 0 };
      bySymbol[r.symbol].trades += r.trades;
      bySymbol[r.symbol].profit += r.profit;
    }

    const out = {
      config: this.cfg,
      rounds: summary.length,
      totalTrades,
      totalProfit,
      bySymbol,
      timestamp: new Date().toISOString(),
    };

    const outPath = path.join(this.artifactsDir, 'montecarlo_results.json');
    try {
      fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
      console.log(`\n💾 Wrote ${outPath}`);
    } catch (err) {
      console.warn('Could not write results:', (err as Error).message);
    }

    console.log('\n🎯 Monte Carlo complete');
    console.log(`   Total trades: ${totalTrades}`);
    console.log(`   Total profit: $${totalProfit.toFixed(2)}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const cfg: Partial<McConfig> = {
    rounds: parseInt(args.find(a => a.startsWith('--rounds='))?.split('=')[1] || '5'),
    hunters: parseInt(args.find(a => a.startsWith('--hunters='))?.split('=')[1] || '8'),
    cyclesPerHunt: parseInt(args.find(a => a.startsWith('--cycles='))?.split('=')[1] || '10'),
    cycleMs: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    minVolatility: parseFloat(args.find(a => a.startsWith('--volatility='))?.split('=')[1] || '2.0'),
    minVolume: parseFloat(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
    dreamMode: (args.find(a => a.startsWith('--dream='))?.split('=')[1]) || undefined,
    dreamAlpha: args.find(a => a.startsWith('--alpha=')) ? parseFloat(args.find(a => a.startsWith('--alpha='))!.split('=')[1]) : undefined,
    dreamBeta: args.find(a => a.startsWith('--beta=')) ? parseFloat(args.find(a => a.startsWith('--beta='))!.split('=')[1]) : undefined,
  };

  const mc = new TestnetMonteCarlo(cfg);
  await mc.run();
}

main().catch(err => { console.error('Fatal:', err.message); process.exit(1); });
