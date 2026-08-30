/**
 * useEcosystemData Hook
 * Reads the in-browser ecosystem model (UnifiedBus + FullEcosystemConnector).
 * Missing source observations remain null/no_data. The hook never substitutes
 * demo frequencies, neutral labels, zero measurements, or derived sensor data.
 */

import { useState, useEffect, useCallback } from 'react';
import { unifiedBus, BusSnapshot, SignalType } from '../core/unifiedBus';
import { fullEcosystemConnector, FullEcosystemState, SystemHealthStatus } from '../core/fullEcosystemConnector';
import { temporalLadder, TemporalLadderState } from '../core/temporalLadder';
import { earthLiveDataIntegration, EarthIntegrationState } from '../core/earthLiveDataIntegration';

export interface EcosystemMetrics {
  // Core field metrics
  coherence: number;
  lambda: number;
  frequency: number;
  
  // Consensus
  consensusSignal: SignalType;
  consensusConfidence: number;
  
  // System health
  systemsOnline: number;
  totalSystems: number;
  hiveMindCoherence: number;
  
  // 6D Harmonic
  waveState: string;
  harmonicLock: boolean;
  probabilityFusion: number;
  
  // Prism
  prismLevel: number;
  prismState: string;
  loveLocked: boolean;
  
  // Rainbow Bridge
  phase: string;
  emotion: string;
  emotionalFrequency: number;
  
  // QGITA
  qgitaSignalType: SignalType;
  qgitaTier: number;
  qgitaConfidence: number;
  
  // Stargate
  stargateNetworkStrength: number;
  activeNodes: number;
  
  // AQAL
  evolutionaryLevel: number;
  dominantQuadrant: string;
  integrationScore: number;
  
  // HNC Imperial
  harmonicFidelity: number;
  rainbowBridgeOpen: boolean;
  criticalMassAchieved: boolean;
  
  // Temporal
  temporalAnchorStrength: number;
  surgeWindowActive: boolean;
}

export interface UseEcosystemDataReturn {
  metrics: EcosystemMetrics;
  busSnapshot: BusSnapshot | null;
  ecosystemState: FullEcosystemState | null;
  ladderState: TemporalLadderState | null;
  systemHealth: SystemHealthStatus[];
  isInitialized: boolean;
  refresh: () => void;
}

const DEFAULT_METRICS: EcosystemMetrics = {
  coherence: null,
  lambda: null,
  frequency: null,
  consensusSignal: null,
  consensusConfidence: null,
  systemsOnline: 0,
  totalSystems: 0,
  hiveMindCoherence: null,
  waveState: null,
  harmonicLock: null,
  probabilityFusion: null,
  prismLevel: null,
  prismState: null,
  loveLocked: null,
  phase: null,
  emotion: null,
  emotionalFrequency: null,
  qgitaSignalType: null,
  qgitaTier: null,
  qgitaConfidence: null,
  stargateNetworkStrength: null,
  activeNodes: null,
  evolutionaryLevel: null,
  dominantQuadrant: null,
  integrationScore: null,
  harmonicFidelity: null,
  rainbowBridgeOpen: null,
  criticalMassAchieved: null,
  temporalAnchorStrength: null,
  surgeWindowActive: null,
};

export function useEcosystemData(): UseEcosystemDataReturn {
  const [metrics, setMetrics] = useState<EcosystemMetrics>(DEFAULT_METRICS);
  const [busSnapshot, setBusSnapshot] = useState<BusSnapshot | null>(null);
  const [ecosystemState, setEcosystemState] = useState<FullEcosystemState | null>(null);
  const [ladderState, setLadderState] = useState<TemporalLadderState | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealthStatus[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  // Extract metrics from ecosystem state
  const extractMetrics = useCallback((
    ecosystem: FullEcosystemState | null,
    bus: BusSnapshot | null,
    ladder: TemporalLadderState | null
  ): EcosystemMetrics => {
    if (!ecosystem && !bus) return DEFAULT_METRICS;

    // Get system states from bus
    const masterEq = bus?.states?.MasterEquation;
    const rainbow = bus?.states?.RainbowBridge;
    const prism = bus?.states?.Prism;
    const sixD = bus?.states?.['6DHarmonic'];
    
    return {
      // Core field
      coherence: masterEq?.coherence ?? ecosystem?.hiveMindCoherence ?? null,
      lambda: masterEq?.data?.lambda ?? null,
      frequency: rainbow?.data?.frequency ?? null,
      
      // Consensus
      consensusSignal: ecosystem?.busConsensus ?? null,
      consensusConfidence: ecosystem?.busConfidence ?? null,
      
      // System health
      systemsOnline: ecosystem?.systemsOnline ?? bus?.systemsReady ?? 0,
      totalSystems: ecosystem?.totalSystems ?? bus?.totalSystems ?? 0,
      hiveMindCoherence: ecosystem?.hiveMindCoherence ?? null,
      
      // 6D Harmonic
      waveState: sixD?.data?.waveState ?? null,
      harmonicLock: sixD?.data?.harmonicLock ?? null,
      probabilityFusion: sixD?.data?.fusedProbability ?? null,
      
      // Prism
      prismLevel: prism?.data?.level ?? null,
      prismState: prism?.data?.state ?? null,
      loveLocked: prism?.data?.loveLocked ?? null,
      
      // Rainbow Bridge
      phase: rainbow?.data?.phase ?? null,
      emotion: rainbow?.data?.dominantEmotion ?? null,
      emotionalFrequency: rainbow?.data?.frequency ?? null,
      
      // QGITA (map HOLD to NEUTRAL for SignalType)
      qgitaSignalType: ecosystem?.qgitaSignal?.signalType === 'HOLD'
        ? 'NEUTRAL' 
        : (ecosystem?.qgitaSignal?.signalType ?? null) as SignalType,
      qgitaTier: ecosystem?.qgitaSignal?.tier ?? null,
      qgitaConfidence: ecosystem?.qgitaSignal?.confidence ?? null,
      
      // Stargate
      stargateNetworkStrength: ecosystem?.stargateNetwork?.networkStrength ?? null,
      activeNodes: ecosystem?.stargateNetwork?.activeNodes ?? null,
      
      // AQAL
      evolutionaryLevel: ecosystem?.aqalState?.overallEvolutionaryLevel ?? null,
      dominantQuadrant: ecosystem?.aqalState?.dominantQuadrant ?? null,
      integrationScore: ecosystem?.aqalState?.integrationScore ?? null,
      
      // HNC Imperial
      harmonicFidelity: ecosystem?.hncDetection?.harmonicFidelity ?? null,
      rainbowBridgeOpen: ecosystem?.hncDetection?.rainbowBridgeOpen ?? null,
      criticalMassAchieved: ecosystem?.hncDetection?.criticalMassAchieved ?? null,
      
      // Temporal
      temporalAnchorStrength: ecosystem?.temporalAnchor?.anchorStrength ?? null,
      surgeWindowActive: ecosystem?.temporalAnchor?.surgeWindowActive ?? null,
    };
  }, []);

  useEffect(() => {
    // Initialize ecosystem connector
    fullEcosystemConnector.initialize().then(() => {
      setIsInitialized(true);
    });

    // Subscribe to UnifiedBus
    const unsubBus = unifiedBus.subscribe((snapshot) => {
      setBusSnapshot(snapshot);
    });

    // Subscribe to Full Ecosystem
    const unsubEcosystem = fullEcosystemConnector.subscribe((state) => {
      setEcosystemState(state);
      setSystemHealth(Array.from(state.systems.values()));
    });

    // Subscribe to Temporal Ladder
    const unsubLadder = temporalLadder.subscribe((state) => {
      setLadderState(state);
    });

    // Initial states
    setBusSnapshot(unifiedBus.snapshot());
    setEcosystemState(fullEcosystemConnector.getState());
    setLadderState(temporalLadder.getState());
    setSystemHealth(fullEcosystemConnector.getSystemHealthArray());

    return () => {
      unsubBus();
      unsubEcosystem();
      unsubLadder();
    };
  }, []);

  // Update metrics when states change
  useEffect(() => {
    const newMetrics = extractMetrics(ecosystemState, busSnapshot, ladderState);
    setMetrics(newMetrics);
  }, [ecosystemState, busSnapshot, ladderState, extractMetrics]);

  const refresh = useCallback(() => {
    setBusSnapshot(unifiedBus.snapshot());
    setEcosystemState(fullEcosystemConnector.getState());
    setLadderState(temporalLadder.getState());
    setSystemHealth(fullEcosystemConnector.getSystemHealthArray());
  }, []);

  return {
    metrics,
    busSnapshot,
    ecosystemState,
    ladderState,
    systemHealth,
    isInitialized,
    refresh,
  };
}

/**
 * Simplified hook for components that just need basic metrics
 */
export function useBasicEcosystemMetrics() {
  const { metrics, isInitialized } = useEcosystemData();
  
  return {
    coherence: metrics.coherence,
    frequency: metrics.frequency,
    consensusSignal: metrics.consensusSignal,
    systemsOnline: metrics.systemsOnline,
    hiveMindCoherence: metrics.hiveMindCoherence,
    isInitialized,
  };
}

/**
 * Hook for Harmonic/Field visualizers
 */
export function useHarmonicMetrics() {
  const { metrics, busSnapshot, isInitialized } = useEcosystemData();
  
  return {
    frequency: metrics.frequency,
    coherence: metrics.coherence,
    waveState: metrics.waveState,
    harmonicLock: metrics.harmonicLock,
    prismLevel: metrics.prismLevel,
    prismState: metrics.prismState,
    loveLocked: metrics.loveLocked,
    harmonicFidelity: metrics.harmonicFidelity,
    probabilityFusion: metrics.probabilityFusion,
    phase: metrics.phase,
    isInitialized,
    busSnapshot,
  };
}

/**
 * Hook for Earth/Schumann analytics - uses REAL Earth Live Data
 */
export function useEarthMetrics() {
  const [earthState, setEarthState] = useState<EarthIntegrationState | null>(null);
  const { metrics, isInitialized } = useEcosystemData();
  
  useEffect(() => {
    // Subscribe to Earth integration updates
    const unsubEarth = earthLiveDataIntegration.subscribe((state) => {
      setEarthState(state);
    });
    
    // Get initial state
    setEarthState(earthLiveDataIntegration.getState());
    
    return () => unsubEarth();
  }, []);
  
  const schumannFrequency = earthState?.frequency ?? null;
  const magneticFieldMagnitude = null;
  const phaseLock = earthState?.phaseLock ?? null;
  const harmonicFidelity = earthState?.harmonicFidelity ?? null;
  
  return {
    // Real Schumann data
    schumannFrequency,
    magneticField: magneticFieldMagnitude,
    electricField: null,
    phaseLock,
    harmonicFidelity,
    
    // 5-mode Schumann amplitudes
    modes: earthState?.modes ?? { mode1: null, mode2: null, mode3: null, mode4: null, mode5: null },
    
    // Field vectors
    magneticVector: null,
    electricVector: null,
    
    // Validation
    validation: earthState?.validation ?? null,
    
    // Legacy derived values
    ionosphereActivity: null,
    solarWind: null,
    geomagneticIndex: earthState?.earthDisturbance ?? null,
    coherenceBoost: earthState?.coherenceBoost ?? null,
    derivation: earthState?.derivation ?? null,
    sourceId: earthState?.sourceId ?? null,
    sourceTimestamp: earthState?.sourceTimestamp ?? null,
    
    // State flags
    isEarthDataLoaded: earthState?.isInitialized ?? false,
    isInitialized,
  };
}

/**
 * Hook for QGITA/Signal analytics
 */
export function useSignalMetrics() {
  const { metrics, isInitialized } = useEcosystemData();
  
  return {
    signalType: metrics.qgitaSignalType,
    tier: metrics.qgitaTier,
    confidence: metrics.qgitaConfidence,
    consensusSignal: metrics.consensusSignal,
    consensusConfidence: metrics.consensusConfidence,
    isInitialized,
  };
}

/**
 * Hook for Stargate/Network analytics
 */
export function useStargateMetrics() {
  const { metrics, isInitialized } = useEcosystemData();
  
  return {
    networkStrength: metrics.stargateNetworkStrength,
    activeNodes: metrics.activeNodes,
    temporalAnchorStrength: metrics.temporalAnchorStrength,
    surgeWindowActive: metrics.surgeWindowActive,
    isInitialized,
  };
}

/**
 * Hook for Auris/Symbol analytics
 */
export function useAurisMetrics() {
  const { metrics, busSnapshot, isInitialized } = useEcosystemData();
  
  // Get dominant node from bus snapshot
  const masterEq = busSnapshot?.states?.MasterEquation;
  const dominantNode = masterEq?.data?.dominantNode ?? null;
  
  return {
    compilationRate: null,
    symbolProcessing: null,
    quantumEntanglement: null,
    dataIntegrity: null,
    dominantNode,
    isInitialized,
  };
}
