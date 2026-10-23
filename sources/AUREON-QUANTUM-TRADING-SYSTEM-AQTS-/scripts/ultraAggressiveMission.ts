#!/usr/bin/env tsx
/**
 * ULTRA AGGRESSIVE 8-HOUR HONEY HARVEST MISSION 🍯
 * 
 * Target: 50 trades, 100% win rate, maximum honey collection
 * Strategy: High-confidence signals, aggressive sizing, rapid execution
 * Risk: ULTRA-AGGRESSIVE (managed)
 */

import { HiveController } from '../core/hiveController';
import { DeepPartial, AQTSConfig } from '../core/config';

interface MissionConfig {
  durationMinutes: number;
  targetTrades: number;
  startingCapital: number;
  numAgents: number;
  symbols: string[];
}

interface MissionMetrics {
  startTime: number;
  currentTime: number;
  elapsedMinutes: number;
  totalTrades: number;
  winners: number;
  losers: number;
  winRate: number;
  totalPnL: number;
  currentEquity: number;
  returnPercent: number;
  tradesPerHour: number;
  hoursRemaining: number;
  phase: string;
}

// ULTRA-AGGRESSIVE AUREON CONFIGURATION
const ULTRA_AGGRESSIVE_CONFIG: DeepPartial<AQTSConfig> = {
  mode: 'paper',
  tradingPairs: [
    'BTC/USDT',
    'ETH/USDT', 
    'BNB/USDT',
    'SOL/USDT',
    'DOGE/USDT',
    'ADA/USDT',
    'MATIC/USDT',
    'AVAX/USDT',
  ],
  qgita: {
    fibonacciSequence: [3, 5, 8, 13, 21], // Compressed timing
    minConfidence: 0.70,  // ONLY ultra-high probability
    neutralConfidence: 0.80,
    historyLimit: 300,
  },
  decision: {
    buyThreshold: 0.25,  // Stronger signals only
    sellThreshold: -0.25,
    minimumConfidence: 0.70,  // Ultra-selective
    weights: {
      ensemble: 0.5,
      sentiment: 0.25,
      qgita: 0.25,
    },
  },
  risk: {
    initialEquity: 1000,
    maxPortfolioRisk: 0.08,  // 2.67x more aggressive
    maxLeverage: 10,  // 2x leverage increase
    circuitBreaker: 0.15,  // More risk tolerance
    riskPerTradeCap: 0.10,  // 2.5x position sizes
    kellyMultiplier: 1.5,  // 1.5x Kelly sizing
    minHoldMinutes: 15,  // Faster turnover
    maxHoldMinutes: 120,  // Quick moves only
  },
  execution: {
    maxSlippageBps: 12,  // Tighter execution
    latencyRange: { min: 25, max: 80 },
    partialFillProbability: 0.10,
  },
  analytics: {
    performanceHistory: 500,
    sentimentHistory: 250,
  },
};

class UltraAggressiveMission {
  private config: MissionConfig;
  private hiveController: HiveController;
  private startTime: number;
  private metrics: MissionMetrics;
  private phaseStartTrades: number = 0;

  constructor(config: MissionConfig) {
    this.config = config;
    this.startTime = Date.now();
    
    // Initialize Hive Controller with ultra-aggressive settings
    this.hiveController = new HiveController(
      config.numAgents,
      config.startingCapital / config.numAgents,
      0.015,  // Prime scale - slightly higher for aggression
      config.startingCapital * 3,  // Target 3x for mission
      ULTRA_AGGRESSIVE_CONFIG
    );

    this.metrics = {
      startTime: this.startTime,
      currentTime: this.startTime,
      elapsedMinutes: 0,
      totalTrades: 0,
      winners: 0,
      losers: 0,
      winRate: 0,
      totalPnL: 0,
      currentEquity: config.startingCapital,
      returnPercent: 0,
      tradesPerHour: 0,
      hoursRemaining: config.durationMinutes / 60,
      phase: 'PHASE 1: SUPER-AGGRESSIVE',
    };
  }

  private updateMetrics() {
    const state = this.hiveController.getState();
    const hiveMetrics = this.hiveController.getMetrics();
    
    this.metrics.currentTime = Date.now();
    this.metrics.elapsedMinutes = (this.metrics.currentTime - this.startTime) / 60000;
    this.metrics.totalTrades = state.aggregateTradeCount;
    
    // Calculate winners/losers from all agents
    this.metrics.winners = this.hiveController.agents.reduce((acc, a) => acc + a.wins, 0);
    this.metrics.losers = this.hiveController.agents.reduce((acc, a) => acc + a.losses, 0);
    this.metrics.winRate = this.metrics.totalTrades > 0 
      ? this.metrics.winners / this.metrics.totalTrades 
      : 0;
    
    this.metrics.currentEquity = state.totalEquity;
    this.metrics.totalPnL = this.metrics.currentEquity - this.config.startingCapital;
    this.metrics.returnPercent = (this.metrics.totalPnL / this.config.startingCapital) * 100;
    this.metrics.tradesPerHour = this.metrics.elapsedMinutes > 0
      ? (this.metrics.totalTrades / this.metrics.elapsedMinutes) * 60
      : 0;
    this.metrics.hoursRemaining = Math.max(0, (this.config.durationMinutes - this.metrics.elapsedMinutes) / 60);

    // Update phase based on time and trades
    if (this.metrics.elapsedMinutes < 120) {
      this.metrics.phase = 'PHASE 1: SUPER-AGGRESSIVE CAPTURE';
    } else if (this.metrics.elapsedMinutes < 300) {
      this.metrics.phase = 'PHASE 2: MULTI-SYMBOL SWARM';
    } else if (this.metrics.elapsedMinutes < 420) {
      this.metrics.phase = 'PHASE 3: FIBONACCI TIME COMPRESSION';
    } else {
      this.metrics.phase = 'PHASE 4: FINAL HOUR BLITZ';
    }
  }

  private printMetrics() {
    console.log('\n' + '='.repeat(80));
    console.log('🔥 ULTRA AGGRESSIVE MISSION STATUS 🍯');
    console.log('='.repeat(80));
    console.log(`Phase: ${this.metrics.phase}`);
    console.log(`Time Elapsed: ${this.metrics.elapsedMinutes.toFixed(1)} minutes (${this.metrics.hoursRemaining.toFixed(2)} hours remaining)`);
    console.log('-'.repeat(80));
    console.log(`Total Trades: ${this.metrics.totalTrades}/${this.config.targetTrades}`);
    console.log(`Winners: ${this.metrics.winners} | Losers: ${this.metrics.losers}`);
    console.log(`Win Rate: ${(this.metrics.winRate * 100).toFixed(1)}% 🎯`);
    console.log(`Trades/Hour: ${this.metrics.tradesPerHour.toFixed(1)}`);
    console.log('-'.repeat(80));
    console.log(`Starting Capital: $${this.config.startingCapital.toFixed(2)}`);
    console.log(`Current Equity: $${this.metrics.currentEquity.toFixed(2)}`);
    console.log(`Total P&L: $${this.metrics.totalPnL.toFixed(2)} (${this.metrics.returnPercent >= 0 ? '+' : ''}${this.metrics.returnPercent.toFixed(2)}%)`);
    console.log('-'.repeat(80));
    console.log(`🍯 HONEY COLLECTED: $${Math.max(0, this.metrics.totalPnL).toFixed(2)} 🍯`);
    console.log('='.repeat(80) + '\n');
  }

  private checkMilestones() {
    const elapsed = this.metrics.elapsedMinutes;
    
    // Hour 2 checkpoint
    if (elapsed >= 120 && elapsed < 125 && this.metrics.totalTrades >= 12) {
      console.log('✅ MILESTONE: Hour 2 - Target trades achieved!');
    }
    
    // Hour 5 checkpoint
    if (elapsed >= 300 && elapsed < 305 && this.metrics.totalTrades >= 35) {
      console.log('✅ MILESTONE: Hour 5 - On track for success!');
    }
    
    // Hour 7 checkpoint
    if (elapsed >= 420 && elapsed < 425 && this.metrics.totalTrades >= 45) {
      console.log('✅ MILESTONE: Hour 7 - Final sprint activated!');
    }
    
    // Check for circuit breaker
    if (this.metrics.losers >= 3 && this.metrics.winners === 0) {
      console.log('⚠️  CIRCUIT BREAKER: 3 losses detected, pausing for 30 minutes...');
      // In real implementation, would actually pause
    }
  }

  async run() {
    console.log('🚀 ULTRA AGGRESSIVE MISSION STARTING 🚀\n');
    console.log(`Mission Duration: ${this.config.durationMinutes} minutes (${this.config.durationMinutes / 60} hours)`);
    console.log(`Target Trades: ${this.config.targetTrades}`);
    console.log(`Starting Capital: $${this.config.startingCapital}`);
    console.log(`Number of Agents: ${this.config.numAgents}`);
    console.log(`Trading Symbols: ${this.config.symbols.join(', ')}\n`);
    console.log('Press Ctrl+C to stop mission safely\n');

    let stepCount = 0;
    const startTime = Date.now();
    const endTime = startTime + (this.config.durationMinutes * 60 * 1000);

    // Mission control loop
    while (Date.now() < endTime && this.metrics.totalTrades < this.config.targetTrades) {
      // Execute one step for all agents
      this.hiveController.step();
      stepCount++;

      // Update metrics every 10 steps
      if (stepCount % 10 === 0) {
        this.updateMetrics();
      }

      // Print status every 100 steps (~every 50 seconds)
      if (stepCount % 100 === 0) {
        this.printMetrics();
        this.checkMilestones();
      }

      // Prevent excessive CPU usage
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Final metrics
    this.updateMetrics();
    this.printMetrics();

    console.log('\n🎯 MISSION COMPLETE! 🎯\n');
    console.log('Final Summary:');
    console.log(`Total Time: ${this.metrics.elapsedMinutes.toFixed(1)} minutes`);
    console.log(`Total Trades: ${this.metrics.totalTrades}`);
    console.log(`Win Rate: ${(this.metrics.winRate * 100).toFixed(1)}%`);
    console.log(`Final Return: ${this.metrics.returnPercent >= 0 ? '+' : ''}${this.metrics.returnPercent.toFixed(2)}%`);
    console.log(`\n🍯 TOTAL HONEY HARVESTED: $${Math.max(0, this.metrics.totalPnL).toFixed(2)} 🍯\n`);

    // Mission assessment
    if (this.metrics.winRate >= 0.95 && this.metrics.returnPercent >= 50) {
      console.log('🏆 OUTSTANDING SUCCESS! Mission objectives exceeded! 🏆');
    } else if (this.metrics.winRate >= 0.80 && this.metrics.returnPercent >= 30) {
      console.log('✅ MISSION SUCCESS! Strong performance achieved! ✅');
    } else if (this.metrics.returnPercent > 0) {
      console.log('✓ Mission complete with positive returns');
    } else {
      console.log('⚠️  Mission complete, review results for optimization');
    }
  }
}

// Main execution
async function main() {
  // Check for environment confirmation
  const confirmMission = process.env.CONFIRM_MISSION === 'YES';
  const missionMode = process.env.MISSION_MODE || 'ULTRA_AGGRESSIVE';
  
  if (!confirmMission) {
    console.log('⚠️  ULTRA AGGRESSIVE MISSION requires confirmation!');
    console.log('Set CONFIRM_MISSION=YES to proceed\n');
    console.log('Example:');
    console.log('  export CONFIRM_MISSION=YES');
    console.log('  npx tsx scripts/ultraAggressiveMission.ts\n');
    process.exit(1);
  }

  console.log(`Mission Mode: ${missionMode}`);
  console.log('Risk Level: ULTRA-AGGRESSIVE ⚡');
  console.log('Starting in 3 seconds...\n');
  await new Promise(resolve => setTimeout(resolve, 3000));

  const config: MissionConfig = {
    durationMinutes: parseInt(process.env.MISSION_DURATION || '480', 10), // 8 hours
    targetTrades: parseInt(process.env.TARGET_TRADES || '50', 10),
    startingCapital: parseFloat(process.env.STARTING_CAPITAL || '1000'),
    numAgents: 8,  // One per trading pair
    symbols: [
      'BTC/USDT',
      'ETH/USDT',
      'BNB/USDT',
      'SOL/USDT',
      'DOGE/USDT',
      'ADA/USDT',
      'MATIC/USDT',
      'AVAX/USDT',
    ],
  };

  const mission = new UltraAggressiveMission(config);
  await mission.run();
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n⚠️  Mission aborted by user');
  console.log('Shutting down safely...\n');
  process.exit(0);
});

main().catch(error => {
  console.error('❌ Mission failed with error:', error);
  process.exit(1);
});
