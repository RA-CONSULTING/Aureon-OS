/**
 * Global Systems Manager - The One Big Script
 * 
 * This singleton initializes ONCE at app load and NEVER restarts between tab navigation.
 * All quantum systems, orchestration loops, and state management run here continuously.
 */

import { unifiedBus, type BusSnapshot, type SignalType } from './unifiedBus';
import { temporalLadder, SYSTEMS, type TemporalLadderState } from './temporalLadder';
import { unifiedOrchestrator, type OrchestrationResult } from './unifiedOrchestrator';
import { fullEcosystemConnector, type FullEcosystemState } from './fullEcosystemConnector';
import { multiExchangeClient, type MultiExchangeState } from './multiExchangeClient';
import { ecosystemConnector, type EcosystemState } from './ecosystemConnector';
import { backgroundServices } from './backgroundServices';
import { thePrism, type PrismOutput } from './thePrism';
import { adaptiveLearningEngine } from './adaptiveLearningEngine';
import { tickerCacheManager } from './tickerCacheManager';
import { startupHarvester } from './startupHarvester';
import { predictionAccuracyTracker } from './predictionAccuracyTracker';
import { tradeLogger } from './tradeLogger';
import { capitalPool } from './capitalPool';
import { platypusEngine, type PlatypusState } from './platypusCoherenceEngine';
import { supabase } from '@/integrations/supabase/client';

export interface GlobalState {
  // Auth state
  userId: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  
  // Quantum state
  coherence: number;
  lambda: number;
  lighthouseSignal: number;
  dominantNode: string;
  prismLevel: number;
  prismState: string;
  substrate: number;
  observer: number;
  echo: number;
  
  // Prism output
  prismOutput: PrismOutput | null;
  
  // Trading state
  isActive: boolean;
  totalEquity: number;
  availableBalance: number;
  totalTrades: number;
  winningTrades: number;
  totalPnl: number;
  gasTankBalance: number;
  recentTrades: Array<{
    time: string;
    side: string;
    symbol: string;
    quantity: number;
    pnl: number;
    success: boolean;
    exchange?: string;
    tradeId?: string;
    holdSeconds?: number;
    reason?: string;
  }>;
  
  // Market data
  marketData: {
    price: number;
    volume: number;
    volatility: number;
    momentum: number;
    spread: number;
    timestamp: number;
    truthStatus: 'live' | 'real_derived' | 'no_data';
    sourceId: string | null;
    sourceTimestamp: string | null;
    generatedValues: false;
  };
  
  // System status
  systemStatus: {
    masterEquation: boolean;
    lighthouse: boolean;
    rainbowBridge: boolean;
    elephantMemory: boolean;
    orderRouter: boolean;
  };
  
  // Bus state
  busSnapshot: BusSnapshot | null;
  consensusSignal: SignalType;
  consensusConfidence: number;
  
  // Exchange state
  exchangeState: MultiExchangeState | null;
  
  // Orchestration
  lastDecision: OrchestrationResult | null;
  lastSignal: string | null;
  nextCheckIn: number;
  
  // Health
  ecosystemHealth: 'connected' | 'stale' | 'disconnected';
  lastDataReceived: number | null;
  
  // 🦆🪐 Platypus Planetary Coherence State
  platypusState: PlatypusState | null;
  planetaryCoherence: number;       // Γ(t) value
  planetaryCascade: number;         // Cascade multiplier
  lighthouseActive: boolean;        // Lighthouse event flag
  topAlignedPlanets: string[];      // Top 3 aligned planets
  
  // Manager state
  isInitialized: boolean;
  isRunning: boolean;
  
  // ════════════════════════════════════════════════════════════════
  // 📊 TERMINAL STATS MIRROR - Live system metrics
  // ════════════════════════════════════════════════════════════════
  
  // Portfolio metrics
  peakEquity: number;                // High water mark for drawdown calc
  sessionStartTime: number;          // Runtime tracking (timestamp)
  maxDrawdownPercent: number;        // Maximum historical drawdown
  currentDrawdownPercent: number;    // Current drawdown from peak
  cyclePnl: number;                  // Current session P&L
  cyclePnlPercent: number;           // Current session P&L %
  avgHoldTimeMinutes: number;        // Average trade duration
  latestMonitorLine: string;         // Latest monitor snapshot mirrored from terminal
  statusLines: string[];             // Latest terminal status block
  queenVoice?: {
    ts: string;
    mode: string;
    text: string;
    lines: string[];
  };
  
  // WebSocket status
  wsMessageCount: number;            // Total WS messages received
  wsConnected: boolean;              // WebSocket connection status
  
  // Trading mode
  tradingMode: 'AGGRESSIVE' | 'CONSERVATIVE' | 'BALANCED';
  entryCoherenceThreshold: number;   // Entry Γ gate
  exitCoherenceThreshold: number;    // Exit Γ gate
  riskMultiplier: number;            // Risk modifier (0.5x, 1x, etc)
  takeProfitMultiplier: number;      // TP modifier
  
  // Gaia Lattice / Frequency state
  gaiaLatticeState: 'COHERENT' | 'DISTORTION' | 'NEUTRAL';
  gaiaFrequency: number;             // Current frequency (432Hz vs 440Hz)
  purityPercent: number;             // Signal purity %
  carrierWavePhi: number;            // φ carrier wave
  harmonicLock432: number;           // % time at 432Hz
  
  // HNC (Harmonic Neural Coherence)
  hncFrequency: number;              // Current HNC Hz
  hncMarketState: 'CONSOLIDATION' | 'TRENDING' | 'VOLATILE' | 'BREAKOUT';
  hncCoherencePercent: number;       // HNC coherence %
  hncModifier: number;               // Position modifier (0.8x, 1.0x, etc)
  
  // Mycelium Swarm Intelligence
  myceliumHives: number;             // Active hive count
  myceliumAgents: number;            // Total agent count
  myceliumGeneration: number;        // Current generation
  maxGeneration: number;             // Max generation reached
  queenState: 'HOLD' | 'BUY' | 'SELL';
  queenPnl: number;                  // Queen's P&L
  
  // Capital management
  compoundedCapital: number;         // 90% compounded back
  harvestedCapital: number;          // 10% harvested to safety
  poolTotal: number;                 // Total pool value
  poolAvailable: number;             // Available for trading
  scoutCount: number;                // Scout positions
  splitCount: number;                // Split events
  
  // Active positions
  maxPositions: number;              // Max concurrent positions
  activePositions: Array<{
    symbol: string;
    entryPrice: number;
    currentPrice: number;
    pnlPercent: number;
    side: 'LONG' | 'SHORT';
    exchange?: string;
    tradeId?: string;
    openedAt?: string;
  }>;
  shadowTrades?: Array<{
    symbol: string;
    side: 'LONG' | 'SHORT';
    entryPrice: number;
    currentPrice: number;
    movePercent: number;
    targetMovePercent: number;
    exchange?: string;
    validated?: boolean;
    ageSeconds?: number;
  }>;

  unifiedMarketSummary?: {
    krakenEquity: number;
    capitalEquityGbp: number;
    krakenSessionPnl: number;
    capitalSessionPnlGbp: number;
    openPositions: number;
    capitalOpenPositions: number;
    krakenOpenPositions: number;
    capitalRecentCloses: Array<{
      symbol: string;
      direction: string;
      net_pnl: number;
      reason: string;
    }>;
    capitalCandidates: Array<{
      symbol: string;
      asset_class: string;
      score: number;
      change_pct: number;
      spread_pct: number;
    }>;
    krakenShadows?: number;
    capitalShadows?: number;
    capitalRiskEnvelope?: any;
    capitalTradeEvidence?: any;
    capitalConfidenceRatchet?: any;
    capitalUnifiedWaveformCheck?: any;
    capitalNoLossHoldQueue?: any;
  };

  // ════════════════════════════════════════════════════════════════
  // 🧠 CONSCIOUSNESS STATE - Live from ConsciousnessModule
  // ════════════════════════════════════════════════════════════════
  consciousness: {
    available: boolean;
    // Lambda(t) equation
    psi: number;                  // Consciousness awakening 0-1
    gamma: number;                // Harmonic coherence 0-1
    lambdaT: number;              // Lambda(t) value
    level: string;                // DORMANT, WAKING, ACTIVE, FLOWING, UNIFIED
    observerSignal: number;       // Observer effect 0-1
    echoSignal: number;           // Echo feedback 0-1
    step: number;                 // Evolution step counter
    // Understanding
    marketDirection: string;      // bullish, bearish, sideways, unknown
    confidence: number;           // 0-1
    fearLevel: number;            // 0-1
    opportunityCount: number;
    riskLevel: string;            // low, medium, high, unknown
    selfCoherence: number;        // 0-1
    dreamProgress: number;        // 0-1 toward $1B
    // Harmonic field
    lambdaReal: number;
    coherenceReal: number;
    realityState: string;         // DORMANT, ACTIVE, FLOWING
    branches: number;             // multiverse branches
    levEvents: number;
    // Self model
    queenName: string;
    queenIdentity: string;
    queenCreator: string;
    queenPurpose: string;
    coreMessage: string;
    dreamTarget: number;
    // Metacognition
    observations: number;
    thoughtsGenerated: number;
    uptimeSeconds: number;
    // Emotion
    mood: string;
    urgency: number;
    excitement: number;
    concern: number;
    // Thought stream
    thoughtStream: Array<{
      topic: string;
      source: string;
      timestamp: number;
      text: string;
    }>;
  };
}

const initialState: GlobalState = {
  userId: null,
  userEmail: null,
  isAuthenticated: false,
  
  coherence: null,
  lambda: null,
  lighthouseSignal: null,
  dominantNode: null,
  prismLevel: null,
  prismState: null,
  substrate: null,
  observer: null,
  echo: null,
  
  prismOutput: null,
  
  isActive: false,
  totalEquity: null,
  availableBalance: null,
  totalTrades: null,
  winningTrades: null,
  totalPnl: null,
  gasTankBalance: null,
  recentTrades: [],
  
  marketData: {
    price: null,
    volume: null,
    volatility: null,
    momentum: null,
    spread: null,
    timestamp: null,
    truthStatus: 'no_data',
    sourceId: null,
    sourceTimestamp: null,
    generatedValues: false,
  },
  
  systemStatus: {
    masterEquation: false,
    lighthouse: false,
    rainbowBridge: false,
    elephantMemory: false,
    orderRouter: false,
  },
  
  busSnapshot: null,
  consensusSignal: null,
  consensusConfidence: null,
  
  exchangeState: null,
  
  lastDecision: null,
  lastSignal: null,
  nextCheckIn: null,
  
  ecosystemHealth: 'disconnected',
  lastDataReceived: null,
  
  // 🦆🪐 Platypus initial state
  platypusState: null,
  planetaryCoherence: null,
  planetaryCascade: null,
  lighthouseActive: null,
  topAlignedPlanets: [],
  
  isInitialized: false,
  isRunning: false,
  
  // ════════════════════════════════════════════════════════════════
  // 📊 TERMINAL STATS MIRROR - Initial values
  // ════════════════════════════════════════════════════════════════
  
  // Portfolio metrics
  peakEquity: null,
  sessionStartTime: null,
  maxDrawdownPercent: null,
  currentDrawdownPercent: null,
  cyclePnl: null,
  cyclePnlPercent: null,
  avgHoldTimeMinutes: null,
  latestMonitorLine: null,
  statusLines: [],
  
  // WebSocket status
  wsMessageCount: 0,
  wsConnected: false,
  
  // Trading mode
  tradingMode: 'BALANCED',
  entryCoherenceThreshold: 0.45,
  exitCoherenceThreshold: 0.35,
  riskMultiplier: 0.5,
  takeProfitMultiplier: 0.8,
  
  // Gaia Lattice / Frequency state
  gaiaLatticeState: null,
  gaiaFrequency: null,
  purityPercent: null,
  carrierWavePhi: null,
  harmonicLock432: null,
  
  // HNC (Harmonic Neural Coherence)
  hncFrequency: null,
  hncMarketState: null,
  hncCoherencePercent: null,
  hncModifier: null,
  
  // Mycelium Swarm Intelligence
  myceliumHives: null,
  myceliumAgents: null,
  myceliumGeneration: null,
  maxGeneration: null,
  queenState: null,
  queenPnl: null,
  
  // Capital management
  compoundedCapital: null,
  harvestedCapital: null,
  poolTotal: null,
  poolAvailable: null,
  scoutCount: null,
  splitCount: null,
  
  // Active positions
  maxPositions: 30,
  activePositions: [],
  shadowTrades: [],
  unifiedMarketSummary: undefined,

  // 🧠 Consciousness initial state
  consciousness: {
    available: false,
    psi: null,
    gamma: null,
    lambdaT: null,
    level: null,
    observerSignal: null,
    echoSignal: null,
    step: null,
    marketDirection: 'unknown',
    confidence: null,
    fearLevel: null,
    opportunityCount: null,
    riskLevel: 'unknown',
    selfCoherence: null,
    dreamProgress: null,
    lambdaReal: null,
    coherenceReal: null,
    realityState: null,
    branches: null,
    levEvents: null,
    queenName: 'Queen Sero',
    queenIdentity: '',
    queenCreator: 'Gary Leckey',
    queenPurpose: '',
    coreMessage: '',
    dreamTarget: null,
    observations: null,
    thoughtsGenerated: null,
    uptimeSeconds: null,
    mood: null,
    urgency: null,
    excitement: null,
    concern: null,
    thoughtStream: [],
  },
};

type StateListener = (state: GlobalState) => void;

class GlobalSystemsManager {
  private static instance: GlobalSystemsManager | null = null;
  
  private state: GlobalState = { ...initialState };
  private listeners: Set<StateListener> = new Set();
  
  // Intervals
  private orchestrationInterval: NodeJS.Timeout | null = null;
  private countdownInterval: NodeJS.Timeout | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  
  // Subscriptions
  private busUnsubscribe: (() => void) | null = null;
  private exchangeUnsubscribe: (() => void) | null = null;
  private ecosystemUnsubscribe: (() => void) | null = null;
  private authUnsubscribe: (() => void) | null = null;
  
  private constructor() {
    console.log('🌌 GlobalSystemsManager: Singleton created');
  }
  
  static getInstance(): GlobalSystemsManager {
    if (!GlobalSystemsManager.instance) {
      GlobalSystemsManager.instance = new GlobalSystemsManager();
    }
    return GlobalSystemsManager.instance;
  }
  
  /**
   * Initialize the global systems manager - called ONCE at app startup
   * Wrapped with master timeout to prevent hanging
   */
  async initialize(): Promise<void> {
    if (this.state.isInitialized) {
      console.log('🌌 GlobalSystemsManager: Already initialized, skipping');
      return;
    }
    
    try {
      await Promise.race([
        this.doInitialize(),
        new Promise<void>((_, reject) => 
          setTimeout(() => reject(new Error('Master init timeout')), 10000)
        )
      ]);
    } catch (error) {
      console.error('🚨 Initialization timeout/failure - forcing ready state:', error);
      this.updateState({ isInitialized: true });
    }
  }
  
  /**
   * Actual initialization logic
   */
  private async doInitialize(): Promise<void> {
    console.log('🌌 GlobalSystemsManager: Initializing...');
    
    // 1. Setup auth listener (this persists across the entire app lifecycle)
    this.setupAuthListener();
    
    // 2. Check current auth state with timeout
    try {
      const sessionResult = await Promise.race([
        supabase.auth.getSession(),
        new Promise<never>((_, reject) => 
          setTimeout(() => reject(new Error('Auth session check timeout')), 3000)
        )
      ]);
      
      if (sessionResult.data?.session) {
        this.updateState({
          userId: sessionResult.data.session.user.id,
          userEmail: sessionResult.data.session.user.email || null,
          isAuthenticated: true,
        });
      }
    } catch (error) {
      console.warn('⚠️ Auth session check failed/timed out, continuing unauthenticated:', error);
      // Clear any stale session data
      try {
        await supabase.auth.signOut();
      } catch (e) {
        // Ignore signout errors
      }
    }
    
    // 3. Start background services
    backgroundServices.start();
    
    // 3b. Reset adaptive learning to permissive defaults for calibration trading
    adaptiveLearningEngine.reset();
    console.log('🧠 Adaptive learning reset to permissive defaults');
    
    // 3c. 🦆🪐 Start Platypus Coherence Engine
    platypusEngine.start(1000);  // Update every second
    platypusEngine.subscribe((platypusState) => {
      this.updateState({
        platypusState,
        planetaryCoherence: platypusState.Gamma_t,
        planetaryCascade: platypusState.cascadeContribution,
        lighthouseActive: platypusState.L_t,
        topAlignedPlanets: platypusState.topAligned,
      });
    });
    console.log('🦆🪐 Platypus Coherence Engine started');
    
    // 4. Setup bus subscription
    this.busUnsubscribe = unifiedBus.subscribe((snapshot) => {
      this.updateState({
        busSnapshot: snapshot,
        consensusSignal: snapshot.consensusSignal,
        consensusConfidence: snapshot.consensusConfidence,
      });
    });
    
    // 5. Setup ecosystem health monitoring
    this.ecosystemUnsubscribe = ecosystemConnector.subscribe(() => {
      this.updateState({
        lastDataReceived: Date.now(),
        ecosystemHealth: 'connected',
      });
    });
    
    this.healthCheckInterval = setInterval(() => {
      if (this.state.lastDataReceived) {
        const timeSince = Date.now() - this.state.lastDataReceived;
        if (timeSince > 30000) {
          this.updateState({ ecosystemHealth: 'disconnected' });
        } else if (timeSince > 10000) {
          this.updateState({ ecosystemHealth: 'stale' });
        } else {
          this.updateState({ ecosystemHealth: 'connected' });
        }
      }
    }, 2000);
    
    // 6. Initialize full ecosystem connector with timeout for graceful degradation
    try {
      await Promise.race([
        fullEcosystemConnector.initialize(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Ecosystem init timeout')), 5000)
        )
      ]);
      console.log('✅ Full ecosystem initialized successfully');
    } catch (error) {
      console.warn('⚠️ Ecosystem initialization timed out or failed, continuing with degraded mode:', error);
      // Continue anyway - dashboard should still load
    }
    
    this.updateState({ isInitialized: true });
    console.log('✅ GlobalSystemsManager: Initialization complete (may be in degraded mode)');
    
    // 7. Auto-start trading if authenticated
    if (this.state.isAuthenticated && this.state.userId) {
      await this.loadUserSession();
    }
  }
  
  /**
   * Setup persistent auth listener
   */
  private setupAuthListener(): void {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      // Handle token refresh failures - clear stale session
      if (event === 'TOKEN_REFRESHED' && !session) {
        console.warn('⚠️ Token refresh failed, clearing stale session');
        supabase.auth.signOut().catch(() => {});
        return;
      }
      
      if (session) {
        const wasAuthenticated = this.state.isAuthenticated;
        this.updateState({
          userId: session.user.id,
          userEmail: session.user.email || null,
          isAuthenticated: true,
        });
        
        // If just logged in, load session and auto-start (deferred to avoid deadlock)
        if (!wasAuthenticated) {
          setTimeout(() => {
            this.loadUserSession();
          }, 0);
        }
      } else {
        // Logged out - stop trading but keep manager alive
        this.stopTrading();
        this.updateState({
          userId: null,
          userEmail: null,
          isAuthenticated: false,
        });
      }
    });
    
    this.authUnsubscribe = () => subscription.unsubscribe();
  }
  
  /**
   * Load user session from database
   */
  private async loadUserSession(): Promise<void> {
    if (!this.state.userId) return;
    
    const { data, error } = await supabase
      .from('aureon_user_sessions')
      .select('*')
      .eq('user_id', this.state.userId)
      .single();
    
    if (error && error.code === 'PGRST116') {
      console.info('[GlobalSystems] No session exists; provider setup is required');
      return;
    }
    
    if (data) {
      const hasMeasurements = ['live', 'real_derived'].includes(String(data.measurement_truth_status));
      this.updateState({
        coherence: hasMeasurements && data.current_coherence != null ? Number(data.current_coherence) : null,
        lambda: hasMeasurements && data.current_lambda != null ? Number(data.current_lambda) : null,
        lighthouseSignal: hasMeasurements && data.current_lighthouse_signal != null ? Number(data.current_lighthouse_signal) : null,
        dominantNode: hasMeasurements ? data.dominant_node ?? null : null,
        prismLevel: hasMeasurements ? data.prism_level ?? null : null,
        prismState: hasMeasurements ? data.prism_state ?? null : null,
        totalEquity: hasMeasurements && data.total_equity_usd != null ? Number(data.total_equity_usd) : null,
        availableBalance: hasMeasurements && data.available_balance_usdt != null ? Number(data.available_balance_usdt) : null,
        totalTrades: data.total_trades ?? null,
        winningTrades: data.winning_trades ?? null,
        totalPnl: data.total_pnl_usdt == null ? null : Number(data.total_pnl_usdt),
        gasTankBalance: data.gas_tank_balance == null ? null : Number(data.gas_tank_balance),
        recentTrades: Array.isArray(data.recent_trades) ? data.recent_trades as any[] : [],
      });
    }
  }
  
  /**
   * Start autonomous trading loop
   */
  async startTrading(): Promise<void> {
    if (this.state.isRunning) {
      console.log('[GlobalSystems] Already running');
      return;
    }
    
    console.log('🚀 GlobalSystemsManager: Starting autonomous trading...');
    
    // Initialize ticker cache (800+ pairs like Python ecosystem) with WebSocket
    await tickerCacheManager.initialize();
    
    // Load trade history for calibration
    await tradeLogger.loadFromDatabase(500);
    
    // Initialize and start prediction accuracy tracker
    await predictionAccuracyTracker.loadFromDatabase(100);
    predictionAccuracyTracker.start();
    
    // Run startup harvest (scan existing holdings for profit opportunities)
    // GAP CLOSURE: Execute startup harvest on login
    const dryRun = unifiedOrchestrator.getConfig().dryRun;
    console.log('🌾 [GlobalSystems] Running startup harvest...');
    try {
      const harvestResult = await startupHarvester.harvest(dryRun);
      console.log(`🌾 [GlobalSystems] Startup harvest complete: ${harvestResult.harvested} positions harvested, $${harvestResult.totalProfit.toFixed(2)} profit`);
    } catch (err) {
      console.warn('⚠️ [GlobalSystems] Startup harvest failed:', err);
    }
    
    // Initialize exchange client
    multiExchangeClient.initialize().catch(console.error);
    
    // Subscribe to exchange updates and sync balances for trading
    this.exchangeUnsubscribe = multiExchangeClient.subscribe((state: MultiExchangeState) => {
      this.updateState({ 
        exchangeState: state,
        // Sync balance to trading state
        totalEquity: state.totalEquityUsd || 0,
        availableBalance: state.totalEquityUsd || 0,
      });
      
      // Update Capital Pool with new equity
      if (state.totalEquityUsd > 0) {
        capitalPool.updateEquity(state.totalEquityUsd, 0);
        console.log(`💰 [GlobalSystems] Balance synced: $${state.totalEquityUsd.toFixed(2)}`);
      }
    });
    
    // Register systems with Temporal Ladder
    temporalLadder.registerSystem(SYSTEMS.MASTER_EQUATION);
    temporalLadder.registerSystem(SYSTEMS.HARMONIC_NEXUS);
    temporalLadder.registerSystem(SYSTEMS.QUANTUM_QUACKERS);
    temporalLadder.registerSystem(SYSTEMS.TICKER_CACHE);
    temporalLadder.registerSystem(SYSTEMS.CAPITAL_POOL);
    
    this.updateState({
      isActive: true,
      isRunning: true,
      systemStatus: {
        masterEquation: true,
        lighthouse: true,
        rainbowBridge: true,
        elephantMemory: true,
        orderRouter: true,
      },
    });
    
    // Start 3-second orchestration loop (uses runFullCycle for multi-symbol scanning)
    this.orchestrationInterval = setInterval(() => this.runQuantumCycle(), 3000);
    
    // Countdown timer
    this.countdownInterval = setInterval(() => {
      this.updateState({
        nextCheckIn: this.state.nextCheckIn <= 1 ? 3 : this.state.nextCheckIn - 1,
      });
    }, 1000);
    
    // Run immediately
    this.runQuantumCycle();
    
    console.log('✅ GlobalSystemsManager: Autonomous trading active with multi-symbol scanning + WebSocket');
  }
  
  /**
   * Stop trading loop
   */
  stopTrading(): void {
    console.log('⏹️ GlobalSystemsManager: Stopping trading...');
    
    if (this.orchestrationInterval) {
      clearInterval(this.orchestrationInterval);
      this.orchestrationInterval = null;
    }
    
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
    
    if (this.exchangeUnsubscribe) {
      this.exchangeUnsubscribe();
      this.exchangeUnsubscribe = null;
    }
    
    // Stop prediction tracker
    predictionAccuracyTracker.stop();
    
    // Destroy ticker cache (including WebSocket)
    tickerCacheManager.destroy();
    
    // Unregister from Temporal Ladder
    temporalLadder.unregisterSystem(SYSTEMS.MASTER_EQUATION);
    temporalLadder.unregisterSystem(SYSTEMS.HARMONIC_NEXUS);
    
    this.updateState({
      isActive: false,
      isRunning: false,
      systemStatus: {
        masterEquation: false,
        lighthouse: false,
        rainbowBridge: false,
        elephantMemory: false,
        orderRouter: false,
      },
    });
    
    console.log('✅ GlobalSystemsManager: Trading stopped');
  }
  
  /**
   * Run a single quantum computation cycle - now uses full multi-symbol scanning
   */
  private async runQuantumCycle(): Promise<void> {
    if (!this.state.userId) return;
    
    try {
      // Run full cycle with multi-symbol scanning (mirrors Python aureon_unified_ecosystem.py)
      // This will: 1) Refresh all tickers, 2) Scan opportunities, 3) Check positions, 4) Execute best trade
      const fullResult = await unifiedOrchestrator.runFullCycle();
      
      // Extract nested orchestration result
      const result = fullResult.result;
      
      // Get latest market data for state update
      const marketData = await this.fetchMarketData('BTCUSDT');
      this.updateState({ marketData });
      
      // Log market sweep stats
      console.log(`[GlobalSystems] Sweep: ${fullResult.tickersScanned} tickers → ${fullResult.opportunitiesFound} opps → ${fullResult.filteredOpportunities} filtered | Best: ${fullResult.bestOpportunity?.symbol || 'none'}`);
      
      // Update state from result
      if (result?.lambdaState) {
        // Run Prism transformation
        const prismOutput = result.rainbowState ? thePrism.transform({
          lambda: result.lambdaState.lambda,
          coherence: result.lambdaState.coherence,
          substrate: result.lambdaState.substrate,
          observer: result.lambdaState.observer,
          echo: result.lambdaState.echo,
          volatility: marketData.volatility,
          momentum: marketData.momentum,
          baseFrequency: result.rainbowState.frequency,
        }) : null;
        
        this.updateState({
          coherence: result.lambdaState.coherence,
          lambda: result.lambdaState.lambda,
          lighthouseSignal: result.lighthouseState?.L ?? null,
          dominantNode: result.lambdaState.dominantNode,
          prismLevel: prismOutput?.level ?? null,
          prismState: prismOutput?.state ?? null,
          substrate: result.lambdaState.substrate,
          observer: result.lambdaState.observer,
          echo: result.lambdaState.echo,
          prismOutput,
          lastDecision: result,
        });
        
        // Heartbeats to Temporal Ladder
        temporalLadder.heartbeat(SYSTEMS.MASTER_EQUATION, result.lambdaState.coherence);
        temporalLadder.heartbeat(SYSTEMS.HARMONIC_NEXUS, result.busSnapshot.consensusConfidence);
        
        // Persist to database
        await supabase
          .from('aureon_user_sessions')
          .update({
            current_coherence: result.lambdaState.coherence,
            current_lambda: result.lambdaState.lambda,
            current_lighthouse_signal: result.lighthouseState?.L ?? null,
            dominant_node: result.lambdaState.dominantNode,
            prism_level: prismOutput?.level ?? null,
            prism_state: prismOutput?.state ?? null,
            last_quantum_update_at: marketData.sourceTimestamp,
            measurement_truth_status: 'real_derived',
            measurement_source_id: marketData.sourceId,
            measurement_source_timestamp: marketData.sourceTimestamp,
            measurement_collected_at: new Date().toISOString(),
            measurement_generated_values: false,
          })
          .eq('user_id', this.state.userId);
      }
      
      // A decision is advisory until an exchange receipt exists.
      if (result?.finalDecision?.action !== 'HOLD') {
        const symbol = fullResult.bestOpportunity?.symbol;
        if (!symbol) return;
        const signal = `${result.finalDecision.action} ${symbol} @ $${marketData.price.toFixed(2)} (advisory; not an execution receipt)`;
        
        temporalLadder.broadcast(SYSTEMS.QUANTUM_QUACKERS, 'TRADE_SIGNAL', {
          action: result.finalDecision.action,
          symbol: symbol,
          confidence: result.finalDecision.confidence,
          reason: result.finalDecision.reason
        });
        
        this.updateState({ lastSignal: signal });
      }
      
    } catch (error) {
      console.error('[GlobalSystems] Quantum cycle error:', error);
    }
  }
  
  /**
   * Fetch market data from edge function
   * THROWS if live data is unavailable - no simulation fallback
   */
  private async fetchMarketData(symbol: string = 'BTCUSDT'): Promise<GlobalState['marketData']> {
    const { data, error } = await supabase.functions.invoke('get-user-market-data', {
      body: { symbol }
    });
    
    if (error) {
      console.error('[GlobalSystems] Failed to fetch live market data:', error);
      throw new Error(`Live market data unavailable: ${error.message}`);
    }
    
    const sourceAgeMs = Date.now() - Date.parse(String(data?.sourceTimestamp || ''));
    const values = [data?.price, data?.volume, data?.volatility, data?.momentum, data?.spread, data?.timestamp];
    if (!data || !values.every(Number.isFinite) || data.price <= 0 || data.volume < 0 ||
        !['live', 'real_derived'].includes(String(data.truthStatus)) || !data.sourceId ||
        data.generatedValues !== false || !Number.isFinite(sourceAgeMs) || sourceAgeMs < -60_000 || sourceAgeMs > 300_000) {
      throw new Error('LIVE_DATA_REQUIRED: invalid or stale market observation');
    }
    
    return data;
  }
  
  /**
   * Update state and notify listeners
   */
  private updateState(partial: Partial<GlobalState>): void {
    this.state = { ...this.state, ...partial };
    this.notifyListeners();
  }
  
  /**
   * Notify all subscribers
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.state);
      } catch (error) {
        console.error('[GlobalSystems] Listener error:', error);
      }
    });
  }
  
  /**
   * Subscribe to state changes
   */
  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    // Immediately call with current state
    listener(this.state);
    
    return () => {
      this.listeners.delete(listener);
    };
  }
  
  /**
   * Get current state (snapshot)
   */
  getState(): GlobalState {
    return { ...this.state };
  }
  
  /**
   * Public method to update state from external hooks (e.g., useTerminalSync)
   */
  setPartialState(partial: Partial<GlobalState>): void {
    this.updateState(partial);
  }
  
  /**
   * Cleanup (only call on app unmount, which basically never happens in SPA)
   */
  destroy(): void {
    console.log('🌌 GlobalSystemsManager: Destroying...');
    
    this.stopTrading();
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    
    if (this.busUnsubscribe) this.busUnsubscribe();
    if (this.ecosystemUnsubscribe) this.ecosystemUnsubscribe();
    if (this.authUnsubscribe) this.authUnsubscribe();
    
    backgroundServices.stop();
    
    this.listeners.clear();
    GlobalSystemsManager.instance = null;
  }
}

// Export singleton instance
export const globalSystemsManager = GlobalSystemsManager.getInstance();
