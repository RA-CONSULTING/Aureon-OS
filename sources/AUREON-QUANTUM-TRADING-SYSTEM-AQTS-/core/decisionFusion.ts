import { DataIngestionSnapshot } from './dataIngestion';
import { LighthouseEvent } from './qgitaEngine';

type DecisionAction = 'buy' | 'sell' | 'hold';

type EnsembleModel = 'lstm' | 'randomForest' | 'xgboost' | 'transformer';

export interface ModelSignal {
  model: EnsembleModel;
  score: number;
  confidence: number;
}

export interface DecisionSignal {
  action: DecisionAction;
  positionSize: number;
  confidence: number;
  modelSignals: ModelSignal[];
  sentimentScore: number;
}

export interface DecisionFusionConfig {
  buyThreshold: number;
  sellThreshold: number;
  weights: {
    ensemble: number;
    sentiment: number;
    qgita: number;
  };
  minimumConfidence: number;
}

const DEFAULT_CONFIG: DecisionFusionConfig = {
  buyThreshold: 0.15,
  sellThreshold: -0.15,
  weights: {
    ensemble: 0.6,
    sentiment: 0.2,
    qgita: 0.2,
  },
  minimumConfidence: 0.35,
};

const generateModelSignal = (model: EnsembleModel, snapshot: DataIngestionSnapshot): ModelSignal => {
  const trend = snapshot.consolidatedOHLCV.close - snapshot.consolidatedOHLCV.open;
  const volatility = snapshot.consolidatedOHLCV.high - snapshot.consolidatedOHLCV.low;
  const sentiment = snapshot.sentiment.reduce((acc, s) => acc + s.score, 0) / snapshot.sentiment.length;
  const normalizedTrend = Math.tanh(trend / Math.max(1, volatility));
  const baseConfidence = 0.4 + Math.random() * 0.5;

  const bias = model === 'lstm' ? 0.2 : model === 'randomForest' ? -0.1 : model === 'xgboost' ? 0.1 : 0;
  const score = normalizedTrend + sentiment * 0.2 + bias + (Math.random() - 0.5) * 0.1;

  return {
    model,
    score,
    confidence: Math.max(0.2, Math.min(0.95, baseConfidence - Math.abs(score) * 0.1)),
  } satisfies ModelSignal;
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

  decide(snapshot: DataIngestionSnapshot, lighthouseEvent: LighthouseEvent | null): DecisionSignal {
    const models: EnsembleModel[] = ['lstm', 'randomForest', 'xgboost', 'transformer'];
    const modelSignals = models.map(model => generateModelSignal(model, snapshot));

    const aggregateScore = modelSignals.reduce((acc, signal) => acc + signal.score * signal.confidence, 0);
    const totalConfidence = modelSignals.reduce((acc, signal) => acc + signal.confidence, 0);
    const normalizedScore = totalConfidence === 0 ? 0 : aggregateScore / totalConfidence;

    const sentimentScore = snapshot.sentiment.reduce((acc, s) => acc + s.score, 0) / snapshot.sentiment.length;
    const qgitaBoost = lighthouseEvent ? lighthouseEvent.confidence * (lighthouseEvent.direction === 'long' ? 1 : -1) : 0;

    const weights = this.config.weights;
    const weightTotal = weights.ensemble + weights.sentiment + weights.qgita;
    const normalizedWeights = {
      ensemble: weights.ensemble / weightTotal,
      sentiment: weights.sentiment / weightTotal,
      qgita: weights.qgita / weightTotal,
    };

    const finalScore =
      normalizedScore * normalizedWeights.ensemble +
      sentimentScore * normalizedWeights.sentiment +
      qgitaBoost * normalizedWeights.qgita;

    let action: DecisionAction = 'hold';
    if (finalScore > this.config.buyThreshold) {
      action = 'buy';
    } else if (finalScore < this.config.sellThreshold) {
      action = 'sell';
    }

    const baseSize = Math.min(1, Math.abs(finalScore));
    const qgitaConfidence = lighthouseEvent?.confidence ?? 0.4;
    const combinedConfidence = Math.max(
      this.config.minimumConfidence,
      Math.min(1, Math.abs(finalScore) + qgitaConfidence * normalizedWeights.qgita)
    );

    return {
      action,
      positionSize: Number((baseSize * (0.5 + qgitaConfidence)).toFixed(3)),
      confidence: combinedConfidence,
      modelSignals,
      sentimentScore,
    } satisfies DecisionSignal;
  }
}
