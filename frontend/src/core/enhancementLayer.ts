/**
 * 🌈 ENHANCEMENT LAYER - Unified Enhancement Integration
 * 
 * Combines all enhancement systems into a single interface:
 * - Rainbow Bridge (emotional frequency mapping)
 * - Synchronicity Decoder (pattern detection)
 * - Stargate Grid (global resonance network)
 * - Gaia Lattice (carrier wave dynamics)
 */

import { unifiedBus, type SystemState } from './unifiedBus';
import { temporalLadder } from './temporalLadder';
import { synchronicityDecoder, SyncState } from './synchronicityDecoder';
import { stargateGrid, GridState } from './stargateGrid';
import { gaiaLatticeEngine, LatticeState } from './gaiaLatticeEngine';
import { RainbowBridge } from './rainbowBridge';

const rainbowBridgeInstance = new RainbowBridge();

// Prime tier bonuses
const PRIME_TIER_BONUS: Record<string, number> = {
  'Heart Prime': 0.05,
  'Crown Prime': 0.06,
  'Third-Eye Prime': 0.05,
  'Gaia Tier': 0.03,
  'Social Prime': 0.03,
  'Visionary Tier': 0.03,
  'Root Harmonic': 0.02,
  'Root Prime': 0.02,
  'Sacral Tier': 0.02,
};

// Shadow tier penalties
const SHADOW_TIER_PENALTIES: Record<string, number> = {
  'Root Shadow': 0.05,
  'Sacral Shadow': 0.04,
  'Heart Shadow': 0.04,
  'Root Collapse': 0.06,
  'Sacral Collapse': 0.05,
};

// Band modifiers
const BAND_MODIFIERS: Record<string, number> = {
  survival: -0.04,
  growth: 0.02,
  branches: 0.03,
  crown: 0.04,
  radiance: 0.05,
};

export interface EnhancementResult {
  tradingModifier: number;
  emotionalState: string;
  emotionalFrequency: number;
  cyclePhase: string;
  synchronicityBoost: number;
  gridCoherence: number;
  activeNode: string;
  leylineActivity: number;
  latticePhase: string;
  carrierStrength: number;
  confidence: number;
  reasons: string[];
}

export class EnhancementLayer {
  private registered = false;
  private lastResult: EnhancementResult | null = null;
  
  constructor() {}
  
  register(): void {
    if (this.registered) return;
    
    // Register subsystems
    synchronicityDecoder.register();
    stargateGrid.register();
    gaiaLatticeEngine.register();
    
    temporalLadder.registerSystem('enhancement-layer');
    
    // Start heartbeat
    setInterval(() => {
      temporalLadder.heartbeat('enhancement-layer', this.lastResult?.confidence ?? 0.5);
    }, 2000);
    
    this.registered = true;
    console.log('🌈 Enhancement Layer registered');
  }
  
  getUnifiedModifier(
    lambdaValue: number,
    coherence: number,
    price: number,
    volume: number,
    volatility = 0,
    exchange = 'GLOBAL'
  ): EnhancementResult {
    const reasons: string[] = [];
    const modifiers: number[] = [];
    
    // 1. Rainbow Bridge - Emotional frequency mapping
    let emotionalState = 'Neutral';
    let emotionalFrequency = 440;
    let cyclePhase = 'LOVE';
    
    try {
      // RainbowBridge doesn't have a getState method - use map instead
      const rainbowState = rainbowBridgeInstance.map(lambdaValue, coherence);
      if (rainbowState) {
        emotionalState = rainbowState.phase || 'Neutral';
        emotionalFrequency = rainbowState.frequency || 440;
        cyclePhase = rainbowState.phase || 'LOVE';
        
        const rainbowMod = rainbowState.intensity > 0.7 ? 1.15 : rainbowState.intensity > 0.5 ? 1.05 : 0.95;
        modifiers.push(rainbowMod);
        
        if (rainbowMod > 1.1) {
          reasons.push(`🌈 Rainbow Bridge boost: ${emotionalState} @ ${emotionalFrequency}Hz`);
        } else if (rainbowMod < 0.95) {
          reasons.push(`🌈 Rainbow Bridge caution: ${emotionalState}`);
        }
      }
    } catch (e) {
      console.warn('Rainbow Bridge not available');
    }
    
    // 2. Synchronicity Decoder - Pattern detection
    synchronicityDecoder.addDataPoint(price, volume);
    const syncState = synchronicityDecoder.decode();
    const syncBoost = synchronicityDecoder.getSyncBoost();
    modifiers.push(syncBoost);
    
    if (syncState.overallSync > 0.6) {
      reasons.push(`🔮 Synchronicity: ${syncState.dominantPattern} pattern (${(syncState.overallSync * 100).toFixed(0)}%)`);
    }
    
    // 3. Stargate Grid - Global resonance
    const gridState = stargateGrid.update(coherence);
    const gridMod = stargateGrid.getModifier();
    modifiers.push(gridMod);
    
    if (gridState.overallCoherence > 0.6) {
      reasons.push(`🌐 Stargate: ${gridState.dominantNode} active @ ${gridState.dominantFrequency}Hz`);
    }
    
    // 4. Gaia Lattice - Carrier wave dynamics
    const latticeState = gaiaLatticeEngine.getState();
    if (latticeState.riskMod !== null) modifiers.push(latticeState.riskMod);
    
    if (latticeState.phase === 'GAIA_RESONANCE') {
      reasons.push(`🌍 Gaia Resonance: 432Hz healing field active`);
    } else if (latticeState.phase === 'CARRIER_ACTIVE') {
      reasons.push(`💜 528Hz Love carrier injected`);
    }
    
    // 5. Calculate tier bonuses/penalties based on emotional state
    const tier = this.determineTier(emotionalState, coherence);
    if (tier) {
      const bonus = PRIME_TIER_BONUS[tier];
      const penalty = SHADOW_TIER_PENALTIES[tier];
      
      if (bonus) {
        modifiers.push(1 + bonus);
        reasons.push(`💎 Prime tier ${tier}: +${(bonus * 100).toFixed(0)}% resonance`);
      } else if (penalty) {
        modifiers.push(Math.max(0.85, 1 - penalty));
        reasons.push(`⚫ Shadow tier ${tier}: -${(penalty * 100).toFixed(0)}%`);
      }
    }
    
    // Calculate final modifier
    const finalModifier = modifiers.reduce((a, b) => a * b, 1);
    const clampedModifier = Math.max(0.5, Math.min(2.0, finalModifier));
    
    // Calculate confidence
    const confidenceInputs = [syncState.overallSync, gridState.overallCoherence, coherence];
    if (latticeState.fieldPurity !== null) confidenceInputs.push(latticeState.fieldPurity);
    const confidence = confidenceInputs.reduce((sum, value) => sum + value, 0) / confidenceInputs.length;
    
    this.lastResult = {
      tradingModifier: clampedModifier,
      emotionalState,
      emotionalFrequency,
      cyclePhase,
      synchronicityBoost: syncBoost,
      gridCoherence: gridState.overallCoherence,
      activeNode: gridState.dominantNode,
      leylineActivity: gridState.leylines[0]?.activity ?? 0,
      latticePhase: latticeState.phase,
      carrierStrength: latticeState.carrierStrength,
      confidence,
      reasons
    };
    
    // Publish to UnifiedBus
    unifiedBus.publish({
      systemName: 'EnhancementLayer',
      timestamp: Date.now(),
      ready: true,
      coherence: confidence,
      confidence: clampedModifier - 0.5,
      signal: clampedModifier > 1.2 ? 'BUY' : clampedModifier < 0.8 ? 'SELL' : 'NEUTRAL',
      data: {
        modifier: clampedModifier,
        emotionalState,
        latticePhase: latticeState.phase,
        gridNode: gridState.dominantNode,
        syncPattern: syncState.dominantPattern
      }
    });
    
    return this.lastResult;
  }
  
  private determineTier(emotionalState: string, coherence: number): string | null {
    const state = emotionalState.toUpperCase();
    
    // Prime tiers (positive states + high coherence)
    if (coherence > 0.7) {
      if (['LOVE', 'JOY', 'PEACE', 'GRATITUDE'].includes(state)) return 'Heart Prime';
      if (['ENLIGHTENMENT', 'UNITY', 'TRANSCENDENCE'].includes(state)) return 'Crown Prime';
      if (['INSIGHT', 'CLARITY', 'VISION'].includes(state)) return 'Third-Eye Prime';
    }
    
    // Shadow tiers (negative states or low coherence)
    if (coherence < 0.3) {
      if (['FEAR', 'ANXIETY', 'PANIC'].includes(state)) return 'Root Shadow';
      if (['SHAME', 'GUILT'].includes(state)) return 'Sacral Shadow';
      if (['GRIEF', 'DESPAIR'].includes(state)) return 'Heart Shadow';
    }
    
    return null;
  }
  
  displayStatus(): string {
    if (!this.lastResult) {
      return '✨ ENHANCEMENTS | Awaiting data...';
    }
    
    const { tradingModifier, emotionalState, latticePhase, confidence } = this.lastResult;
    const modPct = ((tradingModifier - 1) * 100).toFixed(0);
    const sign = tradingModifier >= 1 ? '+' : '';
    
    return `✨ ENHANCEMENTS | ${emotionalState} | ${latticePhase} | ${sign}${modPct}% | Conf: ${(confidence * 100).toFixed(0)}%`;
  }
  
  getState(): EnhancementResult | null {
    return this.lastResult;
  }
}

export const enhancementLayer = new EnhancementLayer();
