#!/usr/bin/env node
/**
 * 🚀 SWARM TO MILLION: Paper Trading Simulator
 * 
 * Simulates coordinated swarm trading until $1M is reached
 * - Tracks cycles, time, and growth rate
 * - Uses realistic returns based on strategy profiles
 * - No API calls, pure simulation for speed
 */

import 'dotenv/config';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

interface SwarmStats {
  startCapital: number;
  currentCapital: number;
  cyclesCompleted: number;
  totalProfits: number;
  antTrades: number;
  wolfSignals: number;
  hummingbirdTrades: number;
  startTime: number;
  targetReached: boolean;
}

class MillionSimulator {
  private stats: SwarmStats;
  private readonly TARGET = 1_000_000;
  
  // Realistic return profiles (per cycle)
  private readonly ANT_RETURN_RANGE = [-0.005, 0.015]; // -0.5% to +1.5%
  private readonly HUMMINGBIRD_RETURN_RANGE = [-0.01, 0.025]; // -1% to +2.5%
  private readonly WOLF_SIGNAL_CHANCE = 0.3; // 30% chance per cycle
  private readonly ANT_ALLOCATION = 0.1; // Ants use 10% of capital
  private readonly HB_ALLOCATION = 0.2; // Hummingbird uses 20% when wolf signals

  constructor(startCapital: number) {
    this.stats = {
      startCapital,
      currentCapital: startCapital,
      cyclesCompleted: 0,
      totalProfits: 0,
      antTrades: 0,
      wolfSignals: 0,
      hummingbirdTrades: 0,
      startTime: Date.now(),
      targetReached: false
    };
  }

  private randomReturn(min: number, max: number): number {
    return min + Math.random() * (max - min);
  }

  private simulateCycle(): void {
    // Wolf scouts
    const wolfFindsSignal = Math.random() < this.WOLF_SIGNAL_CHANCE;
    if (wolfFindsSignal) this.stats.wolfSignals++;

    // Ants forage (always active)
    const antCapital = this.stats.currentCapital * this.ANT_ALLOCATION;
    const antReturn = this.randomReturn(this.ANT_RETURN_RANGE[0], this.ANT_RETURN_RANGE[1]);
    const antProfit = antCapital * antReturn;
    this.stats.currentCapital += antProfit;
    this.stats.totalProfits += antProfit;
    this.stats.antTrades++;

    // Hummingbird executes (only when wolf signals)
    if (wolfFindsSignal) {
      const hbCapital = this.stats.currentCapital * this.HB_ALLOCATION;
      const hbReturn = this.randomReturn(this.HUMMINGBIRD_RETURN_RANGE[0], this.HUMMINGBIRD_RETURN_RANGE[1]);
      const hbProfit = hbCapital * hbReturn;
      this.stats.currentCapital += hbProfit;
      this.stats.totalProfits += hbProfit;
      this.stats.hummingbirdTrades++;
    }

    this.stats.cyclesCompleted++;

    // Check if target reached
    if (this.stats.currentCapital >= this.TARGET) {
      this.stats.targetReached = true;
    }
  }

  private printProgress(): void {
    const elapsed = (Date.now() - this.stats.startTime) / 1000;
    const growth = ((this.stats.currentCapital - this.stats.startCapital) / this.stats.startCapital) * 100;
    const avgCycleTime = elapsed / this.stats.cyclesCompleted;
    const roi = (this.stats.totalProfits / this.stats.startCapital) * 100;
    
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🚀 SWARM TO MILLION - Progress Update                 ║
╚════════════════════════════════════════════════════════════════╝

Capital Progress:
  Start: $${this.stats.startCapital.toFixed(2)}
  Current: $${this.stats.currentCapital.toFixed(2)}
  Target: $${this.TARGET.toLocaleString()}
  Growth: ${growth.toFixed(2)}%
  ROI: ${roi.toFixed(2)}%

Trading Activity:
  Cycles: ${this.stats.cyclesCompleted.toLocaleString()}
  Ant Trades: ${this.stats.antTrades.toLocaleString()}
  Wolf Signals: ${this.stats.wolfSignals.toLocaleString()}
  Hummingbird Trades: ${this.stats.hummingbirdTrades.toLocaleString()}

Time Analysis:
  Elapsed: ${this.formatTime(elapsed)}
  Avg per cycle: ${avgCycleTime.toFixed(3)}s
  Cycles/hour: ${(3600 / avgCycleTime).toFixed(0)}
`);
  }

  private formatTime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (mins > 0) parts.push(`${mins}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
    
    return parts.join(' ');
  }

  private projectToMillion(): void {
    const growth = this.stats.currentCapital / this.stats.startCapital;
    const avgGrowthPerCycle = Math.pow(growth, 1 / this.stats.cyclesCompleted);
    const multiplierNeeded = this.TARGET / this.stats.currentCapital;
    const cyclesNeeded = Math.log(multiplierNeeded) / Math.log(avgGrowthPerCycle);
    const totalCycles = this.stats.cyclesCompleted + cyclesNeeded;
    
    const elapsed = (Date.now() - this.stats.startTime) / 1000;
    const avgCycleTime = elapsed / this.stats.cyclesCompleted;
    const totalTimeSeconds = totalCycles * avgCycleTime;
    const remainingSeconds = cyclesNeeded * avgCycleTime;
    
    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         📊 PROJECTION TO $1 MILLION                           ║
╚════════════════════════════════════════════════════════════════╝

Growth Analysis:
  Average growth per cycle: ${((avgGrowthPerCycle - 1) * 100).toFixed(4)}%
  Multiplier needed: ${multiplierNeeded.toFixed(2)}x
  Estimated cycles remaining: ${Math.ceil(cyclesNeeded).toLocaleString()}
  Total cycles needed: ${Math.ceil(totalCycles).toLocaleString()}

Time Estimates:
  Time remaining: ${this.formatTime(remainingSeconds)}
  Total time to $1M: ${this.formatTime(totalTimeSeconds)}
  
  @ 1 min/cycle: ${this.formatTime(totalCycles * 60)}
  @ 30 sec/cycle: ${this.formatTime(totalCycles * 30)}
  @ 10 sec/cycle: ${this.formatTime(totalCycles * 10)}
`);
  }

  async run(): Promise<void> {
    const LOG_INTERVAL = Number(process.env.LOG_INTERVAL || 1000);
    const PROJECTION_INTERVAL = Number(process.env.PROJECTION_INTERVAL || 5000);
    const CYCLE_DELAY = Number(process.env.CYCLE_DELAY_MS || 0); // No delay for fast sim

    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🚀 SWARM TO MILLION                                   ║
║         Paper Trading Simulator                               ║
╚════════════════════════════════════════════════════════════════╝

Starting simulation...
  Initial Capital: $${this.stats.startCapital.toFixed(2)}
  Target: $${this.TARGET.toLocaleString()}
  Multiplier needed: ${(this.TARGET / this.stats.startCapital).toFixed(2)}x
  
  Strategy:
    - Ants: ${(this.ANT_ALLOCATION * 100)}% allocation, ${this.ANT_RETURN_RANGE[0] * 100}% to ${this.ANT_RETURN_RANGE[1] * 100}% return
    - Wolf: ${(this.WOLF_SIGNAL_CHANCE * 100)}% signal rate
    - Hummingbird: ${(this.HB_ALLOCATION * 100)}% allocation, ${this.HUMMINGBIRD_RETURN_RANGE[0] * 100}% to ${this.HUMMINGBIRD_RETURN_RANGE[1] * 100}% return

Starting cycles...
`);

    while (!this.stats.targetReached) {
      this.simulateCycle();

      if (this.stats.cyclesCompleted % LOG_INTERVAL === 0) {
        this.printProgress();
      }

      if (this.stats.cyclesCompleted % PROJECTION_INTERVAL === 0 && this.stats.cyclesCompleted > 100) {
        this.projectToMillion();
      }

      if (CYCLE_DELAY > 0) {
        await sleep(CYCLE_DELAY);
      }
    }

    // Final report
    const elapsed = (Date.now() - this.stats.startTime) / 1000;
    const avgCycleTime = elapsed / this.stats.cyclesCompleted;
    const totalGrowth = ((this.stats.currentCapital - this.stats.startCapital) / this.stats.startCapital) * 100;

    console.log(`
╔════════════════════════════════════════════════════════════════╗
║         🎉 TARGET REACHED: $1 MILLION!                        ║
╚════════════════════════════════════════════════════════════════╝

Final Results:
  Starting Capital: $${this.stats.startCapital.toFixed(2)}
  Final Capital: $${this.stats.currentCapital.toFixed(2)}
  Total Profit: $${this.stats.totalProfits.toFixed(2)}
  Growth: ${totalGrowth.toFixed(2)}%

Trading Statistics:
  Total Cycles: ${this.stats.cyclesCompleted.toLocaleString()}
  Ant Trades: ${this.stats.antTrades.toLocaleString()}
  Wolf Signals: ${this.stats.wolfSignals.toLocaleString()}
  Hummingbird Trades: ${this.stats.hummingbirdTrades.toLocaleString()}

Time Analysis:
  Total Time: ${this.formatTime(elapsed)}
  Average per cycle: ${avgCycleTime.toFixed(3)}s
  Cycles per hour: ${(3600 / avgCycleTime).toFixed(0)}

Real-World Projections:
  @ 60s/cycle: ${this.formatTime(this.stats.cyclesCompleted * 60)}
  @ 30s/cycle: ${this.formatTime(this.stats.cyclesCompleted * 30)}
  @ 10s/cycle: ${this.formatTime(this.stats.cyclesCompleted * 10)}
  @ 5s/cycle: ${this.formatTime(this.stats.cyclesCompleted * 5)}

═══════════════════════════════════════════════════════════════

${this.estimateDaysToMillion()}
`);
  }

  private estimateDaysToMillion(): string {
    const cyclesPerDay_60s = (24 * 3600) / 60;
    const cyclesPerDay_30s = (24 * 3600) / 30;
    const cyclesPerDay_10s = (24 * 3600) / 10;
    
    const days_60s = this.stats.cyclesCompleted / cyclesPerDay_60s;
    const days_30s = this.stats.cyclesCompleted / cyclesPerDay_30s;
    const days_10s = this.stats.cyclesCompleted / cyclesPerDay_10s;

    return `Realistic Trading Scenarios:
  Conservative (60s/cycle, 24/7): ${days_60s.toFixed(1)} days (${(days_60s / 365).toFixed(2)} years)
  Moderate (30s/cycle, 24/7): ${days_30s.toFixed(1)} days (${(days_30s / 365).toFixed(2)} years)
  Aggressive (10s/cycle, 24/7): ${days_10s.toFixed(1)} days (${(days_10s / 365).toFixed(2)} years)`;
  }
}

async function main() {
  const startCapital = Number(process.env.START_CAPITAL || 100);
  const simulator = new MillionSimulator(startCapital);
  await simulator.run();
}

main().catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});
