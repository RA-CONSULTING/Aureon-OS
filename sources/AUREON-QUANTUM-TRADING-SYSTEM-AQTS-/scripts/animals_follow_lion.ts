#!/usr/bin/env tsx
import '../core/environment';
import { spawn, ChildProcess } from 'child_process';
import PrideScanner from './prideScanner';

interface OrchestratorCfg {
  hunters: number;  // number of lion targets to consider (top-N)
  cycles: number;   // lion cycles
  interval: number; // ms per lion cycle
  durationMin: number; // overall orchestration window in minutes (soft)
  minVolatility: number;
  minVolume: number; // USD
  dreamMode?: string;
  alpha?: number;
  beta?: number;
}

function pad(n: number, w=2) { return String(n).padStart(w,'0'); }

class AnimalsFollowLion {
  private cfg: OrchestratorCfg;
  private children: ChildProcess[] = [];
  private scanner: PrideScanner;

  constructor(cfg: Partial<OrchestratorCfg> = {}) {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    if (!apiKey || !apiSecret) throw new Error('BINANCE_API_KEY/SECRET required');

    this.scanner = new PrideScanner(apiKey, apiSecret, testnet);
    this.cfg = {
      hunters: cfg.hunters ?? 5,
      cycles: cfg.cycles ?? 10,
      interval: cfg.interval ?? 5000,
      durationMin: cfg.durationMin ?? 10,
      minVolatility: cfg.minVolatility ?? 2.0,
      minVolume: cfg.minVolume ?? 100000,
      dreamMode: cfg.dreamMode,
      alpha: cfg.alpha,
      beta: cfg.beta,
    };
  }

  async run(): Promise<void> {
    console.log('\n🦁 ORCHESTRATOR — Animals follow the Lion');
    console.log(`   🐝 The Bees pollinate — without them, nothing grows`);
    console.log(`   Top-N targets: ${this.cfg.hunters}`);
    console.log(`   Lion cycles: ${this.cfg.cycles} @ ${this.cfg.interval}ms`);
    console.log(`   Window: ~${this.cfg.durationMin} minutes`);
    console.log(`   Volatility ≥ ${this.cfg.minVolatility}% | Volume ≥ $${this.cfg.minVolume}`);
    const dream = this.cfg.dreamMode ? `${this.cfg.dreamMode}` : (this.cfg.alpha!==undefined && this.cfg.beta!==undefined ? `custom α=${this.cfg.alpha} β=${this.cfg.beta}` : 'off');
    console.log(`   Dream: ${dream}`);

    // 1) Scan and choose targets
    await this.scanner.scanPride();
    const targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, this.cfg.minVolatility).slice(0, this.cfg.hunters);
    if (!targets.length) { console.log('No targets found. Exiting.'); return; }

    console.log('\n🎯 Lion assigns prey:');
    targets.forEach((t, i) => {
      const price = t.price ? (t.price < 1 ? `$${t.price.toFixed(6)}` : `$${t.price.toFixed(2)}`) : 'N/A';
      console.log(`   #${pad(i+1)} ${t.symbol} | ${price} | ${(t.priceChangePercent ?? 0).toFixed(2)}% | $${((t.volume24h || 0)/1_000_000).toFixed(2)}M`);
    });

    // 2) Start the Lion (Rainbow Architect) on top-1
    const lionSymbol = targets[0].symbol;
    await this.launchLion(lionSymbol);

    // 3) Followers: Ants, Hummingbird, Lone Wolf
    await this.launchFollowers(targets.map(t => t.symbol));

    // 4) Wait window duration then cleanup
    await this.sleep(this.cfg.durationMin * 60 * 1000);
    this.teardown();
  }

  private buildDreamEnv(base: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
    const env = { ...base };
    if (this.cfg.dreamMode) env.DREAM_MODE = this.cfg.dreamMode;
    if (this.cfg.alpha !== undefined) env.DREAM_ALPHA = String(this.cfg.alpha);
    if (this.cfg.beta !== undefined) env.DREAM_BETA = String(this.cfg.beta);
    return env;
  }

  private async launchLion(symbol: string): Promise<void> {
    console.log(`\n🦁 LION leading on ${symbol}...`);
    const env = this.buildDreamEnv({
      ...process.env,
      CONFIRM_LIVE_TRADING: 'no',
      DRY_RUN: 'false',
      RAINBOW_CYCLES: String(this.cfg.cycles),
    });
    const child = spawn('npx', ['tsx', 'scripts/rainbowArch.ts', symbol, '--live', `--interval=${this.cfg.interval}`], { env, stdio: 'inherit' });
    this.children.push(child);
  }

  private async launchFollowers(symbols: string[]): Promise<void> {
    const usdtSymbols = symbols.filter(s => s.endsWith('USDT'));
    const ethSymbols = symbols
      .map(s => s.endsWith('USDT') ? s.replace('USDT','ETH') : (s.endsWith('ETH') ? s : ''))
      .filter(Boolean);

    // 🐝 Army Ants (The Bees) — Essential pollinators, bringing life to the forest floor
    console.log('\n🐝 Launching the Bees (Army Ants) — The garden depends on them...');
    const antsEnv = {
      ...process.env,
      CONFIRM_LIVE_TRADING: 'no', DRY_RUN: 'false', BINANCE_TESTNET: process.env.BINANCE_TESTNET || 'true',
      ANTS_UNIVERSE: (usdtSymbols.length ? usdtSymbols : ['ADAUSDT','DOGEUSDT','XRPUSDT']).join(','),
      ANTS_ROTATIONS: String(Math.min(4, usdtSymbols.length || 3)),
      ANTS_SPEND_USDT: process.env.ANTS_SPEND_USDT || '11',
      ANTS_MAX_MIN: process.env.ANTS_MAX_MIN || '3',
    } as NodeJS.ProcessEnv;
    const ants = spawn('npx', ['tsx', 'scripts/armyAnts.ts'], { env: antsEnv, stdio: 'inherit' });
    this.children.push(ants);

    // 🕊️ Hummingbird — Swift pollinator of ETH flowers
    console.log('🕊️ Launching the Hummingbird — Pollinating ETH blooms...');
    const hbEnv = {
      ...process.env,
      CONFIRM_LIVE_TRADING: 'no', DRY_RUN: 'false', BINANCE_TESTNET: process.env.BINANCE_TESTNET || 'true',
      HB_UNIVERSE: (ethSymbols.length ? ethSymbols : ['BNBETH','SOLETH','ADAETH']).join(','),
      HB_MAX_MINUTES: process.env.HB_MAX_MINUTES || '20',
    } as NodeJS.ProcessEnv;
    const hb = spawn('npx', ['tsx', 'scripts/hummingbird.ts'], { env: hbEnv, stdio: 'inherit' });
    this.children.push(hb);

    // 🐺 Lone Wolf — Silent watcher, precise striker
    console.log('🐺 Launching the Lone Wolf — Watching from the shadows...');
    const wolfEnv = {
      ...process.env,
      CONFIRM_LIVE_TRADING: 'no', DRY_RUN: 'false', BINANCE_TESTNET: process.env.BINANCE_TESTNET || 'true',
      WOLF_UNIVERSE_USDT: (usdtSymbols.length ? usdtSymbols : ['BTCUSDT','ETHUSDT','SOLUSDT']).join(','),
      WOLF_UNIVERSE_ETH: (ethSymbols.length ? ethSymbols : ['BNBETH','SOLETH','LINKETH']).join(','),
      WOLF_WAIT_FOR_FUNDS: process.env.WOLF_WAIT_FOR_FUNDS || 'no',
      WOLF_SPEND_USDT: process.env.WOLF_SPEND_USDT || '12',
      WOLF_MAX_MIN: process.env.WOLF_MAX_MIN || '5',
    } as NodeJS.ProcessEnv;
    const wolf = spawn('npx', ['tsx', 'scripts/loneWolf.ts'], { env: wolfEnv, stdio: 'inherit' });
    this.children.push(wolf);
  }

  private teardown() {
    console.log('\n🛑 Orchestrator window ended — stopping followers...');
    for (const c of this.children) {
      try { c.kill('SIGTERM'); } catch {}
    }
  }

  private sleep(ms: number): Promise<void> { return new Promise(r => setTimeout(r, ms)); }
}

async function main() {
  const args = process.argv.slice(2);
  const cfg: Partial<OrchestratorCfg> = {
    hunters: parseInt(args.find(a => a.startsWith('--hunters='))?.split('=')[1] || '5'),
    cycles: parseInt(args.find(a => a.startsWith('--cycles='))?.split('=')[1] || '10'),
    interval: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    durationMin: parseInt(args.find(a => a.startsWith('--duration='))?.split('=')[1] || '10'),
    minVolatility: parseFloat(args.find(a => a.startsWith('--volatility='))?.split('=')[1] || '2.0'),
    minVolume: parseFloat(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
    dreamMode: (args.find(a => a.startsWith('--dream='))?.split('=')[1]) || undefined,
    alpha: args.find(a => a.startsWith('--alpha=')) ? parseFloat(args.find(a => a.startsWith('--alpha='))!.split('=')[1]) : undefined,
    beta: args.find(a => a.startsWith('--beta=')) ? parseFloat(args.find(a => a.startsWith('--beta='))!.split('=')[1]) : undefined,
  };

  const orch = new AnimalsFollowLion(cfg);
  process.on('SIGINT', () => { orch['teardown'](); process.exit(0); });
  await orch.run();
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
