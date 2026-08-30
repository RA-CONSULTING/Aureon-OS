// QGITA Signal Generator
// Combines FTCP detection, Lighthouse consensus, and coherence metrics
// to generate high-confidence trading signals

import { FTCPDetector, CurvaturePoint } from './ftcpDetector';
import { LighthouseConsensus, LighthouseState } from './lighthouseConsensus';
import { QGITACoherenceEngine, calculateAnomalyPointer, CoherenceMetrics } from './qgitaCoherence';
import { FibonacciLattice } from './fibonacciLattice';
import { asDerivedProvenance, assertFreshProvenance, type DataProvenance } from './liveDataContract';

export type QGITASignal = DataProvenance & {
  timestamp: number;
  signalType: 'BUY' | 'SELL' | 'HOLD';
  confidence: number; // 0-100%
  tier: 1 | 2 | 3; // Tier 1: 80-100%, Tier 2: 60-79%, Tier 3: <60%
  curvature: number;
  curvatureDirection: 'UPWARD' | 'DOWNWARD' | 'NEUTRAL';
  lighthouse: LighthouseState;
  coherence: CoherenceMetrics;
  ftcpDetected: boolean;
  goldenRatioScore: number;
  anomalyPointer: number;
  reasoning: string;
  observedSampleCount: number;
};

export class QGITASignalGenerator {
  private ftcpDetector: FTCPDetector;
  private lighthouse: LighthouseConsensus;
  private coherenceEngine: QGITACoherenceEngine;
  private fibLattice: FibonacciLattice;
  
  private priceHistory: number[] = [];
  private volumeHistory: number[] = [];
  private timestampHistory: number[] = [];
  
  private config = {
    curvatureThresholdPercentile: 90,
    goldenRatioTolerance: 0.05,
    lighthouseThresholdSigma: 2.0,
    minConfidenceForSignal: 60,
    tier1Threshold: 80,
    tier2Threshold: 60,
    tier1PositionMultiplier: 1.0,
    tier2PositionMultiplier: 0.5,
    tier3PositionMultiplier: 0.0,
  };
  
  constructor() {
    this.ftcpDetector = new FTCPDetector();
    this.lighthouse = new LighthouseConsensus();
    this.coherenceEngine = new QGITACoherenceEngine();
    this.fibLattice = new FibonacciLattice();
  }
  
  /**
   * Update configuration parameters
   */
  updateConfig(newConfig: Partial<typeof this.config>) {
    this.config = { ...this.config, ...newConfig };
  }
  
  /**
   * Process new market data and generate trading signal
   */
  generateSignal(
    timestamp: number,
    price: number,
    volume: number,
    lambda: number,
    coherenceValue: number,
    substrate: number,
    observer: number,
    echo: number,
    provenance: DataProvenance,
  ): QGITASignal | null {
    assertFreshProvenance(provenance);
    if (!Number.isFinite(timestamp) || timestamp <= 0 || Math.abs(timestamp - Date.parse(provenance.sourceTimestamp)) > 60_000) {
      throw new Error('LIVE_DATA_REQUIRED: QGITA timestamp must match the provider observation');
    }
    if (!Number.isFinite(price) || price <= 0) {
      throw new Error('LIVE_DATA_REQUIRED: QGITA price must be a positive observed value');
    }
    if (!Number.isFinite(volume) || volume < 0) {
      throw new Error('LIVE_DATA_REQUIRED: QGITA volume must be an observed nonnegative value');
    }
    if (![lambda, coherenceValue, substrate, observer, echo].every(Number.isFinite)) {
      throw new Error('LIVE_DATA_REQUIRED: QGITA field metrics must be finite real-derived values');
    }
    
    // Update history
    this.priceHistory.push(price);
    this.volumeHistory.push(volume);
    this.timestampHistory.push(timestamp);
    
    // Keep only recent history
    const maxHistory = 200;
    if (this.priceHistory.length > maxHistory) {
      this.priceHistory.shift();
      this.volumeHistory.shift();
      this.timestampHistory.shift();
    }

    // Absence of sufficient observed history is no_data, not a fabricated HOLD.
    if (this.priceHistory.length < 10) return null;
    
    // Stage 1: FTCP Detection
    const ftcpResult = this.ftcpDetector.addPoint(timestamp, price);
    const ftcpDetected = ftcpResult?.isFTCP || false;
    const goldenRatioScore = ftcpResult?.goldenRatioScore || 0;
    const curvature = ftcpResult?.curvature || 0;
    
    // Determine curvature direction
    const curvatureDirection = this.determineCurvatureDirection(curvature);
    
    // Calculate Geff (effective gravity signal)
    const Geff = this.ftcpDetector.computeGeff();
    const normalizedGeff = Math.min(1.0, Geff / 10); // Normalize to 0-1
    
    // Stage 2: Coherence Metrics
    const coherence = this.coherenceEngine.calculateAllMetrics(this.priceHistory);
    
    // Calculate Anomaly Pointer |Q| and component metrics (Ablation Study)
    const { pointer: anomalyPointer, volumeSpike, spreadExpansion, priceAcceleration } = 
      this.calculateAnomalyComponents(this.priceHistory, this.volumeHistory);
    const normalizedQ = Math.min(1.0, anomalyPointer);
    
    // Stage 3: Lighthouse Validation (Ablation Study: weighted geometric mean)
    const lighthouseState = this.lighthouse.validate(
      lambda,
      coherenceValue,
      substrate,
      observer,
      echo,
      normalizedGeff,
      ftcpDetected,
      volumeSpike,
      spreadExpansion,
      priceAcceleration
    );
    
    // === KILL SWITCH: If Lighthouse is very low (< 0.05), force HOLD ===
    // Note: Lighthouse now uses minimum floor values so L=0 is extremely rare
    if (lighthouseState.L < 0.05 && this.priceHistory.length >= 20) {
      console.warn(`🛑 Lighthouse consensus very low (L=${lighthouseState.L.toFixed(3)}). Forcing HOLD.`);
      return {
        ...asDerivedProvenance(provenance),
        timestamp,
        signalType: 'HOLD',
        confidence: 0,
        tier: 3,
        curvature,
        curvatureDirection: this.determineCurvatureDirection(curvature),
        lighthouse: lighthouseState,
        coherence,
        ftcpDetected,
        goldenRatioScore,
        anomalyPointer,
        reasoning: `🛑 KILL SWITCH: Lighthouse consensus too low (L=${lighthouseState.L.toFixed(3)}). Need more data.`,
        observedSampleCount: this.priceHistory.length,
      };
    }
    
    // Stage 4: Signal Generation
    const signal = this.interpretSignal(
      timestamp,
      curvature,
      curvatureDirection,
      lighthouseState,
      coherence,
      ftcpDetected,
      goldenRatioScore,
      normalizedQ,
      provenance,
    );
    
    return signal;
  }
  
  /**
   * Calculate Anomaly Pointer components (Ablation Study: 40% volume, 30% spread, 30% price accel)
   */
  private calculateAnomalyComponents(
    prices: number[],
    volumes: number[]
  ): { pointer: number; volumeSpike: number; spreadExpansion: number; priceAcceleration: number } {
    if (prices.length < 10 || volumes.length < 10) {
      return { pointer: 0, volumeSpike: 0, spreadExpansion: 0, priceAcceleration: 0 };
    }

    // Volume spike (recent volume vs 20-period average)
    const recentVolume = volumes.slice(-1)[0];
    const avgVolume = volumes.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, volumes.length);
    const volumeSpike = avgVolume > 0 ? Math.min(1.0, (recentVolume - avgVolume) / avgVolume) : 0;

    // Spread expansion (recent price range vs average range)
    const recentPrices = prices.slice(-5);
    const recentSpread = Math.max(...recentPrices) - Math.min(...recentPrices);
    const avgPrices = prices.slice(-20);
    const avgSpread = (Math.max(...avgPrices) - Math.min(...avgPrices)) / 4; // /4 to normalize to 5-period chunks
    const spreadExpansion = avgSpread > 0 ? Math.min(1.0, (recentSpread - avgSpread) / avgSpread) : 0;

    // Price acceleration (second derivative)
    const p1 = prices[prices.length - 1];
    const p2 = prices[prices.length - 2];
    const p3 = prices[prices.length - 3];
    const velocity1 = p1 - p2;
    const velocity2 = p2 - p3;
    const acceleration = Math.abs(velocity1 - velocity2);
    const avgPrice = prices.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, prices.length);
    const priceAcceleration = avgPrice > 0 ? Math.min(1.0, acceleration / (avgPrice * 0.01)) : 0;

    // Weighted combination (Ablation Study)
    const pointer = 0.4 * volumeSpike + 0.3 * spreadExpansion + 0.3 * priceAcceleration;

    return { pointer, volumeSpike, spreadExpansion, priceAcceleration };
  }

  /**
   * Interpret all metrics to generate final signal
   */
  private interpretSignal(
    timestamp: number,
    curvature: number,
    curvatureDirection: 'UPWARD' | 'DOWNWARD' | 'NEUTRAL',
    lighthouse: LighthouseState,
    coherence: CoherenceMetrics,
    ftcpDetected: boolean,
    goldenRatioScore: number,
    anomalyPointer: number,
    provenance: DataProvenance,
  ): QGITASignal {
    let signalType: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
    let reasoning = '';
    
    // BUY Signal Conditions:
    // - FTCP detected with positive curvature (upward bend)
    // - Lighthouse Event confirmed (L > threshold)
    // - Confidence > 60%
    // - Cross-scale coherence increasing (self-similar uptrend)
    
    if (lighthouse.isLHE && ftcpDetected) {
      if (curvatureDirection === 'UPWARD' && coherence.crossScaleCoherence > 0.6) {
        signalType = 'BUY';
        reasoning = `🟢 BUY: FTCP detected with upward curvature (${curvature.toFixed(4)}). ` +
                   `Lighthouse Event confirmed (L=${lighthouse.L.toFixed(3)}). ` +
                   `Cross-scale coherence strong (${(coherence.crossScaleCoherence * 100).toFixed(1)}%). ` +
                   `Golden ratio timing: ${(goldenRatioScore * 100).toFixed(1)}%.`;
      } 
      // SELL Signal Conditions:
      // - FTCP detected with negative curvature (downward bend)
      // - Lighthouse Event confirmed
      // - Confidence > 60%
      // - Linear coherence breaking down (trend exhaustion)
      else if (curvatureDirection === 'DOWNWARD' && coherence.linearCoherence < 0.5) {
        signalType = 'SELL';
        reasoning = `🔴 SELL: FTCP detected with downward curvature (${curvature.toFixed(4)}). ` +
                   `Lighthouse Event confirmed (L=${lighthouse.L.toFixed(3)}). ` +
                   `Linear coherence breakdown (${(coherence.linearCoherence * 100).toFixed(1)}%). ` +
                   `Trend exhaustion detected.`;
      } else {
        signalType = 'HOLD';
        reasoning = `⚪ HOLD: Lighthouse Event detected but conditions unclear. ` +
                   `Curvature: ${curvatureDirection}, ` +
                   `Linear coherence: ${(coherence.linearCoherence * 100).toFixed(1)}%, ` +
                   `Cross-scale: ${(coherence.crossScaleCoherence * 100).toFixed(1)}%.`;
      }
    } else {
      signalType = 'HOLD';
      reasoning = `⚪ HOLD: No Lighthouse Event. ` +
                 `FTCP: ${ftcpDetected ? 'Yes' : 'No'}, ` +
                 `L: ${lighthouse.L.toFixed(3)}, ` +
                 `Threshold: ${lighthouse.threshold.toFixed(3)}.`;
    }
    
    // Calculate overall confidence
    const confidence = this.calculateConfidence(
      lighthouse,
      coherence,
      goldenRatioScore,
      ftcpDetected
    );
    
    // Determine signal tier
    const tier = this.determineSignalTier(confidence);
    
    return {
      ...asDerivedProvenance(provenance),
      timestamp,
      signalType,
      confidence,
      tier,
      curvature,
      curvatureDirection,
      lighthouse,
      coherence,
      ftcpDetected,
      goldenRatioScore,
      anomalyPointer,
      reasoning,
      observedSampleCount: this.priceHistory.length,
    };
  }
  
  /**
   * Calculate overall confidence score (0-100%)
   */
  private calculateConfidence(
    lighthouse: LighthouseState,
    coherence: CoherenceMetrics,
    goldenRatioScore: number,
    ftcpDetected: boolean
  ): number {
    let confidence = 0;
    
    // Lighthouse contribution (40%)
    confidence += lighthouse.confidence * 0.4;
    
    // Coherence metrics contribution (30%)
    const avgCoherence = (
      coherence.linearCoherence +
      coherence.nonlinearCoherence +
      coherence.crossScaleCoherence
    ) / 3;
    confidence += avgCoherence * 100 * 0.3;
    
    // Golden ratio timing (20%)
    confidence += goldenRatioScore * 100 * 0.2;
    
    // FTCP detection bonus (10%)
    if (ftcpDetected) {
      confidence += 10;
    }
    
    return Math.min(100, Math.max(0, confidence));
  }
  
  /**
   * Determine signal tier based on confidence
   */
  private determineSignalTier(confidence: number): 1 | 2 | 3 {
    if (confidence >= this.config.tier1Threshold) return 1;
    if (confidence >= this.config.tier2Threshold) return 2;
    return 3;
  }
  
  /**
   * Determine direction of curvature
   */
  private determineCurvatureDirection(curvature: number): 'UPWARD' | 'DOWNWARD' | 'NEUTRAL' {
    if (Math.abs(curvature) < 0.01) return 'NEUTRAL';
    
    // Check recent price trend to determine if curvature is upward or downward
    if (this.priceHistory.length < 3) return 'NEUTRAL';
    
    const recent = this.priceHistory.slice(-3);
    const trend = recent[2] - recent[0];
    
    if (trend > 0 && curvature > 0) return 'UPWARD';
    if (trend < 0 && curvature > 0) return 'DOWNWARD';
    if (trend > 0 && curvature < 0) return 'DOWNWARD';
    if (trend < 0 && curvature < 0) return 'UPWARD';
    
    return 'NEUTRAL';
  }
  
  /**
   * Get recommended position size based on signal tier
   */
  getPositionSizeMultiplier(tier: 1 | 2 | 3): number {
    switch (tier) {
      case 1: return this.config.tier1PositionMultiplier;
      case 2: return this.config.tier2PositionMultiplier;
      case 3: return this.config.tier3PositionMultiplier;
    }
  }
  
  /**
   * Reset all detection engines
   */
  reset() {
    this.ftcpDetector.reset();
    this.lighthouse.reset();
    this.priceHistory = [];
    this.volumeHistory = [];
    this.timestampHistory = [];
  }
}

// Singleton instance
export const qgitaSignalGenerator = new QGITASignalGenerator();
