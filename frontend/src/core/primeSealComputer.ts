/**
 * Prime Seal Computer (10-9-1)
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Computes the 10-9-1 weighted Prime Seal packet from all system states.
 * - Unity systems (10x weight): MasterEquation, Lighthouse
 * - Flow systems (9x weight): RainbowBridge, Prism, 6DHarmonic
 * - Anchor systems (1x weight): DataIngestion, ElephantMemory
 * 
 * Seal locks at prime_coherence > 0.945 (only then can trades execute)
 */

import { unifiedBus, BusSnapshot, SignalType } from './unifiedBus';

// 10-9-1 system classification
const UNITY_SYSTEMS = ['MasterEquation', 'Lighthouse']; // 10x weight
const FLOW_SYSTEMS = ['RainbowBridge', 'Prism', '6DHarmonic', 'DecisionFusion']; // 9x weight
const ANCHOR_SYSTEMS = ['DataIngestion', 'ElephantMemory', 'MultiExchange']; // 1x weight

const UNITY_WEIGHT = 10;
const FLOW_WEIGHT = 9;
const ANCHOR_WEIGHT = 1;

// Seal lock threshold
const SEAL_LOCK_THRESHOLD = 0.945;

export interface PrimeSealPacket {
  temporal_id: string;
  timestamp: number;
  intent_text: string;
  w_unity_10: number;
  w_flow_9: number;
  w_anchor_1: number;
  amplitude_gain: number;
  packet_value: number;
  seal_lock: boolean;
  prime_coherence: number;
  lattice_phase: number | null;
  systems_contributing: string[];
  consensus_signal: SignalType;
}

export interface PrimeSealState {
  packet: PrimeSealPacket;
  unityCoherence: number;
  flowCoherence: number;
  anchorCoherence: number;
  isLocked: boolean;
  lockReason: string;
}

class PrimeSealComputer {
  private listeners: Set<(state: PrimeSealState) => void> = new Set();
  private lastPacket: PrimeSealPacket | null = null;

  /**
   * Compute 10-9-1 Prime Seal packet from current bus snapshot
   */
  compute(snapshot: BusSnapshot): PrimeSealState {
    const temporalId = `prime-${Date.now()}`;
    const systemsContributing: string[] = [];

    // Compute Unity coherence (10x weight)
    let unitySum = 0;
    let unityCount = 0;
    for (const name of UNITY_SYSTEMS) {
      const state = snapshot.states[name];
      if (state?.ready) {
        unitySum += state.coherence * UNITY_WEIGHT;
        unityCount += UNITY_WEIGHT;
        systemsContributing.push(name);
      }
    }
    const unityCoherence = unityCount > 0 ? unitySum / unityCount : 0;

    // Compute Flow coherence (9x weight)
    let flowSum = 0;
    let flowCount = 0;
    for (const name of FLOW_SYSTEMS) {
      const state = snapshot.states[name];
      if (state?.ready) {
        flowSum += state.coherence * FLOW_WEIGHT;
        flowCount += FLOW_WEIGHT;
        systemsContributing.push(name);
      }
    }
    const flowCoherence = flowCount > 0 ? flowSum / flowCount : 0;

    // Compute Anchor coherence (1x weight)
    let anchorSum = 0;
    let anchorCount = 0;
    for (const name of ANCHOR_SYSTEMS) {
      const state = snapshot.states[name];
      if (state?.ready) {
        anchorSum += state.coherence * ANCHOR_WEIGHT;
        anchorCount += ANCHOR_WEIGHT;
        systemsContributing.push(name);
      }
    }
    const anchorCoherence = anchorCount > 0 ? anchorSum / anchorCount : 0;

    // Compute weighted prime coherence
    const totalWeight = 
      (unityCount > 0 ? 10 : 0) + 
      (flowCount > 0 ? 9 : 0) + 
      (anchorCount > 0 ? 1 : 0);
    
    const primeCoherence = totalWeight > 0
      ? (unityCoherence * 10 + flowCoherence * 9 + anchorCoherence * 1) / 20
      : 0;

    // Determine seal lock
    const sealLock = primeCoherence >= SEAL_LOCK_THRESHOLD;
    const lockReason = sealLock 
      ? `🔒 SEALED: Γ=${primeCoherence.toFixed(4)} ≥ ${SEAL_LOCK_THRESHOLD}`
      : `🔓 UNLOCKED: Γ=${primeCoherence.toFixed(4)} < ${SEAL_LOCK_THRESHOLD}`;

    // A clock phase is not a measured lattice. Leave it unavailable.
    const latticePhase = null;

    // Compute amplitude gain from system readiness
    const amplitudeGain = 1 + (systemsContributing.length / 10) * 0.5;

    // Compute packet value (10-9-1 weighted sum)
    const packetValue = (unityCoherence * 10 + flowCoherence * 9 + anchorCoherence * 1);

    // Generate intent text based on consensus
    const intentText = this.generateIntent(snapshot.consensusSignal, sealLock, primeCoherence);

    const packet: PrimeSealPacket = {
      temporal_id: temporalId,
      timestamp: Date.now(),
      intent_text: intentText,
      w_unity_10: UNITY_WEIGHT,
      w_flow_9: FLOW_WEIGHT,
      w_anchor_1: ANCHOR_WEIGHT,
      amplitude_gain: amplitudeGain,
      packet_value: packetValue,
      seal_lock: sealLock,
      prime_coherence: primeCoherence,
      lattice_phase: latticePhase,
      systems_contributing: systemsContributing,
      consensus_signal: snapshot.consensusSignal,
    };

    this.lastPacket = packet;

    const state: PrimeSealState = {
      packet,
      unityCoherence,
      flowCoherence,
      anchorCoherence,
      isLocked: sealLock,
      lockReason,
    };

    this.notifyListeners(state);
    return state;
  }

  /**
   * Generate intent text based on consensus and seal state
   */
  private generateIntent(signal: SignalType, sealLock: boolean, coherence: number): string {
    if (!sealLock) {
      return `OBSERVING: Awaiting seal lock (Γ=${coherence.toFixed(3)})`;
    }
    
    switch (signal) {
      case 'BUY':
        return `MANIFEST BUY: 10-9-1 aligned, seal locked at Γ=${coherence.toFixed(3)}`;
      case 'SELL':
        return `MANIFEST SELL: 10-9-1 aligned, seal locked at Γ=${coherence.toFixed(3)}`;
      default:
        return `HOLD STEADY: 10-9-1 sealed but awaiting signal clarity`;
    }
  }

  /**
   * Get last computed packet
   */
  getLastPacket(): PrimeSealPacket | null {
    return this.lastPacket;
  }

  /**
   * Check if seal is currently locked
   */
  isSealLocked(): boolean {
    return this.lastPacket?.seal_lock ?? false;
  }

  /**
   * Get current prime coherence
   */
  getPrimeCoherence(): number {
    return this.lastPacket?.prime_coherence ?? 0;
  }

  /**
   * Subscribe to seal state changes
   */
  subscribe(callback: (state: PrimeSealState) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyListeners(state: PrimeSealState): void {
    this.listeners.forEach(cb => cb(state));
  }

  /**
   * Validate that seal is locked before allowing trade execution
   */
  validateTradeExecution(): { allowed: boolean; reason: string } {
    if (!this.lastPacket) {
      return { allowed: false, reason: 'No seal packet computed yet' };
    }
    
    if (!this.lastPacket.seal_lock) {
      return { 
        allowed: false, 
        reason: `Seal not locked: Γ=${this.lastPacket.prime_coherence.toFixed(4)} < ${SEAL_LOCK_THRESHOLD}` 
      };
    }
    
    return { 
      allowed: true, 
      reason: `Seal locked: Γ=${this.lastPacket.prime_coherence.toFixed(4)} ✓` 
    };
  }
}

// Singleton instance
export const primeSealComputer = new PrimeSealComputer();
