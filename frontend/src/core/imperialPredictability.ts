/**
 * Imperial Predictability Engine
 * 
 * Combines cosmic synchronization with trading strategies for enhanced decision-making.
 * Ported from Python hnc_imperial_predictability.py
 */

import { unifiedBus, type SignalType } from './unifiedBus';
import { temporalLadder, SYSTEMS } from './temporalLadder';

// Cosmic phase enumeration
export enum CosmicPhase {
  DISTORTION = 'DISTORTION',   // 440 Hz dominance, avoid trading
  TRANSITION = 'TRANSITION',   // Mixed signals, reduce position
  HARMONIC = 'HARMONIC',       // Good alignment, normal trading
  COHERENCE = 'COHERENCE',     // Strong alignment, increase position
  UNITY = 'UNITY',             // Perfect sync, maximum position
}

// Imperial constants from Master Equation Tree
const PHI = (1 + Math.sqrt(5)) / 2; // Golden ratio ≈ 1.618
const SCHUMANN_BASE = 7.83;        // Earth resonance Hz
const LOVE_FREQUENCY = 528;         // DNA repair frequency
const UNITY_FREQUENCY = 963;        // Crown chakra frequency
const DISTORTION_FREQUENCY = 440;   // Artificial tuning (avoid)

// Cosmic calendar for December 2025 (special alignment dates)
export const COSMIC_CALENDAR: Record<string, { phase: CosmicPhase; torqueMultiplier: number; description: string }> = {
  '2025-12-01': { phase: CosmicPhase.TRANSITION, torqueMultiplier: 1.0, description: 'Month open - neutral' },
  '2025-12-04': { phase: CosmicPhase.HARMONIC, torqueMultiplier: 1.2, description: 'Mercury-Jupiter trine' },
  '2025-12-08': { phase: CosmicPhase.COHERENCE, torqueMultiplier: 1.4, description: 'Sun-Moon harmonic' },
  '2025-12-12': { phase: CosmicPhase.UNITY, torqueMultiplier: 1.618, description: '12/12 portal - PHI alignment' },
  '2025-12-15': { phase: CosmicPhase.HARMONIC, torqueMultiplier: 1.3, description: 'Winter solstice approach' },
  '2025-12-21': { phase: CosmicPhase.UNITY, torqueMultiplier: 1.8, description: 'Winter Solstice - maximum alignment' },
  '2025-12-25': { phase: CosmicPhase.COHERENCE, torqueMultiplier: 1.5, description: 'Golden cross alignment' },
  '2025-12-31': { phase: CosmicPhase.TRANSITION, torqueMultiplier: 1.1, description: 'Year close - transition' },
};

// Lunar phase influence (0-1 scale)
const LUNAR_PHASES = ['NEW', 'WAXING_CRESCENT', 'FIRST_QUARTER', 'WAXING_GIBBOUS', 'FULL', 'WANING_GIBBOUS', 'LAST_QUARTER', 'WANING_CRESCENT'] as const;
type LunarPhase = typeof LUNAR_PHASES[number];

export interface CosmicState {
  timestamp: number;
  phase: CosmicPhase;
  torqueMultiplier: number;
  lunarPhase: LunarPhase;
  lunarInfluence: number;
  planetaryAlignment: number;
  imperialYield: number;
  schumannResonance: number | null;
  frequencyRatio: number;
  positionMultiplier: number;
  shouldTrade: boolean;
  description: string;
}

export interface ImperialPrediction {
  symbol: string;
  probability: number;
  confidence: number;
  cosmicPhase: CosmicPhase;
  torqueMultiplier: number;
  positionModifier: number;
  forecasts: {
    h1: number;  // Hour +1 probability
    h4: number;  // Hour +4 probability
    h24: number; // Hour +24 probability
  };
}

/**
 * CosmicStateEngine - Computes real-time cosmic state
 */
class CosmicStateEngine {
  private lastState: CosmicState | null = null;

  /**
   * Get current lunar phase (simplified calculation)
   */
  private getLunarPhase(date: Date): { phase: LunarPhase; influence: number } {
    // Lunar cycle is ~29.5 days
    const lunarCycle = 29.53;
    const knownNewMoon = new Date('2025-01-29').getTime();
    const daysSinceNewMoon = (date.getTime() - knownNewMoon) / (1000 * 60 * 60 * 24);
    const phasePosition = (daysSinceNewMoon % lunarCycle) / lunarCycle;
    
    const phaseIndex = Math.floor(phasePosition * 8);
    const phase = LUNAR_PHASES[phaseIndex];
    
    // Influence is highest at full moon (0.5 in cycle)
    const influence = Math.sin(phasePosition * Math.PI * 2) * 0.5 + 0.5;
    
    return { phase, influence };
  }

  /**
   * Calculate planetary alignment (simplified)
   * Based on day of year and golden ratio harmonics
   */
  private calculatePlanetaryAlignment(date: Date): number {
    const dayOfYear = Math.floor((date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / (1000 * 60 * 60 * 24));
    const yearProgress = dayOfYear / 365;
    
    // Multiple harmonic cycles
    const jupiterCycle = Math.sin(yearProgress * 2 * Math.PI / 11.86);  // Jupiter: 11.86 years
    const saturnCycle = Math.sin(yearProgress * 2 * Math.PI / 29.5);   // Saturn: 29.5 years
    const venusCycle = Math.sin(yearProgress * 2 * Math.PI * 1.6);     // Venus: ~225 days
    
    // Weighted average with PHI
    return (jupiterCycle * 0.4 + saturnCycle * 0.2 + venusCycle * 0.4 + 1) / 2;
  }

  /**
   * Imperial Yield Equation: E = (J³ × C² × R × T²) / D × 10³³
   * Simplified version based on coherence metrics
   */
  private computeImperialYield(
    coherence: number,
    planetaryAlignment: number,
    lunarInfluence: number,
    torque: number
  ): number {
    const J = coherence; // Jupiter influence (coherence proxy)
    const C = planetaryAlignment; // Cosmic alignment
    const R = lunarInfluence; // Lunar resonance
    const T = torque; // Torque multiplier
    const D = 1 + (1 - coherence) * 0.5; // Distortion factor
    
    return (Math.pow(J, 3) * Math.pow(C, 2) * R * Math.pow(T, 2)) / D;
  }

  /**
   * Compute frequency ratio (528/440 alignment)
   * Higher = more aligned with love frequency
   */
  private computeFrequencyRatio(coherence: number, alignment: number): number {
    const base = LOVE_FREQUENCY / DISTORTION_FREQUENCY; // ≈ 1.2
    const boost = coherence * alignment * (PHI - 1);
    return Math.min(base + boost, PHI);
  }

  /**
   * Determine cosmic phase from metrics
   */
  private determinePhase(
    coherence: number,
    alignment: number,
    calendarPhase?: CosmicPhase
  ): CosmicPhase {
    // Calendar override if special date
    if (calendarPhase) return calendarPhase;
    
    const score = coherence * 0.6 + alignment * 0.4;
    
    if (score >= 0.85) return CosmicPhase.UNITY;
    if (score >= 0.70) return CosmicPhase.COHERENCE;
    if (score >= 0.50) return CosmicPhase.HARMONIC;
    if (score >= 0.30) return CosmicPhase.TRANSITION;
    return CosmicPhase.DISTORTION;
  }

  /**
   * Compute position multiplier from cosmic phase
   */
  private getPositionMultiplier(phase: CosmicPhase, torque: number): number {
    const baseMultipliers: Record<CosmicPhase, number> = {
      [CosmicPhase.UNITY]: 1.5,
      [CosmicPhase.COHERENCE]: 1.25,
      [CosmicPhase.HARMONIC]: 1.0,
      [CosmicPhase.TRANSITION]: 0.75,
      [CosmicPhase.DISTORTION]: 0.5,
    };
    
    return baseMultipliers[phase] * torque;
  }

  /**
   * Compute complete cosmic state
   */
  computeState(coherence: number = 0.7): CosmicState {
    const now = new Date();
    const dateKey = now.toISOString().split('T')[0];
    
    // Check cosmic calendar for special dates
    const calendarEntry = COSMIC_CALENDAR[dateKey];
    const calendarPhase = calendarEntry?.phase;
    const baseTorque = calendarEntry?.torqueMultiplier ?? 1.0;
    const description = calendarEntry?.description ?? 'Standard trading day';
    
    // Compute all metrics
    const lunar = this.getLunarPhase(now);
    const planetaryAlignment = this.calculatePlanetaryAlignment(now);
    
    // Compute torque with lunar modulation
    const torqueMultiplier = baseTorque * (1 + lunar.influence * 0.1);
    
    // Determine phase
    const phase = this.determinePhase(coherence, planetaryAlignment, calendarPhase);
    
    // Compute imperial yield
    const imperialYield = this.computeImperialYield(
      coherence,
      planetaryAlignment,
      lunar.influence,
      torqueMultiplier
    );
    
    // Frequency ratio
    const frequencyRatio = this.computeFrequencyRatio(coherence, planetaryAlignment);
    
    // Position multiplier
    const positionMultiplier = this.getPositionMultiplier(phase, torqueMultiplier);
    
    // Should trade decision
    const shouldTrade = phase !== CosmicPhase.DISTORTION && coherence >= 0.5;
    
    // No live Schumann reading is wired here.
    const schumannResonance = null;
    
    const state: CosmicState = {
      timestamp: now.getTime(),
      phase,
      torqueMultiplier,
      lunarPhase: lunar.phase,
      lunarInfluence: lunar.influence,
      planetaryAlignment,
      imperialYield,
      schumannResonance,
      frequencyRatio,
      positionMultiplier,
      shouldTrade,
      description,
    };
    
    this.lastState = state;
    return state;
  }

  getLastState(): CosmicState | null {
    return this.lastState;
  }
}

/**
 * PredictabilityEngine - Multi-timeframe probability forecasts
 */
class PredictabilityEngine {
  private cosmicEngine: CosmicStateEngine;

  constructor() {
    this.cosmicEngine = new CosmicStateEngine();
  }

  /**
   * Get prediction for a symbol
   */
  getPrediction(
    symbol: string,
    coherence: number,
    currentMomentum: number = 0
  ): ImperialPrediction {
    const cosmicState = this.cosmicEngine.computeState(coherence);
    
    // Base probability from coherence and cosmic alignment
    const baseProbability = (coherence * 0.5 + cosmicState.planetaryAlignment * 0.3 + cosmicState.lunarInfluence * 0.2);
    
    // Momentum adjustment
    const momentumFactor = Math.tanh(currentMomentum * 5) * 0.2;
    
    // Multi-timeframe forecasts
    const h1 = Math.max(0, Math.min(1, baseProbability + momentumFactor * cosmicState.torqueMultiplier));
    const h4 = Math.max(0, Math.min(1, baseProbability * 0.9 + cosmicState.imperialYield * 0.1));
    const h24 = Math.max(0, Math.min(1, baseProbability * 0.8 + cosmicState.frequencyRatio * 0.2 / PHI));
    
    // Confidence from phase
    const phaseConfidence: Record<CosmicPhase, number> = {
      [CosmicPhase.UNITY]: 0.95,
      [CosmicPhase.COHERENCE]: 0.85,
      [CosmicPhase.HARMONIC]: 0.70,
      [CosmicPhase.TRANSITION]: 0.50,
      [CosmicPhase.DISTORTION]: 0.30,
    };
    
    return {
      symbol,
      probability: h1,
      confidence: phaseConfidence[cosmicState.phase],
      cosmicPhase: cosmicState.phase,
      torqueMultiplier: cosmicState.torqueMultiplier,
      positionModifier: cosmicState.positionMultiplier,
      forecasts: { h1, h4, h24 },
    };
  }

  /**
   * Get cosmic state directly
   */
  getCosmicState(coherence: number = 0.7): CosmicState {
    return this.cosmicEngine.computeState(coherence);
  }

  /**
   * Should trade based on imperial conditions
   */
  shouldTradeImperial(coherence: number): boolean {
    const state = this.cosmicEngine.computeState(coherence);
    return state.shouldTrade;
  }

  /**
   * Get position size modifier
   */
  getPositionModifier(coherence: number): number {
    const state = this.cosmicEngine.computeState(coherence);
    return state.positionMultiplier;
  }
}

/**
 * ImperialTradingIntegration - Connects cosmic state with trading
 */
export class ImperialTradingIntegration {
  private engine: PredictabilityEngine;
  private systemName = 'imperial-predictability';

  constructor() {
    this.engine = new PredictabilityEngine();
  }

  /**
   * Run imperial cycle and publish to bus
   */
  runCycle(coherence: number, symbol: string = 'BTCUSDT', momentum: number = 0): {
    cosmicState: CosmicState;
    prediction: ImperialPrediction;
  } {
    const cosmicState = this.engine.getCosmicState(coherence);
    const prediction = this.engine.getPrediction(symbol, coherence, momentum);
    
    // Publish to bus
    this.publishToUnifiedBus(cosmicState, prediction);
    
    // Register with Temporal Ladder
    temporalLadder.registerSystem(this.systemName as any);
    temporalLadder.heartbeat(this.systemName as any, cosmicState.planetaryAlignment);
    
    // Broadcast cosmic event
    temporalLadder.broadcast(
      this.systemName as any,
      'COSMIC_STATE_UPDATE',
      {
        phase: cosmicState.phase,
        torque: cosmicState.torqueMultiplier,
        shouldTrade: cosmicState.shouldTrade,
      }
    );
    
    return { cosmicState, prediction };
  }

  /**
   * Publish to UnifiedBus
   */
  private publishToUnifiedBus(state: CosmicState, prediction: ImperialPrediction): void {
    let signal: SignalType = 'NEUTRAL';
    if (prediction.probability > 0.65 && state.shouldTrade) {
      signal = 'BUY';
    } else if (prediction.probability < 0.35 && state.shouldTrade) {
      signal = 'SELL';
    }

    const phaseEmoji = {
      [CosmicPhase.UNITY]: '🌈',
      [CosmicPhase.COHERENCE]: '🔵',
      [CosmicPhase.HARMONIC]: '🟢',
      [CosmicPhase.TRANSITION]: '🟡',
      [CosmicPhase.DISTORTION]: '🔴',
    }[state.phase];

    console.log(
      `[Imperial] ${phaseEmoji} ${state.phase} | ` +
      `Torque: ${state.torqueMultiplier.toFixed(2)} | ` +
      `Lunar: ${state.lunarPhase} (${(state.lunarInfluence * 100).toFixed(0)}%) | ` +
      `Yield: ${state.imperialYield.toFixed(3)} | ` +
      `Trade: ${state.shouldTrade ? '✅' : '❌'}`
    );

    unifiedBus.publish({
      systemName: 'ImperialPredictability',
      timestamp: state.timestamp,
      ready: true,
      coherence: state.planetaryAlignment,
      confidence: prediction.confidence,
      signal,
      data: {
        cosmicState: state,
        prediction,
        phase: state.phase,
        torqueMultiplier: state.torqueMultiplier,
        lunarPhase: state.lunarPhase,
        lunarInfluence: state.lunarInfluence,
        imperialYield: state.imperialYield,
        positionMultiplier: state.positionMultiplier,
        shouldTrade: state.shouldTrade,
        forecasts: prediction.forecasts,
      },
    });
  }

  /**
   * Get cosmic status for UI
   */
  getCosmicStatus(coherence: number = 0.7): CosmicState {
    return this.engine.getCosmicState(coherence);
  }

  /**
   * Should trade based on imperial conditions
   */
  shouldTrade(coherence: number): boolean {
    return this.engine.shouldTradeImperial(coherence);
  }

  /**
   * Get position modifier
   */
  getPositionModifier(coherence: number): number {
    return this.engine.getPositionModifier(coherence);
  }
}

// Singleton instance
export const imperialPredictability = new ImperialTradingIntegration();
