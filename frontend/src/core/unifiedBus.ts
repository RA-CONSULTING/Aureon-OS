// UnifiedBus - Central state communication layer
// Each system publishes state, all systems read from bus
// "Each system reads and reassures the next. Each is a piece to a big puzzle."

export type SignalType = 'BUY' | 'SELL' | 'NEUTRAL';

export interface SystemState {
  systemName: string;
  timestamp: number;
  ready: boolean;
  coherence: number | null;
  confidence: number | null;
  signal: SignalType | null;
  data: Record<string, any>;
}

export interface BusSnapshot {
  states: Record<string, SystemState>;
  timestamp: number;
  consensusSignal: SignalType | null;
  consensusConfidence: number | null;
  systemsReady: number;
  totalSystems: number;
}

// 10-9-1 Prime Seal weighted system classification
// Unity (10x): Core decision systems
// Flow (9x): Signal processing systems  
// Anchor (1x): Data ingestion systems

const UNITY_SYSTEMS = ['MasterEquation', 'Lighthouse']; // 10x weight
const FLOW_SYSTEMS = ['RainbowBridge', 'Prism', '6DHarmonic', 'DecisionFusion', 'HocusPattern', 'ProbabilityMatrix']; // 9x weight
const ANCHOR_SYSTEMS = ['DataIngestion', 'ElephantMemory', 'MultiExchange']; // 1x weight

// Legacy weights (normalized) - used as sub-weights within each tier
const SYSTEM_WEIGHTS: Record<string, number> = {
  // Unity tier (10x base)
  MasterEquation: 0.55,
  Lighthouse: 0.45,
  // Flow tier (9x base) - now includes ProbabilityMatrix
  RainbowBridge: 0.20,
  DecisionFusion: 0.20,
  Prism: 0.15,
  '6DHarmonic': 0.15,
  ProbabilityMatrix: 0.15, // HNC 2-hour temporal forecasting
  HocusPattern: 0.10,
  QGITASignal: 0.05,
  // Anchor tier (1x base)
  DataIngestion: 0.40,
  MultiExchange: 0.35,
  ElephantMemory: 0.25,
  // Extended systems (contribute to flow)
  IntegralAQAL: 0.05,
  StargateLattice: 0.05,
  HNCImperial: 0.05,
};

const REQUIRED_SYSTEMS = ['DataIngestion', 'Lighthouse', 'MasterEquation', 'RainbowBridge'];
const OPTIONAL_SYSTEMS = ['DecisionFusion', 'QGITASignal', 'Prism', 'IntegralAQAL', 'StargateLattice', 'HNCImperial', '6DHarmonic', 'MultiExchange', 'ProbabilityMatrix'];

class UnifiedBus {
  private states: Map<string, SystemState> = new Map();
  private listeners: Set<(snapshot: BusSnapshot) => void> = new Set();
  
  /**
   * Publish a system's state to the bus
   */
  publish(state: SystemState): void {
    const truthStatus = state.data?.truthStatus ?? state.data?.truth_status;
    const sourceId = state.data?.sourceId ?? state.data?.source_id;
    const sourceTimestamp = state.data?.sourceTimestamp ?? state.data?.source_timestamp;
    const generatedValues = state.data?.generatedValues ?? state.data?.generated_values;
    const sourceTime = Date.parse(String(sourceTimestamp || ''));
    const sourceAge = Date.now() - sourceTime;
    const hasEvidence = ['live', 'real_derived'].includes(String(truthStatus)) &&
      generatedValues === false && Boolean(sourceId) && Number.isFinite(sourceTime) &&
      sourceAge >= -5 * 60 * 1000 && sourceAge <= 5 * 60 * 1000 && Number.isFinite(state.coherence) &&
      Number.isFinite(state.confidence) && state.signal !== null;

    this.states.set(state.systemName, hasEvidence ? {
      ...state,
      timestamp: sourceTime,
    } : {
      systemName: state.systemName,
      timestamp: Number.isFinite(sourceTime) ? sourceTime : Date.now(),
      ready: false,
      coherence: null,
      confidence: null,
      signal: null,
      data: {
        truthStatus: 'no_data',
        generatedValues: false,
        blocker: 'FRESH_PRODUCTION_PROVENANCE_REQUIRED',
      },
    });
    this.notifyListeners();
  }
  
  /**
   * Read a specific system's state
   */
  read(systemName: string): SystemState | undefined {
    return this.states.get(systemName);
  }
  
  /**
   * Read all system states
   */
  readAll(): Record<string, SystemState> {
    const result: Record<string, SystemState> = {};
    this.states.forEach((state, name) => {
      result[name] = state;
    });
    return result;
  }
  
  /**
   * Get a complete snapshot of the bus including consensus
   */
  snapshot(): BusSnapshot {
    const states = this.readAll();
    const { signal, confidence } = this.computeConsensus();
    const systemsReady = Object.values(states).filter(s => s.ready).length;
    
    return {
      states,
      timestamp: Date.now(),
      consensusSignal: signal,
      consensusConfidence: confidence,
      systemsReady,
      totalSystems: this.states.size,
    };
  }
  
  /**
   * Check if all required systems are ready and compute consensus
   */
  checkConsensus(): { ready: boolean; signal: SignalType | null; confidence: number | null } {
    const allReady = REQUIRED_SYSTEMS.every(name => {
      const state = this.states.get(name);
      return state?.ready && Number.isFinite(state.coherence) && (state.coherence as number) > 0.7;
    });
    
    const { signal, confidence } = this.computeConsensus();
    
    return {
      ready: allReady,
      signal,
      confidence,
    };
  }
  
  /**
   * Compute 10-9-1 weighted consensus from all systems
   * Unity systems (10x), Flow systems (9x), Anchor systems (1x)
   */
  private computeConsensus(): { signal: SignalType | null; confidence: number | null } {
    // Compute tier-weighted scores
    let unityBuy = 0, unitySell = 0, unityTotal = 0;
    let flowBuy = 0, flowSell = 0, flowTotal = 0;
    let anchorBuy = 0, anchorSell = 0, anchorTotal = 0;
    
    // Process Unity systems (10x weight)
    for (const name of UNITY_SYSTEMS) {
      const state = this.states.get(name);
      if (!state?.ready || !Number.isFinite(state.confidence)) continue;
      const subWeight = SYSTEM_WEIGHTS[name] ?? 0.5;
      unityTotal += subWeight;
      if (state.signal === 'BUY') unityBuy += subWeight * (state.confidence as number);
      else if (state.signal === 'SELL') unitySell += subWeight * (state.confidence as number);
    }
    
    // Process Flow systems (9x weight)
    for (const name of FLOW_SYSTEMS) {
      const state = this.states.get(name);
      if (!state?.ready || !Number.isFinite(state.confidence)) continue;
      const subWeight = SYSTEM_WEIGHTS[name] ?? 0.2;
      flowTotal += subWeight;
      if (state.signal === 'BUY') flowBuy += subWeight * (state.confidence as number);
      else if (state.signal === 'SELL') flowSell += subWeight * (state.confidence as number);
    }
    
    // Process Anchor systems (1x weight)
    for (const name of ANCHOR_SYSTEMS) {
      const state = this.states.get(name);
      if (!state?.ready || !Number.isFinite(state.confidence)) continue;
      const subWeight = SYSTEM_WEIGHTS[name] ?? 0.33;
      anchorTotal += subWeight;
      if (state.signal === 'BUY') anchorBuy += subWeight * (state.confidence as number);
      else if (state.signal === 'SELL') anchorSell += subWeight * (state.confidence as number);
    }
    
    // Normalize within each tier
    const unityBuyNorm = unityTotal > 0 ? unityBuy / unityTotal : 0;
    const unitySellNorm = unityTotal > 0 ? unitySell / unityTotal : 0;
    const flowBuyNorm = flowTotal > 0 ? flowBuy / flowTotal : 0;
    const flowSellNorm = flowTotal > 0 ? flowSell / flowTotal : 0;
    const anchorBuyNorm = anchorTotal > 0 ? anchorBuy / anchorTotal : 0;
    const anchorSellNorm = anchorTotal > 0 ? anchorSell / anchorTotal : 0;
    
    // Apply 10-9-1 weights
    const totalWeight = 10 + 9 + 1; // 20
    const buyScore = (unityBuyNorm * 10 + flowBuyNorm * 9 + anchorBuyNorm * 1) / totalWeight;
    const sellScore = (unitySellNorm * 10 + flowSellNorm * 9 + anchorSellNorm * 1) / totalWeight;
    
    // Compute overall confidence using 10-9-1 weighting
    let totalConfidence = 0;
    let confWeight = 0;
    for (const name of [...UNITY_SYSTEMS, ...FLOW_SYSTEMS, ...ANCHOR_SYSTEMS]) {
      const state = this.states.get(name);
      if (!state?.ready || !Number.isFinite(state.confidence)) continue;
      const tierWeight = UNITY_SYSTEMS.includes(name) ? 10 : FLOW_SYSTEMS.includes(name) ? 9 : 1;
      totalConfidence += (state.confidence as number) * tierWeight;
      confWeight += tierWeight;
    }
    const confidence = confWeight > 0 ? totalConfidence / confWeight : null;
    
    // Determine signal
    let signal: SignalType | null = confWeight > 0 ? 'NEUTRAL' : null;
    if (buyScore > sellScore && buyScore > 0.3) {
      signal = 'BUY';
    } else if (sellScore > buyScore && sellScore > 0.3) {
      signal = 'SELL';
    }
    
    return { signal, confidence };
  }
  
  /**
   * Subscribe to bus updates
   */
  subscribe(callback: (snapshot: BusSnapshot) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }
  
  /**
   * Notify all listeners of state changes
   */
  private notifyListeners(): void {
    const snapshot = this.snapshot();
    this.listeners.forEach(callback => callback(snapshot));
  }
  
  /**
   * Clear all states (useful for reset)
   */
  clear(): void {
    this.states.clear();
  }
  
  /**
   * Get system health status
   */
  getSystemHealth(): Array<{ name: string; ready: boolean; coherence: number | null; lastUpdate: number | null }> {
    const health: Array<{ name: string; ready: boolean; coherence: number | null; lastUpdate: number | null }> = [];
    
    const allSystems = [...REQUIRED_SYSTEMS, 'ElephantMemory', 'ZeroPoint', 'Dimensional', 'Akashic'];
    
    for (const name of allSystems) {
      const state = this.states.get(name);
      health.push({
        name,
        ready: state?.ready ?? false,
        coherence: state?.coherence ?? null,
        lastUpdate: state?.timestamp ?? null,
      });
    }
    
    return health;
  }
}

// Singleton instance
export const unifiedBus = new UnifiedBus();
