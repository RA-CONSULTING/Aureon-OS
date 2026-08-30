/**
 * Earth data integration backed by the live NOAA-derived Supabase function.
 * Local CSV/JSON datasets are research inputs and are never replayed as live.
 */

import { unifiedBus } from './unifiedBus';
import { supabase } from '@/integrations/supabase/client';
import { assertFreshProvenance, type DataProvenance } from './liveDataContract';

interface SchumannProxyResponse extends DataProvenance {
  fundamentalHz: number;
  amplitude: number;
  quality: number;
  variance: number;
  coherenceBoost: number;
  resonancePhase: string;
  earthDisturbance: number;
  harmonics: Array<{ frequency: number; amplitude: number; name: string }>;
  derivation: string;
}

export interface EarthIntegrationState {
  isInitialized: boolean;
  dataStatus: 'real_derived' | 'no_data' | 'stale';
  lastUpdate: number | null;
  sourceId: string | null;
  sourceTimestamp: string | null;
  derivation: string | null;
  schumann: null;
  lattice: null;
  sealPacket: null;
  marker: null;
  validation: null;
  coherence: number | null;
  frequency: number | null;
  fieldStrength: number | null;
  phaseLock: boolean | null;
  harmonicFidelity: number | null;
  coherenceBoost: number | null;
  earthDisturbance: number | null;
  modes: {
    mode1: number | null;
    mode2: number | null;
    mode3: number | null;
    mode4: number | null;
    mode5: number | null;
  };
  magneticField: null;
  electricField: null;
}

const EMPTY_STATE: EarthIntegrationState = {
  isInitialized: false,
  dataStatus: 'no_data',
  lastUpdate: null,
  sourceId: null,
  sourceTimestamp: null,
  derivation: null,
  schumann: null,
  lattice: null,
  sealPacket: null,
  marker: null,
  validation: null,
  coherence: null,
  frequency: null,
  fieldStrength: null,
  phaseLock: null,
  harmonicFidelity: null,
  coherenceBoost: null,
  earthDisturbance: null,
  modes: { mode1: null, mode2: null, mode3: null, mode4: null, mode5: null },
  magneticField: null,
  electricField: null,
};

class EarthLiveDataIntegration {
  private state: EarthIntegrationState = { ...EMPTY_STATE, modes: { ...EMPTY_STATE.modes } };
  private refreshInterval: ReturnType<typeof setInterval> | null = null;
  private readonly listeners = new Set<(state: EarthIntegrationState) => void>();

  async initialize(): Promise<void> {
    if (this.refreshInterval) return;
    await this.refresh();
    this.refreshInterval = setInterval(() => {
      this.refresh().catch((error) => console.warn('[EarthIntegration] refresh failed', error));
    }, 60_000);
  }

  async refresh(): Promise<void> {
    const { data, error } = await supabase.functions.invoke<SchumannProxyResponse>('fetch-schumann-data');
    if (error || !data) {
      this.state = { ...EMPTY_STATE, modes: { ...EMPTY_STATE.modes } };
      this.notifyListeners();
      throw new Error(`NO_DATA: NOAA-derived Earth proxy unavailable${error ? `: ${error.message}` : ''}`);
    }
    assertFreshProvenance(data, 20 * 60 * 1000);
    const numericValues = [
      data.fundamentalHz,
      data.amplitude,
      data.quality,
      data.variance,
      data.coherenceBoost,
      data.earthDisturbance,
    ];
    if (!numericValues.every(Number.isFinite) || !Array.isArray(data.harmonics)) {
      throw new Error('NO_DATA: invalid NOAA-derived Earth proxy response');
    }
    const amplitudeAt = (index: number) => {
      const value = data.harmonics[index]?.amplitude;
      return Number.isFinite(value) ? value : null;
    };
    this.state = {
      ...EMPTY_STATE,
      isInitialized: true,
      dataStatus: 'real_derived',
      lastUpdate: Date.parse(data.sourceTimestamp),
      sourceId: data.sourceId,
      sourceTimestamp: data.sourceTimestamp,
      derivation: data.derivation,
      coherence: data.quality,
      frequency: data.fundamentalHz,
      phaseLock: data.resonancePhase === 'peak',
      harmonicFidelity: data.quality,
      coherenceBoost: data.coherenceBoost,
      earthDisturbance: data.earthDisturbance,
      modes: {
        mode1: amplitudeAt(0),
        mode2: amplitudeAt(1),
        mode3: amplitudeAt(2),
        mode4: amplitudeAt(3),
        mode5: null,
      },
    };

    unifiedBus.publish({
      systemName: 'EarthIntegration',
      timestamp: Date.parse(data.sourceTimestamp),
      ready: true,
      coherence: data.quality,
      confidence: data.quality,
      signal: 'NEUTRAL',
      data: {
        frequency: data.fundamentalHz,
        phaseLock: this.state.phaseLock,
        harmonicFidelity: data.quality,
        modes: this.state.modes,
        earthDisturbance: data.earthDisturbance,
        derivation: data.derivation,
        provenance: {
          truthStatus: data.truthStatus,
          sourceId: data.sourceId,
          sourceTimestamp: data.sourceTimestamp,
          generatedValues: false,
        },
      },
    });
    this.notifyListeners();
  }

  getState(): EarthIntegrationState {
    if (this.state.lastUpdate !== null && Date.now() - this.state.lastUpdate > 20 * 60 * 1000) {
      return { ...this.state, isInitialized: false, dataStatus: 'stale' };
    }
    return { ...this.state, modes: { ...this.state.modes } };
  }

  subscribe(callback: (state: EarthIntegrationState) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach((callback) => callback(state));
  }

  destroy(): void {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
    this.refreshInterval = null;
    this.listeners.clear();
    this.state = { ...EMPTY_STATE, modes: { ...EMPTY_STATE.modes } };
  }
}

export const earthLiveDataIntegration = new EarthLiveDataIntegration();
