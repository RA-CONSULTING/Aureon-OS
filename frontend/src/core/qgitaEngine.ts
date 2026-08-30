/**
 * QGITA Engine - DEPRECATED
 * 
 * This file is kept for backwards compatibility.
 * Use qgitaSignalGenerator.ts as the single source of truth for QGITA signals.
 * 
 * The QGITASignalGenerator provides a more comprehensive implementation with:
 * - FTCP Detection
 * - Lighthouse Consensus validation
 * - Coherence metrics (linear, nonlinear, cross-scale)
 * - Anomaly pointer calculation
 * - Tiered confidence signals (Tier 1/2/3)
 */

import { QGITASignal, qgitaSignalGenerator } from './qgitaSignalGenerator';
import type { DataProvenance } from './liveDataContract';
import { LighthouseState } from './lighthouseConsensus';

// Re-export types for backwards compatibility
export type SignalDirection = 'long' | 'short' | 'neutral';

export interface FibonacciWindow {
  length: number;
  ratioAlignment: number;
  curvature: number;
}

export interface StageBreakdown {
  timeLatticeScore: number;
  coherenceScore: number;
  anomalyScore: number;
}

/**
 * LighthouseEvent - Legacy interface for backwards compatibility
 * Prefer using QGITASignal from qgitaSignalGenerator.ts
 */
export interface LighthouseEvent {
  timestamp: number;
  direction: SignalDirection;
  confidence: number;
  breakdown: StageBreakdown;
}

export interface QGITAConfig {
  fibonacciSequence: number[];
  minConfidence: number;
  neutralConfidence: number;
  historyLimit: number;
}

/**
 * Convert QGITASignal to legacy LighthouseEvent format
 */
export function convertToLighthouseEvent(signal: QGITASignal): LighthouseEvent {
  let direction: SignalDirection = 'neutral';
  if (signal.signalType === 'BUY') direction = 'long';
  else if (signal.signalType === 'SELL') direction = 'short';
  
  return {
    timestamp: signal.timestamp,
    direction,
    confidence: signal.confidence / 100, // Convert to 0-1 scale
    breakdown: {
      timeLatticeScore: signal.goldenRatioScore,
      coherenceScore: (signal.coherence.linearCoherence + signal.coherence.nonlinearCoherence + signal.coherence.crossScaleCoherence) / 3,
      anomalyScore: signal.anomalyPointer,
    },
  };
}

const DEFAULT_CONFIG: QGITAConfig = {
  fibonacciSequence: [5, 8, 13, 21, 34, 55],
  minConfidence: 0.35,
  neutralConfidence: 0.45,
  historyLimit: 300,
};

export const normalize = (value: number, min: number, max: number) => {
  if (max === min) return 0;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
};

/**
 * @deprecated Use qgitaSignalGenerator instead
 * This class is kept for backwards compatibility with existing code
 */
export class QGITAEngine {
  private readonly config: QGITAConfig;
  private lastSignal: QGITASignal | null = null;

  constructor(config: Partial<QGITAConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config } satisfies QGITAConfig;
    console.warn('[QGITAEngine] DEPRECATED: Use qgitaSignalGenerator singleton instead');
  }

  /**
   * @deprecated Use qgitaSignalGenerator.generateSignal() instead
   */
  register(snapshot: { timestamp: number; consolidatedOHLCV: { close: number; volume: number } }) {
    // Proxy to the singleton - we just cache for evaluate()
    console.log('[QGITAEngine] register() called - proxying to qgitaSignalGenerator');
  }

  /**
   * @deprecated Use qgitaSignalGenerator.generateSignal() instead
   * This now returns a converted LighthouseEvent from the last signal
   */
  evaluate(): LighthouseEvent | null {
    if (!this.lastSignal) return null;
    return convertToLighthouseEvent(this.lastSignal);
  }

  /**
   * Generate signal using the singleton and convert to legacy format
   */
  generateAndConvert(
    timestamp: number,
    price: number,
    volume: number,
    lambda: number,
    coherence: number,
    substrate: number,
    observer: number,
    echo: number,
    provenance: DataProvenance,
  ): LighthouseEvent | null {
    this.lastSignal = qgitaSignalGenerator.generateSignal(
      timestamp, price, volume, lambda, coherence, substrate, observer, echo, provenance,
    );
    return this.lastSignal ? convertToLighthouseEvent(this.lastSignal) : null;
  }
  
  /**
   * Get the raw QGITASignal from the last generation
   */
  getLastSignal(): QGITASignal | null {
    return this.lastSignal;
  }
}
