#!/usr/bin/env npx tsx
/**
 * PRIDE HUNT — The Lion and His Lionesses
 * 
 * 1 Lion + 12 Lionesses = 13 Hunters
 * Each hunts a different prey simultaneously
 * Coordinated multi-symbol conscious trading
 * 
 * "The pride hunts together" — Gary Leckey, Nov 15 2025
 */

// Load environment (.env) settings
import '../core/environment';

import { spawn, ChildProcess } from 'child_process';
import PrideScanner from './prideScanner';
import ElephantMemory from '../core/elephantMemory';

interface Hunter {
  id: number;
  role: 'LION' | 'LIONESS';
  symbol: string;
  process: ChildProcess | null;
  trades: number;
  profit: number;
  status: 'hunting' | 'resting' | 'complete';
}

interface PrideConfig {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  cyclesPerHunt: number;
  cycleDurationMs: number;
  minVolatility: number;
  minVolume: number;
  huntDuration: number; // Minutes before reassigning targets
  cooldownMinutes?: number; // Elephant memory cooldown
}

class PrideHunt {
  private config: PrideConfig;
  private scanner: PrideScanner;
  private memory: ElephantMemory;
  private hunters: Hunter[] = [];
  private prideCount = 13; // 1 Lion + 12 Lionesses
  private huntRound = 0;

  constructor(config: Partial<PrideConfig> = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.BINANCE_API_KEY || '',
      apiSecret: config.apiSecret || process.env.BINANCE_API_SECRET || '',
      testnet: config.testnet ?? (!(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false")),
      cyclesPerHunt: config.cyclesPerHunt || 20,
      cycleDurationMs: config.cycleDurationMs || 5000,
      minVolatility: config.minVolatility || 2.0,
      minVolume: config.minVolume || 100000,
      huntDuration: config.huntDuration || 5, // 5 minutes per hunt round
      cooldownMinutes: config.cooldownMinutes ?? 15,
    };

    if (!this.config.apiKey || !this.config.apiSecret) {
      throw new Error('❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set');
    }

    this.scanner = new PrideScanner(this.config.apiKey, this.config.apiSecret, this.config.testnet);
    this.memory = new ElephantMemory({ cooldownMinutes: this.config.cooldownMinutes });
    this.initializePride();
  }

  /**
   * Initialize the pride: 1 Lion + 12 Lionesses
   */
  private initializePride() {
    for (let i = 0; i < this.prideCount; i++) {
      this.hunters.push({
        id: i + 1,
        role: i === 0 ? 'LION' : 'LIONESS',
        symbol: '',
        process: null,
        trades: 0,
        profit: 0,
        status: 'resting',
      });
    }
  }

  /**
   * Start the pride hunt
   */
  async start() {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║                                                           ║');
    console.log('║         🦁 THE PRIDE HUNTS TOGETHER 🦁                   ║');
    console.log('║                                                           ║');
    console.log('║              1 Lion + 12 Lionesses = 13                   ║');
    console.log('║                                                           ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    console.log('🦁 Pride Configuration:');
    console.log(`   • Hunters: ${this.prideCount} (1 Lion, 12 Lionesses)`);
    console.log(`   • Testnet: ${this.config.testnet ? 'YES' : 'NO'}`);
    console.log(`   • Cycles per Hunt: ${this.config.cyclesPerHunt}`);
    console.log(`   • Cycle Duration: ${this.config.cycleDurationMs}ms`);
    console.log(`   • Hunt Duration: ${this.config.huntDuration} minutes`);
    console.log(`   • Min Volatility: ${this.config.minVolatility}%`);
    console.log(`   • Min Volume: $${(this.config.minVolume / 1000).toFixed(0)}K`);
    console.log(`   • Cooldown: ${this.config.cooldownMinutes} minutes`);
    // Dream Band banner (inherited by child processes via env)
    const dreamMode = (process.env.DREAM_MODE || 'off').toLowerCase();
    const dreamAlpha = process.env.DREAM_ALPHA ? parseFloat(process.env.DREAM_ALPHA) : undefined;
    const dreamBeta = process.env.DREAM_BETA ? parseFloat(process.env.DREAM_BETA) : undefined;
    if (dreamMode !== 'off' || (dreamAlpha !== undefined && dreamBeta !== undefined)) {
      const modeLabel = dreamMode === 'dream' ? 'DREAM BAND — SELF-SIMULATION' : dreamMode === 'sweet' ? 'SWEET SPOT — COHERENCE LOCK' : 'CUSTOM BAND';
      const a = (dreamAlpha ?? (dreamMode === 'dream' ? 0.3 : dreamMode === 'sweet' ? 0.9 : 1.2)).toFixed(3);
      const b = (dreamBeta ?? (dreamMode === 'dream' || dreamMode === 'sweet' ? 0.8 : 0.8)).toFixed(3);
      console.log('');
      console.log('   Dream Band: ' + modeLabel);
      console.log(`   • α (observer gain): ${a}`);
      console.log(`   • β (memory gain):   ${b}`);
    }
    console.log('');

    while (true) {
      try {
        this.huntRound++;
        await this.executeHuntRound();
        
        // Rest between rounds
        console.log('\n🦁 The pride rests...\n');
        await this.sleep(30000); // 30 seconds rest
        
      } catch (error: any) {
        console.error(`\n❌ Hunt round error: ${error.message}`);
        console.log('⏳ Waiting 60 seconds before retry...\n');
        await this.sleep(60000);
      }
    }
  }

  /**
   * Execute one hunt round: scan, assign targets, hunt, collect
   */
  private async executeHuntRound() {
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`🦁 HUNT ROUND #${this.huntRound} — The Pride Awakens`);
    console.log(`${'═'.repeat(60)}\n`);

    // 1. Scan the territory
    console.log('🔍 Scanning the territory...\n');
    await this.scanner.scanPride();

    // 2. Get top targets
    let targets = this.scanner.getHuntingTargets(
      this.config.minVolume / 1000000,
      this.config.minVolatility
    );

    // Elephant memory filter: avoid recently hunted / blacklisted
    const avoided: string[] = [];
    targets = targets.filter(t => {
      const avoid = this.memory.shouldAvoid(t.symbol);
      if (avoid) avoided.push(t.symbol);
      return !avoid;
    });
    if (avoided.length) {
      console.log(`🧠 Elephant avoids (cooldown/blacklist): ${avoided.slice(0,10).join(', ')}${avoided.length>10?'…':''}`);
    }

    if (targets.length < this.prideCount) {
      console.log(`⚠️  Only ${targets.length} targets found, need ${this.prideCount}`);
      console.log(`   Lowering volatility threshold temporarily...\n`);
      
      // Get more targets with lower threshold
      const moreTargets = this.scanner.getHuntingTargets(
        this.config.minVolume / 1000000,
        this.config.minVolatility / 2
      );
      
      if (moreTargets.length < this.prideCount) {
        console.log(`⚠️  Still only ${moreTargets.length} targets. Pride will hunt these.\n`);
        await this.assignTargets(moreTargets.slice(0, this.prideCount));
      } else {
        await this.assignTargets(moreTargets.slice(0, this.prideCount));
      }
    } else {
      await this.assignTargets(targets.slice(0, this.prideCount));
    }

    // 3. Hunt in parallel
    await this.huntInParallel();

    // 4. Collect results
    this.displayResults();
  }

  /**
   * Assign targets to hunters
   */
  private async assignTargets(targets: any[]) {
    console.log('🎯 TARGET ASSIGNMENTS:\n');
    
    for (let i = 0; i < Math.min(targets.length, this.prideCount); i++) {
      const hunter = this.hunters[i];
      const target = targets[i];
      
      hunter.symbol = target.symbol;
      hunter.status = 'hunting';
      
      const icon = hunter.role === 'LION' ? '🦁' : '🦁💛';
      const price = target.price ? `$${target.price.toFixed(target.price < 1 ? 6 : 2)}` : 'N/A';
      const change = target.priceChangePercent?.toFixed(2) || '0.00';
      const volume = ((target.volume24h || 0) / 1000000).toFixed(2);
      
      console.log(`   ${icon} ${hunter.role.padEnd(8)} #${hunter.id.toString().padStart(2)} → ${hunter.symbol.padEnd(12)} | ${price.padStart(12)} | ${change.padStart(7)}% | $${volume}M`);

      // Remember assignment in memory
      this.memory.rememberHunt(hunter.symbol, {
        volume: target.volume24h || 0,
        change: target.priceChangePercent || 0,
        hunter: `${hunter.role}#${hunter.id}`,
        round: this.huntRound,
      });
    }
    console.log('');
  }

  /**
   * Hunt in parallel: all 13 hunters at once
   */
  private async huntInParallel() {
    console.log(`\n${'─'.repeat(60)}`);
    console.log('🦁 THE PRIDE HUNTS AS ONE');
    console.log(`${'─'.repeat(60)}\n`);

    const huntPromises: Promise<void>[] = [];

    // Launch all hunters
    for (const hunter of this.hunters) {
      if (hunter.status === 'hunting' && hunter.symbol) {
        huntPromises.push(this.launchHunter(hunter));
      }
    }

    // Wait for all hunts to complete (with timeout)
    const huntTimeout = this.config.huntDuration * 60 * 1000; // Convert minutes to ms
    
    await Promise.race([
      Promise.all(huntPromises),
      this.sleep(huntTimeout),
    ]);

    // Kill any remaining processes
    for (const hunter of this.hunters) {
      if (hunter.process) {
        hunter.process.kill('SIGTERM');
        hunter.process = null;
      }
      if (hunter.status === 'hunting') {
        hunter.status = 'complete';
      }
    }

    console.log(`\n✅ Hunt round complete\n`);
  }

  /**
   * Launch a single hunter
   */
  private async launchHunter(hunter: Hunter): Promise<void> {
    return new Promise((resolve) => {
      const icon = hunter.role === 'LION' ? '🦁' : '💛';
      console.log(`${icon} ${hunter.role} #${hunter.id} hunting ${hunter.symbol}...`);

      const args = [
        'scripts/rainbowArch.ts',
        hunter.symbol,
        '--live',
        `--interval=${this.config.cycleDurationMs}`,
      ];

      const env = {
        ...process.env,
        BINANCE_API_KEY: this.config.apiKey,
        BINANCE_API_SECRET: this.config.apiSecret,
        BINANCE_TESTNET: this.config.testnet.toString(),
        CONFIRM_LIVE_TRADING: 'no',
        DRY_RUN: 'false',
        RAINBOW_CYCLES: this.config.cyclesPerHunt.toString(),
        // Propagate Dream Band controls
        DREAM_MODE: process.env.DREAM_MODE || '',
        DREAM_ALPHA: process.env.DREAM_ALPHA || '',
        DREAM_BETA: process.env.DREAM_BETA || '',
      };

      hunter.process = spawn('npx', ['tsx', ...args], {
        env,
        stdio: 'pipe', // Capture output
        cwd: '/workspaces/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-',
      });

      // Parse output for trades/profit (optional)
      hunter.process.stdout?.on('data', (data) => {
        const output = data.toString();
        // Look for trade signals
        if (output.includes('TRADE SIGNAL')) {
          hunter.trades++;
        }
        // Capture summary lines
        const tradesMatch = output.match(/Total Trades:\s*(\d+)/i);
        if (tradesMatch) {
          const n = parseInt(tradesMatch[1] || '0');
          if (!Number.isNaN(n)) hunter.trades = n;
        }
        const profitMatch = output.match(/Total Profit:\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*USDT/i);
        if (profitMatch) {
          const p = parseFloat(profitMatch[1] || '0');
          if (!Number.isNaN(p)) hunter.profit = p;
        }
      });

      hunter.process.on('close', (code: number) => {
        hunter.status = 'complete';
        hunter.process = null;
        // Remember result
        this.memory.rememberResult(hunter.symbol, { trades: hunter.trades, profit: hunter.profit });
        resolve();
      });

      hunter.process.on('error', (error: Error) => {
        console.error(`   ❌ ${hunter.role} #${hunter.id} error: ${error.message}`);
        hunter.status = 'complete';
        hunter.process = null;
        resolve();
      });
    });
  }

  /**
   * Display hunt results
   */
  private displayResults() {
    console.log(`\n${'═'.repeat(60)}`);
    console.log('📊 HUNT ROUND RESULTS');
    console.log(`${'═'.repeat(60)}\n`);

    let totalTrades = 0;
    let totalProfit = 0;

    // Lion first
    const lion = this.hunters.find(h => h.role === 'LION');
    if (lion) {
      const icon = '🦁';
      console.log(`   ${icon} ${lion.role.padEnd(8)} #${lion.id.toString().padStart(2)} | ${lion.symbol.padEnd(12)} | Trades: ${lion.trades} | Profit: $${lion.profit.toFixed(2)}`);
      totalTrades += lion.trades;
      totalProfit += lion.profit;
    }

    // Then lionesses
    const lionesses = this.hunters.filter(h => h.role === 'LIONESS');
    for (const lioness of lionesses) {
      const icon = '💛';
      console.log(`   ${icon} ${lioness.role.padEnd(8)} #${lioness.id.toString().padStart(2)} | ${lioness.symbol.padEnd(12)} | Trades: ${lioness.trades} | Profit: $${lioness.profit.toFixed(2)}`);
      totalTrades += lioness.trades;
      totalProfit += lioness.profit;
    }

    console.log('\n   ─────────────────────────────────────────────────────');
    console.log(`   Total Pride: ${totalTrades} trades | $${totalProfit.toFixed(2)} profit`);
    console.log('');
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Stop all hunts gracefully
   */
  async stop() {
    console.log('\n🦁 The pride returns home...');
    
    for (const hunter of this.hunters) {
      if (hunter.process) {
        hunter.process.kill('SIGTERM');
        hunter.process = null;
      }
    }
  }
}

/**
 * Main execution
 */
async function main() {
  const args = process.argv.slice(2);
  
  const config: Partial<PrideConfig> = {
    cyclesPerHunt: parseInt(args.find(a => a.startsWith('--cycles='))?.split('=')[1] || '20'),
    cycleDurationMs: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    minVolatility: parseFloat(args.find(a => a.startsWith('--volatility='))?.split('=')[1] || '2.0'),
    minVolume: parseFloat(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
    huntDuration: parseInt(args.find(a => a.startsWith('--duration='))?.split('=')[1] || '5'),
  };

  const pride = new PrideHunt(config);

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\n\n🦁 The pride rests...');
    await pride.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    await pride.stop();
    process.exit(0);
  });

  await pride.start();
}

// Run if called directly
main().catch(console.error);

export default PrideHunt;
