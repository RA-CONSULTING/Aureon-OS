/**
 * MASTER EQUATION — Harmonic Nexus Core (HNC) Implementation
 * 
 * Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α·tanh[g·Λ̄_Δt(t)] + β·Λ(t-τ)
 * 
 * Level 5 - Composite Reality Field:
 * - Term 1: Substrate (harmonic superposition of natural modes)
 * - Term 2: Observer feedback (nonlinear saturation via tanh)
 * - Term 3: Causal Echo (delayed self-reference - Lighthouse Echo)
 * 
 * Coherence Metric: Γ = 1 - σ/μ (target Γ ≥ 0.945)
 * 
 * TEMPORAL LADDER INTEGRATION: Orchestrates all systems with hive-mind coordination
 */

import { AurisNodes, type MarketSnapshot } from './aurisNodes';
import { stargateLayer, type StargateInfluence } from './stargateLattice';
import { earthAureonBridge, type EarthFieldInfluence } from './earthAureonBridge';
import { nexusLiveFeedBridge, type NexusInfluence } from './nexusLiveFeedBridge';
import type { NexusBridgeConfig } from './nexusLiveFeedBridge';
import type { SimpleEarthStreams } from '../lib/earth-streams';
import { temporalLadder, SYSTEMS } from './temporalLadder';

// HNC Configuration Constants
const HNC_CONFIG = {
  // Base frequencies (Hz) - harmonic scaffold
  frequencies: [7.83, 14.3, 20.8, 33.8, 528, 963], // Schumann harmonics + Love + Unity
  
  // Frequency weights (normalized contributions)
  weights: [0.25, 0.15, 0.10, 0.05, 0.30, 0.15], // 528 Hz dominant
  
  // Observer feedback parameters
  alpha: 0.35,      // Observer gain (feedback strength)
  g: 2.5,           // Nonlinear gain for tanh saturation
  deltaT: 5,        // Integration window (number of samples for moving average)
  
  // Causal Echo (Lighthouse) parameters  
  beta: 0.25,       // Echo gain (memory strength)
  tau: 10,          // Delay in samples (creates frequency comb at 1/τ)
  
  // Coherence target
  gammaTarget: 0.945, // Minimum coherence for stable timeline
  
  // Harmonic interference
  parasiteFreq: 440,   // Mars distortion frequency
  gaiaFreq: 528,       // Earth love frequency
  rho: 440 / 528,      // Interference ratio ≈ 0.833 (dissonant)
};

export type LambdaState = {
  lambda: number;
  coherence: number;
  substrate: number;
  observer: number;
  echo: number;
  dominantNode: string;
  nodeResponses: Record<string, number>;
  
  // HNC-specific outputs
  harmonicComponents: number[];  // Per-frequency contributions
  observerResponse: number;      // tanh output
  echoSignal: number;           // Delayed feedback
  coherenceLinear: number;      // Raw Γ before boosts
  coherenceNonlinear: number;   // After tanh stabilization
  coherencePhi: number;         // Golden ratio alignment
  qualityFactor: number;        // Q = stability metric
  effectiveGain: number;        // G_eff = α + β
  
  // External influences
  stargateInfluence?: StargateInfluence;
  earthFieldInfluence?: EarthFieldInfluence;
  nexusInfluence?: NexusInfluence;
};

export class MasterEquation {
  private history: number[] = [];
  private maxHistory = 100;
  private userLocation: { lat: number; lng: number } | null = null;
  private celestialBoost: number = 0;
  private schumannBoost: number = 0;
  private earthStreams: SimpleEarthStreams | null = null;
  private regionId: string | null = null;
  private nexusEnabled = true;
  
  // Time tracking for harmonic oscillation
  private stepCount = 0;
  
  constructor() {
    // Register with Temporal Ladder as primary orchestrator
    temporalLadder.registerSystem(SYSTEMS.MASTER_EQUATION);
  }
  
  setUserLocation(lat: number, lng: number, celestialBoost: number = 0, schumannBoost: number = 0) {
    this.userLocation = { lat, lng };
    this.celestialBoost = celestialBoost;
    this.schumannBoost = schumannBoost;
  }

  setSchumannBoost(schumannBoost: number) {
    if (!Number.isFinite(schumannBoost)) throw new Error('SCHUMANN_BOOST_MUST_BE_FINITE');
    this.schumannBoost = schumannBoost;
  }

  setEarthStreams(streams: SimpleEarthStreams, regionId?: string) {
    this.earthStreams = streams;
    if (regionId) this.regionId = regionId;
  }

  enableEarthSync(enable: boolean = true) {
    earthAureonBridge.setConfig({ enableEarthSync: enable });
  }

  enableNexusSync(enable: boolean = true, configOverrides?: Partial<NexusBridgeConfig>) {
    this.nexusEnabled = enable;
    nexusLiveFeedBridge.setConfig({ enable, ...(configOverrides || {}) });
  }
  
  /**
   * LEVEL 2 - SUBSTRATE: Harmonic Base
   * Λ_base(t) = Σ wᵢ sin(2πfᵢt + φᵢ)
   */
  private computeSubstrate(snapshot: MarketSnapshot, nodeResponses: Record<string, number>): {
    substrate: number;
    harmonicComponents: number[];
  } {
    const t = this.stepCount;
    const harmonicComponents: number[] = [];
    let harmonicSum = 0;
    
    // Compute harmonic superposition
    for (let i = 0; i < HNC_CONFIG.frequencies.length; i++) {
      const f = HNC_CONFIG.frequencies[i];
      const w = HNC_CONFIG.weights[i];
      
      // Phase offset from market volatility (creates variation)
      const phi = (snapshot.volatility || 0) * Math.PI;
      
      // Normalized time (scale frequencies to sample rate)
      const normalizedF = f / 1000; // Scale down for discrete steps
      
      // Harmonic component
      const component = w * Math.sin(2 * Math.PI * normalizedF * t + phi);
      harmonicComponents.push(component);
      harmonicSum += component;
    }
    
    // Combine with node responses (market-derived weights)
    const nodeAvg = Object.values(nodeResponses).reduce((a, b) => a + b, 0) / 
                    Object.keys(nodeResponses).length;
    
    // Substrate = harmonic scaffold + market modulation
    const substrate = (harmonicSum + nodeAvg) / 2;
    
    return { substrate, harmonicComponents };
  }
  
  /**
   * LEVEL 4 - OBSERVER FEEDBACK: Integration & Nonlinearity
   * Λ̄_Δt(t) = (1/Δt) ∫ Λ(t') dt' over [t-Δt, t]
   * R_obs(t) = tanh[g · Λ̄_Δt(t)]
   */
  private computeObserver(): { observer: number; observerResponse: number } {
    if (this.history.length < HNC_CONFIG.deltaT) {
      return { observer: 0, observerResponse: 0 };
    }
    
    // Moving average (integration over Δt window)
    const recentHistory = this.history.slice(-HNC_CONFIG.deltaT);
    const lambdaAvg = recentHistory.reduce((a, b) => a + b, 0) / recentHistory.length;
    
    // Nonlinear saturation: tanh(g · Λ̄)
    // This prevents runaway amplification and ensures bounded output [-1, 1]
    const observerResponse = Math.tanh(HNC_CONFIG.g * lambdaAvg);
    
    // Observer contribution with gain α
    const observer = HNC_CONFIG.alpha * observerResponse;
    
    return { observer, observerResponse };
  }
  
  /**
   * LEVEL 3 - CAUSAL ECHO: Memory Loop (Lighthouse Echo)
   * L_loop(t) = Λ(t - τ)
   * Creates frequency comb at multiples of 1/τ
   */
  private computeEcho(): { echo: number; echoSignal: number } {
    if (this.history.length < HNC_CONFIG.tau) {
      return { echo: 0, echoSignal: 0 };
    }
    
    // Delayed self-reference: Λ(t - τ)
    const echoSignal = this.history[this.history.length - HNC_CONFIG.tau];
    
    // Echo contribution with gain β
    const echo = HNC_CONFIG.beta * echoSignal;
    
    return { echo, echoSignal };
  }
  
  /**
   * COHERENCE METRIC: Γ = 1 - σ/μ
   * Measures how well the field correlates with itself
   */
  private computeCoherence(nodeResponses: Record<string, number>): {
    coherenceLinear: number;
    coherenceNonlinear: number;
    coherencePhi: number;
    qualityFactor: number;
  } {
    const responses = Object.values(nodeResponses);
    
    // Mean (μ) and standard deviation (σ)
    const mu = responses.reduce((a, b) => a + b, 0) / responses.length;
    const variance = responses.reduce((sum, r) => sum + Math.pow(r - mu, 2), 0) / responses.length;
    const sigma = Math.sqrt(variance);
    
    // Linear coherence: Γ = 1 - σ/μ (avoid division by zero)
    const coherenceLinear = mu !== 0 
      ? Math.max(0, Math.min(1, 1 - Math.abs(sigma / mu)))
      : 0.5;
    
    // Nonlinear coherence (stabilized through observer feedback)
    // Apply tanh to prevent extreme values
    const coherenceNonlinear = (1 + Math.tanh(2 * (coherenceLinear - 0.5))) / 2;
    
    // Golden ratio alignment (φ = 1.618...)
    const phi = 1.618033988749895;
    const goldenCheck = Math.abs((coherenceLinear * phi) % 1);
    const coherencePhi = 1 - Math.min(goldenCheck, 1 - goldenCheck) * 2;
    
    // Quality factor Q = stability of the resonance
    const effectiveGain = HNC_CONFIG.alpha + HNC_CONFIG.beta;
    const qualityFactor = effectiveGain < 1 
      ? 1 / (1 - effectiveGain) 
      : Math.min(10, effectiveGain * 2); // Bounded Q for high gains
    
    return { coherenceLinear, coherenceNonlinear, coherencePhi, qualityFactor };
  }
  
  async step(snapshot: MarketSnapshot): Promise<LambdaState> {
    this.stepCount++;
    
    // Compute node responses from 9 Auris nodes
    const nodeResponses: Record<string, number> = {};
    let dominantNode = '';
    let maxResponse = -Infinity;
    
    Object.entries(AurisNodes).forEach(([name, node]) => {
      const response = node.compute(snapshot) * node.weight;
      nodeResponses[name] = response;
      
      if (response > maxResponse) {
        maxResponse = response;
        dominantNode = name;
      }
    });
    
    // LEVEL 2: Substrate (harmonic superposition)
    const { substrate, harmonicComponents } = this.computeSubstrate(snapshot, nodeResponses);
    
    // LEVEL 4: Observer feedback (tanh nonlinearity)
    const { observer, observerResponse } = this.computeObserver();
    
    // LEVEL 3: Causal Echo (delayed self-reference)
    const { echo, echoSignal } = this.computeEcho();
    
    // LEVEL 5: Master Equation
    // Λ(t) = Substrate + Observer + Echo
    const lambda = substrate + observer + echo;
    
    // Update history for next iteration
    this.history.push(lambda);
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }
    
    // Compute coherence metrics
    const { coherenceLinear, coherenceNonlinear, coherencePhi, qualityFactor } = 
      this.computeCoherence(nodeResponses);
    
    // Start with nonlinear coherence as base
    let coherence = coherenceNonlinear;
    
    // Effective gain for stability analysis
    const effectiveGain = HNC_CONFIG.alpha + HNC_CONFIG.beta;
    
    // Apply Earth Field influence
    let earthFieldInfluence: EarthFieldInfluence | undefined;
    try {
      earthFieldInfluence = await earthAureonBridge.getEarthInfluence(
        this.earthStreams || undefined,
        this.regionId || undefined
      );
      coherence = Math.min(1, coherence + earthFieldInfluence.combinedBoost);
    } catch (error) {
      console.warn('Earth field sync error (non-critical):', error);
    }
    
    // Apply Nexus influence
    let nexusInfluence: NexusInfluence | undefined;
    if (this.nexusEnabled) {
      try {
        nexusInfluence = await nexusLiveFeedBridge.poll();
        coherence = Math.min(1, Math.max(0, coherence + nexusInfluence.compositeBoost));
      } catch (error) {
        console.warn('Nexus live feed error (non-critical):', error);
      }
    }

    // Apply Stargate Lattice influence
    let stargateInfluence: StargateInfluence | undefined;
    if (this.userLocation) {
      stargateInfluence = stargateLayer.getInfluence(
        this.userLocation.lat,
        this.userLocation.lng,
        this.celestialBoost
      );
      const totalBoost = stargateInfluence.coherenceModifier + this.schumannBoost;
      coherence = Math.min(1, coherence + totalBoost);
    } else if (this.schumannBoost > 0) {
      coherence = Math.min(1, coherence + this.schumannBoost);
    }
    
    return {
      lambda,
      coherence,
      substrate,
      observer,
      echo,
      dominantNode,
      nodeResponses,
      
      // HNC-specific outputs
      harmonicComponents,
      observerResponse,
      echoSignal,
      coherenceLinear,
      coherenceNonlinear,
      coherencePhi,
      qualityFactor,
      effectiveGain,
      
      stargateInfluence,
      earthFieldInfluence,
      nexusInfluence,
    };
  }
  
  /**
   * Get HNC configuration for external reference
   */
  getConfig() {
    return { ...HNC_CONFIG };
  }
  
  /**
   * Check if system is in stable attractor (locked timeline)
   */
  isLocked(): boolean {
    if (this.history.length < HNC_CONFIG.tau * 2) return false;
    
    // Check for periodicity in recent history (indicates limit cycle)
    const recent = this.history.slice(-HNC_CONFIG.tau * 2);
    const firstHalf = recent.slice(0, HNC_CONFIG.tau);
    const secondHalf = recent.slice(HNC_CONFIG.tau);
    
    // Correlation between two periods
    let correlation = 0;
    for (let i = 0; i < HNC_CONFIG.tau; i++) {
      correlation += firstHalf[i] * secondHalf[i];
    }
    correlation /= HNC_CONFIG.tau;
    
    // High correlation indicates locked state
    return correlation > 0.8;
  }
  
  reset() {
    this.history = [];
    this.stepCount = 0;
  }
}
