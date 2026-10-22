/**
 * SMOKE TEST PHASE VALIDATOR
 * 
 * Uses Lighthouse Protocol to auto-validate system families
 * on their way up through startup phases.
 * 
 * Prevents "ghosts in the machine" - fake calls that don't
 * have real system backing.
 * 
 * Each phase must achieve Lighthouse consensus before advancing.
 */

import { temporalLadder, SYSTEMS, SystemName, SystemStatus } from './temporalLadder';
import { unifiedBus, SystemState } from './unifiedBus';
import { LighthouseConsensus, LighthouseState } from './lighthouseConsensus';

// ============= PHASE DEFINITIONS =============

export type PhaseStatus = 'PENDING' | 'VALIDATING' | 'PASSED' | 'FAILED' | 'GHOST_DETECTED';

export interface PhaseValidation {
  phase: number;
  name: string;
  status: PhaseStatus;
  requiredSystems: SystemName[];
  validatedSystems: SystemName[];
  ghostsDetected: SystemName[];
  lighthouseL: number;
  coherence: number;
  timestamp: number;
  errorMessage?: string;
  exchangeDataStatus?: 'LIVE' | 'DEMO' | 'OFFLINE' | 'PENDING';
  liveExchangeCount?: number;
}

export interface SmokeTestState {
  currentPhase: number;
  totalPhases: number;
  phases: PhaseValidation[];
  overallStatus: 'INITIALIZING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'GHOST_ALERT' | 'DEMO_DATA_DETECTED';
  startTime: number;
  endTime?: number;
  lighthouseValidated: boolean;
  exchangeDataVerified: boolean;
  isLiveData: boolean;
}

// System family groupings for phased startup
const PHASE_FAMILIES: Array<{ name: string; systems: SystemName[]; requiresExchangeData?: boolean }> = [
  {
    name: 'CORE_NEXUS',
    systems: [SYSTEMS.HARMONIC_NEXUS, SYSTEMS.MASTER_EQUATION],
  },
  {
    name: 'EARTH_INTEGRATION',
    systems: [SYSTEMS.EARTH_INTEGRATION, SYSTEMS.NEXUS_FEED],
  },
  {
    name: 'QUANTUM_PERCEPTION',
    systems: [SYSTEMS.QUANTUM_QUACKERS, SYSTEMS.AKASHIC_MAPPER, SYSTEMS.ZERO_POINT],
  },
  {
    name: 'DIMENSIONAL_CONTROL',
    systems: [SYSTEMS.DIMENSIONAL_DIALLER, SYSTEMS.STARGATE_LATTICE, SYSTEMS.INTEGRAL_AQAL],
  },
  {
    name: 'SIGNAL_DETECTION',
    systems: [SYSTEMS.FTCP_DETECTOR, SYSTEMS.QGITA_SIGNAL, SYSTEMS.HNC_IMPERIAL],
  },
  {
    name: 'EXECUTION_LAYER',
    systems: [SYSTEMS.SMART_ROUTER, SYSTEMS.HIVE_CONTROLLER, SYSTEMS.DECISION_FUSION],
  },
  {
    name: 'HARMONIC_OUTPUT',
    systems: [SYSTEMS.PRISM, SYSTEMS.SIX_D_HARMONIC, SYSTEMS.PROBABILITY_MATRIX],
  },
  {
    name: 'ADVANCED_PERCEPTION',
    systems: [SYSTEMS.TEMPORAL_ANCHOR, SYSTEMS.QUANTUM_TELESCOPE],
  },
  {
    // NEW PHASE: Exchange Data Verification
    name: 'DATA_VERIFICATION',
    systems: [], // No specific systems - validates exchange connectivity
    requiresExchangeData: true,
  },
];

// Minimum thresholds for phase validation
const MIN_LIGHTHOUSE_L = 0.4;          // Minimum Lighthouse signal for phase pass
const MIN_COHERENCE = 0.6;              // Minimum coherence for phase pass
const HEARTBEAT_FRESHNESS_MS = 5000;    // Heartbeat must be within 5 seconds
const GHOST_DETECTION_THRESHOLD = 3;    // Consecutive failures = ghost

class SmokeTestPhaseValidator {
  private state: SmokeTestState;
  private lighthouse: LighthouseConsensus;
  private listeners: Set<(state: SmokeTestState) => void> = new Set();
  private ghostTracking: Map<SystemName, number> = new Map();
  private validationInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.lighthouse = new LighthouseConsensus();
    this.state = this.createInitialState();
  }

  private createInitialState(): SmokeTestState {
    return {
      currentPhase: 0,
      totalPhases: PHASE_FAMILIES.length,
      phases: PHASE_FAMILIES.map((family, index) => ({
        phase: index + 1,
        name: family.name,
        status: 'PENDING' as PhaseStatus,
        requiredSystems: family.systems,
        validatedSystems: [],
        ghostsDetected: [],
        lighthouseL: 0,
        coherence: 0,
        timestamp: 0,
        exchangeDataStatus: family.requiresExchangeData ? 'PENDING' : undefined,
      })),
      overallStatus: 'INITIALIZING',
      startTime: Date.now(),
      lighthouseValidated: false,
      exchangeDataVerified: false,
      isLiveData: false,
    };
  }

  /**
   * Start the smoke test validation sequence
   */
  start(): void {
    console.log('🔥 SMOKE TEST: Starting Lighthouse-validated phase sequence');
    this.state = this.createInitialState();
    this.state.overallStatus = 'RUNNING';
    this.ghostTracking.clear();
    
    // Start validation loop
    this.validationInterval = setInterval(() => this.validateCurrentPhase(), 1000);
    this.notifyListeners();
  }

  /**
   * Stop the smoke test
   */
  stop(): void {
    if (this.validationInterval) {
      clearInterval(this.validationInterval);
      this.validationInterval = null;
    }
    console.log('🛑 SMOKE TEST: Stopped');
  }

  /**
   * Validate current phase using Lighthouse protocol
   */
  private async validateCurrentPhase(): Promise<void> {
    if (this.state.currentPhase >= this.state.totalPhases) {
      this.completeTest();
      return;
    }

    const phaseIndex = this.state.currentPhase;
    const phase = this.state.phases[phaseIndex];
    const family = PHASE_FAMILIES[phaseIndex];

    phase.status = 'VALIDATING';
    phase.timestamp = Date.now();

    // Special handling for DATA_VERIFICATION phase
    if (family.requiresExchangeData) {
      await this.validateExchangeData(phase);
      return;
    }

    // Check each system in this phase family
    const validatedSystems: SystemName[] = [];
    const ghostsDetected: SystemName[] = [];

    for (const systemName of family.systems) {
      const validation = this.validateSystem(systemName);
      
      if (validation.isGhost) {
        ghostsDetected.push(systemName);
        this.trackGhost(systemName);
      } else if (validation.isValid) {
        validatedSystems.push(systemName);
        this.clearGhostTracking(systemName);
      }
    }

    phase.validatedSystems = validatedSystems;
    phase.ghostsDetected = ghostsDetected;

    // Run Lighthouse consensus on this phase
    const lighthouseResult = this.runLighthouseValidation(phase);
    phase.lighthouseL = lighthouseResult.L;
    phase.coherence = lighthouseResult.coherence;

    // Determine phase status
    if (ghostsDetected.length > 0) {
      phase.status = 'GHOST_DETECTED';
      phase.errorMessage = `Ghost systems detected: ${ghostsDetected.join(', ')}`;
      console.warn(`👻 SMOKE TEST Phase ${phase.phase}: GHOST DETECTED - ${ghostsDetected.join(', ')}`);
    } else if (family.systems.length === 0) {
      // Phase has no required systems - skip
      phase.status = 'PASSED';
      console.log(`✅ SMOKE TEST Phase ${phase.phase} (${phase.name}): PASSED (no systems required)`);
      this.state.currentPhase++;
    } else if (validatedSystems.length === 0) {
      // NO systems registered - this is a problem, not a pass!
      phase.status = 'VALIDATING';
      phase.errorMessage = `No systems registered - awaiting: ${family.systems.join(', ')}`;
      console.warn(`⏳ SMOKE TEST Phase ${phase.phase} (${phase.name}): Waiting for systems to register...`);
    } else if (
      validatedSystems.length === family.systems.length &&
      lighthouseResult.L >= MIN_LIGHTHOUSE_L &&
      lighthouseResult.coherence >= MIN_COHERENCE
    ) {
      phase.status = 'PASSED';
      console.log(`✅ SMOKE TEST Phase ${phase.phase} (${phase.name}): PASSED | L=${lighthouseResult.L.toFixed(3)} Γ=${lighthouseResult.coherence.toFixed(3)}`);
      this.state.currentPhase++;
    } else if (validatedSystems.length < family.systems.length) {
      const missing = family.systems.filter(s => !validatedSystems.includes(s));
      phase.errorMessage = `${validatedSystems.length}/${family.systems.length} ready - awaiting: ${missing.join(', ')}`;
    } else {
      phase.errorMessage = `Lighthouse validation pending: L=${lighthouseResult.L.toFixed(3)} (need ${MIN_LIGHTHOUSE_L})`;
    }

    // Check for critical ghost alert
    if (this.hasSystemicGhostProblem()) {
      this.state.overallStatus = 'GHOST_ALERT';
      this.stop();
      console.error('🚨 SMOKE TEST: SYSTEMIC GHOST PROBLEM DETECTED - HALTING');
    }

    this.notifyListeners();
  }

  /**
   * Validate exchange data connectivity - no ghost/fake data allowed
   */
  private async validateExchangeData(phase: PhaseValidation): Promise<void> {
    console.log('🔌 SMOKE TEST: Validating exchange data connectivity...');
    
    try {
      // Call the verification endpoint
      const response = await fetch(
        `${this.getSupabaseUrl()}/functions/v1/verify-exchange-connectivity`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'apikey': this.getSupabaseAnonKey(),
          },
        }
      );

      if (!response.ok) {
        phase.status = 'FAILED';
        phase.exchangeDataStatus = 'OFFLINE';
        phase.errorMessage = 'Failed to verify exchange connectivity';
        console.error('❌ SMOKE TEST: Exchange verification failed');
        this.notifyListeners();
        return;
      }

      const data = await response.json();
      
      const liveCount = data.exchanges?.filter((e: any) => e.status === 'LIVE').length || 0;
      const totalCount = data.exchanges?.length || 0;
      
      phase.liveExchangeCount = liveCount;
      
      if (data.overallStatus === 'ALL_LIVE') {
        phase.status = 'PASSED';
        phase.exchangeDataStatus = 'LIVE';
        this.state.exchangeDataVerified = true;
        this.state.isLiveData = true;
        console.log(`✅ SMOKE TEST Phase ${phase.phase} (DATA_VERIFICATION): ALL EXCHANGES LIVE (${liveCount}/${totalCount})`);
        this.state.currentPhase++;
      } else if (data.overallStatus === 'PARTIAL_LIVE' && liveCount >= 1) {
        // Allow partial live if at least one exchange is live
        phase.status = 'PASSED';
        phase.exchangeDataStatus = 'LIVE';
        this.state.exchangeDataVerified = true;
        this.state.isLiveData = true;
        console.log(`⚠️ SMOKE TEST Phase ${phase.phase} (DATA_VERIFICATION): PARTIAL LIVE (${liveCount}/${totalCount})`);
        this.state.currentPhase++;
      } else if (data.overallStatus === 'ALL_DEMO') {
        phase.status = 'GHOST_DETECTED';
        phase.exchangeDataStatus = 'DEMO';
        phase.errorMessage = '⚠️ ALL EXCHANGES RETURNING DEMO DATA - NOT REAL TRADING DATA';
        this.state.overallStatus = 'DEMO_DATA_DETECTED';
        this.state.isLiveData = false;
        console.error('👻 SMOKE TEST: DEMO DATA DETECTED - Trading blocked until live data available');
      } else {
        phase.status = 'FAILED';
        phase.exchangeDataStatus = 'OFFLINE';
        phase.errorMessage = 'No exchange connections available';
        console.error('❌ SMOKE TEST: No exchanges connected');
      }
      
    } catch (error) {
      phase.status = 'FAILED';
      phase.exchangeDataStatus = 'OFFLINE';
      phase.errorMessage = error instanceof Error ? error.message : 'Verification failed';
      console.error('❌ SMOKE TEST: Exchange verification error:', error);
    }

    this.notifyListeners();
  }

  private getSupabaseUrl(): string {
    // Browser environment
    if (typeof window !== 'undefined' && (window as any).__SUPABASE_URL__) {
      return (window as any).__SUPABASE_URL__;
    }
    // Fallback to hardcoded (replace in production)
    return 'https://owfeyxrfyhprpcgqwxqh.supabase.co';
  }

  private getSupabaseAnonKey(): string {
    // Browser environment
    if (typeof window !== 'undefined' && (window as any).__SUPABASE_ANON_KEY__) {
      return (window as any).__SUPABASE_ANON_KEY__;
    }
    // No key is committed. Set window.__SUPABASE_ANON_KEY__ or leave this empty.
    return '';
  }

  /**
   * Validate a single system - check for ghost (fake) registration
   */
  private validateSystem(systemName: SystemName): { isValid: boolean; isGhost: boolean } {
    const ladderStatus = temporalLadder.getSystemStatus(systemName);
    const busState = unifiedBus.read(this.mapSystemToBusName(systemName));
    const now = Date.now();

    // GHOST DETECTION RULES:
    // 1. System claims active in ladder but no bus state
    // 2. System has bus state but ladder says inactive
    // 3. Heartbeat is stale (>5 seconds)
    // 4. Coherence is exactly 0 (placeholder/fake)
    // 5. Ready is true but coherence is impossibly low

    // Check 1: Ladder active but no bus state
    if (ladderStatus?.active && !busState) {
      console.warn(`👻 Ghost Check: ${systemName} - active in ladder but no bus state`);
      return { isValid: false, isGhost: true };
    }

    // Check 2: Bus state exists but ladder inactive
    if (busState && !ladderStatus?.active) {
      console.warn(`👻 Ghost Check: ${systemName} - bus state exists but ladder inactive`);
      return { isValid: false, isGhost: true };
    }

    // Check 3: Stale heartbeat
    if (ladderStatus?.active && (now - ladderStatus.lastHeartbeat) > HEARTBEAT_FRESHNESS_MS) {
      console.warn(`👻 Ghost Check: ${systemName} - stale heartbeat (${now - ladderStatus.lastHeartbeat}ms)`);
      return { isValid: false, isGhost: true };
    }

    // Check 4: Zero coherence (likely fake)
    if (busState?.coherence === 0 && busState?.ready) {
      console.warn(`👻 Ghost Check: ${systemName} - zero coherence but claims ready`);
      return { isValid: false, isGhost: true };
    }

    // Check 5: Ready with impossibly low coherence
    if (busState?.ready && busState?.coherence < 0.1) {
      console.warn(`👻 Ghost Check: ${systemName} - ready with coherence < 0.1`);
      return { isValid: false, isGhost: true };
    }

    // System is valid if:
    // - Active in ladder
    // - Has bus state OR is optional
    // - Health above 0.5
    const isValid = ladderStatus?.active === true && 
                    ladderStatus.health > 0.5 &&
                    (!busState || busState.ready);

    return { isValid, isGhost: false };
  }

  /**
   * Map Temporal Ladder system name to UnifiedBus name
   */
  private mapSystemToBusName(systemName: SystemName): string {
    const mapping: Record<SystemName, string> = {
      'harmonic-nexus': 'HarmonicNexus',
      'master-equation': 'MasterEquation',
      'earth-integration': 'EarthIntegration',
      'nexus-feed': 'NexusFeed',
      'quantum-quackers': 'QuantumQuackers',
      'akashic-mapper': 'AkashicMapper',
      'zero-point': 'ZeroPoint',
      'dimensional-dialler': 'DimensionalDialler',
      'integral-aqal': 'IntegralAQAL',
      'stargate-lattice': 'StargateLattice',
      'ftcp-detector': 'FTCPDetector',
      'qgita-signal': 'QGITASignal',
      'hnc-imperial': 'HNCImperial',
      'hocus-pattern': 'HocusPattern',
      'smart-router': 'SmartRouter',
      'temporal-anchor': 'TemporalAnchor',
      'hive-controller': 'HiveController',
      'decision-fusion': 'DecisionFusion',
      'prism': 'Prism',
      '6d-harmonic': '6DHarmonic',
      'probability-matrix': 'ProbabilityMatrix',
      'quantum-telescope': 'QuantumTelescope',
      'gaia-lattice': 'GaiaLattice',
      'synchronicity-decoder': 'SynchronicityDecoder',
      'stargate-grid': 'StargateGrid',
      'market-pulse': 'MarketPulse',
      'anomaly-detector': 'AnomalyDetector',
      'enhancement-layer': 'EnhancementLayer',
      'data-ingestion': 'DataIngestion',
      'opportunity-scanner': 'OpportunityScanner',
      'position-manager': 'PositionManager',
      'ticker-cache': 'TickerCache',
      'capital-pool': 'CapitalPool',
      'startup-harvester': 'StartupHarvester',
    };
    return mapping[systemName] || systemName;
  }

  /**
   * Run Lighthouse consensus validation on a phase
   */
  private runLighthouseValidation(phase: PhaseValidation): { L: number; coherence: number } {
    const ladderState = temporalLadder.getState();
    
    // Compute phase-level coherence from validated systems
    let totalHealth = 0;
    let count = 0;
    
    for (const systemName of phase.validatedSystems) {
      const status = ladderState.systems.get(systemName);
      if (status?.active) {
        totalHealth += status.health;
        count++;
      }
    }
    
    const coherence = count > 0 ? totalHealth / count : 0;
    
    // Run Lighthouse validation
    const lighthouseState = this.lighthouse.validate(
      coherence,           // lambda approximation
      coherence,           // coherence
      coherence * 0.4,     // substrate
      coherence * 0.35,    // observer
      coherence * 0.25,    // echo
      coherence,           // Geff
      count >= phase.requiredSystems.length * 0.8, // FTCP detected if 80%+ systems ready
      0,                   // volumeSpike
      0,                   // spreadExpansion
      0                    // priceAcceleration
    );

    return {
      L: lighthouseState.L,
      coherence,
    };
  }

  /**
   * Track ghost occurrences for a system
   */
  private trackGhost(systemName: SystemName): void {
    const count = (this.ghostTracking.get(systemName) || 0) + 1;
    this.ghostTracking.set(systemName, count);
  }

  /**
   * Clear ghost tracking when system validates
   */
  private clearGhostTracking(systemName: SystemName): void {
    this.ghostTracking.delete(systemName);
  }

  /**
   * Check if there's a systemic ghost problem (multiple persistent ghosts)
   */
  private hasSystemicGhostProblem(): boolean {
    let criticalGhosts = 0;
    this.ghostTracking.forEach((count) => {
      if (count >= GHOST_DETECTION_THRESHOLD) {
        criticalGhosts++;
      }
    });
    return criticalGhosts >= 3; // 3+ systems consistently failing = systemic problem
  }

  /**
   * Complete the test (all phases passed or failed)
   */
  private completeTest(): void {
    this.stop();
    this.state.endTime = Date.now();
    
    const failedPhases = this.state.phases.filter(p => p.status === 'FAILED' || p.status === 'GHOST_DETECTED');
    
    if (failedPhases.length === 0) {
      this.state.overallStatus = 'PASSED';
      this.state.lighthouseValidated = true;
      console.log('🎉 SMOKE TEST: ALL PHASES PASSED - LIGHTHOUSE VALIDATED');
    } else {
      this.state.overallStatus = 'FAILED';
      console.error(`❌ SMOKE TEST: FAILED - ${failedPhases.length} phases failed`);
    }
    
    this.notifyListeners();
  }

  /**
   * Force advance to next phase (manual override)
   */
  forceAdvance(): void {
    if (this.state.currentPhase < this.state.totalPhases) {
      const phase = this.state.phases[this.state.currentPhase];
      phase.status = 'PASSED';
      phase.errorMessage = 'FORCED ADVANCE';
      this.state.currentPhase++;
      console.warn(`⚠️ SMOKE TEST: Force advanced past phase ${phase.phase}`);
      this.notifyListeners();
    }
  }

  /**
   * Get current state
   */
  getState(): SmokeTestState {
    return { ...this.state };
  }

  /**
   * Subscribe to state updates
   */
  subscribe(callback: (state: SmokeTestState) => void): () => void {
    this.listeners.add(callback);
    // Immediately send current state
    callback(this.getState());
    return () => this.listeners.delete(callback);
  }

  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach(cb => {
      try {
        cb(state);
      } catch (e) {
        console.error('SmokeTestPhaseValidator listener error:', e);
      }
    });
  }

  /**
   * Reset the test
   */
  reset(): void {
    this.stop();
    this.state = this.createInitialState();
    this.ghostTracking.clear();
    this.lighthouse.reset();
    this.notifyListeners();
  }
}

// Singleton export
export const smokeTestPhaseValidator = new SmokeTestPhaseValidator();
