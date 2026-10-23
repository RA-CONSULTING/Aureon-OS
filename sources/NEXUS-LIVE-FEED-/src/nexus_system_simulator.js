const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

class SignalStrengthAnalyzer {
  constructor(baseFrequency = 7.83) {
    this.baseFrequency = baseFrequency;
    this.harmonics = [7.83, 13.9, 20.8, 27.3, 33.8, 39.9];
    this.surgeWindows = [
      { threshold: 0.9, label: "2162: Quantum Leap", color: "#ffd700" },
      { threshold: 0.75, label: "2113: Galactic Threshold", color: "#ffb347" },
      { threshold: 0.6, label: "2098: Unity Awakening", color: "#ffa07a" },
      { threshold: 0.45, label: "2078: Cosmic Integration", color: "#87ceeb" },
      { threshold: 0.3, label: "2043: Surge Initiation", color: "#6495ed" },
      { threshold: 0, label: "Temporal Baseline", color: "#1e3a8a" }
    ];
    this.timelineAnchors = [
      { threshold: 0.82, label: "Barry Lundy Lattice", descriptor: "Emotional quantum lattice harmonising across spectrum." },
      { threshold: 0.68, label: "Quantum Liberation", descriptor: "Liberation markers accelerating coherence convergence." },
      { threshold: 0.52, label: "Schumann Surge", descriptor: "Schumann resonance bands showing amplified discharge." },
      { threshold: 0, label: "Coherence Drift", descriptor: "System operating within nominal harmonic drift." }
    ];
    this.guardianBridgeSettings = { active: false };
    this.lastAnalysis = this.#emptySnapshot();
  }

  applyGuardianBridge(settings = {}) {
    this.guardianBridgeSettings = {
      active: true,
      reverseBridgeGain: settings.reverseBridgeGain ?? 1,
      coherenceRamp: settings.coherenceRamp ?? 0,
      phaseCompression: settings.phaseCompression ?? 0,
      anchorThreshold: settings.anchorThreshold ?? 0.9
    };
  }

  analyze({ time, coherence, phase, amplitude }) {
    const normalizedCoherence = clamp(coherence, 0, 1);
    const normalizedPhase = clamp(phase / (Math.PI / 2), 0, 1);
    const amplitudeIntensity = clamp(Math.abs(amplitude) / (this.baseFrequency * 12), 0, 1.5);

    let signalStrength = clamp(
      normalizedCoherence * 0.55 +
      (1 - normalizedPhase) * 0.25 +
      amplitudeIntensity * 0.2,
      0,
      1
    );

    if (this.guardianBridgeSettings.active) {
      const gain = clamp(this.guardianBridgeSettings.reverseBridgeGain ?? 1, 1, 2.5);
      const anchorInfluence = normalizedCoherence >= (this.guardianBridgeSettings.anchorThreshold ?? 0.9) ? 0.08 : 0.04;
      signalStrength = clamp(signalStrength + anchorInfluence * (gain - 1), 0, 1);
    }

    const surgeIntensity = clamp(signalStrength * 0.7 + amplitudeIntensity * 0.3, 0, 1);
    const window = this.#resolveSurgeWindow(surgeIntensity);
    const frequencyShift = (normalizedCoherence - normalizedPhase) * this.baseFrequency;
    const spectralBands = this.#mapSpectralBands(surgeIntensity);
    const liberationMarkers = spectralBands
      .filter(band => band.strength >= 0.58)
      .map(band => ({ frequency: band.frequency, strength: band.strength }));
    const anchor = this.#resolveTimelineAnchor(signalStrength);

    const snapshot = {
      time,
      baseFrequency: this.baseFrequency,
      signalStrength,
      surgeIntensity,
      frequencyShift,
      window,
      spectralBands,
      liberationMarkers,
      timelineAnchor: anchor
    };

    this.lastAnalysis = snapshot;
    return snapshot;
  }

  getLastAnalysis() {
    return { ...this.lastAnalysis };
  }

  #resolveSurgeWindow(intensity) {
    return this.surgeWindows.find(window => intensity >= window.threshold) || this.surgeWindows[this.surgeWindows.length - 1];
  }

  #mapSpectralBands(intensity) {
    return this.harmonics.map((frequency, index) => {
      const harmonicWeight = 1 - index * 0.08;
      const strength = clamp(intensity * (0.85 + harmonicWeight * 0.3), 0, 1);
      return {
        frequency,
        strength,
        label: `H${index + 1}`
      };
    });
  }

  #resolveTimelineAnchor(signalStrength) {
    const anchor = this.timelineAnchors.find(point => signalStrength >= point.threshold) || this.timelineAnchors[this.timelineAnchors.length - 1];
    return { ...anchor };
  }

  #emptySnapshot() {
    return {
      time: 0,
      baseFrequency: this.baseFrequency,
      signalStrength: 0,
      surgeIntensity: 0,
      frequencyShift: 0,
      window: this.surgeWindows[this.surgeWindows.length - 1],
      spectralBands: this.#mapSpectralBands(0),
      liberationMarkers: [],
      timelineAnchor: this.timelineAnchors[this.timelineAnchors.length - 1]
    };
  }
}

class EgoDeathSimulator {
  constructor(numObservers = 1) {
    this.numObservers = numObservers;
    this.time = 0;
    this.coherence = 0.82;
    this.phase = Math.PI / 4;
    this.unityEventTriggered = false;
    this.guardianBridge = {
      active: false,
      reverseBridgeGain: 1,
      anchorThreshold: 0.95,
      coherenceRamp: 0,
      phaseCompression: 0,
      anchored: false
    };
  }

  step(deltaT = 0.01) {
    this.time += deltaT;

    const harmonicDrift = 0.85 + 0.1 * Math.sin(this.time / 2);
    const noise = (Math.random() - 0.5) * 0.02;
    let targetCoherence = harmonicDrift;

    if (this.guardianBridge.active) {
      const {
        reverseBridgeGain,
        anchorThreshold,
        coherenceRamp
      } = this.guardianBridge;

      targetCoherence = clamp(
        targetCoherence + coherenceRamp * reverseBridgeGain,
        0,
        1
      );

      if (this.coherence < anchorThreshold) {
        const anchorDelta = anchorThreshold - this.coherence;
        targetCoherence = clamp(
          targetCoherence + anchorDelta * 0.5 * reverseBridgeGain,
          0,
          1
        );
      }
    }

    const integrationRate = this.guardianBridge.active
      ? 0.35 * this.guardianBridge.reverseBridgeGain
      : 0.2;

    this.coherence = clamp(
      this.coherence + (targetCoherence - this.coherence) * integrationRate + noise,
      0,
      1
    );

    const phaseDrift = Math.abs(Math.sin(this.time / 3)) * 0.12;
    let newPhase = clamp((Math.PI / 2) * (1 - this.coherence) + phaseDrift, 0, Math.PI / 2);

    if (this.guardianBridge.active) {
      const { phaseCompression, reverseBridgeGain } = this.guardianBridge;
      const compression = clamp(1 - phaseCompression * reverseBridgeGain, 0, 1);
      newPhase *= compression;
      if (!this.guardianBridge.anchored && this.coherence >= this.guardianBridge.anchorThreshold) {
        this.guardianBridge.anchored = true;
        this.guardianBridge.anchoredAt = this.time;
      }
    }

    this.phase = newPhase;

    if (!this.unityEventTriggered && this.coherence > 0.95 && this.phase < Math.PI / 6) {
      this.unityEventTriggered = true;
    }

    return {
      coherence: this.coherence,
      phase: this.phase,
      unityEvent: this.unityEventTriggered,
    };
  }

  calculateCoherence() {
    return this.coherence;
  }

  calculatePhase() {
    return this.phase;
  }

  exportData() {
    return {
      numObservers: this.numObservers,
      coherence: this.coherence,
      phase: this.phase,
      time: this.time,
      unityEventTriggered: this.unityEventTriggered,
      guardianBridge: { ...this.guardianBridge }
    };
  }

  applyGuardianBridgeProtocol(config = {}) {
    const defaults = {
      reverseBridgeGain: 1.5,
      anchorThreshold: 0.93,
      coherenceRamp: 0.08,
      phaseCompression: 0.22
    };

    this.guardianBridge = {
      ...defaults,
      ...config,
      active: true,
      anchored: false,
      activatedAt: new Date().toISOString()
    };
  }
}

class ObserverFunction {
  constructor(dimensionality = 3) {
    this.dimensionality = dimensionality;
    this.collapsed = false;
    this.projections = [];
    this.coherence = 0.84;
    this.phase = 0.12;
    this.guardianBridge = {
      active: false
    };
  }

  addProjection(angle) {
    this.projections.push(angle);
    this.#recalculateState();
  }

  collapse() {
    this.collapsed = true;
    this.#recalculateState();
  }

  calculateCoherence() {
    return this.coherence;
  }

  exportState() {
    return {
      dimensionality: this.dimensionality,
      collapsed: this.collapsed,
      projections: [...this.projections],
      coherence: this.coherence,
      phase: this.phase,
      guardianBridge: { ...this.guardianBridge }
    };
  }

  #recalculateState() {
    const base = this.collapsed ? 0.9 : 0.82;
    const variation = this.projections.length
      ? this.projections.reduce((sum, angle) => sum + Math.cos(angle), 0) / this.projections.length
      : 0;

    this.coherence = clamp(base + variation * 0.05, 0, 1);
    if (this.projections.length) {
      const latest = Math.abs(this.projections[this.projections.length - 1]);
      this.phase = clamp(latest % (Math.PI / 2), 0, Math.PI / 2);
    }
  }

  harmonizeWithGuardianBridge(protocol = {}) {
    const settings = {
      anchorVector: 0,
      coherenceLift: 0.06,
      phaseAlignment: 0.18,
      ...protocol
    };

    this.guardianBridge = {
      ...settings,
      active: true,
      harmonizedAt: new Date().toISOString()
    };

    if (typeof settings.anchorVector === "number") {
      this.projections.push(settings.anchorVector);
    }

    this.coherence = clamp(this.coherence + settings.coherenceLift, 0, 1);
    this.phase = clamp(this.phase * (1 - settings.phaseAlignment), 0, Math.PI / 2);
  }
}

/**
 * Complete Nexus System with Ego Death & Observer Collapse
 * Integrates RFE, Ego Death Simulator, Observer Function, and Sacred Geometry
 */
export class NexusSystem {
  constructor(config = {}) {
    this.config = {
      numObservers: config.numObservers || 7, // 7 chakras / 7 observers
      dimensionality: config.dimensionality || 4, // 4D spacetime
      schumannBase: 7.83,
      phi: 1.618033988749,
      fibonacci: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144],
      ...config
    };

    this.egoDeathSim = new EgoDeathSimulator(this.config.numObservers);
    this.observerFunction = new ObserverFunction(this.config.dimensionality);
    this.guardianBridge = { active: false };

    // Signal analyzer tracks harmonic telemetry across the simulation. It
    // needs to exist before any cycles run so downstream calls (like
    // exportState or runCycle) can safely reference it.
    this.signalAnalyzer = new SignalStrengthAnalyzer(this.config.schumannBase);
    this.lastSignalWindow = null;
    this.lastSignalLogTime = 0;
    this.lastLoggedWindowLabel = null;
    this.unityEventRecorded = false;

    this.RFE = this.initializeRFE();
    this.seal = this.generatePrimeSentinelSeal();
  }
  
  /**
   * Initialize Reality Field Equation components
   * R(t) = α(M+F)·O·T(o) + βG(wells,waves) + γS
   */
  initializeRFE({
    observer = this.observerFunction,
    simulator = this.egoDeathSim
  } = {}) {
    return {
      // α(M+F) - Masculine + Feminine carrier wave
      MF: {
        M: {
          type: "ELECTRIC",
          frequency: 432, // Hz (harmony)
          phase: 0,
          amplitude: 1.0
        },
        F: {
          type: "MAGNETIC",
          frequency: 528, // Hz (love)
          phase: Math.PI / 2, // 90° phase shift
          amplitude: 1.0
        },
        combined: function(t) {
          const M_wave = this.M.amplitude * Math.cos(2 * Math.PI * this.M.frequency * t + this.M.phase);
          const F_wave = this.F.amplitude * Math.sin(2 * Math.PI * this.F.frequency * t + this.F.phase);
          return M_wave + F_wave;
        }
      },
      
      // O - Observer (from ObserverFunction)
      O: observer,

      // T(o) - Temporal Evolution (Fibonacci/Phi-based)
      T: {
        phi: this.config.phi,
        fibonacci: this.config.fibonacci,
        evolution: function(t) {
          // Fibonacci spiral growth: φ^(t/τ)
          const tau = 1.0; // Time constant
          return Math.pow(this.phi, t / tau);
        },
        spiral: function(t, theta0 = 0) {
          const r = this.evolution(t);
          const theta = theta0 + t;
          return {
            x: r * Math.cos(theta),
            y: r * Math.sin(theta),
            r: r,
            theta: theta
          };
        }
      },
      
      // G - Gravitational/Geometric (Schumann grounding)
      G: {
        schumann: this.config.schumannBase,
        wells: [], // Gravity wells (mass concentrations)
        waves: [], // Gravitational waves
        grounding: function(t) {
          // Schumann resonance oscillation
          return Math.sin(2 * Math.PI * this.schumann * t);
        }
      },
      
      // S - Spooky Entanglement (from EgoDeathSim)
      S: {
        simulator: simulator,
        entanglement: function() {
          // Entanglement strength = coherence
          return this.simulator.calculateCoherence();
        },
        maxEntanglement: 1.0 // Unity Event state
      },
      
      // Coefficients
      alpha: 1.0,
      beta: 0.5,
      gamma: 0.8,
      
      // Complete RFE calculation
      calculate: function(t) {
        const core = this.alpha * this.MF.combined(t) * this.O.calculateCoherence() * this.T.evolution(t);
        const gravity = this.beta * this.G.grounding(t);
        const entanglement = this.gamma * this.S.entanglement();
        
        return {
          R_t: core + gravity + entanglement,
          components: {
            core: core,
            gravity: gravity,
            entanglement: entanglement
          },
          timestamp: t
        };
      }
    };
  }
  
  /**
   * Generate Prime Sentinel's Seal of Authority
   */
  generatePrimeSentinelSeal() {
    const sealData = {
      sentinel: {
        name: "Gary Leckey",
        birthCode: "02/11/1991",
        lightLanguage: "Gar-Aya Lek-Aey",
        role: "Prime Sentinel"
      },
      declaration: "NO BODY NOT EVEN ME WILL EVER CLAIM THE SOURCE OF COGNITION",
      constants: {
        PHI: this.config.phi,
        SCHUMANN: this.config.schumannBase,
        FIBONACCI: this.config.fibonacci
      },
      timestamp: new Date().toISOString()
    };
    
    // Compute SHA-256 hash (requires crypto library)
    const canonicalString = JSON.stringify(sealData, Object.keys(sealData).sort());
    // In browser: const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonicalString));
    // Simplified for demo:
    const hash = this.simpleHash(canonicalString);
    
    return {
      ...sealData,
      hash: hash,
      verified: true
    };
  }

  activateGuardianBridgeAnchorProtocol(options = {}) {
    const defaults = {
      reverseBridgeGain: 1.6,
      anchorThreshold: 0.92,
      coherenceRamp: 0.12,
      phaseCompression: 0.25,
      observerCoherenceLift: 0.08,
      phaseAlignment: 0.22,
      anchorVector: 0,
      unityIntent: "MANIFEST_UNITY_THIS_TIMELINE"
    };

    const settings = {
      ...defaults,
      ...options
    };

    this.guardianBridge = {
      ...settings,
      active: true,
      activatedAt: new Date().toISOString()
    };

    this.signalAnalyzer.applyGuardianBridge(settings);


    this.egoDeathSim.applyGuardianBridgeProtocol({
      reverseBridgeGain: settings.reverseBridgeGain,
      anchorThreshold: settings.anchorThreshold,
      coherenceRamp: settings.coherenceRamp,
      phaseCompression: settings.phaseCompression
    });

    this.observerFunction.harmonizeWithGuardianBridge({
      anchorVector: settings.anchorVector,
      coherenceLift: settings.observerCoherenceLift,
      phaseAlignment: settings.phaseAlignment
    });


    return { ...this.guardianBridge };
  }

  /**
   * Advance the Nexus system by a single integration step while
   * incorporating optional external coherence (C_t) and stress inputs.
   *
   * @param {number | null} C_t - Observed coherence value to blend in.
   * @param {number | null} stress_t - Normalized stress reading applied as
   *   a penalty to coherence and a boost to phase spread.
   * @param {object} [options]
   * @param {number} [options.deltaT=0.01] - Time increment supplied to the
   *   internal EgoDeath simulator.
   * @param {number} [options.coherenceBlend=0.35] - Weight applied when
   *   blending the simulated coherence with the observed C_t input.
   * @param {number} [options.stressCoherencePenalty=0.2] - Portion of
   *   coherence reduced when stress_t is present.
   * @param {number} [options.stressPhaseGain=0.35] - Gain applied when
   *   converting stress into additional phase spread.
   * @returns {object} Snapshot of the updated system state.
   */
  step(C_t = null, stress_t = null, options = {}) {
    const {
      deltaT = 0.01,
      coherenceBlend = 0.35,
      stressCoherencePenalty = 0.2,
      stressPhaseGain = 0.35
    } = options;

    const dt = Math.max(0, Number.isFinite(deltaT) ? deltaT : 0.01);
    const blend = clamp(Number.isFinite(coherenceBlend) ? coherenceBlend : 0.35, 0, 1);
    const stressPenalty = Math.max(0, Number.isFinite(stressCoherencePenalty) ? stressCoherencePenalty : 0.2);
    const stressGain = Math.max(0, Number.isFinite(stressPhaseGain) ? stressPhaseGain : 0.35);

    const egoState = this.egoDeathSim.step(dt);

    let coherence = egoState.coherence;
    let phase = egoState.phase;

    if (Number.isFinite(C_t)) {
      const observed = clamp(C_t, 0, 1);
      coherence = clamp(coherence * (1 - blend) + observed * blend, 0, 1);
    }

    let normalizedStress = null;
    if (Number.isFinite(stress_t)) {
      normalizedStress = clamp(stress_t, 0, 1);
      const coherenceDrop = normalizedStress * stressPenalty;
      coherence = clamp(coherence * (1 - coherenceDrop), 0, 1);
      const phaseShift = normalizedStress * stressGain * (Math.PI / 6);
      phase = clamp(phase + phaseShift, 0, Math.PI / 2);
    }

    this.egoDeathSim.coherence = coherence;
    this.egoDeathSim.phase = phase;
    if (!this.egoDeathSim.unityEventTriggered && coherence > 0.95 && phase < Math.PI / 6) {
      this.egoDeathSim.unityEventTriggered = true;
    }

    const t = this.egoDeathSim.time;
    const R_t = this.RFE.calculate(t);
    const signalTelemetry = this.signalAnalyzer.analyze({
      time: t,
      coherence,
      phase,
      amplitude: R_t.R_t
    });

    const windowChanged = !this.lastSignalWindow || this.lastSignalWindow.label !== signalTelemetry.window.label;
    if (windowChanged) {
      this.lastSignalWindow = signalTelemetry.window;
      this.lastLoggedWindowLabel = signalTelemetry.window.label;
      this.lastSignalLogTime = Date.now();
    }

    return {
      time: t,
      deltaT: dt,
      coherence,
      phase,
      unityEvent: this.egoDeathSim.unityEventTriggered,
      stress: normalizedStress,
      realityField: R_t,
      signalStrength: signalTelemetry,
      observerCoherence: this.observerFunction.calculateCoherence(),
      guardianBridge: { ...this.guardianBridge }
    };
  }

  /**
   * Simple hash function (replace with proper SHA-256 in production)
   */
  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).padStart(16, '0');
  }
  
  /**
   * Run complete Nexus cycle
   */
  async runCycle(duration = 1000, stepDelay = 10) {
    console.log("🌟 NEXUS SYSTEM INITIALIZING 🌟");
    console.log(`Observers: ${this.config.numObservers}`);
    console.log(`Dimensionality: ${this.config.dimensionality}D`);
    console.log(`Seal Hash: ${this.seal.hash}`);
    console.log("\n");

    this.unityEventRecorded = false;
    this.lastSignalWindow = null;
    this.lastSignalLogTime = 0;
    this.lastLoggedWindowLabel = null;

    const startTime = Date.now();
    const results = [];
    
    while (Date.now() - startTime < duration) {
      const t = (Date.now() - startTime) / 1000; // Time in seconds
      
      // Step 1: Ego Death Simulation (phase alignment)
      const egoState = this.egoDeathSim.step(0.01);

      if (
        this.guardianBridge.active &&
        this.egoDeathSim.guardianBridge.anchored &&
        !this.guardianBridge.anchorAnnounced
      ) {
        this.guardianBridge.anchorAnnounced = true;
        this.guardianBridge.anchoredAt = this.egoDeathSim.guardianBridge.anchoredAt;
        console.log("🛡️ GUARDIAN BRIDGE ANCHORED");
        console.log(`Reverse Bridge Gain: ${this.guardianBridge.reverseBridgeGain.toFixed(2)}`);
      }

      // Step 2: Observer Collapse (if not already collapsed)
      if (!this.observerFunction.collapsed && egoState.coherence > 0.8) {
        this.observerFunction.addProjection(0); // Add measurement basis
        this.observerFunction.collapse();
        console.log("⚡ OBSERVER COLLAPSE TRIGGERED");
      }
      
      // Step 3: Calculate Reality Field
      const R_t = this.RFE.calculate(t);
      const signalTelemetry = this.signalAnalyzer.analyze({
        time: t,
        coherence: egoState.coherence,
        phase: egoState.phase,
        amplitude: R_t.R_t
      });

      const now = Date.now();
      const windowChanged = !this.lastSignalWindow || this.lastSignalWindow.label !== signalTelemetry.window.label;
      const labelChangedSinceLog = this.lastLoggedWindowLabel !== signalTelemetry.window.label;
      if (
        windowChanged &&
        labelChangedSinceLog &&
        (this.lastSignalLogTime === 0 || now - this.lastSignalLogTime > 750)
      ) {
        if (this.lastSignalWindow) {
          console.log(`📶 Signal window transition: ${this.lastSignalWindow.label} → ${signalTelemetry.window.label}`);
        } else {
          console.log(`📶 Signal window established: ${signalTelemetry.window.label}`);
        }
        this.lastSignalLogTime = now;
        this.lastLoggedWindowLabel = signalTelemetry.window.label;
      }
      if (windowChanged) {
        this.lastSignalWindow = signalTelemetry.window;
      }

      // Step 4: Check for Unity Event
      if (egoState.unityEvent && !this.unityEventRecorded) {
        console.log("\n🌈 UNITY EVENT ACHIEVED 🌈");
        console.log(`Time: ${t.toFixed(2)}s`);
        console.log(`Coherence: ${egoState.coherence.toFixed(6)}`);
        console.log(`Phase: ${egoState.phase.toFixed(6)}`);
        console.log(`R(t): ${R_t.R_t.toFixed(6)}`);
        console.log("\n");
        this.unityEventRecorded = true;
      }
      
      // Record results
      results.push({
        time: t,
        egoState: egoState,
        observerCoherence: this.observerFunction.calculateCoherence(),
        realityField: R_t,
        signalStrength: signalTelemetry,
        unityEvent: egoState.unityEvent,

      });
      
      // Delay for visualization
      if (stepDelay > 0) {
        await new Promise(resolve => setTimeout(resolve, stepDelay));
      }
    }
    
    console.log("✨ NEXUS CYCLE COMPLETE ✨\n");
    return results;
  }
  
  /**
   * Calculate Divine Union state for two observers
   */
  calculateDivineUnion(observer1, observer2) {
    // Get current coherence for each observer
    const C1 = observer1.coherence || 0.96; // Gary
    const C2 = observer2.coherence || 0.91; // Tanya
    
    // Calculate entanglement
    const entanglement = Math.sqrt(C1 * C2);
    
    // Calculate phase difference
    const theta1 = observer1.phase || 0;
    const theta2 = observer2.phase || 0;
    const phaseDiff = Math.abs(theta1 - theta2);
    
    // Divine Union metric
    const divineUnion = entanglement * Math.exp(-phaseDiff);
    
    // Check if Unity Event criteria met
    const unityAchieved = divineUnion > 0.98 && phaseDiff < 0.05;
    
    return {
      observer1: observer1.name || "Observer 1",
      observer2: observer2.name || "Observer 2",
      coherence1: C1,
      coherence2: C2,
      entanglement: entanglement,
      phaseDifference: phaseDiff,
      divineUnionMetric: divineUnion,
      unityAchieved: unityAchieved,
      status: unityAchieved ? "DIVINE UNION ACHIEVED" : "APPROACHING UNITY"
    };
  }
  
  /**
   * Export complete system state
   */
  exportState() {
    return {
      config: this.config,
      seal: this.seal,
      guardianBridge: { ...this.guardianBridge },
      egoDeathState: this.egoDeathSim.exportData(),
      observerState: this.observerFunction.exportState(),
      signalStrength: this.signalAnalyzer.getLastAnalysis(),
      RFE: {
        MF: {
          M: this.RFE.MF.M,
          F: this.RFE.MF.F
        },
        T: {
          phi: this.RFE.T.phi,
          fibonacci: this.RFE.T.fibonacci
        },
        G: {
          schumann: this.RFE.G.schumann
        },
        S: {
          entanglement: this.RFE.S.entanglement()
        },
        coefficients: {
          alpha: this.RFE.alpha,
          beta: this.RFE.beta,
          gamma: this.RFE.gamma
        }
      },
      timestamp: new Date().toISOString()
    };
  }
  
  /**
   * Visualize current state (for dashboard integration)
   */
  getVisualizationData() {
    const t = Date.now() / 1000;
    const R_t = this.RFE.calculate(t);


    return {
      // For Prime Sentinel Status card
      sentinel: {
        consciousness: this.observerFunction.calculateCoherence() * 100,
        coherence: this.egoDeathSim.calculateCoherence() * 100,
        phase: this.egoDeathSim.calculatePhase()
      },
      
      // For Energy Resonance card
      energy: {
        frequency: 963, // Unity frequency
        amplitude: R_t.R_t,
        timestamp: t
      },
      
      // For Nexus Stability card
      stability: {
        stable: (1 - this.egoDeathSim.phase / (Math.PI / 2)) * 100,
        fluctuation: (this.egoDeathSim.phase / (Math.PI / 2)) * 100
      },
      
      // For Sacred Frequencies card
      frequencies: {
        schumann: { amplitude: Math.abs(this.RFE.G.grounding(t)) * 100 },
        love: { amplitude: Math.abs(Math.sin(2 * Math.PI * 528 * t)) * 100 },
        harmony: { amplitude: Math.abs(Math.cos(2 * Math.PI * 432 * t)) * 100 },
        unity: { amplitude: Math.abs(this.RFE.MF.combined(t)) * 100 }
      },
      
      // For Unity Event detection
      unityEvent: {
        triggered: this.egoDeathSim.unityEventTriggered,
        coherence: this.egoDeathSim.coherence,
        phase: this.egoDeathSim.phase,
        progress: Math.min(100, (1 - this.egoDeathSim.phase / (Math.PI / 2)) * 100)
      },

      guardianBridge: {
        active: this.guardianBridge.active,
        reverseBridgeGain: this.guardianBridge.reverseBridgeGain || this.egoDeathSim.guardianBridge.reverseBridgeGain,
        anchored: this.egoDeathSim.guardianBridge.anchored,
        anchorThreshold: this.guardianBridge.anchorThreshold || this.egoDeathSim.guardianBridge.anchorThreshold,
        unityIntent: this.guardianBridge.unityIntent

      }
    };
  }

  /**
   * Provide a canonical diagnostic snapshot aligned with the Harmonic Nexus
   * formulation. This is designed for dashboards and verification tooling that
   * need to confirm the simulation is interpreting resonance data correctly
   * without mutating system state.
   */
  getSystemDiagnostics() {
    const analysis = this.signalAnalyzer.getLastAnalysis();
    const guardianBridgeState = {
      active: Boolean(this.guardianBridge.active || this.egoDeathSim.guardianBridge.active),
      anchored: Boolean(this.egoDeathSim.guardianBridge.anchored),
      anchorThreshold: this.guardianBridge.anchorThreshold ?? this.egoDeathSim.guardianBridge.anchorThreshold ?? null,
      reverseBridgeGain: this.guardianBridge.reverseBridgeGain ?? this.egoDeathSim.guardianBridge.reverseBridgeGain ?? null,
      unityIntent: this.guardianBridge.unityIntent ?? null,
    };

    return {
      timestamp: new Date().toISOString(),
      unityEvent: this.egoDeathSim.unityEventTriggered,
      coherence: this.egoDeathSim.calculateCoherence(),
      phase: this.egoDeathSim.calculatePhase(),
      guardianBridge: guardianBridgeState,
      signal: {
        baseFrequency: analysis.baseFrequency,
        strength: analysis.signalStrength,
        surgeIntensity: analysis.surgeIntensity,
        frequencyShift: analysis.frequencyShift,
        window: analysis.window,
        liberationMarkers: analysis.liberationMarkers,
        spectralBands: analysis.spectralBands,
      },
      observer: {
        dimensionality: this.observerFunction.dimensionality,
        collapsed: this.observerFunction.collapsed,
        projections: [...this.observerFunction.projections],
      },
      rfeSample: this.RFE.calculate(Date.now() / 1000),
    };
  }

  #seedRandom(seed) {
    if (typeof seed !== "number" || Number.isNaN(seed)) {
      return () => {};
    }

    let state = Math.floor(seed) % 2147483647;
    if (state <= 0) {
      state += 2147483646;
    }

    const originalRandom = Math.random;
    Math.random = () => {
      state = (state * 16807) % 2147483647;
      return (state - 1) / 2147483646;
    };

    return () => {
      Math.random = originalRandom;
    };
  }

  #buildProcessFoundation() {
    return {
      unityEvent: {
        description: "State of maximal coherence and zero separation across the observer lattice.",
        formula: "lim_{θ→0} ∏ Ψ_i(θ) = 1",
        observers: this.config.numObservers,
        coherenceTarget: 0.99,
        phaseThreshold: 0.01,
      },
      observerCollapse: {
        description: "Conscious intention collapses quantum potential into realized outcomes.",
        transform: "ρ(t) → Σ Π_k ρ(t) Π_k",
      },
      realityFieldEquation: {
        formula: "R(t) = α(M+F)·O·T(o) + βG + γS",
        coefficients: {
          alpha: this.RFE.alpha,
          beta: this.RFE.beta,
          gamma: this.RFE.gamma,
        },
      },
      temporalLaw: {
        loveConstantSymbol: "Φ-9",
        narrative: "System evolves toward the Love Constant (Λₗ) where coherence asymptotically overwhelms entropy.",
      },
    };
  }

  simulateProcessTree(options = {}) {
    const {
      steps = 180,
      deltaT = 0.1,
      seed = 2025,
      guardianBridge = null,
      stabilizeAfterUnity = true,
    } = options;

    const restoreRandom = this.#seedRandom(seed);

    const localEgo = new EgoDeathSimulator(this.config.numObservers);
    const localObserver = new ObserverFunction(this.config.dimensionality);
    const localAnalyzer = new SignalStrengthAnalyzer(this.config.schumannBase);

    let guardianSettings = null;
    if (guardianBridge) {
      const defaults = {
        reverseBridgeGain: 1.6,
        anchorThreshold: 0.93,
        coherenceRamp: 0.1,
        phaseCompression: 0.24,
        observerCoherenceLift: 0.08,
        phaseAlignment: 0.2,
        anchorVector: 0,
        unityIntent: "REALITY_FIELD_PROCESS_TREE",
      };

      guardianSettings = {
        ...defaults,
        ...guardianBridge,
        active: true,
      };

      localAnalyzer.applyGuardianBridge(guardianSettings);
      localEgo.applyGuardianBridgeProtocol(guardianSettings);
      localObserver.harmonizeWithGuardianBridge({
        anchorVector: guardianSettings.anchorVector,
        coherenceLift: guardianSettings.observerCoherenceLift,
        phaseAlignment: guardianSettings.phaseAlignment,
      });
    }

    const localRFE = this.initializeRFE({
      observer: localObserver,
      simulator: localEgo,
    });

    const foundation = this.#buildProcessFoundation();

    const samples = [];
    const windowTransitions = [];
    let unityStep = null;
    let anchorStep = null;
    let lastWindowLabel = null;

    try {
      for (let index = 0; index < steps; index += 1) {
        const time = index * deltaT;
        const egoState = localEgo.step(deltaT);

        if (!localObserver.collapsed && egoState.coherence > 0.8) {
          localObserver.addProjection(0);
          localObserver.collapse();
        }

        const realityField = localRFE.calculate(time);
        const signalStrength = localAnalyzer.analyze({
          time,
          coherence: egoState.coherence,
          phase: egoState.phase,
          amplitude: realityField.R_t,
        });

        if (guardianSettings?.active && localEgo.guardianBridge.anchored && anchorStep === null) {
          anchorStep = index;
        }

        if (unityStep === null && egoState.unityEvent) {
          unityStep = index;
        }

        if (stabilizeAfterUnity && (unityStep !== null || egoState.unityEvent)) {
          const gain = guardianSettings?.reverseBridgeGain ?? 1;
          const coherenceLift = Math.min(1, 1.0 * gain);
          const basePhaseFactor = 1 - (guardianSettings?.phaseCompression ?? 0.2) * gain;
          const phaseFactor = Math.min(0.85, Math.max(0.02, basePhaseFactor));

          localEgo.coherence = clamp(
            localEgo.coherence + (1 - localEgo.coherence) * coherenceLift,
            0,
            1,
          );
          localEgo.phase = clamp(localEgo.phase * phaseFactor, 0, Math.PI / 2);
          localEgo.unityEventTriggered = true;

          if (localEgo.coherence >= 0.999) {
            localEgo.coherence = 1;
            localEgo.phase = 0;
          }

          egoState.coherence = localEgo.coherence;
          egoState.phase = localEgo.phase;
          egoState.unityEvent = true;
        }

        if (!lastWindowLabel || lastWindowLabel !== signalStrength.window.label) {
          windowTransitions.push({
            step: index,
            time,
            from: lastWindowLabel,
            to: signalStrength.window.label,
          });
          lastWindowLabel = signalStrength.window.label;
        }

        samples.push({
          step: index,
          time,
          coherence: egoState.coherence,
          phase: egoState.phase,
          unityEvent: egoState.unityEvent,
          realityField: {
            total: realityField.R_t,
            core: realityField.components.core,
            gravity: realityField.components.gravity,
            entanglement: realityField.components.entanglement,
          },
          signal: {
            strength: signalStrength.signalStrength,
            surgeIntensity: signalStrength.surgeIntensity,
            window: signalStrength.window.label,
          },
        });
      }
    } finally {
      restoreRandom();
    }

    const timeSeries = samples.map((sample) => sample.time);
    const coherenceSeries = samples.map((sample) => sample.coherence);
    const phaseSeries = samples.map((sample) => sample.phase);
    const realitySeries = samples.map((sample) => sample.realityField.total);
    const signalSeries = samples.map((sample) => sample.signal.strength);

    const finalSample = samples[samples.length - 1] || null;
    const unitySample = unityStep !== null ? samples[unityStep] : null;

    const phaseSpreadNormalized = finalSample
      ? finalSample.phase / (Math.PI / 2)
      : null;

    const epsilon = 1e-6;
    const loveConstantEstimateRaw = phaseSpreadNormalized !== null
      && phaseSpreadNormalized !== undefined
      && phaseSpreadNormalized > epsilon
      ? (finalSample?.coherence ?? 0) / Math.max(phaseSpreadNormalized, epsilon)
      : null;
    const loveConstantEstimate = loveConstantEstimateRaw === null
      ? null
      : Math.min(1_000_000, loveConstantEstimateRaw);

    return {
      foundation,
      simulation: {
        steps,
        deltaT,
        seed,
        guardianBridge: guardianSettings || { active: false },
        unityEventStep: unityStep,
        anchorStep,
        metrics: {
          finalCoherence: finalSample?.coherence ?? null,
          finalPhase: finalSample?.phase ?? null,
          finalRealityField: finalSample?.realityField.total ?? null,
          peakSignalStrength: signalSeries.length ? Math.max(...signalSeries) : null,
          peakRealityField: realitySeries.length ? Math.max(...realitySeries) : null,
          minimumPhase: phaseSeries.length ? Math.min(...phaseSeries) : null,
          unityEventCoherence: unitySample?.coherence ?? null,
          unityEventPhase: unitySample?.phase ?? null,
          loveConstantEstimate,
          phaseSpreadNormalized,
        },
        transitions: windowTransitions,
      },
      telemetry: {
        samples,
        series: {
          time: timeSeries,
          coherence: coherenceSeries,
          phase: phaseSeries,
          realityField: realitySeries,
          signalStrength: signalSeries,
        },
      },
    };
  }
}

// Note: Historically this module included imperative demo calls (running the
// simulator immediately on import). Those were removed to keep browser builds
// side-effect free—the React app simply imports { NexusSystem } and manages
// lifecycle itself.
