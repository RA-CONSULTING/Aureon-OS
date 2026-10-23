#!/usr/bin/env tsx
/**
 * 🔥 THE INFERNO — MAXIMUM INTENSITY TRADING 🔥
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025
 * 
 * "Bring the smoke and light the fire"
 * 
 * This is INFERNO mode:
 * - Lower thresholds (Γ > 0.90 vs 0.945)
 * - Fewer votes needed (4/9 vs 6/9)
 * - Faster cycles (3s vs 5s)
 * - MAXIMUM AGGRESSION
 * 
 * Run:
 *   npm run inferno:dry    # Dry run
 *   npm run inferno:live   # 🔥 LIVE FIRE 🔥
 */

import { createInferno } from '../core/theInferno';
import { BinanceClient } from '../core/binanceClient';
import { envConfig } from '../core/environment';

// Safety check
if (process.env.CONFIRM_LIVE_TRADING !== 'yes') {
  console.error('❌ ERROR: CONFIRM_LIVE_TRADING must be "yes"');
  console.error('Set environment variable: CONFIRM_LIVE_TRADING=yes');
  process.exit(1);
}

// Get configuration from environment
const DRY_RUN = process.env.DRY_RUN === 'true';
const CYCLES = parseInt(process.env.INFERNO_CYCLES || '30', 10);
const CYCLE_MS = parseInt(process.env.INFERNO_CYCLE_MS || '3000', 10);
const TRADE_SIZE = parseFloat(process.env.INFERNO_TRADE_SIZE || '10');

console.log('\n');
console.log('🔥'.repeat(70));
console.log('🔥                    THE INFERNO — IGNITION                       🔥');
console.log('🔥'.repeat(70));
console.log('\n');

// Create Binance client
const client = new BinanceClient({
  apiKey: envConfig.binance.apiKey || '',
  apiSecret: envConfig.binance.apiSecret || '',
  testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false"),
});

// Create and ignite inferno
const inferno = createInferno({
  symbol: 'ETHUSDT',
  tradeSize: TRADE_SIZE,
  coherenceThreshold: 0.90,  // More aggressive
  consensusThreshold: 0.65,  // More permissive
  minConsensusVotes: 4,      // Only need 4/9
  cycleDelayMs: CYCLE_MS,
  maxCycles: CYCLES,
  dryRun: DRY_RUN,
}, client);

// BURN
inferno.ignite().catch(error => {
  console.error('❌ INFERNO ERROR:', error);
  process.exit(1);
});
