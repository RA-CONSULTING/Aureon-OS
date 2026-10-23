#!/usr/bin/env tsx
/**
 * AQTS CO-ARCHITECT — LIVE TRADING SCRIPT
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025 08:41 AM GMT
 * 
 * This is the dream in code.
 * 
 * Run modes:
 * - DRY RUN:  npm run coarch:dry
 * - LIVE:     npm run coarch:live (requires CONFIRM_LIVE_TRADING=yes)
 * 
 * Λ(t) = S(t) + O(t) + E(t)
 * 
 * S(t) — 9 Auris nodes in superposition
 * O(t) — Your conscious focus
 * E(t) — Causal echo from the past
 * 
 * "You are not dreaming. You are engineering reality."
 */

import { BinanceClient } from '../core/binanceClient';
import { CoArchitect, CoArchitectConfig } from '../core/coArchitect';
import * as dotenv from 'dotenv';

dotenv.config();

// ==============================
// CONFIGURATION
// ==============================

const DRY_RUN = process.env.DRY_RUN === 'true';
const CONFIRM_LIVE = process.env.CONFIRM_LIVE_TRADING === 'yes';

const config: CoArchitectConfig = {
  symbol: 'ETHUSDT',
  tradeAmountUSDT: parseFloat(process.env.COARCH_TRADE_AMOUNT || '10'),
  coherenceThreshold: parseFloat(process.env.COARCH_COHERENCE || '0.945'),
  consensusThreshold: parseFloat(process.env.COARCH_CONSENSUS || '0.7'),
  cycleDelayMs: parseInt(process.env.COARCH_CYCLE_MS || '5000', 10),
  maxCycles: parseInt(process.env.COARCH_CYCLES || '20', 10),
  dryRun: DRY_RUN,
};

// ==============================
// SAFETY CHECK
// ==============================

if (!DRY_RUN && !CONFIRM_LIVE) {
  console.error('❌ LIVE TRADING BLOCKED');
  console.error('Set CONFIRM_LIVE_TRADING=yes to enable live trading.');
  process.exit(1);
}

// ==============================
// INITIALIZE CLIENT
// ==============================

const apiKey = process.env.BINANCE_API_KEY;
const apiSecret = process.env.BINANCE_API_SECRET;
const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");

if (!apiKey || !apiSecret) {
  console.error('❌ Missing BINANCE_API_KEY or BINANCE_API_SECRET');
  process.exit(1);
}

const client = new BinanceClient({
  apiKey,
  apiSecret,
  testnet,
});

// ==============================
// RUN CO-ARCHITECT
// ==============================

(async () => {
  try {
    const coArchitect = new CoArchitect(config, client);
    await coArchitect.run();
  } catch (error: any) {
    console.error('\n❌ ERROR:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
})();
