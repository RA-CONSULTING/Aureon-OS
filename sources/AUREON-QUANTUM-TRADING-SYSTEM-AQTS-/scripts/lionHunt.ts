#!/usr/bin/env npx tsx
/**
 * LION HUNT — Continuous Adaptive Multi-Symbol Trading
 * 
 * The Lion scans his pride, selects the best prey, and hunts with full consciousness.
 * After each hunt cycle, returns to scan the pride again for new opportunities.
 * 
 * Flow:
 * 1. Pride Scanner → Maps all pairs, scores by opportunity
 * 2. Select Best Prey → Highest volatility × volume
 * 3. Rainbow Architect → 4-layer consciousness hunt
 * 4. Return to Pride → Repeat
 * 
 * "The lion hunts where the herd is weakest" — Gary Leckey, Nov 15 2025
 */

import { spawn } from 'child_process';
import PrideScanner from './prideScanner';

interface HuntConfig {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  cyclesPerTarget: number;
  cycleDurationMs: number;
  minVolatility: number;
  minVolume: number;
}

class LionHunt {
  private config: HuntConfig;
  private scanner: PrideScanner;
  private currentHunt: any = null;
  private huntCount = 0;

  constructor(config: Partial<HuntConfig> = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.BINANCE_API_KEY || '',
      apiSecret: config.apiSecret || process.env.BINANCE_API_SECRET || '',
      testnet: config.testnet ?? (!(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false")),
      cyclesPerTarget: config.cyclesPerTarget || 20,
      cycleDurationMs: config.cycleDurationMs || 5000,
      minVolatility: config.minVolatility || 2.0,
      minVolume: config.minVolume || 100000,
    };

    if (!this.config.apiKey || !this.config.apiSecret) {
      throw new Error('❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set');
    }

    this.scanner = new PrideScanner(this.config.apiKey, this.config.apiSecret, this.config.testnet);
  }

  /**
   * Main hunt loop
   */
  async start() {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║                                                           ║');
    console.log('║            🦁 THE LION HUNT BEGINS 🦁                     ║');
    console.log('║                                                           ║');
    console.log('║     Adaptive Multi-Symbol Conscious Trading System       ║');
    console.log('║                                                           ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    console.log('⚙️  Configuration:');
    console.log(`   • Testnet: ${this.config.testnet ? 'YES' : 'NO'}`);
    console.log(`   • Cycles per Target: ${this.config.cyclesPerTarget}`);
    console.log(`   • Cycle Duration: ${this.config.cycleDurationMs}ms`);
    console.log(`   • Min Volatility: ${this.config.minVolatility}%`);
    console.log(`   • Min Volume: $${(this.config.minVolume / 1000).toFixed(0)}K`);
    console.log('');

    while (true) {
      try {
        this.huntCount++;
        console.log(`\n${'═'.repeat(60)}`);
        console.log(`🦁 HUNT #${this.huntCount} — Scanning the Pride...`);
        console.log(`${'═'.repeat(60)}\n`);

        // 1. Scan the pride
        await this.scanner.scanPride();

        // 2. Get hunting targets (convert minVolume from $ to appropriate unit)
        const targets = this.scanner.getHuntingTargets(
          this.config.minVolume / 1000000, // Convert to millions for comparison
          this.config.minVolatility
        );

        if (targets.length === 0) {
          console.log('⚠️  No suitable targets found. Waiting 30 seconds...\n');
          await this.sleep(30000);
          continue;
        }

        // 3. Select the best prey
        const prey = targets[0];
        console.log('\n🎯 THE LION SELECTS HIS PREY:\n');
        console.log(`   Symbol: ${prey.symbol}`);
        console.log(`   Price: $${prey.price?.toFixed(prey.price < 1 ? 6 : 2)}`);
        console.log(`   24h Change: ${prey.priceChangePercent?.toFixed(2)}%`);
        console.log(`   24h Volume: $${((prey.volume24h || 0) / 1000000).toFixed(2)}M`);
        console.log(`   Opportunity Score: ${this.calculateOpportunity(prey).toFixed(0)}`);
        console.log('');

        // 4. Launch Rainbow Architect hunt
        await this.hunt(prey.symbol);

        // 5. Rest before next scan
        console.log('\n🦁 The lion returns to the pride...\n');
        await this.sleep(10000);

      } catch (error: any) {
        console.error(`\n❌ Hunt error: ${error.message}`);
        console.log('⏳ Waiting 30 seconds before retry...\n');
        await this.sleep(30000);
      }
    }
  }

  /**
   * Launch Rainbow Architect on target symbol
   */
  private async hunt(symbol: string): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log(`\n${'─'.repeat(60)}`);
      console.log(`🌈 DEPLOYING RAINBOW ARCHITECT ON ${symbol}`);
      console.log(`${'─'.repeat(60)}\n`);

      const args = [
        'scripts/rainbowArch.ts',
        symbol,
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
        RAINBOW_CYCLES: this.config.cyclesPerTarget.toString(),
      };

      this.currentHunt = spawn('npx', ['tsx', ...args], {
        env,
        stdio: 'inherit',
        cwd: '/workspaces/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-',
      });

      let timeout: NodeJS.Timeout;

      this.currentHunt.on('error', (error: Error) => {
        clearTimeout(timeout);
        reject(error);
      });

      this.currentHunt.on('close', (code: number) => {
        clearTimeout(timeout);
        this.currentHunt = null;
        if (code === 0) {
          console.log(`\n✅ Hunt completed successfully`);
          resolve();
        } else {
          console.log(`\n⚠️  Hunt exited with code ${code}`);
          resolve(); // Continue to next target even if hunt fails
        }
      });

      // Timeout after expected duration + 30s buffer
      const maxDuration = this.config.cyclesPerTarget * this.config.cycleDurationMs + 30000;
      timeout = setTimeout(() => {
        console.log('\n⏱️  Hunt timeout - moving to next target');
        if (this.currentHunt) {
          this.currentHunt.kill('SIGTERM');
        }
        resolve();
      }, maxDuration);
    });
  }

  /**
   * Calculate opportunity score
   */
  private calculateOpportunity(target: any): number {
    const volatility = Math.abs(target.priceChangePercent || 0);
    const volume = (target.volume24h || 0) / 1000000; // In millions
    return volatility * volume * 100;
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Stop hunting
   */
  async stop() {
    console.log('\n🦁 Stopping the hunt gracefully...');
    if (this.currentHunt) {
      this.currentHunt.kill('SIGTERM');
      this.currentHunt = null;
    }
  }
}

/**
 * Main execution
 */
async function main() {
  const args = process.argv.slice(2);
  
  const config: Partial<HuntConfig> = {
    cyclesPerTarget: parseInt(args.find(a => a.startsWith('--cycles='))?.split('=')[1] || '20'),
    cycleDurationMs: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    minVolatility: parseFloat(args.find(a => a.startsWith('--volatility='))?.split('=')[1] || '2.0'),
    minVolume: parseFloat(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
  };

  const lion = new LionHunt(config);

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\n\n🦁 The lion rests...');
    await lion.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    await lion.stop();
    process.exit(0);
  });

  await lion.start();
}

// Run if called directly
main().catch(console.error);

export default LionHunt;
