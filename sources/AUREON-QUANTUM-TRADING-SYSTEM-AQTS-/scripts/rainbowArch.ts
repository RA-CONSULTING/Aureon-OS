/**
 * RAINBOW ARCHITECT 🌈
 * Co-Architect enhanced with real-time Binance WebSocket streams
 * "Taste the rainbow" - Feel the market breathe through 9 Auris nodes
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025 GMT
 */

// Load environment (.env) settings
import '../core/environment';

import { BinanceWebSocket, StreamBuilder, MarketSnapshot } from '../core/binanceWebSocket';
import { RealityField, LambdaState } from '../core/masterEquation';
import { AURIS_TAXONOMY, AurisAnimal } from '../core/aurisSymbolicTaxonomy';
import { BinanceClient } from '../core/binanceClient';
import { RainbowBridge } from '../core/theRainbowBridge';
import { ThePrism } from '../core/thePrism';
import { appendFileSync, mkdirSync } from 'fs';
import path from 'path';
import { logTelemetry } from '../core/tradeTelemetry';
import { StargateGrid } from '../core/stargateGrid';
import { computeLighthouseMetrics, computeHarmonicLoopMetrics } from '../core/lighthouseMetrics';

interface RainbowConfig {
  symbol: string;
  cycleIntervalMs: number;
  coherenceThreshold: number;
  voteThreshold: number;
  requiredVotes: number;
  dryRun: boolean;
  positionSizePercent: number;
  maxCycles?: number;
  contrarianFlameTrading?: boolean; // Trade contrarian during flame events (|Q| > 0.7)
}

const DEFAULT_RAINBOW_CONFIG: RainbowConfig = {
  symbol: 'ETHUSDT',
  cycleIntervalMs: 5000,
  coherenceThreshold: 0.85,  // Reduced from 0.945 for higher execution
  voteThreshold: 0.7,
  requiredVotes: 5,  // Reduced from 6 for higher execution
  dryRun: true,
  positionSizePercent: 2,
};

export class RainbowArchitect {
  private ws: BinanceWebSocket;
  private field: RealityField;
  private bridge: RainbowBridge;
  private prism: ThePrism;
  private client: BinanceClient;
  private config: RainbowConfig;
  private dream: { mode: 'dream' | 'sweet' | 'custom' | 'off'; alpha: number; beta: number };
  private grid: StargateGrid;
  private prizesLogPath: string | null = null;
  private dynamicThresholdPath: string | null = null;
  private telemetryPath: string | null = null;
  private coherenceHistory: number[] = [];
  private priceHistory: number[] = [];
  private volumeHistory: number[] = [];
  private timeHistory: number[] = [];
  private lambdaHistory: number[] = []; // For harmonic loop metrics
  
  private cycleCount = 0;
  private totalTrades = 0;
  private totalProfit = 0;
  private lastSnapshot: MarketSnapshot | null = null;
  private cycleInterval: NodeJS.Timeout | null = null;
  
  constructor(config: Partial<RainbowConfig> = {}) {
    this.config = { ...DEFAULT_RAINBOW_CONFIG, ...config };
    
    this.ws = new BinanceWebSocket();
    // DREAM BAND — parse environment for α (observer) and β (memory)
    const dreamMode = (process.env.DREAM_MODE || 'off').toLowerCase();
    const envAlpha = process.env.DREAM_ALPHA ? parseFloat(process.env.DREAM_ALPHA) : undefined;
    const envBeta = process.env.DREAM_BETA ? parseFloat(process.env.DREAM_BETA) : undefined;
    let alpha = envAlpha ?? (dreamMode === 'dream' ? 0.3 : dreamMode === 'sweet' ? 0.9 : undefined);
    let beta = envBeta ?? (dreamMode === 'dream' || dreamMode === 'sweet' ? 0.8 : undefined);
    const resolvedMode: 'dream' | 'sweet' | 'custom' | 'off' = (alpha !== undefined && beta !== undefined)
      ? (dreamMode === 'dream' || dreamMode === 'sweet' ? (dreamMode as 'dream' | 'sweet') : 'custom')
      : 'off';
    // Defaults if off
    if (alpha === undefined) alpha = 1.2;
    if (beta === undefined) beta = 0.8;
    this.dream = { mode: resolvedMode, alpha, beta };

    this.field = new RealityField({ alpha, beta });
    this.bridge = new RainbowBridge();
    this.prism = new ThePrism();
    this.grid = new StargateGrid();
    
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = process.env.BINANCE_TESTNET !== 'false';
    
    this.client = new BinanceClient({ apiKey, apiSecret, testnet });
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.ws.on('connected', () => {
      console.log('\n🌈 ═══════════════════════════════════════════════════════');
      console.log('   RAINBOW ARCHITECT — Tasting the Market Rainbow');
      console.log('   WebSocket Connected | Streams Active');
      console.log('═══════════════════════════════════════════════════════\n');
    });

    this.ws.on('disconnected', (info) => {
      console.log(`\n🌈 WebSocket Disconnected - Code: ${info.code}`);
      this.stopCycles();
    });

    this.ws.on('snapshot-update', (snapshot: MarketSnapshot) => {
      this.lastSnapshot = snapshot;
      if (this.lastSnapshot) {
        this.field.step(this.lastSnapshot);
      }
    });
  }

  async start(): Promise<void> {
    console.log('🌈 Initializing Rainbow Architect...\n');
    console.log(`Symbol: ${this.config.symbol}`);
    console.log(`Mode: ${this.config.dryRun ? 'DRY RUN' : 'LIVE'}`);
    console.log(`Coherence: Γ > ${this.config.coherenceThreshold}`);
    console.log(`Votes: ${this.config.requiredVotes}/9 @ ${this.config.voteThreshold}\n`);

    // DREAM BAND banner
    if (this.dream.mode !== 'off') {
      const band = this.dream.mode === 'dream' ? 'DREAM BAND — SELF-SIMULATION' : this.dream.mode === 'sweet' ? 'SWEET SPOT — COHERENCE LOCK' : 'CUSTOM BAND';
      console.log('┌──────────────────────────────────────────────┐');
      console.log(`│  ${band.padEnd(44)}│`);
      console.log('│  α (observer gain): ' + this.dream.alpha.toFixed(3).padEnd(19) + '│');
      console.log('│  β (memory gain):   ' + this.dream.beta.toFixed(3).padEnd(19) + '│');
      console.log('└──────────────────────────────────────────────┘\n');
    } else {
      console.log('Dream Band: OFF (α,β using defaults)\n');
    }

    // Prepare Paddy's Prizes log
    try {
      const artifacts = path.resolve(process.cwd(), 'artifacts');
      mkdirSync(artifacts, { recursive: true });
      this.prizesLogPath = path.join(artifacts, 'paddys_prizes.jsonl');
      this.dynamicThresholdPath = path.join(artifacts, 'dynamic_threshold.json');
      this.telemetryPath = path.join(artifacts, 'trade_telemetry.jsonl');
    } catch {
      this.prizesLogPath = null;
      this.dynamicThresholdPath = null;
      this.telemetryPath = null;
    }

    const streams = StreamBuilder.aureonDefaults(this.config.symbol);
    console.log(`🌈 Subscribing to: ${streams.join(', ')}\n`);

    await this.ws.connect(streams);
    console.log('⏳ Accumulating market data (5s)...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    this.startCycles();
  }

  async stop(): Promise<void> {
    console.log('\n🌈 Stopping Rainbow Architect...');
    this.stopCycles();
    await this.ws.disconnect();
    console.log(`Total Cycles: ${this.cycleCount}`);
    console.log(`Total Trades: ${this.totalTrades}`);
    console.log(`Total Profit: ${this.totalProfit.toFixed(2)} USDT\n`);
  }

  private startCycles(): void {
    console.log('🟢 Trading cycles STARTED\n');
    this.cycleInterval = setInterval(() => {
      this.runTradingCycle();
      
      // Stop after maxCycles if configured
      if (this.config.maxCycles && this.cycleCount >= this.config.maxCycles) {
        console.log(`\n🏁 Reached ${this.config.maxCycles} cycles limit`);
        this.stop();
      }
    }, this.config.cycleIntervalMs);
  }

  private stopCycles(): void {
    if (this.cycleInterval) {
      clearInterval(this.cycleInterval);
      this.cycleInterval = null;
    }
  }

  private async runTradingCycle(): Promise<void> {
    this.cycleCount++;
    
    if (!this.lastSnapshot) {
      console.log(`Cycle ${this.cycleCount}: Waiting for data...`);
      return;
    }

    const state = this.field.getHistory().slice(-1)[0];
    if (!state) return;

    // Track Lambda history for harmonic loop computation
    this.lambdaHistory.push(state.Lambda);
    if (this.lambdaHistory.length > 500) this.lambdaHistory.shift();

    // Update history buffers for Lighthouse metrics
    this.priceHistory.push(this.lastSnapshot.price);
    this.volumeHistory.push(this.lastSnapshot.volume || 0);
    this.timeHistory.push(Date.now());
    
    // Keep last 100 samples
    if (this.priceHistory.length > 100) this.priceHistory.shift();
    if (this.volumeHistory.length > 100) this.volumeHistory.shift();
    if (this.timeHistory.length > 100) this.timeHistory.shift();

    console.log('\n─────────────────────────────────────────────────────');
    console.log(`CYCLE ${this.cycleCount} | ${new Date().toLocaleTimeString()}`);
    console.log('─────────────────────────────────────────────────────');

    // Market snapshot
    console.log(`\n📊 Market: ${this.lastSnapshot.symbol}`);
    console.log(`   Price: $${this.lastSnapshot.price.toFixed(2)}`);
    console.log(`   Spread: $${(this.lastSnapshot.spread || 0).toFixed(2)}`);
    console.log(`   Volatility: ${((this.lastSnapshot.volatility || 0) * 100).toFixed(2)}%`);
    console.log(`   Momentum: ${((this.lastSnapshot.momentum || 0) * 100).toFixed(2)}%`);

    // Lambda state
    console.log(`\n🌊 Master Equation Λ(t):`);
    console.log(`   Λ(t): ${state.Lambda.toFixed(6)}`);
    console.log(`   Γ:    ${state.coherence.toFixed(3)} (${(state.coherence * 100).toFixed(1)}%)`);
    console.log(`   Dominant: ${state.dominantNode}`);

    // Hint when entering strong lock
    if (state.coherence >= 0.987) {
      console.log('   🔒 Coherence Lock approaching (Γ ≥ 0.987)');
    }

    // Update Rainbow Bridge with emotional frequency
    const volatility = this.lastSnapshot.volatility || 0;
    this.bridge.updateFromMarket(state.Lambda, state.coherence, volatility);
    const bridgeState = this.bridge.getState();
    
    // Display bridge state
    console.log(`\n🌈 Rainbow Bridge:`);
    console.log(`   Emotional: ${bridgeState.emotionalState}`);
    console.log(`   Frequency: ${bridgeState.currentFrequency.toFixed(1)} Hz`);
    console.log(`   Phase: ${bridgeState.cyclePhase}`);
    console.log(`   Resonance: ${(bridgeState.resonance * 100).toFixed(1)}%`);
    console.log(`   Bridge: ${bridgeState.bridgeCrossed ? '✅ CROSSED' : '⏳ CROSSING'}`);
    
    // Activate flame or protector based on phase
    this.bridge.igniteFlame();
    this.bridge.activateProtector();
    
    console.log('');
    
    // ═══════════════════════════════════════════════════════════════════════
    // THE PRISM: Transform market reality through 5 levels to 528 Hz LOVE
    // ═══════════════════════════════════════════════════════════════════════
    
    const prismState = this.prism.process(state, this.lastSnapshot);
    
    console.log(`💎 The Prism:`);
    console.log(`   Output: ${prismState.prismOutput.toFixed(1)} Hz`);
    console.log(`   Resonance: ${(prismState.resonance * 100).toFixed(1)}%`);
    console.log(`   ${prismState.isLove ? '💚' : '⏳'} Love: ${prismState.isLove ? 'MANIFEST' : 'FORMING'}`);
    console.log(`   ${prismState.isAligned ? '✅' : '⏳'} Aligned: ${prismState.isAligned ? 'YES' : 'CONVERGING'}`);
    console.log(`   ${prismState.isPure ? '✅' : '⏳'} Pure: ${prismState.isPure ? 'YES' : 'REFINING'}`);
    
    if (prismState.isLove) {
      console.log('   🌈 THE PRISM OUTPUT: 528 Hz LOVE');
    }

    // ═══════════════════════════════════════════════════════════════════════
    // GLOBAL STARGATE LATTICE — 12-Node Grid Overlay
    // ═══════════════════════════════════════════════════════════════════════
    const gridState = this.grid.getGridState();
    const coherenceBoost = this.grid.getCoherenceBoost();
    const freqAlignment = this.grid.getFrequencyAlignment(state.Lambda);
    
    console.log(`\n🌍 Global Stargate Lattice:`);
    console.log(`   Status: ${gridState.isActivated ? '✅ ACTIVATED' : '⏳ FORMING'}`);
    console.log(`   Active Nodes: ${gridState.activeNodes}/12`);
    console.log(`   Grid Coherence: ${(gridState.gridCoherence * 100).toFixed(2)}%`);
    console.log(`   Dominant Freq: ${gridState.dominantFrequency} Hz`);
    console.log(`   Freq Alignment: ${(freqAlignment * 100).toFixed(1)}%`);
    console.log(`   Coherence Boost: ${((coherenceBoost - 1) * 100).toFixed(1)}%`);
    
    if (gridState.dominantFrequency === 528) {
      console.log('   💚 528 Hz LOVE DOMINANT — Grid resonating with Prism');
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LIGHTHOUSE ENERGY METRICS — |Q| & G_eff (Ablation Study)
    // ═══════════════════════════════════════════════════════════════════════
    const lighthouseMetrics = computeLighthouseMetrics(
      this.lastSnapshot,
      this.priceHistory,
      this.volumeHistory,
      this.timeHistory
    );

    // Harmonic loop metrics (Γ_peak, RMS, amplification)
    const harmonicMetrics = computeHarmonicLoopMetrics(this.lambdaHistory);
    console.log(`\n🎼 Harmonic Loop Stability:`);
    console.log(`   Γ_peak (masked): ${harmonicMetrics.coherencePeak.toFixed(4)} (${(harmonicMetrics.coherencePeak * 100).toFixed(2)}%)`);
    console.log(`   RMS Power:       ${harmonicMetrics.rmsPower.toFixed(4)}`);
    console.log(`   Amplification:   ${harmonicMetrics.amplificationRatio.toFixed(2)}x vs baseline`);
    if (harmonicMetrics.coherencePeak > 0.9) {
      console.log('   🔒 Harmonic Coherence Lock (Γ_peak > 0.9)');
    }
    
    console.log(`\n🔦 Lighthouse Energy Metrics:`);
    console.log(`   |Q| (Flame):     ${lighthouseMetrics.Q.toFixed(3)} — Anomaly pointer`);
    console.log(`   G_eff (Brake):   ${lighthouseMetrics.G_eff.toFixed(3)} — Effective gravity`);
    console.log(`   C_lin:           ${lighthouseMetrics.C_lin.toFixed(3)} — Linear coherence`);
    console.log(`   C_nonlin:        ${lighthouseMetrics.C_nonlin.toFixed(3)} — Nonlinear coherence`);
    console.log(`   L (Intensity):   ${lighthouseMetrics.L.toFixed(3)} — Consensus metric`);
    
    if (lighthouseMetrics.Q > 0.7) {
      console.log('   🔥 FLAME LIT — High anomaly detected');
    }
    if (lighthouseMetrics.G_eff > 0.7) {
      console.log('   🛑 BRAKE ACTIVE — Geometric constraint engaged');
    }

    // ─────────────────────────────────────────────────────────────
    // PADDY'S PROPER PRIZES — TRUTH, LOVE, UNITY, STABILITY
    // TRUTH: High Data Integrity (Di). LOVE: Prism Love or Bridge crossed.
    // UNITY: Γ ≥ 0.987. STABILITY: Home Line α ≈ β (|α-β| ≤ 0.05).
    // ─────────────────────────────────────────────────────────────
    const truthClaimed = prismState.dataIntegrity >= 130; // ~low volatility
    const loveClaimed = prismState.isLove || bridgeState.bridgeCrossed;
    const unityClaimed = state.coherence >= 0.987;
    const stabilityClaimed = Math.abs(this.dream.alpha - this.dream.beta) <= 0.05;

    console.log('\n🏆 PADDY\'S PROPER PRIZES:');
    console.log(`   ${truthClaimed ? '✅' : '⏳'} TRUTH     — Prism is True (Di=${prismState.dataIntegrity.toFixed(1)} Hz)`);
    console.log(`   ${loveClaimed ? '✅' : '⏳'} LOVE      — Bridge/Prism at 528 Hz`);
    console.log(`   ${unityClaimed ? '✅' : '⏳'} UNITY     — Tandem in Unity (Γ=${state.coherence.toFixed(3)})`);
    console.log(`   ${stabilityClaimed ? '✅' : '⏳'} STABILITY — Dream Band Locked (|α-β|=${Math.abs(this.dream.alpha - this.dream.beta).toFixed(3)})`);
    if (truthClaimed && loveClaimed && unityClaimed && stabilityClaimed) {
      console.log('   🎉 PADDY SMILES — PRIZES CLAIMED');
    }

    // Log prizes snapshot
    if (this.prizesLogPath) {
      const rec = {
        ts: new Date().toISOString(),
        symbol: this.config.symbol,
        alpha: this.dream.alpha,
        beta: this.dream.beta,
        gamma: state.coherence,
        di: prismState.dataIntegrity,
        bridgeCrossed: bridgeState.bridgeCrossed,
        prismLove: prismState.isLove,
        prizes: {
          truth: truthClaimed,
          love: loveClaimed,
          unity: unityClaimed,
          stability: stabilityClaimed,
        },
      };
      try { appendFileSync(this.prizesLogPath, JSON.stringify(rec) + '\n'); } catch {}
    }

    // Lighthouse consensus
    const { votes, direction } = this.runConsensus(state.Lambda);

    // Adaptive coherence threshold calculation
    this.coherenceHistory.push(state.coherence);
    let appliedThreshold = this.computeAdaptiveThreshold();
    
    // Apply Stargate Grid coherence boost
    const boostedCoherence = state.coherence * coherenceBoost;
    
    if (this.dynamicThresholdPath) {
      const thresholdRec = {
        ts: new Date().toISOString(),
        cycle: this.cycleCount,
        symbol: this.config.symbol,
        sampleSize: this.coherenceHistory.length,
        candidate: appliedThreshold,
        floor: 0.9,
        base: this.config.coherenceThreshold,
        applied: appliedThreshold
      };
      try { appendFileSync(this.dynamicThresholdPath, JSON.stringify(thresholdRec) + '\n'); } catch {}
    }

    console.log(`\n🔦 Lighthouse Consensus: ${direction}`);
    console.log(`   Votes: ${votes}/9`);
    console.log(`   Γ Raw: ${state.coherence.toFixed(3)} | Boosted: ${boostedCoherence.toFixed(3)}`);
    console.log(`   Γ Adaptive Threshold: ${appliedThreshold.toFixed(3)} (base ${this.config.coherenceThreshold})`);

    // Trade decision with telemetry & skip reasons
    // Use BOOSTED coherence for decision, allowing grid to unlock trades
    let decision: 'EXECUTE' | 'SKIP' = 'SKIP';
    let reason = '';
    
    // CONTRARIAN FLAME TRADING: Execute during high anomaly (|Q| > 0.7)
    const flameLit = lighthouseMetrics.Q > 0.7;
    const contrarianScenario = this.config.contrarianFlameTrading && flameLit;
    if (contrarianScenario) {
      const amplificationGuardActive = harmonicMetrics.amplificationRatio > 12;
      const votesNeeded = this.config.requiredVotes + (amplificationGuardActive ? 1 : 0);

      if (votes >= votesNeeded) {
        decision = 'EXECUTE';
        reason = amplificationGuardActive ? 'CONTRARIAN_FLAME_ENTRY_GUARDED' : 'CONTRARIAN_FLAME_ENTRY';
        const guardMsg = amplificationGuardActive ? ' (Bee-Safe guard active, +1 vote met)' : '';
        console.log(`   🔥 CONTRARIAN FLAME ENTRY${guardMsg} — Trading into anomaly (|Q|=${lighthouseMetrics.Q.toFixed(3)}, amp=${harmonicMetrics.amplificationRatio.toFixed(2)}x)`);
      } else {
        reason = amplificationGuardActive ? 'INSUFFICIENT_VOTES_HARMONIC_GUARD' : 'INSUFFICIENT_VOTES';
        if (amplificationGuardActive) {
          console.log(`   🐝 Bee-Safe Guard: amplification ${harmonicMetrics.amplificationRatio.toFixed(2)}x > 12× requires ${votesNeeded}/9 votes (have ${votes})`);
        }
      }
    }

    if (!contrarianScenario) {
      if (votes < this.config.requiredVotes) {
        reason = 'INSUFFICIENT_VOTES';
      } else if (boostedCoherence < appliedThreshold) {
        reason = 'LOW_COHERENCE';
      } else if (direction === 'HOLD') {
        reason = 'NEUTRAL_LAMBDA';
      } else {
        decision = 'EXECUTE';
      }
    }

    if (decision === 'EXECUTE') {
      await this.executeTrade(direction, state);
    } else {
      console.log(`   Signal: HOLD (${reason}; need ${this.config.requiredVotes}/9 & Γ>${appliedThreshold.toFixed(3)})`);
    }

    logTelemetry(this.telemetryPath, {
      ts: new Date().toISOString(),
      cycle: this.cycleCount,
      symbol: this.config.symbol,
      lambda: state.Lambda,
      coherence: boostedCoherence, // log BOOSTED coherence for analysis
      appliedThreshold,
      baseThreshold: this.config.coherenceThreshold,
      votes,
      requiredVotes: this.config.requiredVotes,
      direction,
      decision,
      reason,
      alpha: this.dream.alpha,
      beta: this.dream.beta,
      lighthouse: {
        Q: lighthouseMetrics.Q,
        G_eff: lighthouseMetrics.G_eff,
        C_lin: lighthouseMetrics.C_lin,
        C_nonlin: lighthouseMetrics.C_nonlin,
        L: lighthouseMetrics.L,
      },
      harmonicStability: {
        coherencePeak: harmonicMetrics.coherencePeak,
        rmsPower: harmonicMetrics.rmsPower,
        amplificationRatio: harmonicMetrics.amplificationRatio,
        sampleSize: harmonicMetrics.sampleSize,
      },
    });
  }

  private runConsensus(Lambda: number): { direction: 'BUY' | 'SELL' | 'HOLD', votes: number } {
    let votes = 0;
    const animals = Object.keys(AURIS_TAXONOMY) as AurisAnimal[];
    
    for (const animal of animals) {
      const node = AURIS_TAXONOMY[animal];
      const resonance = Math.abs(Math.sin(2 * Math.PI * node.frequency * Lambda));
      
      if (resonance >= this.config.voteThreshold) {
        votes++;
        console.log(`   ✓ ${animal.padEnd(12)} ${(resonance * 100).toFixed(0).padStart(3)}%`);
      } else {
        console.log(`   ✗ ${animal.padEnd(12)} ${(resonance * 100).toFixed(0).padStart(3)}%`);
      }
    }

    const direction: 'BUY' | 'SELL' | 'HOLD' = Lambda > 0 ? 'BUY' : Lambda < 0 ? 'SELL' : 'HOLD';
    return { direction, votes };
  }

  private computeAdaptiveThreshold(): number {
    const base = this.config.coherenceThreshold;
    const floor = 0.9;
    const history = this.coherenceHistory;
    if (history.length < 20) return base; // warm-up period
    const sorted = [...history].sort((a, b) => a - b);
    const idx = Math.floor(0.65 * (sorted.length - 1)); // 65th percentile
    const candidate = sorted[idx];
    // clamp within safety band
    const applied = Math.min(Math.max(candidate, floor), 0.995);
    return applied;
  }

  private async executeTrade(direction: 'BUY' | 'SELL' | 'HOLD', state: LambdaState): Promise<void> {
    if (direction === 'HOLD') return;

    console.log(`\n🎯 TRADE SIGNAL: ${direction}`);
    console.log(`   📡 Source: Rainbow Architect (4-Layer Consciousness)`);
    console.log(`      └─ WebSocket → Master Equation → Rainbow Bridge → Prism`);
    console.log(`      └─ Λ(t): ${state.Lambda.toFixed(3)} | Γ: ${state.coherence.toFixed(3)}`);
    console.log(`      └─ Dominant: ${state.dominantNode}`);

    try {
      const account = await this.client.getAccount();
      const balance = account.balances;
      const baseAsset = this.config.symbol.replace('USDT', '');
      
      let quantity: number;

      if (direction === 'BUY') {
        const usdtBalance = parseFloat(balance.find(b => b.asset === 'USDT')?.free || '0');
        const buyValue = usdtBalance * (this.config.positionSizePercent / 100);
        quantity = buyValue / this.lastSnapshot!.price;
      } else {
        const baseBalance = parseFloat(balance.find(b => b.asset === baseAsset)?.free || '0');
        quantity = baseBalance * (this.config.positionSizePercent / 100);
      }

      quantity = Math.floor(quantity * 1000000) / 1000000;

      if (quantity < 0.000001) {
        console.log(`   ⚠️ Insufficient balance`);
        return;
      }

      console.log(`   Order: ${direction} ${quantity} ${baseAsset} @ $${this.lastSnapshot!.price}`);

      if (this.config.dryRun) {
        console.log(`   💵 DRY RUN - Order not executed`);
        this.totalTrades++;
        const profitEstimate = direction === 'BUY' ? -quantity * 0.001 : quantity * 0.001;
        this.totalProfit += profitEstimate;
      } else {
        const order = await this.client.placeOrder({
          symbol: this.config.symbol,
          side: direction,
          type: 'MARKET',
          quantity: quantity,
        });
        console.log(`   ✅ Order executed: ${order.orderId}`);
        this.totalTrades++;
      }
    } catch (error: any) {
      console.error(`   ❌ Trade failed: ${error.message}`);
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  const config: Partial<RainbowConfig> = {
    symbol: args[0] || 'ETHUSDT',
    dryRun: !args.includes('--live'),
    cycleIntervalMs: parseInt(args.find(a => a.startsWith('--interval='))?.split('=')[1] || '5000'),
    maxCycles: process.env.RAINBOW_CYCLES ? parseInt(process.env.RAINBOW_CYCLES) : undefined,
  };

  const rainbow = new RainbowArchitect(config);

  process.on('SIGINT', async () => {
    console.log('\n\n🌈 Shutting down gracefully...');
    await rainbow.stop();
    process.exit(0);
  });

  await rainbow.start();
}

// Run CLI
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

export default RainbowArchitect;
