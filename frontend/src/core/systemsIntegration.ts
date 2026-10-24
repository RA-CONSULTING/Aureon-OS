/**
 * Systems Integration Module
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Connects ALL systems to the Temporal Ladder hive mind:
 * - Zero Point Field Detector
 * - Dimensional Dialler
 * - Akashic Mapper
 * - HNC Imperial Detector
 * - Harmonic Nexus Core
 * - Omega Equation
 * 
 * This module ensures full hive mind coherence across all quantum systems.
 */

import { temporalLadder, SYSTEMS, type SystemName } from './temporalLadder';
import { ZeroPointFieldDetector, type ZeroPointFieldState } from './zeroPointFieldDetector';
import { DimensionalDialler, type DimensionalDiallerState } from './dimensionalDialler';
import { attuneToAkashicFrequency, calculateAkashicBoost, type AkashicAttunement } from './akashicFrequencyMapper';

export interface IntegratedSystemState {
  timestamp: number;
  zeroPoint: ZeroPointFieldState | null;
  dimensional: DimensionalDiallerState | null;
  akashic: AkashicAttunement | null;
  hiveMindCoherence: number;
  systemsActive: number;
  systemsTotal: number;
  integrationHealth: number;
}

export interface SystemHeartbeat {
  system: SystemName;
  health: number;
  timestamp: number;
  data?: any;
}

/**
 * Integrated Systems Manager
 * Connects all quantum systems to the Temporal Ladder hive mind
 */
export class SystemsIntegrationManager {
  private zeroPointDetector: ZeroPointFieldDetector;
  private dimensionalDialler: DimensionalDialler;
  private akashicAttunement: AkashicAttunement | null = null;
  
  private heartbeatInterval: number | null = null;
  private listeners: Array<(state: IntegratedSystemState) => void> = [];
  private isInitialized = false;

  constructor() {
    this.zeroPointDetector = new ZeroPointFieldDetector();
    this.dimensionalDialler = new DimensionalDialler();
  }

  /**
   * Initialize and register all systems with the Temporal Ladder
   */
  public initialize(): void {
    if (this.isInitialized) return;

    console.log('🌌 Systems Integration: Initializing hive mind connections...');

    // Register Zero Point Detector
    temporalLadder.registerSystem(SYSTEMS.ZERO_POINT);
    console.log('✅ Zero Point Field Detector registered');

    // Register Dimensional Dialler
    temporalLadder.registerSystem(SYSTEMS.DIMENSIONAL_DIALLER);
    console.log('✅ Dimensional Dialler registered');

    // Register Akashic Mapper
    temporalLadder.registerSystem(SYSTEMS.AKASHIC_MAPPER);
    this.akashicAttunement = attuneToAkashicFrequency(7);
    console.log(`✅ Akashic Mapper registered (frequency: ${this.akashicAttunement.finalFrequency.toFixed(4)} Hz)`);

    // Start heartbeat system
    this.startHeartbeat();
    
    this.isInitialized = true;
    console.log('🌌 Systems Integration: All systems connected to hive mind');
  }

  /**
   * Start sending heartbeats to Temporal Ladder
   */
  private startHeartbeat(): void {
    if (this.heartbeatInterval) return;

    this.heartbeatInterval = window.setInterval(() => {
      this.sendHeartbeats();
      this.notifyListeners();
    }, 1000);
  }

  /**
   * Send heartbeats from all integrated systems
   */
  private sendHeartbeats(): void {
    const now = Date.now();

    // Zero Point heartbeat
    const zeroPointState = this.getZeroPointState();
    if (zeroPointState) {
      temporalLadder.heartbeat(SYSTEMS.ZERO_POINT, zeroPointState.zeroPointCoherence);
    }

    // Dimensional heartbeat
    const dimensionalState = this.getDimensionalState();
    if (dimensionalState) {
      temporalLadder.heartbeat(SYSTEMS.DIMENSIONAL_DIALLER, dimensionalState.stability.overall);
    }

    // Akashic heartbeat
    if (this.akashicAttunement) {
      temporalLadder.heartbeat(SYSTEMS.AKASHIC_MAPPER, this.akashicAttunement.stabilityIndex);
    }
  }

  /**
   * Get current Zero Point Field state
   */
  public getZeroPointState(): ZeroPointFieldState | null {
    // No live field is wired here. A clock sine is not coherence.
    return null;
  }

  /**
   * Get current Dimensional Dialler state
   */
  public getDimensionalState(): DimensionalDiallerState | null {
    // No live field is wired here. A clock sine is not coherence.
    return null;
  }

  /**
   * Get current Akashic attunement
   */
  public getAkashicState(): AkashicAttunement | null {
    return this.akashicAttunement;
  }

  /**
   * Refresh Akashic attunement with new meditation cycle
   */
  public refreshAkashicAttunement(iterations: number = 7): AkashicAttunement {
    this.akashicAttunement = attuneToAkashicFrequency(iterations);
    
    // Broadcast to hive mind
    temporalLadder.broadcast(SYSTEMS.AKASHIC_MAPPER, 'attunement_refresh', {
      frequency: this.akashicAttunement.finalFrequency,
      stability: this.akashicAttunement.stabilityIndex
    });

    return this.akashicAttunement;
  }

  /**
   * Calculate harmonic boost based on Akashic alignment
   */
  public calculateAkashicBoost(systemCoherence: number): number {
    if (!this.akashicAttunement) return 1.0;
    return calculateAkashicBoost(this.akashicAttunement, systemCoherence);
  }

  /**
   * Get integrated state from all systems
   */
  public getIntegratedState(): IntegratedSystemState {
    const ladderState = temporalLadder.getState();
    
    let activeCount = 0;
    ladderState.systems.forEach(status => {
      if (status.active) activeCount++;
    });

    return {
      timestamp: Date.now(),
      zeroPoint: this.getZeroPointState(),
      dimensional: this.getDimensionalState(),
      akashic: this.akashicAttunement,
      hiveMindCoherence: ladderState.hiveMindCoherence,
      systemsActive: activeCount,
      systemsTotal: 8,
      integrationHealth: activeCount / 8
    };
  }

  /**
   * Subscribe to state updates
   */
  public subscribe(listener: (state: IntegratedSystemState) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners(): void {
    const state = this.getIntegratedState();
    this.listeners.forEach(listener => {
      try {
        listener(state);
      } catch (error) {
        console.error('Integration listener error:', error);
      }
    });
  }

  /**
   * Request cross-system assistance
   */
  public requestCrossSystemAssistance(
    fromSystem: SystemName,
    toSystem: SystemName,
    reason: string
  ): boolean {
    return temporalLadder.requestAssistance(fromSystem, toSystem, reason);
  }

  /**
   * Broadcast event to all systems
   */
  public broadcastToHiveMind(
    sourceSystem: SystemName,
    event: string,
    data?: any
  ): void {
    temporalLadder.broadcast(sourceSystem, event, data);
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    // Unregister systems
    temporalLadder.unregisterSystem(SYSTEMS.ZERO_POINT);
    temporalLadder.unregisterSystem(SYSTEMS.DIMENSIONAL_DIALLER);
    temporalLadder.unregisterSystem(SYSTEMS.AKASHIC_MAPPER);

    this.listeners = [];
    this.isInitialized = false;
  }
}

// Singleton instance
export const systemsIntegration = new SystemsIntegrationManager();

// Auto-initialize when imported in browser context
if (typeof window !== 'undefined') {
  // Delay initialization to ensure other systems are ready
  setTimeout(() => {
    systemsIntegration.initialize();
  }, 100);
}
