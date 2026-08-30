import { DataIngestionSnapshot } from './dataIngestion';
import { LighthouseEvent } from './qgitaEngine';
import type { ProbabilityFusion } from './enhanced6DProbabilityMatrix';

type DecisionAction = 'buy' | 'sell' | 'hold';

export interface ModelSignal {
  model: string;
  score: number;
  confidence: number;
  sourceId: string;
  sourceEventId: string;
  sourceTimestamp: number;
  truthStatus: 'live' | 'real_derived';
  generated: false;
}

/** Autonomy Hub consensus signal from the authenticated Python backend. */
export interface AutonomyHubSignal {
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  confidence: number;
  strength: number;
  rollingWinRate: number;
  numPredictors: number;
  agreementRatio: number;
  sourceId?: string;
  sourceEventId?: string;
  sourceTimestamp?: number;
}

export interface DecisionSignal {
  action: DecisionAction;
  positionSize: number;
  confidence: number;
  measuredWinRate: number | null;
  modelSignals: ModelSignal[];
  sentimentScore: number | null;
  harmonic6DScore: number | null;
  waveState: string;
  harmonicLock: boolean;
  autonomyHubAligned: boolean;
  truthStatus: 'real_derived';
  generated: false;
  sourceEventIds: string[];
}

export interface DecisionFusionConfig {
  buyThreshold: number;
  sellThreshold: number;
  weights: {
    ensemble: number;
    sentiment: number;
    qgita: number;
    harmonic6D: number;
    autonomyHub: number;
  };
  minimumConfidence: number;
}

const DEFAULT_CONFIG: DecisionFusionConfig = {
  buyThreshold: 0.15,
  sellThreshold: -0.15,
  weights: {
    ensemble: 0.4,
    sentiment: 0.1,
    qgita: 0.15,
    harmonic6D: 0.1,
    autonomyHub: 0.25,
  },
  minimumConfidence: 0.35,
};

const inUnitRange = (value: number): boolean => Number.isFinite(value) && value >= 0 && value <= 1;

const validateModelSignal = (signal: ModelSignal, now: number): void => {
  if (!signal.model || !signal.sourceId || !signal.sourceEventId || signal.generated !== false) {
    throw new Error('MODEL_SIGNAL_PROVENANCE_REQUIRED');
  }
  if (!Number.isFinite(signal.score) || !inUnitRange(signal.confidence)) {
    throw new Error('MODEL_SIGNAL_VALUE_INVALID');
  }
  const sourceTimestamp = signal.sourceTimestamp < 10_000_000_000
    ? signal.sourceTimestamp * 1000
    : signal.sourceTimestamp;
  if (now - sourceTimestamp > 300_000 || sourceTimestamp - now > 30_000) {
    throw new Error(`MODEL_SIGNAL_STALE:${signal.model}`);
  }
};

export class DecisionFusionLayer {
  private readonly config: DecisionFusionConfig;

  constructor(config: Partial<DecisionFusionConfig> = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      weights: { ...DEFAULT_CONFIG.weights, ...(config.weights ?? {}) },
    } satisfies DecisionFusionConfig;
  }

  decide(
    snapshot: DataIngestionSnapshot,
    lighthouseEvent: LighthouseEvent | null,
    probabilityFusion?: ProbabilityFusion | null,
    autonomyHubSignal?: AutonomyHubSignal | null,
    modelSignals: ModelSignal[] = []
  ): DecisionSignal {
    if (!modelSignals.length) {
      throw new Error('NO_LIVE_EXTERNAL_MODEL_SIGNALS');
    }
    const now = Date.now();
    modelSignals.forEach(signal => validateModelSignal(signal, now));

    const modelConfidenceTotal = modelSignals.reduce((sum, signal) => sum + signal.confidence, 0);
    if (modelConfidenceTotal <= 0) {
      throw new Error('MODEL_SIGNAL_CONFIDENCE_UNAVAILABLE');
    }
    const ensembleScore = modelSignals.reduce(
      (sum, signal) => sum + signal.score * signal.confidence,
      0
    ) / modelConfidenceTotal;
    const ensembleConfidence = modelConfidenceTotal / modelSignals.length;

    const sentimentScore = snapshot.sentiment.length
      ? snapshot.sentiment.reduce((sum, item) => sum + item.score, 0) / snapshot.sentiment.length
      : null;
    const qgitaScore = lighthouseEvent
      ? lighthouseEvent.confidence * (lighthouseEvent.direction === 'long' ? 1 : -1)
      : null;
    const harmonic6DScore = probabilityFusion
      ? (probabilityFusion.fusedProbability - 0.5) * 2
      : null;
    const harmonicLock = probabilityFusion?.harmonicLock ?? false;
    const waveState = probabilityFusion?.waveState ?? 'NO_DATA';

    let autonomyHubScore: number | null = null;
    let autonomyHubAligned = false;
    if (autonomyHubSignal && autonomyHubSignal.direction !== 'NEUTRAL') {
      const direction = autonomyHubSignal.direction === 'BULLISH' ? 1 : -1;
      autonomyHubScore = autonomyHubSignal.strength * autonomyHubSignal.confidence * direction;
      const ensembleDirection = ensembleScore > 0 ? 'BULLISH' : ensembleScore < 0 ? 'BEARISH' : 'NEUTRAL';
      autonomyHubAligned = autonomyHubSignal.direction === ensembleDirection;
    }

    const candidates = [
      { value: ensembleScore, confidence: ensembleConfidence, weight: this.config.weights.ensemble },
      ...(sentimentScore === null ? [] : [{ value: sentimentScore, confidence: 1, weight: this.config.weights.sentiment }]),
      ...(qgitaScore === null ? [] : [{ value: qgitaScore, confidence: lighthouseEvent!.confidence, weight: this.config.weights.qgita }]),
      ...(harmonic6DScore === null ? [] : [{ value: harmonic6DScore, confidence: probabilityFusion!.confidence, weight: this.config.weights.harmonic6D }]),
      ...(autonomyHubScore === null ? [] : [{ value: autonomyHubScore, confidence: autonomyHubSignal!.confidence, weight: this.config.weights.autonomyHub }]),
    ];
    const activeWeight = candidates.reduce((sum, item) => sum + item.weight, 0);
    if (activeWeight <= 0) {
      throw new Error('NO_WEIGHTED_DECISION_EVIDENCE');
    }
    const finalScore = candidates.reduce((sum, item) => sum + item.value * item.weight, 0) / activeWeight;
    const confidence = candidates.reduce((sum, item) => sum + item.confidence * item.weight, 0) / activeWeight;

    let buyThreshold = this.config.buyThreshold;
    let sellThreshold = this.config.sellThreshold;
    if (waveState === 'CRYSTALLINE') {
      buyThreshold *= 0.8;
      sellThreshold *= 0.8;
    } else if (waveState === 'CHAOTIC') {
      buyThreshold *= 1.5;
      sellThreshold *= 1.5;
    }
    if (autonomyHubAligned && autonomyHubSignal && autonomyHubSignal.agreementRatio > 0.7) {
      buyThreshold *= 0.9;
      sellThreshold *= 0.9;
    }

    let action: DecisionAction = 'hold';
    if (confidence >= this.config.minimumConfidence) {
      if (finalScore > buyThreshold) action = 'buy';
      else if (finalScore < sellThreshold) action = 'sell';
    }

    return {
      action,
      positionSize: action === 'hold' ? 0 : Number((Math.min(1, Math.abs(finalScore)) * confidence).toFixed(3)),
      confidence,
      measuredWinRate: autonomyHubSignal?.numPredictors ? autonomyHubSignal.rollingWinRate : null,
      modelSignals,
      sentimentScore,
      harmonic6DScore,
      waveState,
      harmonicLock,
      autonomyHubAligned,
      truthStatus: 'real_derived',
      generated: false,
      sourceEventIds: [snapshot.sourceEventId, ...modelSignals.map(signal => signal.sourceEventId)],
    };
  }
}
