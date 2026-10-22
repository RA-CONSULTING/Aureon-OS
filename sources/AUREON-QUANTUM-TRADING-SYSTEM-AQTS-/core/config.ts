import { DataIngestionConfig } from './dataIngestion';
import { DecisionFusionConfig } from './decisionFusion';
import { ExecutionConfig } from './executionEngine';
import { QGITAConfig } from './qgitaEngine';
import { RiskConfig } from './riskManagement';

export interface AnalyticsConfig {
  performanceHistory: number;
  sentimentHistory: number;
}

export interface AQTSConfig {
  mode: 'paper' | 'live';
  tradingPairs: string[];
  ingestion: DataIngestionConfig;
  qgita: QGITAConfig;
  decision: DecisionFusionConfig;
  risk: RiskConfig;
  execution: ExecutionConfig;
  analytics: AnalyticsConfig;
}

export type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends Array<infer U>
    ? Array<U>
    : T[K] extends object
      ? DeepPartial<T[K]>
      : T[K];
};

export const defaultAQTSConfig: AQTSConfig = {
  mode: 'paper',
  tradingPairs: ['BTC/USDT', 'ETH/USDT'],
  ingestion: {
    initialPrice: 42000,
    exchanges: [
      { name: 'Binance', liquidityWeight: 1.0, latencyMs: 25 },
      { name: 'Coinbase', liquidityWeight: 0.8, latencyMs: 35 },
      { name: 'Kraken', liquidityWeight: 0.6, latencyMs: 40 },
      { name: 'Bybit', liquidityWeight: 0.9, latencyMs: 32 },
      { name: 'KuCoin', liquidityWeight: 0.5, latencyMs: 45 },
    ],
  },
  qgita: {
    fibonacciSequence: [5, 8, 13, 21, 34, 55],
    minConfidence: 0.35,
    neutralConfidence: 0.45,
    historyLimit: 300,
  },
  decision: {
    buyThreshold: 0.15,
    sellThreshold: -0.15,
    minimumConfidence: 0.35,
    weights: {
      ensemble: 0.6,
      sentiment: 0.2,
      qgita: 0.2,
    },
  },
  risk: {
    initialEquity: 100000,
    maxPortfolioRisk: 0.03,
    maxLeverage: 5,
    circuitBreaker: 0.1,
    riskPerTradeCap: 0.04,
    kellyMultiplier: 1,
    minHoldMinutes: 45,
    maxHoldMinutes: 360,
  },
  execution: {
    maxSlippageBps: 18,
    latencyRange: { min: 35, max: 125 },
    partialFillProbability: 0.15,
  },
  analytics: {
    performanceHistory: 500,
    sentimentHistory: 250,
  },
};

export const mergeConfig = (base: AQTSConfig, overrides?: DeepPartial<AQTSConfig>): AQTSConfig => {
  if (!overrides) {
    return base;
  }

  const result: AQTSConfig = { ...base } as AQTSConfig;

  for (const key of Object.keys(overrides) as (keyof AQTSConfig)[]) {
    const overrideValue = overrides[key];
    if (overrideValue === undefined) continue;

    const baseValue = base[key];
    if (Array.isArray(overrideValue)) {
      (result[key] as unknown) = overrideValue.slice();
    } else if (typeof overrideValue === 'object' && overrideValue !== null && typeof baseValue === 'object' && baseValue !== null) {
      const merged = mergeConfigRecursive(baseValue as any as Record<string, unknown>, overrideValue as any as Record<string, unknown>);
      (result as any)[key] = merged;
    } else {
      (result[key] as unknown) = overrideValue as AQTSConfig[typeof key];
    }
  }

  return result;
};

const mergeConfigRecursive = (
  base: Record<string, unknown>,
  overrides: Record<string, unknown>
): Record<string, unknown> => {
  const result: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(overrides)) {
    const baseValue = base[key];
    if (Array.isArray(value)) {
      result[key] = value.slice();
    } else if (value !== null && typeof value === 'object' && baseValue !== null && typeof baseValue === 'object') {
      result[key] = mergeConfigRecursive(baseValue as Record<string, unknown>, value as Record<string, unknown>);
    } else {
      result[key] = value;
    }
  }
  return result;
};

export const config = defaultAQTSConfig;

