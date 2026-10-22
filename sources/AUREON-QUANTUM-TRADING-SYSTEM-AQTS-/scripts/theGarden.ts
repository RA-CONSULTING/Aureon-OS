#!/usr/bin/env tsx
/**
 * THE GARDEN — The Natural Order of Growth
 * 
 * SOURCE LAW: 10 out, 9 in, 1 for building new hives
 * - 10 parts profit flow out
 * - 9 parts reinvested into the garden  
 * - 1 part reserved for expansion (new strategies, new agents, new hives)
 * 
 * 🐝 The Bee (Hummingbird) — Above: Swift pollinator of ETH flowers
 * 🐜 The Ant (Army Ants) — Below: Patient worker of the USDT earth
 *    They work in tandem — as above, so below
 * 🦁 The Lion hunts when Bee + Ant profit ≥ threshold
 * 🐺 The Wolf emerges at portfolio ≥ $1M (Monte Carlo threshold)
 * 
 * Each honored. Each essential. Each called at the right time.
 * Not a hierarchy of power, but a dance of purpose.
 */

import '../core/environment';
import { spawn, ChildProcess } from 'child_process';
import { BinanceClient } from '../core/binanceClient';
import PrideScanner from './prideScanner';
import * as fs from 'fs/promises';
import * as path from 'path';

interface GardenConfig {
  beeThresholdUSD: number;      // Profit threshold before Lion hunts
  wolfThresholdUSD: number;     // Portfolio threshold before Wolf emerges
  hiveExpansionRatio: number;   // SOURCE LAW: portion for new hives (default 0.1 = 10%)
  beeCycles: number;            // How many rotations for the bees
  hbMaxMinutes: number;         // Hummingbird flight time
  lionCycles: number;           // Lion hunt cycles (after threshold)
  wolfMaxMinutes: number;       // Wolf hunt duration
  interval: number;             // Price check interval
  minVolatility: number;        // Minimum volatility for targets
  minVolume: number;            // Minimum volume for targets
  dreamMode?: string;
  alpha?: number;
  beta?: number;
}

class TheGarden {
  private cfg: GardenConfig;
  private children: ChildProcess[] = [];
  private scanner: PrideScanner;
  private client: BinanceClient;

  constructor(cfg: Partial<GardenConfig> = {}) {
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    if (!apiKey || !apiSecret) throw new Error('BINANCE_API_KEY/SECRET required');

    this.client = new BinanceClient({ apiKey, apiSecret, testnet });
    this.scanner = new PrideScanner(apiKey, apiSecret, testnet);
    
    this.cfg = {
      beeThresholdUSD: cfg.beeThresholdUSD ?? 5.0,
      wolfThresholdUSD: cfg.wolfThresholdUSD ?? 1_000_000,
      hiveExpansionRatio: cfg.hiveExpansionRatio ?? 0.1,
      beeCycles: cfg.beeCycles ?? 4,
      hbMaxMinutes: cfg.hbMaxMinutes ?? 10,
      lionCycles: cfg.lionCycles ?? 10,
      wolfMaxMinutes: cfg.wolfMaxMinutes ?? 5,
      interval: cfg.interval ?? 5000,
      minVolatility: cfg.minVolatility ?? 2.0,
      minVolume: cfg.minVolume ?? 100000,
      dreamMode: cfg.dreamMode,
      alpha: cfg.alpha,
      beta: cfg.beta,
    };
  }

  async grow(): Promise<void> {
    console.log('\n🌸 THE GARDEN — The Natural Order of Growth');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('⚖️  SOURCE LAW: 10 out → 9 in → 1 for new hives');
    console.log('🐝 The Bee (Hummingbird) — Swift pollinator of ETH flowers');
    console.log('🐜 The Ant (Army Ants) — Patient worker of the USDT earth');
    console.log('   They work in tandem — as above, so below');
    console.log(`🦁 The Lion hunts when they profit ≥ $${this.cfg.beeThresholdUSD.toFixed(2)}`);
    console.log(`🐺 The Wolf emerges at portfolio ≥ $${(this.cfg.wolfThresholdUSD / 1000).toFixed(0)}K`);
    console.log('═══════════════════════════════════════════════════════════\n');

    // Phase 1: The Bee and Ant work together
    await this.phase1_BeeAndAnt();

    // Phase 2: Check if threshold reached
    const profit = await this.checkBeesProfit();
    console.log(`\n💰 Combined profit: $${profit.toFixed(2)}`);
    
    // Apply SOURCE LAW if profitable
    if (profit > 0) {
      const forHive = profit * this.cfg.hiveExpansionRatio;
      const reinvest = profit * (1 - this.cfg.hiveExpansionRatio);
      console.log(`⚖️  SOURCE LAW: $${profit.toFixed(2)} → $${reinvest.toFixed(2)} reinvest + $${forHive.toFixed(2)} for new hives`);
      await this.saveHiveExpansionFund(forHive);
    }

    if (profit >= this.cfg.beeThresholdUSD) {
      console.log(`✅ Threshold reached! The Lion may now hunt.\n`);
      await this.phase2_TheLion();
    } else {
      console.log(`⏸️  Threshold not reached. The Lion rests.\n`);
    }

    // Phase 3: Check portfolio for Wolf threshold
    const portfolioValue = await this.getPortfolioValueUSD();
    console.log(`💰 Portfolio value: $${portfolioValue.toFixed(2)}`);

    if (portfolioValue >= this.cfg.wolfThresholdUSD) {
      console.log(`✅ Million-dollar threshold! The Wolf emerges.\n`);
      await this.phase3_TheWolf();
    } else {
      console.log(`⏸️  Wolf threshold not reached. The Wolf watches from shadows.\n`);
    }

    console.log('\n🌺 THE GARDEN CYCLE COMPLETE');
    console.log('═══════════════════════════════════════════════════════════');
  }

  private async phase1_BeeAndAnt(): Promise<void> {
    console.log('🌱 PHASE 1: The Bee and the Ant begin their work\n');
    console.log('   🐝 Above: The Bee dances through ETH flowers');
    console.log('   🐜 Below: The Ant gathers from USDT earth\n');

    // Scan for targets
    await this.scanner.scanPride();
    const targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, this.cfg.minVolatility);
    const usdtSymbols = targets.filter(t => t.symbol.endsWith('USDT')).slice(0, this.cfg.beeCycles).map(t => t.symbol);
    const ethSymbols = usdtSymbols.map(s => s.replace('USDT', 'ETH')).filter(s => s !== 'ETHETH');

    console.log(`🐜 Ants will work: ${usdtSymbols.join(', ')}`);
    console.log(`🐝 Bee will pollinate: ${ethSymbols.join(', ')}\n`);

    const startETH = await this.getBalance('ETH');
    const ethPrice = await this.client.getPrice('ETHUSDT');
    const startValueUSD = startETH * ethPrice;

    // Launch Ants (below - USDT earth)
    const antsPromise = this.launchAnts(usdtSymbols);
    
    // Launch Bee (above - ETH sky) in tandem
    const beePromise = this.launchBee(ethSymbols);

    // Wait for both to complete - as above, so below
    await Promise.all([beePromise, antsPromise]);

    const endETH = await this.getBalance('ETH');
    const endValueUSD = endETH * ethPrice;
    const profitUSD = endValueUSD - startValueUSD;

    console.log(`\n🌸 Phase 1 complete: $${profitUSD >= 0 ? '+' : ''}${profitUSD.toFixed(2)}`);
  }

  private async phase2_TheLion(): Promise<void> {
    console.log('🦁 PHASE 2: The Lion hunts\n');
    
    await this.scanner.scanPride();
    const targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, this.cfg.minVolatility);
    if (!targets.length) {
      console.log('No targets found. Lion rests.');
      return;
    }

    const lionSymbol = targets[0].symbol;
    console.log(`🦁 Lion hunting: ${lionSymbol}\n`);

    await this.launchLion(lionSymbol);
    console.log('\n🦁 Lion hunt complete');
  }

  private async phase3_TheWolf(): Promise<void> {
    console.log('🐺 PHASE 3: The Wolf emerges\n');

    await this.scanner.scanPride();
    const targets = this.scanner.getHuntingTargets(this.cfg.minVolume / 1_000_000, this.cfg.minVolatility);
    const usdtSymbols = targets.filter(t => t.symbol.endsWith('USDT')).slice(0, 5).map(t => t.symbol);
    const ethSymbols = usdtSymbols.map(s => s.replace('USDT', 'ETH')).filter(s => s !== 'ETHETH');

    console.log(`🐺 Wolf targets: ${usdtSymbols.join(', ')}`);

    await this.launchWolf(usdtSymbols, ethSymbols);
    console.log('\n🐺 Wolf returns to shadows');
  }

  private async launchAnts(universe: string[]): Promise<void> {
    console.log('🐜 Launching the Ants — workers of the earth...');
    return new Promise((resolve) => {
      const env = {
        ...process.env,
        CONFIRM_LIVE_TRADING: 'no',
        DRY_RUN: 'false',
        ANTS_UNIVERSE: universe.join(','),
        ANTS_ROTATIONS: String(this.cfg.beeCycles),
        ANTS_SPEND_USDT: process.env.ANTS_SPEND_USDT || '11',
        ANTS_MAX_MIN: '3',
      };
      const child = spawn('npx', ['tsx', 'scripts/armyAnts.ts'], { env, stdio: 'inherit' });
      child.on('close', () => resolve());
      this.children.push(child);
    });
  }

  private async launchBee(universe: string[]): Promise<void> {
    if (!universe.length) return;
    console.log('🐝 Launching the Bee — pollinator of the sky...');
    return new Promise((resolve) => {
      const env = {
        ...process.env,
        CONFIRM_LIVE_TRADING: 'no',
        DRY_RUN: 'false',
        HB_UNIVERSE: universe.join(','),
        HB_MAX_MINUTES: String(this.cfg.hbMaxMinutes),
      };
      const child = spawn('npx', ['tsx', 'scripts/hummingbird.ts'], { env, stdio: 'inherit' });
      child.on('close', () => resolve());
      this.children.push(child);
    });
  }

  private async launchLion(symbol: string): Promise<void> {
    return new Promise((resolve) => {
      const env: NodeJS.ProcessEnv = {
        ...process.env,
        CONFIRM_LIVE_TRADING: 'no',
        DRY_RUN: 'false',
        RAINBOW_CYCLES: String(this.cfg.lionCycles),
      };
      if (this.cfg.dreamMode) env.DREAM_MODE = this.cfg.dreamMode;
      if (this.cfg.alpha !== undefined) env.DREAM_ALPHA = String(this.cfg.alpha);
      if (this.cfg.beta !== undefined) env.DREAM_BETA = String(this.cfg.beta);

      const child = spawn('npx', ['tsx', 'scripts/rainbowArch.ts', symbol, '--live', `--interval=${this.cfg.interval}`], { env, stdio: 'inherit' });
      child.on('close', () => resolve());
      this.children.push(child);
    });
  }

  private async launchWolf(usdtUniverse: string[], ethUniverse: string[]): Promise<void> {
    return new Promise((resolve) => {
      const env = {
        ...process.env,
        CONFIRM_LIVE_TRADING: 'no',
        DRY_RUN: 'false',
        WOLF_UNIVERSE_USDT: usdtUniverse.join(','),
        WOLF_UNIVERSE_ETH: ethUniverse.join(','),
        WOLF_SPEND_USDT: process.env.WOLF_SPEND_USDT || '50',
        WOLF_MAX_MIN: String(this.cfg.wolfMaxMinutes),
      };
      const child = spawn('npx', ['tsx', 'scripts/loneWolf.ts'], { env, stdio: 'inherit' });
      child.on('close', () => resolve());
      this.children.push(child);
    });
  }

  private async checkBeesProfit(): Promise<number> {
    // Check combined profit from both Bee and Ant
    let total = 0;
    try {
      const antPath = path.join(process.cwd(), 'artifacts', 'ants_profit.json');
      const antData = await fs.readFile(antPath, 'utf-8');
      total += JSON.parse(antData).profitUSD || 0;
    } catch {}
    try {
      const beePath = path.join(process.cwd(), 'artifacts', 'bee_profit.json');
      const beeData = await fs.readFile(beePath, 'utf-8');
      total += JSON.parse(beeData).profitUSD || 0;
    } catch {}
    return total;
  }

  private async saveHiveExpansionFund(amount: number): Promise<void> {
    try {
      const fundPath = path.join(process.cwd(), 'artifacts', 'hive_expansion_fund.json');
      let current = 0;
      try {
        const data = await fs.readFile(fundPath, 'utf-8');
        current = JSON.parse(data).total || 0;
      } catch {}
      const newTotal = current + amount;
      await fs.writeFile(fundPath, JSON.stringify({ total: newTotal, lastAdded: amount, timestamp: Date.now() }, null, 2));
      console.log(`🏛️  Hive Expansion Fund: $${newTotal.toFixed(2)} (+$${amount.toFixed(2)})`);
    } catch (e: any) {
      console.error(`Failed to save hive expansion fund: ${e.message}`);
    }
  }

  private async getBalance(asset: string): Promise<number> {
    const acct = await this.client.getAccount();
    return Number(acct.balances.find(b => b.asset === asset)?.free || 0);
  }

  private async getPortfolioValueUSD(): Promise<number> {
    const acct = await this.client.getAccount();
    let total = 0;
    for (const bal of acct.balances) {
      const free = Number(bal.free);
      if (free <= 0) continue;
      if (bal.asset === 'USDT') {
        total += free;
      } else if (bal.asset === 'ETH') {
        const ethPrice = await this.client.getPrice('ETHUSDT');
        total += free * ethPrice;
      } else {
        // Try to price other assets via USDT pair
        try {
          const price = await this.client.getPrice(`${bal.asset}USDT`);
          total += free * price;
        } catch {
          // Skip if no USDT pair
        }
      }
    }
    return total;
  }

  private teardown() {
    console.log('\n🌺 THE GARDEN RESTS');
    console.log('═══════════════════════════════════════════════════════════');
    for (const c of this.children) {
      try { c.kill('SIGTERM'); } catch {}
    }
  }

  private sleep(ms: number): Promise<void> { return new Promise(r => setTimeout(r, ms)); }
}

async function main() {
  const args = process.argv.slice(2);
  const cfg: Partial<GardenConfig> = {
    beeThresholdUSD: parseFloat(args.find(a => a.startsWith('--bee-threshold='))?.split('=')[1] || '5'),
    wolfThresholdUSD: parseFloat(args.find(a => a.startsWith('--wolf-threshold='))?.split('=')[1] || '1000000'),
    hiveExpansionRatio: parseFloat(args.find(a => a.startsWith('--hive-ratio='))?.split('=')[1] || '0.1'),
    beeCycles: parseInt(args.find(a => a.startsWith('--bee-cycles='))?.split('=')[1] || '4'),
    hbMaxMinutes: parseInt(args.find(a => a.startsWith('--hb-minutes='))?.split('=')[1] || '10'),
    lionCycles: parseInt(args.find(a => a.startsWith('--lion-cycles='))?.split('=')[1] || '10'),
    wolfMaxMinutes: parseInt(args.find(a => a.startsWith('--wolf-minutes='))?.split('=')[1] || '5'),
    interval: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    minVolatility: parseFloat(args.find(a => a.startsWith('--volatility='))?.split('=')[1] || '2.0'),
    minVolume: parseFloat(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
    dreamMode: args.find(a => a.startsWith('--dream='))?.split('=')[1],
    alpha: args.find(a => a.startsWith('--alpha=')) ? parseFloat(args.find(a => a.startsWith('--alpha='))!.split('=')[1]) : undefined,
    beta: args.find(a => a.startsWith('--beta=')) ? parseFloat(args.find(a => a.startsWith('--beta='))!.split('=')[1]) : undefined,
  };

  const garden = new TheGarden(cfg);
  process.on('SIGINT', () => {
    garden['teardown']();
    process.exit(0);
  });
  
  await garden.grow();
}

main().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
