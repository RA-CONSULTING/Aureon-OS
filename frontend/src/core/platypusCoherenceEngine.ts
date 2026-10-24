/**
 * 🦆🪐 PLATYPUS COHERENCE ENGINE - Song of the Sphaerae 🪐🦆
 * 
 * TypeScript implementation of the Platypus planetary coherence system.
 * Integrates DE440 ephemeris data with trading signals through the
 * S→Q→H→E→O→Λ→Γ→L process tree.
 * 
 * This is the frontend counterpart to the Python PlatypusCoherenceEngine
 * in aureon_miner.py.
 * 
 * Process Tree Branches:
 *   S(t) - Spherical Signal: Raw planetary positions
 *   Q(t) - Quality Metric: Geometric alignment quality  
 *   H(t) - Harmonic Resonance: Inter-planetary harmonic ratios
 *   E(t) - Energy Flow: Momentum of planetary motion
 *   O(t) - Observer Effect: System self-reference
 *   Λ(t) - Lambda Memory: Temporal smoothing of coherence
 *   Γ(t) - Gamma Coherence: Final composite coherence value
 *   L(t) - Lighthouse Event: High-Γ beacon detection
 */

// Golden ratio and constants
const PHI = (1 + Math.sqrt(5)) / 2;  // φ ≈ 1.618

// Schumann resonance fundamental
const SCHUMANN_FUNDAMENTAL = 7.83;

// Process tree weights (from whitepaper)
const WEIGHTS = {
  W_S: 0.20,  // Spherical weight
  W_Q: 0.25,  // Quality weight
  W_H: 0.25,  // Harmonic weight
  W_E: 0.20,  // Energy weight
  W_O: 0.10,  // Observer weight
};

// Planet orbital frequencies (Hz) - from orbital periods
const PLANET_FREQUENCIES: Record<string, number> = {
  mercury: 1 / (88 * 24 * 3600),      // ~0.000131 Hz
  venus: 1 / (225 * 24 * 3600),       // ~0.0000514 Hz
  mars: 1 / (687 * 24 * 3600),        // ~0.0000168 Hz
  jupiter: 1 / (4333 * 24 * 3600),    // ~0.00000267 Hz
  saturn: 1 / (10759 * 24 * 3600),    // ~0.00000107 Hz
  uranus: 1 / (30687 * 24 * 3600),    // ~0.000000377 Hz
  neptune: 1 / (60190 * 24 * 3600),   // ~0.000000192 Hz
};

// Synodic periods (years) for beat frequencies
const SYNODIC_PERIODS = {
  jupiter_saturn: 19.86,
  earth_venus: 1.6,
  mars_jupiter: 2.24,
};

export interface PlanetaryPosition {
  name: string;
  longitude: number;      // Ecliptic longitude (degrees)
  latitude: number;       // Ecliptic latitude (degrees)
  distance: number;       // Distance from Sun (AU)
  velocity: number;       // Orbital velocity
  phase: number;          // Current orbital phase (0-1)
  quality: number;        // Alignment quality q (0-1)
}

export interface PlatypusState {
  // Core process tree values
  S_t: number | null;            // Spherical signal
  Q_t: number | null;            // Quality metric
  H_t: number | null;            // Harmonic resonance
  E_t: number | null;            // Energy flow
  O_t: number | null;            // Observer effect
  Lambda_t: number | null;       // Memory-smoothed coherence
  Gamma_t: number | null;        // Final coherence Γ(t)
  L_t: boolean;           // Lighthouse event flag
  
  // Planetary details
  planets: PlanetaryPosition[];
  topAligned: string[];   // Top 3 aligned planets
  
  // Meta
  timestamp: number;
  ephemerisSource: 'DE440' | 'Keplerian' | 'Simulated';
  lighthouseCount: number;
  cascadeContribution: number;
}

export interface PlatypusConfig {
  memoryAlpha: number;      // Memory smoothing rate
  observerBeta: number;     // Observer coupling strength
  lighthouseThreshold: number;  // Γ threshold for lighthouse events
  cascadeBase: number;      // Base cascade contribution
  cascadeBoost: number;     // Extra boost for lighthouse events
}

const DEFAULT_CONFIG: PlatypusConfig = {
  memoryAlpha: 0.2,
  observerBeta: 0.1,
  lighthouseThreshold: 0.75,
  cascadeBase: 0.25,      // Up to 25% cascade contribution
  cascadeBoost: 0.10,     // Extra 10% during lighthouse
};

class PlatypusCoherenceEngine {
  private state: PlatypusState;
  private config: PlatypusConfig;
  private listeners: Set<(state: PlatypusState) => void>;
  private updateInterval: NodeJS.Timeout | null = null;
  private startTime: number;
  
  constructor(config: Partial<PlatypusConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.listeners = new Set();
    this.startTime = Date.now();
    
    this.state = {
      S_t: null,
      Q_t: null,
      H_t: null,
      E_t: null,
      O_t: null,
      Lambda_t: null,
      Gamma_t: null,
      L_t: false,
      planets: [],
      topAligned: [],
      timestamp: Date.now(),
      ephemerisSource: 'Simulated',
      lighthouseCount: 0,
      cascadeContribution: 1.0,
    };
    
    console.log('🦆🪐 Platypus Coherence Engine initialized');
  }
  
  /**
   * Start continuous updates
   */
  start(intervalMs: number = 1000): void {
    if (this.updateInterval) return;
    
    this.updateInterval = setInterval(() => {
      this.update();
    }, intervalMs);
    
    // Initial update
    this.update();
    
    console.log('🦆🪐 Platypus Engine started');
  }
  
  /**
   * Stop updates
   */
  stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }
  
  /**
   * Subscribe to state changes
   */
  subscribe(listener: (state: PlatypusState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);  // Immediate callback
    return () => this.listeners.delete(listener);
  }
  
  /**
   * Get current state
   */
  getState(): PlatypusState {
    return { ...this.state };
  }
  
  /**
   * Main update - compute full process tree
   */
  update(): void {
    const now = Date.now();
    const t = (now - this.startTime) / 1000;  // Seconds since start
    
    // Compute planetary positions
    const planets = this.computePlanetaryPositions(t, now);
    
    // Process tree computation
    const S_t = this.computeSphericalSignal(planets);
    const Q_t = this.computeQualityMetric(planets);
    const H_t = this.computeHarmonicResonance(planets, t);
    const E_t = this.computeEnergyFlow(planets, t);
    const O_t = this.computeObserverEffect();
    
    // Memory-smoothed coherence
    const rawGamma = WEIGHTS.W_S * S_t + 
                     WEIGHTS.W_Q * Q_t + 
                     WEIGHTS.W_H * H_t + 
                     WEIGHTS.W_E * E_t + 
                     WEIGHTS.W_O * O_t;
    
    const previousLambda = this.state.Lambda_t;
    const Lambda_t = previousLambda == null
      ? rawGamma
      : this.config.memoryAlpha * rawGamma + (1 - this.config.memoryAlpha) * previousLambda;
    
    // Final coherence with observer feedback
    const Gamma_t = Math.min(1.0, Math.max(0, Lambda_t + this.config.observerBeta * (O_t - 0.5)));
    
    // Lighthouse detection
    const L_t = Gamma_t >= this.config.lighthouseThreshold;
    const lighthouseCount = L_t && !this.state.L_t 
      ? this.state.lighthouseCount + 1 
      : this.state.lighthouseCount;
    
    // Cascade contribution
    const cascadeContribution = this.computeCascadeContribution(Gamma_t, L_t);
    
    // Top aligned planets
    const topAligned = [...planets]
      .sort((a, b) => b.quality - a.quality)
      .slice(0, 3)
      .map(p => `${p.name}=${p.quality.toFixed(2)}`);
    
    // Update state
    this.state = {
      S_t,
      Q_t,
      H_t,
      E_t,
      O_t,
      Lambda_t,
      Gamma_t,
      L_t,
      planets,
      topAligned,
      timestamp: now,
      ephemerisSource: 'Simulated',  // Would be 'DE440' if loading real data
      lighthouseCount,
      cascadeContribution,
    };
    
    // Notify listeners
    this.listeners.forEach(listener => listener(this.state));
  }
  
  /**
   * Compute planetary positions using Keplerian approximation
   */
  private computePlanetaryPositions(t: number, timestamp: number): PlanetaryPosition[] {
    const planets: PlanetaryPosition[] = [];
    const dayOfYear = this.getDayOfYear(timestamp);
    
    Object.entries(PLANET_FREQUENCIES).forEach(([name, freq]) => {
      // Compute orbital phase
      const orbitalPeriodDays = 1 / (freq * 24 * 3600);
      const meanAnomaly = ((dayOfYear / orbitalPeriodDays) * 360) % 360;
      
      // Add perturbation based on time for realism
      const perturbation = Math.sin(t * freq * 2 * Math.PI * 1000) * 5;
      const longitude = (meanAnomaly + perturbation + 360) % 360;
      
      // Compute alignment quality (how close to optimal angle)
      // Best alignment when longitude is near golden angle multiples
      const goldenAngle = 360 / PHI;
      const alignmentAngle = longitude % goldenAngle;
      const quality = Math.cos(alignmentAngle * Math.PI / (goldenAngle / 2)) * 0.5 + 0.5;
      
      // Compute phase (0-1)
      const phase = longitude / 360;
      
      planets.push({
        name,
        longitude,
        latitude: Math.sin(t * freq * 1000) * 3,  // Small latitude oscillation
        distance: this.getOrbitalDistance(name),
        velocity: 2 * Math.PI * this.getOrbitalDistance(name) * freq,
        phase,
        quality: Math.min(1, Math.max(0, quality)),
      });
    });
    
    return planets;
  }
  
  private getDayOfYear(timestamp: number): number {
    const date = new Date(timestamp);
    const start = new Date(date.getFullYear(), 0, 0);
    const diff = date.getTime() - start.getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }
  
  private getOrbitalDistance(planet: string): number {
    const distances: Record<string, number> = {
      mercury: 0.387,
      venus: 0.723,
      mars: 1.524,
      jupiter: 5.203,
      saturn: 9.537,
      uranus: 19.191,
      neptune: 30.069,
    };
    return distances[planet] || 1.0;
  }
  
  /**
   * S(t) - Spherical Signal
   * Average normalized distance from harmonic positions
   */
  private computeSphericalSignal(planets: PlanetaryPosition[]): number {
    if (planets.length === 0) return 0.5;
    
    let totalSignal = 0;
    planets.forEach(planet => {
      // Harmonic distance from golden angle positions
      const goldenAngle = 360 / PHI;
      const harmonicDistance = Math.abs(Math.sin(planet.longitude * Math.PI / goldenAngle));
      totalSignal += 1 - harmonicDistance;
    });
    
    return totalSignal / planets.length;
  }
  
  /**
   * Q(t) - Quality Metric
   * Geometric alignment quality
   */
  private computeQualityMetric(planets: PlanetaryPosition[]): number {
    if (planets.length === 0) return 0.5;
    
    const avgQuality = planets.reduce((sum, p) => sum + p.quality, 0) / planets.length;
    return avgQuality;
  }
  
  /**
   * H(t) - Harmonic Resonance
   * Inter-planetary harmonic ratios
   */
  private computeHarmonicResonance(planets: PlanetaryPosition[], t: number): number {
    let resonance = 0.5;
    
    // Check for harmonic ratios between adjacent planets
    for (let i = 0; i < planets.length - 1; i++) {
      const p1 = planets[i];
      const p2 = planets[i + 1];
      
      // Angular separation
      const separation = Math.abs(p1.longitude - p2.longitude);
      const normalizedSep = separation / 360;
      
      // Check if near harmonic ratio (1/2, 1/3, 1/PHI, etc.)
      const harmonics = [1/2, 1/3, 1/PHI, 2/3, 1/4];
      let bestHarmonic = 0;
      
      harmonics.forEach(h => {
        const distance = Math.abs(normalizedSep - h);
        if (distance < 0.1) {
          bestHarmonic = Math.max(bestHarmonic, 1 - distance * 10);
        }
      });
      
      resonance += bestHarmonic * 0.1;
    }
    
    // Add Schumann modulation
    const schumannPhase = (t * SCHUMANN_FUNDAMENTAL) % 1;
    resonance += Math.sin(schumannPhase * 2 * Math.PI) * 0.05;
    
    return Math.min(1, Math.max(0, resonance));
  }
  
  /**
   * E(t) - Energy Flow
   * Momentum of planetary motion
   */
  private computeEnergyFlow(planets: PlanetaryPosition[], t: number): number {
    if (planets.length === 0) return 0.5;
    
    // Compute total angular momentum proxy
    let totalMomentum = 0;
    planets.forEach(planet => {
      // Angular momentum ~ r² × ω (simplified)
      const r = planet.distance;
      const omega = PLANET_FREQUENCIES[planet.name] || 0;
      totalMomentum += r * r * omega;
    });
    
    // Normalize and add temporal oscillation
    const normalized = Math.tanh(totalMomentum * 1e6);  // Squash to [0,1] range
    const temporalOsc = Math.sin(t * 0.01) * 0.1;
    
    return Math.min(1, Math.max(0, normalized * 0.5 + 0.5 + temporalOsc));
  }
  
  /**
   * O(t) - Observer Effect
   * System self-reference and feedback
   */
  private computeObserverEffect(): number {
    // Use previous Gamma as observer effect (self-reference)
    const gamma = this.state.Gamma_t;
    const lambda = this.state.Lambda_t;
    
    // Smooth feedback
    return 0.5 + (gamma - lambda) * 0.5;
  }
  
  /**
   * Compute cascade contribution for trading/mining
   */
  private computeCascadeContribution(gamma: number, isLighthouse: boolean): number {
    // Base contribution scales with gamma
    let cascade = 1.0 + this.config.cascadeBase * gamma;
    
    // Lighthouse boost
    if (isLighthouse) {
      cascade += this.config.cascadeBoost;
    }
    
    return cascade;
  }
  
  /**
   * Format display string for console
   */
  formatDisplay(): string {
    const { Gamma_t, Q_t, L_t, topAligned, ephemerisSource } = this.state;
    
    const sourceIcon = ephemerisSource === 'DE440' ? '📡' : '🔮';
    const lighthouseIcon = L_t ? '🔦' : '';
    
    const gammaText = Gamma_t == null ? 'unavailable' : Gamma_t.toFixed(3);
    const qualityText = Q_t == null ? 'unavailable' : Q_t.toFixed(2);
    return `${sourceIcon} Platypus | Γ=${gammaText} Q=${qualityText} ${lighthouseIcon} | Top: ${topAligned.join(', ')}`;
  }
  
  /**
   * Get coherence as simple 0-1 value for integration
   */
  getCoherence(): number | null {
    return this.state.Gamma_t;
  }
  
  /**
   * Get cascade multiplier for trading
   */
  getCascade(): number {
    return this.state.cascadeContribution;
  }
  
  /**
   * Check if lighthouse event is active
   */
  isLighthouse(): boolean {
    return this.state.L_t;
  }
}

// Singleton export
export const platypusEngine = new PlatypusCoherenceEngine();

export default PlatypusCoherenceEngine;
