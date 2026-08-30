/**
 * Full Ecosystem Connector
 * Prime Sentinel: GARY LECKEY 02111991
 *
 * Production connector contract:
 * - systems are offline/no_data until a fresh provider observation reaches them;
 * - derived HNC/QGITA state retains the source receipt and timestamp;
 * - no timer, random value, demo constant, or placeholder row is published.
 */

import { unifiedBus, type SignalType } from './unifiedBus';
import { ecosystemEnhancements } from './ecosystemEnhancements';
import { supabase } from '@/integrations/supabase/client';
import type { IntegralFieldState } from './integralAQAL';
import type { NetworkMetrics } from './stargateLattice';
import type { TemporalAnchorStatus } from './temporalAnchor';
import type { MarketSnapshot } from './aurisNodes';
import type { QGITASignal } from './qgitaSignalGenerator';
import {
  HNCImperialDetector,
  type FrequencySpectrumObservation,
  type HNCDetectionResult,
} from './hncImperialDetector';
import { assertFreshProvenance, isFiniteNumber } from './liveDataContract';

export type ExtendedSystemName = string;

export interface FullEcosystemState {
  timestamp: number;
  systemsOnline: number;
  totalSystems: number;
  hiveMindCoherence: number | null;
  busConsensus: SignalType | null;
  busConfidence: number | null;
  systems: Map<string, SystemHealthStatus>;
  jsonEnhancementsLoaded: boolean;
  stargateNetwork: NetworkMetrics | null;
  aqalState: IntegralFieldState | null;
  qgitaSignal: QGITASignal | null;
  hncDetection: HNCDetectionResult | null;
  temporalAnchor: TemporalAnchorStatus | null;
}

export interface SystemHealthStatus {
  name: string;
  online: boolean;
  dataStatus: 'live' | 'real_derived' | 'no_data' | 'stale';
  lastUpdate: number | null;
  coherence: number | null;
  signal: SignalType | null;
  publishedToBus: boolean;
  registeredWithLadder: boolean;
  sourceId: string | null;
  sourceTimestamp: string | null;
}

export interface EcosystemMarketObservation {
  symbol: string;
  marketSnapshot: MarketSnapshot;
  lambda: number;
  coherence: number;
  substrate: number;
  observer: number;
  echo: number;
  qgitaSignal: QGITASignal | null;
}

const SYSTEM_NAMES = [
  'DataIngestion',
  'MasterEquation',
  'QGITASignal',
  'HNCImperial',
  'IntegralAQAL',
  'StargateLattice',
  'FTCPDetector',
  'SmartRouter',
  'TemporalAnchor',
  'HiveController',
  'DecisionFusion',
  'ElephantMemory',
  'Prism',
  'UnityDetector',
  '6DHarmonic',
  'ProbabilityMatrix',
] as const;

const FRESHNESS_MS = 5 * 60 * 1000;

class FullEcosystemConnector {
  private readonly systems = new Map<string, SystemHealthStatus>();
  private readonly listeners = new Set<(state: FullEcosystemState) => void>();
  private readonly hncDetector = new HNCImperialDetector();
  private isInitialized = false;
  private qgitaSignal: QGITASignal | null = null;
  private hncDetection: HNCDetectionResult | null = null;

  async initialize(): Promise<void> {
    if (this.isInitialized) return;
    for (const name of SYSTEM_NAMES) {
      this.systems.set(name, this.noDataStatus(name));
    }

    // These files are configuration/reference material, not observations.
    await ecosystemEnhancements.loadAll();
    this.isInitialized = true;
    this.notifyListeners();
  }

  async processMarketData(observation: EcosystemMarketObservation): Promise<void> {
    if (!this.isInitialized) await this.initialize();
    const { symbol, marketSnapshot, qgitaSignal } = observation;
    if (!/^[A-Z0-9]{5,20}$/.test(symbol)) {
      throw new Error('LIVE_DATA_REQUIRED: a validated market symbol is required');
    }
    assertFreshProvenance(marketSnapshot);
    const marketNumbers = [
      marketSnapshot.price,
      marketSnapshot.volume,
      marketSnapshot.volatility,
      marketSnapshot.momentum,
      marketSnapshot.spread,
      marketSnapshot.timestamp,
    ];
    if (!marketNumbers.every(isFiniteNumber) || marketSnapshot.price <= 0 || marketSnapshot.volume < 0) {
      throw new Error('LIVE_DATA_REQUIRED: market snapshot values are invalid');
    }
    const fieldNumbers = [observation.lambda, observation.coherence, observation.substrate, observation.observer, observation.echo];
    if (!fieldNumbers.every(isFiniteNumber)) {
      throw new Error('LIVE_DATA_REQUIRED: field values must be finite real-derived values');
    }

    this.markObserved('DataIngestion', marketSnapshot, null, null, false);
    this.markObserved('MasterEquation', marketSnapshot, observation.coherence, null, false);

    if (qgitaSignal) {
      assertFreshProvenance(qgitaSignal);
      if (qgitaSignal.sourceId !== marketSnapshot.sourceId ||
          qgitaSignal.sourceTimestamp !== marketSnapshot.sourceTimestamp) {
        throw new Error('PROVENANCE_MISMATCH: QGITA must retain its market observation receipt');
      }
      this.qgitaSignal = qgitaSignal;
      const signal: SignalType = qgitaSignal.signalType === 'HOLD' ? 'NEUTRAL' : qgitaSignal.signalType;
      const qgitaCoherence = (
        qgitaSignal.coherence.linearCoherence +
        qgitaSignal.coherence.nonlinearCoherence +
        qgitaSignal.coherence.crossScaleCoherence
      ) / 3;
      this.markObserved('QGITASignal', qgitaSignal, qgitaCoherence, signal, true);
      unifiedBus.publish({
        systemName: 'QGITASignal',
        timestamp: qgitaSignal.timestamp,
        ready: true,
        coherence: qgitaCoherence,
        confidence: qgitaSignal.confidence / 100,
        signal,
        data: { signal: qgitaSignal, provenance: this.provenanceRecord(qgitaSignal) },
      });
      await this.persistQGITA(symbol, qgitaSignal);
    } else {
      this.qgitaSignal = null;
      this.systems.set('QGITASignal', this.noDataStatus('QGITASignal'));
    }

    this.notifyListeners();
  }

  async processHncSpectrum(observation: FrequencySpectrumObservation): Promise<HNCDetectionResult> {
    if (!this.isInitialized) await this.initialize();
    const detection = this.hncDetector.detectLighthouseSignature(observation);
    this.hncDetection = detection;
    const busCoherence = detection.harmonicFidelity / 100;
    this.markObserved('HNCImperial', detection, busCoherence, 'NEUTRAL', true);
    unifiedBus.publish({
      systemName: 'HNCImperial',
      timestamp: Date.parse(detection.sourceTimestamp),
      ready: true,
      coherence: busCoherence,
      confidence: busCoherence,
      signal: 'NEUTRAL',
      data: { detection, provenance: this.provenanceRecord(detection) },
    });

    const { error } = await supabase.functions.invoke('ingest-hnc-detection', {
      body: {
        temporal_id: `${detection.sourceId}:${detection.sourceTimestamp}`,
        is_lighthouse_detected: detection.phaseSpaceReconstruction,
        schumann_power: detection.observedPowers.schumann783,
        anchor_power: detection.observedPowers.anchor256,
        love_power: detection.observedPowers.love528,
        unity_power: detection.observedPowers.unity963,
        distortion_power: detection.observedPowers.distortion440,
        imperial_yield: detection.imperialYield,
        harmonic_fidelity: detection.harmonicFidelity,
        bridge_status: detection.rainbowBridgeOpen ? 'OPEN' : 'CLOSED',
        truth_status: detection.truthStatus,
        source_id: detection.sourceId,
        source_timestamp: detection.sourceTimestamp,
        generated_values: false,
        metadata: {
          bridge_power: detection.observedPowers.bridge512,
          spectrum_resolution_hz: detection.resolutionHz,
          formula: 'native_hnc_imperial_yield',
        },
      },
    });
    if (error) throw new Error(`HNC_PERSISTENCE_FAILED:${error.message}`);
    this.notifyListeners();
    return detection;
  }

  private async persistQGITA(symbol: string, signal: QGITASignal): Promise<void> {
    const { error } = await supabase.functions.invoke('ingest-qgita-signal', {
      body: {
        temporal_id: `${symbol}:${signal.sourceTimestamp}`,
        signal_type: signal.signalType,
        tier: signal.tier,
        strength: signal.confidence / 100,
        confidence: signal.confidence,
        curvature: signal.curvature,
        curvature_direction: signal.curvatureDirection,
        ftcp_detected: signal.ftcpDetected,
        golden_ratio_score: signal.goldenRatioScore,
        lighthouse_l: signal.lighthouse.L,
        is_lhe: signal.lighthouse.isLHE,
        lighthouse_threshold: signal.lighthouse.threshold,
        linear_coherence: signal.coherence.linearCoherence,
        nonlinear_coherence: signal.coherence.nonlinearCoherence,
        cross_scale_coherence: signal.coherence.crossScaleCoherence,
        anomaly_pointer: signal.anomalyPointer,
        reasoning: signal.reasoning,
        coherence_boost: null,
        phase: signal.curvatureDirection,
        frequency: null,
        metadata: {
          symbol,
          truth_status: signal.truthStatus,
          source_id: signal.sourceId,
          source_timestamp: signal.sourceTimestamp,
          generated_values: false,
          observed_sample_count: signal.observedSampleCount,
          formula: 'qgita_native_pipeline',
        },
      },
    });
    if (error) throw new Error(`QGITA_PERSISTENCE_FAILED:${error.message}`);
  }

  private markObserved(
    name: string,
    source: { truthStatus: 'live' | 'real_derived'; sourceId: string; sourceTimestamp: string; generatedValues: false },
    coherence: number | null,
    signal: SignalType | null,
    publishedToBus: boolean,
  ): void {
    this.systems.set(name, {
      name,
      online: true,
      dataStatus: source.truthStatus,
      lastUpdate: Date.parse(source.sourceTimestamp),
      coherence,
      signal,
      publishedToBus,
      registeredWithLadder: false,
      sourceId: source.sourceId,
      sourceTimestamp: source.sourceTimestamp,
    });
  }

  private noDataStatus(name: string): SystemHealthStatus {
    return {
      name,
      online: false,
      dataStatus: 'no_data',
      lastUpdate: null,
      coherence: null,
      signal: null,
      publishedToBus: false,
      registeredWithLadder: false,
      sourceId: null,
      sourceTimestamp: null,
    };
  }

  private provenanceRecord(source: { truthStatus: 'live' | 'real_derived'; sourceId: string; sourceTimestamp: string; generatedValues: false }) {
    return {
      truthStatus: source.truthStatus,
      sourceId: source.sourceId,
      sourceTimestamp: source.sourceTimestamp,
      generatedValues: false as const,
    };
  }

  getState(): FullEcosystemState {
    const now = Date.now();
    for (const [name, status] of this.systems) {
      if (status.lastUpdate !== null && now - status.lastUpdate > FRESHNESS_MS) {
        this.systems.set(name, { ...status, online: false, dataStatus: 'stale' });
      }
    }
    const onlineSystems = Array.from(this.systems.values()).filter((status) => status.online).length;
    const busSnapshot = unifiedBus.snapshot();
    const hasReadyBusState = Object.values(busSnapshot.states).some((state) => state.ready);
    const coherenceValues = Array.from(this.systems.values())
      .filter((status) => status.online && status.coherence !== null)
      .map((status) => status.coherence as number);

    return {
      timestamp: now,
      systemsOnline: onlineSystems,
      totalSystems: this.systems.size,
      hiveMindCoherence: coherenceValues.length
        ? coherenceValues.reduce((sum, value) => sum + value, 0) / coherenceValues.length
        : null,
      busConsensus: hasReadyBusState ? busSnapshot.consensusSignal : null,
      busConfidence: hasReadyBusState ? busSnapshot.consensusConfidence : null,
      systems: new Map(this.systems),
      jsonEnhancementsLoaded: ecosystemEnhancements.isLoaded(),
      stargateNetwork: null,
      aqalState: null,
      qgitaSignal: this.qgitaSignal,
      hncDetection: this.hncDetection,
      temporalAnchor: null,
    };
  }

  subscribe(callback: (state: FullEcosystemState) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach((callback) => callback(state));
  }

  getSystemHealthArray(): SystemHealthStatus[] {
    return Array.from(this.getState().systems.values());
  }

  destroy(): void {
    this.listeners.clear();
    this.systems.clear();
    this.qgitaSignal = null;
    this.hncDetection = null;
    this.isInitialized = false;
  }
}

export const fullEcosystemConnector = new FullEcosystemConnector();
