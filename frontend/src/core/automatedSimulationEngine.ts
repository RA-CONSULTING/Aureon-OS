/**
 * Automated Simulation Engine (Browser-Safe)
 * Dormant simulator. These numbers are not telemetry and are not a market reading.
 * Runs continuous simulations using sampled market data
 * Feeds data through complete light path and tracks accuracy
 */
export const SIMULATION_ONLY = true;

import { temporalProbabilityEcho, ProbabilitySnapshot } from './temporalProbabilityEcho';
import { lightPathTracer, LightPathTrace } from './lightPathTracer';
import { unifiedBus } from './unifiedBus';
import { dataStreamMonitor } from './dataStreamMonitor';

export interface MarketSample {
  timestamp: number;
  symbol: string;
  price: number;
  volume: number;
  volatility: number;
  momentum: number;
  actualOutcome?: 'UP' | 'DOWN' | 'FLAT';
}

export interface SimulationResult {
  simulationId: string;
  timestamp: number;
  marketSample: MarketSample;
  predictedAction: 'BUY' | 'SELL' | 'HOLD';
  predictedConfidence: number;
  actualOutcome?: 'UP' | 'DOWN' | 'FLAT';
  wasCorrect?: boolean;
  lightPathTrace: LightPathTrace | null;
  prismFrequency: number;
  probabilityMatrix: {
    sixD: number;
    hnc: number;
    lighthouse: number;
    fused: number;
  };
  telescopeRefinement: number;
  dataValidation: {
    isValid: boolean;
    errors: string[];
  };
}

export interface SimulationStats {
  totalSimulations: number;
  correctPredictions: number;
  accuracy: number;
  avgConfidence: number;
  avgPrismFrequency: number;
  actionDistribution: { BUY: number; SELL: number; HOLD: number };
  dataValidationRate: number;
  isRunning: boolean;
  lastSimulation: number;
}

class AutomatedSimulationEngineClass {
  private results: SimulationResult[] = [];
  private maxResults = 100;
  private isRunning = false;
  private intervalId: number | null = null;
  private listeners: Set<(stats: SimulationStats) => void> = new Set();
  private simulationInterval = 3000; // 3 seconds

  async runSingleSimulation(marketSample: MarketSample): Promise<SimulationResult> {
    const simulationId = `sim-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
    
    // Start light path trace
    const baseFrequency = this.calculateBaseFrequency(marketSample);
    lightPathTracer.startTrace(baseFrequency);

    // Data Validation
    const validationResult = this.validateMarketData(marketSample);
    if (!validationResult.isValid) {
      validationResult.errors.forEach(err => lightPathTracer.addValidationError(err));
    }

    // Simulate Rainbow Bridge (base frequency computation)
    const rainbowOutput = this.simulateRainbowBridge(marketSample);
    lightPathTracer.addNode('RainbowBridge', baseFrequency, rainbowOutput.frequency, 'emotional_mapping', {
      phase: rainbowOutput.phase,
      emotionalState: rainbowOutput.emotionalState
    });

    // Simulate The Prism (5-level transformation)
    const prismOutput = this.simulatePrism(rainbowOutput.frequency, marketSample);
    lightPathTracer.addNode('ThePrism', rainbowOutput.frequency, prismOutput.frequency, 'frequency_transformation', {
      level: prismOutput.level,
      state: prismOutput.state,
      harmonicPurity: prismOutput.harmonicPurity
    });

    // Simulate Probability Matrix (6D/HNC/Lighthouse fusion)
    const matrixOutput = this.simulateProbabilityMatrix(prismOutput, marketSample);
    lightPathTracer.addNode('ProbabilityMatrix', prismOutput.frequency, matrixOutput.fused, 'probability_fusion', {
      sixD: matrixOutput.sixD,
      hnc: matrixOutput.hnc,
      lighthouse: matrixOutput.lighthouse
    });

    // Simulate Quantum Telescope (geometric refinement)
    const telescopeOutput = this.simulateQuantumTelescope(matrixOutput, prismOutput.frequency);
    lightPathTracer.addNode('QuantumTelescope', matrixOutput.fused, telescopeOutput.refinedProbability, 'geometric_refraction', {
      dominantSolid: telescopeOutput.dominantSolid,
      geometricAlignment: telescopeOutput.geometricAlignment
    });

    // Decision Fusion
    const decision = this.simulateDecisionFusion(telescopeOutput, matrixOutput);
    lightPathTracer.addNode('DecisionFusion', telescopeOutput.refinedProbability, decision.confidence, 'final_determination', {
      action: decision.action
    });

    // Complete trace
    const trace = lightPathTracer.completeTrace(decision.action, decision.confidence);

    // Record to temporal echo
    const echoSnapshot: Omit<ProbabilitySnapshot, 'timestamp'> = {
      sixDProbability: matrixOutput.sixD,
      hncProbability: matrixOutput.hnc,
      lighthouseProbability: matrixOutput.lighthouse,
      fusedProbability: matrixOutput.fused,
      action: decision.action,
      confidence: decision.confidence,
      prismFrequency: prismOutput.frequency,
      prismLevel: prismOutput.level,
      coherence: telescopeOutput.geometricAlignment,
      lambda: prismOutput.lambda
    };
    temporalProbabilityEcho.recordSnapshot(echoSnapshot);

    // Create result
    const result: SimulationResult = {
      simulationId,
      timestamp: Date.now(),
      marketSample,
      predictedAction: decision.action,
      predictedConfidence: decision.confidence,
      actualOutcome: marketSample.actualOutcome,
      wasCorrect: this.checkPrediction(decision.action, marketSample.actualOutcome),
      lightPathTrace: trace,
      prismFrequency: prismOutput.frequency,
      probabilityMatrix: matrixOutput,
      telescopeRefinement: telescopeOutput.refinedProbability,
      dataValidation: validationResult
    };

    this.results.push(result);
    if (this.results.length > this.maxResults) {
      this.results = this.results.slice(-this.maxResults);
    }

    // Record to data stream monitor
    dataStreamMonitor.recordStream(
      'simulation-engine',
      validationResult.isValid,
      Date.now() - marketSample.timestamp,
      marketSample,
      result
    );

    // Publish to UnifiedBus
    unifiedBus.publish({
      systemName: 'SimulationEngine',
      timestamp: Date.now(),
      ready: true,
      coherence: telescopeOutput.geometricAlignment,
      confidence: decision.confidence,
      signal: decision.action === 'HOLD' ? 'NEUTRAL' : decision.action,
      data: { simulationId, action: decision.action, confidence: decision.confidence }
    });

    this.notifyListeners();
    return result;
  }

  private calculateBaseFrequency(sample: MarketSample): number {
    // Base frequency from market momentum and volatility
    const momentumFactor = (sample.momentum + 1) / 2; // Normalize to 0-1
    const volatilityFactor = Math.min(1, sample.volatility / 0.1);
    return 200 + (momentumFactor * 400) + (volatilityFactor * 200);
  }

  private validateMarketData(sample: MarketSample): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (sample.price <= 0) errors.push('Invalid price: must be positive');
    if (sample.volume < 0) errors.push('Invalid volume: must be non-negative');
    if (isNaN(sample.volatility)) errors.push('Invalid volatility: NaN');
    if (isNaN(sample.momentum)) errors.push('Invalid momentum: NaN');
    if (Date.now() - sample.timestamp > 30000) errors.push('Stale data: >30 seconds old');

    return { isValid: errors.length === 0, errors };
  }

  private simulateRainbowBridge(sample: MarketSample): { frequency: number; phase: string; emotionalState: string } {
    const baseFreq = 300 + (sample.momentum * 200);
    const phase = sample.momentum > 0.3 ? 'LOVE' : sample.momentum < -0.3 ? 'FEAR' : 'NEUTRAL';
    const emotionalState = sample.volatility > 0.05 ? 'EXCITED' : 'CALM';
    return { frequency: baseFreq, phase, emotionalState };
  }

  private simulatePrism(inputFreq: number, sample: MarketSample): { frequency: number; level: number; state: string; harmonicPurity: number; lambda: number } {
    // 5-level transformation toward 528Hz
    const targetFreq = 528;
    const coherence = 0.5 + (sample.momentum * 0.3) - (sample.volatility * 0.2);
    
    let level = 1;
    let currentFreq = inputFreq;
    
    // Level progression based on coherence
    if (coherence > 0.4) level = 2;
    if (coherence > 0.6) level = 3;
    if (coherence > 0.75) level = 4;
    if (coherence > 0.9) level = 5;

    // Transform frequency toward 528Hz based on level
    const transformFactor = level / 5;
    currentFreq = inputFreq + (targetFreq - inputFreq) * transformFactor;

    // Lock to 528Hz at high coherence
    if (coherence > 0.9) currentFreq = 528;

    const harmonicPurity = Math.abs(528 - currentFreq) < 50 ? 0.9 + (Math.random() * 0.1) : 0.5 + (Math.random() * 0.3);
    const state = level >= 4 ? 'MANIFEST' : level >= 2 ? 'CONVERGING' : 'FORMING';
    const lambda = 0.5 + (coherence * 0.5);

    return { frequency: currentFreq, level, state, harmonicPurity, lambda };
  }

  private simulateProbabilityMatrix(prism: { frequency: number; level: number; harmonicPurity: number }, sample: MarketSample): { sixD: number; hnc: number; lighthouse: number; fused: number } {
    // 6D Harmonic probability based on prism output
    const sixD = 0.5 + (prism.harmonicPurity - 0.5) * 0.8 + (sample.momentum * 0.2);
    
    // HNC probability based on frequency alignment to 528Hz
    const freqAlignment = 1 - Math.min(1, Math.abs(528 - prism.frequency) / 500);
    const hnc = 0.5 + (freqAlignment - 0.5) * 0.7;
    
    // Lighthouse probability based on prism level
    const lighthouse = 0.3 + (prism.level / 5) * 0.5 + (Math.random() * 0.2);

    // Weighted fusion
    const fused = (sixD * 0.35) + (hnc * 0.35) + (lighthouse * 0.30);

    return {
      sixD: Math.max(0, Math.min(1, sixD)),
      hnc: Math.max(0, Math.min(1, hnc)),
      lighthouse: Math.max(0, Math.min(1, lighthouse)),
      fused: Math.max(0, Math.min(1, fused))
    };
  }

  private simulateQuantumTelescope(matrix: { fused: number }, prismFreq: number): { refinedProbability: number; dominantSolid: string; geometricAlignment: number } {
    // Geometric refinement through Platonic solids
    const solids = ['Tetrahedron', 'Hexahedron', 'Octahedron', 'Icosahedron', 'Dodecahedron'];
    const dominantSolid = solids[Math.floor(prismFreq / 150) % 5];
    
    // Geometric alignment based on frequency harmonics
    const geometricAlignment = 0.5 + (Math.sin(prismFreq / 100) * 0.3) + (Math.random() * 0.2);
    
    // Refine probability with geometric factor
    const refinedProbability = matrix.fused * (0.8 + geometricAlignment * 0.4);

    return {
      refinedProbability: Math.max(0, Math.min(1, refinedProbability)),
      dominantSolid,
      geometricAlignment: Math.max(0, Math.min(1, geometricAlignment))
    };
  }

  private simulateDecisionFusion(telescope: { refinedProbability: number; geometricAlignment: number }, matrix: { sixD: number; hnc: number; lighthouse: number }): { action: 'BUY' | 'SELL' | 'HOLD'; confidence: number } {
    const prob = telescope.refinedProbability;
    const alignment = telescope.geometricAlignment;
    
    // Decision thresholds
    let action: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
    if (prob > 0.65 && alignment > 0.6) {
      action = 'BUY';
    } else if (prob < 0.35 && alignment > 0.6) {
      action = 'SELL';
    }

    // Confidence based on alignment and matrix convergence
    const matrixConvergence = 1 - Math.max(
      Math.abs(matrix.sixD - matrix.hnc),
      Math.abs(matrix.hnc - matrix.lighthouse)
    );
    const confidence = (alignment * 0.5 + matrixConvergence * 0.5) * (action !== 'HOLD' ? 1 : 0.5);

    return { action, confidence: Math.max(0, Math.min(1, confidence)) };
  }

  private checkPrediction(action: 'BUY' | 'SELL' | 'HOLD', outcome?: 'UP' | 'DOWN' | 'FLAT'): boolean | undefined {
    if (!outcome) return undefined;
    
    if (action === 'BUY' && outcome === 'UP') return true;
    if (action === 'SELL' && outcome === 'DOWN') return true;
    if (action === 'HOLD' && outcome === 'FLAT') return true;
    return false;
  }

  generateMarketSample(): MarketSample {
    // Generate realistic market sample for simulation
    const now = Date.now();
    const basePrice = 40000 + (Math.random() * 10000);
    const momentum = (Math.random() - 0.5) * 2;
    const volatility = 0.01 + (Math.random() * 0.1);
    const volume = 1000000 + (Math.random() * 5000000);

    return {
      timestamp: now,
      symbol: 'BTCUSDT',
      price: basePrice,
      volume,
      volatility,
      momentum
    };
  }

  start(interval?: number): void {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.simulationInterval = interval || this.simulationInterval;

    const runSimulation = async () => {
      if (!this.isRunning) return;
      
      const sample = this.generateMarketSample();
      await this.runSingleSimulation(sample);
    };

    runSimulation();
    this.intervalId = window.setInterval(runSimulation, this.simulationInterval);
    this.notifyListeners();
  }

  stop(): void {
    this.isRunning = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.notifyListeners();
  }

  getStats(): SimulationStats {
    const total = this.results.length;
    const withOutcomes = this.results.filter(r => r.wasCorrect !== undefined);
    const correct = withOutcomes.filter(r => r.wasCorrect).length;
    
    const actionDist = { BUY: 0, SELL: 0, HOLD: 0 };
    let totalConfidence = 0;
    let totalFreq = 0;
    let validCount = 0;

    for (const r of this.results) {
      actionDist[r.predictedAction]++;
      totalConfidence += r.predictedConfidence;
      totalFreq += r.prismFrequency;
      if (r.dataValidation.isValid) validCount++;
    }

    return {
      totalSimulations: total,
      correctPredictions: correct,
      accuracy: withOutcomes.length > 0 ? correct / withOutcomes.length : 0,
      avgConfidence: total > 0 ? totalConfidence / total : 0,
      avgPrismFrequency: total > 0 ? totalFreq / total : 0,
      actionDistribution: actionDist,
      dataValidationRate: total > 0 ? validCount / total : 0,
      isRunning: this.isRunning,
      lastSimulation: this.results.length > 0 ? this.results[this.results.length - 1].timestamp : 0
    };
  }

  getResults(): SimulationResult[] {
    return [...this.results];
  }

  getRecentResults(count: number = 10): SimulationResult[] {
    return this.results.slice(-count);
  }

  subscribe(listener: (stats: SimulationStats) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(): void {
    const stats = this.getStats();
    this.listeners.forEach(listener => listener(stats));
  }

  clear(): void {
    this.results = [];
    this.notifyListeners();
  }
}

export const automatedSimulationEngine = new AutomatedSimulationEngineClass();
