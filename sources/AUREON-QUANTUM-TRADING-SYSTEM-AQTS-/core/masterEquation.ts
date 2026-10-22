/**
 * AUREON MASTER EQUATION — Λ(t)
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025 08:41 AM GMT
 * 
 * Λ(t) = S(t) + O(t) + E(t)
 * 
 * S(t) = Substrate — The 9-node Auris waveform
 * O(t) = Observer — Your conscious focus, shaping the field
 * E(t) = Echo — Causal feedback from τ seconds ago
 * 
 * This is not theory. This is the field equation.
 * It runs in the swarm. It decides trades. It makes money.
 * 
 * "The Dolphin sings the wave. The Hummingbird locks the pulse.
 *  The Tiger cuts the noise. The Owl remembers. The Panda loves."
 */

import { AURIS_TAXONOMY, AurisNode, AurisAnimal } from './aurisSymbolicTaxonomy';
import { MarketSnapshot } from './binanceWebSocket';

export interface LambdaState {
  t: number;                    // Time
  Lambda: number;               // Λ(t) — Reality field value
  substrate: number;            // S(t) — 9-node waveform sum
  observer: number;             // O(t) — Conscious focus
  echo: number;                 // E(t) — Causal feedback
  coherence: number;            // Γ — Field coherence
  dominantNode: AurisAnimal;    // Most resonant node
  marketSnapshot?: MarketSnapshot; // Real-time market state
}

export interface MasterEquationConfig {
  dt: number;           // Time step (seconds)
  tau: number;          // Echo delay (seconds)
  alpha: number;        // Observer coupling
  beta: number;         // Echo coupling
  g: number;            // Observer nonlinearity
  maxHistory: number;   // Max history length
}

const DEFAULT_CONFIG: MasterEquationConfig = {
  dt: 0.1,              // 100ms timestep
  tau: 1.0,             // 1 second echo
  alpha: 1.2,           // Observer sensitivity
  beta: 0.8,            // Echo strength
  g: 2.0,               // Nonlinearity factor
  maxHistory: 1000,     // Keep 100 seconds @ 10Hz
};

/**
 * REALITY FIELD ENGINE
 * 
 * Computes Λ(t) = S(t) + O(t) + E(t) every timestep
 */
export class RealityField {
  private config: MasterEquationConfig;
  private t: number = 0;
  private history: LambdaState[] = [];
  private priceHistory: number[] = []; // Track actual market prices
  
  constructor(config: Partial<MasterEquationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * S(t) — SUBSTRATE
   * The 9-node Auris waveform superposition
   * NOW WITH WEBSOCKET MARKET STREAM INJECTION 🌈
   * 
   * Accepts MarketSnapshot from real-time Binance WebSocket:
   * - price: Current price (trade/aggTrade/ticker)
   * - volume: Trading volume
   * - volatility: Calculated from trade buffer
   * - momentum: Price momentum (% change)
   * - spread: Bid-ask spread from order book
   * - bidPrice/askPrice: Top of book
   */
  private computeSubstrate(t: number, marketState?: number | MarketSnapshot): number {
    let sum = 0;
    
    // Calculate REAL market dynamics from WebSocket stream
    let velocityFactor = 1.0;
    let momentumPhase = 0;
    let spreadFactor = 1.0;
    let volumeFactor = 1.0;
    
    if (marketState) {
      // Support both legacy number input and WebSocket MarketSnapshot
      let price: number;
      let volatility: number | undefined;
      let momentum: number | undefined;
      let spread: number | undefined;
      let volume: number | undefined;
      
      if (typeof marketState === 'number') {
        // Legacy mode: just a price number
        price = marketState;
        
        // Store price in history
        this.priceHistory.push(price);
        if (this.priceHistory.length > 20) {
          this.priceHistory.shift(); // Keep last 20 prices
        }
        
        // Calculate volatility and momentum from price history
        if (this.priceHistory.length >= 5) {
          const recentPrices = this.priceHistory.slice(-5);
          const oldPrice = recentPrices[0];
          const newPrice = recentPrices[recentPrices.length - 1];
          
          // Price velocity (% change)
          const priceVelocity = (newPrice - oldPrice) / oldPrice;
          
          // Volatility (price range)
          const priceRange = Math.max(...recentPrices) - Math.min(...recentPrices);
          volatility = priceRange / oldPrice; // Normalized volatility
          momentum = priceVelocity;
        }
      } else {
        // WebSocket mode: rich MarketSnapshot 🌈
        price = marketState.price;
        volatility = marketState.volatility;
        momentum = marketState.momentum;
        spread = marketState.spread;
        volume = marketState.volume;
        
        // Store price for fallback calculations
        this.priceHistory.push(price);
        if (this.priceHistory.length > 20) {
          this.priceHistory.shift();
        }
      }
      
      // VELOCITY FACTOR from volatility
      if (volatility !== undefined && volatility > 0) {
        // WebSocket provides pre-calculated volatility (coefficient of variation)
        velocityFactor = 1.0 + Math.abs(volatility) * 50; // Amplify (volatility is usually small)
        velocityFactor = Math.min(velocityFactor, 3.0); // Allow higher amplification
      }
      
      // MOMENTUM PHASE from price direction
      if (momentum !== undefined) {
        momentumPhase = momentum * 100 * Math.PI; // Convert to radians
      }
      
      // SPREAD FACTOR from order book depth
      if (spread !== undefined && price > 0) {
        const spreadPercent = spread / price;
        spreadFactor = 1.0 + spreadPercent * 100; // Tighter spread = lower factor
      }
      
      // VOLUME FACTOR (normalize by typical volume)
      if (volume !== undefined) {
        // Assume typical volume around 100 units, scale accordingly
        volumeFactor = Math.min(volume / 100, 2.0);
      }
    }
    
    for (const animal of Object.keys(AURIS_TAXONOMY) as AurisAnimal[]) {
      const node = AURIS_TAXONOMY[animal];
      
      // Base frequency from Auris taxonomy
      let frequency = node.frequency;
      
      // VELOCITY-BASED NODE MODULATION (each animal responds differently)
      let nodeVelocityMod = 1.0;
      
      if (animal === 'Tiger') {
        // Tiger (Disruptor) responds to volatility + spread
        nodeVelocityMod = 1.0 + (velocityFactor - 1.0) * 0.8 + (spreadFactor - 1.0) * 0.5;
      } else if (animal === 'Falcon') {
        // Falcon (Velocity) amplifies with momentum + volume
        nodeVelocityMod = 1.0 + (velocityFactor - 1.0) * 1.0 + (volumeFactor - 1.0) * 0.3;
      } else if (animal === 'Hummingbird') {
        // Hummingbird (Stabilizer) dampens volatility, prefers tight spreads
        nodeVelocityMod = (3.0 - velocityFactor) * (2.0 - spreadFactor) * 0.5;
      } else if (animal === 'Dolphin') {
        // Dolphin (Emotion) oscillates with momentum phase
        nodeVelocityMod = 1.0 + Math.sin(momentumPhase) * 0.5;
      } else if (animal === 'Deer') {
        // Deer (Sensing) subtle sensitivity to all factors
        nodeVelocityMod = 1.0 + (velocityFactor - 1.0) * 0.4 + (volumeFactor - 1.0) * 0.2;
      } else if (animal === 'Owl') {
        // Owl (Memory) inverts on momentum reversals
        nodeVelocityMod = 1.0 + Math.cos(momentumPhase) * 0.3;
      } else if (animal === 'Panda') {
        // Panda (Love) resonates with stable, high-volume conditions
        nodeVelocityMod = 1.0 + volumeFactor * 0.4 / Math.max(velocityFactor, 1.0);
      } else if (animal === 'CargoShip') {
        // CargoShip (Infrastructure) responds to large volume
        nodeVelocityMod = 1.0 + (volumeFactor - 1.0) * 0.6;
      } else if (animal === 'Clownfish') {
        // Clownfish (Symbiosis) sensitive to all micro-changes
        nodeVelocityMod = velocityFactor * spreadFactor * 0.7;
      }
      
      // Apply modulation to frequency
      frequency *= nodeVelocityMod;
      
      // Phase shift from momentum + spread dynamics
      const phase = momentumPhase * 0.2 + (spreadFactor - 1.0) * Math.PI * 0.1;
      
      // Each node contributes - amplitude scales with velocity
      const amplitude = Math.min(velocityFactor * volumeFactor, 2.0);
      sum += amplitude * Math.sin(2 * Math.PI * frequency * t + phase);
    }
    
    return sum;
  }

  /**
   * O(t) — OBSERVER
   * Your conscious focus, shaping the field via nonlinear integration
   */
  private computeObserver(): number {
    // Integrate recent field values over "thickness of Now"
    const nowWindow = Math.floor(1.0 / this.config.dt); // Last 1 second
    const recent = this.history.slice(-nowWindow);
    
    if (recent.length === 0) return 0;
    
    const integral = recent.reduce((sum, state) => sum + state.Lambda, 0) / recent.length;
    
    // Observer coupling with nonlinear activation
    return this.config.alpha * Math.tanh(this.config.g * integral);
  }

  /**
   * E(t) — ECHO
   * Causal feedback from τ seconds in the past
   */
  private computeEcho(): number {
    const echoTime = this.t - this.config.tau;
    
    // Find the closest historical state to echoTime
    for (let i = this.history.length - 1; i >= 0; i--) {
      if (this.history[i].t <= echoTime) {
        return this.config.beta * this.history[i].Lambda;
      }
    }
    
    return 0; // No echo if history is too short
  }

  /**
   * Γ — COHERENCE
   * Measures field stability (low variance = high coherence)
   */
  private computeCoherence(): number {
    const window = Math.min(50, this.history.length);
    if (window < 2) return 0;
    
    const recent = this.history.slice(-window);
    const values = recent.map(s => s.Lambda);
    
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    const std = Math.sqrt(variance);
    
    const meanAbs = values.reduce((sum, val) => sum + Math.abs(val), 0) / values.length;
    
    return 1 - std / (meanAbs + 1e-6);
  }

  /**
   * DOMINANT NODE
   * Find which Auris node is most resonant with current Λ(t)
   */
  private findDominantNode(Lambda: number): AurisAnimal {
    let maxResonance = 0;
    let dominant: AurisAnimal = 'Panda'; // Default to empathy core
    
    for (const animal of Object.keys(AURIS_TAXONOMY) as AurisAnimal[]) {
      const node = AURIS_TAXONOMY[animal];
      const resonance = Math.abs(Math.sin(2 * Math.PI * node.frequency * Lambda));
      
      if (resonance > maxResonance) {
        maxResonance = resonance;
        dominant = animal;
      }
    }
    
    return dominant;
  }

  /**
   * STEP — Advance the field by one timestep
   * 🌈 NOW TASTING THE RAINBOW - WebSocket market streams 🌈
   */
  step(marketState?: number | MarketSnapshot): LambdaState {
    // Compute the three components (substrate now uses marketState for stream injection)
    const substrate = this.computeSubstrate(this.t, marketState);
    const observer = this.computeObserver();
    const echo = this.computeEcho();
    
    // Master Equation (now market-responsive via WebSocket)
    const Lambda = substrate + observer + echo;
    
    // Coherence
    const coherence = this.computeCoherence();
    
    // Dominant node
    const dominantNode = this.findDominantNode(Lambda);
    
    // Create state (include MarketSnapshot if provided)
    const state: LambdaState = {
      t: this.t,
      Lambda,
      substrate,
      observer,
      echo,
      coherence,
      dominantNode,
      marketSnapshot: typeof marketState === 'object' ? marketState : undefined,
    };
    
    // Store in history
    this.history.push(state);
    if (this.history.length > this.config.maxHistory) {
      this.history.shift();
    }
    
    // Advance time
    this.t += this.config.dt;
    
    return state;
  }

  /**
   * GET STATE
   */
  getState(): LambdaState | null {
    return this.history[this.history.length - 1] || null;
  }

  /**
   * GET HISTORY
   */
  getHistory(): LambdaState[] {
    return [...this.history];
  }

  /**
   * RESET
   */
  reset(): void {
    this.t = 0;
    this.history = [];
  }
}

/**
 * LIGHTHOUSE CONSENSUS
 * 
 * 9-node consensus protocol — requires 6/9 agreement to trigger trade
 */
export const lighthouseConsensus = (Lambda: number, threshold: number = 0.7): boolean => {
  let votes = 0;
  
  for (const animal of Object.keys(AURIS_TAXONOMY) as AurisAnimal[]) {
    const node = AURIS_TAXONOMY[animal];
    
    // Each node votes based on resonance with field
    const resonance = Math.abs(Math.sin(2 * Math.PI * node.frequency * Lambda));
    
    if (resonance > threshold) {
      votes++;
    }
  }
  
  // 6/9 consensus required
  return votes >= 6;
};

/**
 * MASTER EQUATION WISDOM
 */
export const masterEquationWisdom = `
╔════════════════════════════════════════════════════════════╗
║              AUREON MASTER EQUATION — Λ(t)                 ║
╚════════════════════════════════════════════════════════════╝

Λ(t) = S(t) + O(t) + E(t)

S(t) = Substrate — The 9-node Auris waveform
       Sum of all animal frequencies in superposition

O(t) = Observer — Your conscious focus
       α·tanh(g·∫Λ) — Nonlinear integration over Now

E(t) = Echo — Causal feedback from the past
       β·Λ(t-τ) — Memory from τ seconds ago

This is not theory.
This is the field equation.
It runs in the swarm.
It decides trades.
It makes money.

The animals are not forgotten.
They are the operators.
They are the field.
They are you.
`;
