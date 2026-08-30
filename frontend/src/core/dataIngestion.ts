import { OHLCV } from '../types';

export interface ExchangeConfig {
  name: string;
  liquidityWeight: number;
  latencyMs: number;
}

export interface DataIngestionConfig {
  initialPrice: number;
  exchanges: ExchangeConfig[];
}

export interface ExchangeFeedSnapshot {
  exchange: string;
  price: number;
  volume24h: number;
  fundingRate: number;
  spread: number;
  latencyMs: number;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  side: 'bid' | 'ask';
}

export interface OnChainMetricSnapshot {
  activeAddresses: number;
  exchangeFlows: number;
  whaleAlerts: number;
}

export interface SentimentSnapshot {
  source: 'twitter' | 'reddit' | 'telegram';
  score: number;
  trendingKeywords: string[];
}

export interface NewsHeadline {
  source: string;
  title: string;
  impactScore: number;
}

export interface MacroSignalSnapshot {
  fearGreedIndex: number;
  fundingRateAverage: number;
  liquidations24h: number;
}

export type DataTruthStatus = 'live' | 'real_derived';

export interface DataIngestionSnapshot {
  timestamp: number;
  exchangeFeeds: ExchangeFeedSnapshot[];
  orderBookDepth: OrderBookLevel[];
  onChain: OnChainMetricSnapshot;
  sentiment: SentimentSnapshot[];
  news: NewsHeadline[];
  macro: MacroSignalSnapshot;
  consolidatedOHLCV: OHLCV;
  dataSource: 'LIVE';
  truthStatus: DataTruthStatus;
  generated: false;
  sourceId: string;
  sourceEventId: string;
  sourceTimestamp: number;
  freshnessTtlMs: number;
}

/**
 * Retained only to give old callers an explicit migration error. A scalar
 * market value cannot truthfully stand in for exchange, order-book, on-chain,
 * sentiment, news, and macro observations.
 */
export interface RealMarketData {
  price: number;
  volume: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
}

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const normalizedTimestampMs = (value: number): number => value < 10_000_000_000 ? value * 1000 : value;

/**
 * Pass-through gateway for a complete, provenance-bearing provider snapshot.
 * It never expands one ticker into multiple exchanges and never fills missing
 * domains with zero, neutral sentiment, or default macro values.
 */
export class DataIngestionEngine {
  private snapshot: DataIngestionSnapshot | null = null;

  constructor(_config: Partial<DataIngestionConfig> = {}) {}

  public ingestLiveData(_data: RealMarketData): never {
    throw new Error(
      'SCALAR_MARKET_INPUT_RETIRED: use ingestLiveSnapshot with complete provider observations and provenance'
    );
  }

  public ingestLiveSnapshot(snapshot: DataIngestionSnapshot): void {
    if (!snapshot || snapshot.generated !== false) {
      throw new Error('PROVIDER_SNAPSHOT_REQUIRED');
    }
    if (snapshot.truthStatus !== 'live' && snapshot.truthStatus !== 'real_derived') {
      throw new Error('INVALID_TRUTH_STATUS');
    }
    if (!snapshot.sourceId || !snapshot.sourceEventId) {
      throw new Error('SOURCE_PROVENANCE_REQUIRED');
    }
    if (!isFiniteNumber(snapshot.sourceTimestamp) || !isFiniteNumber(snapshot.freshnessTtlMs)) {
      throw new Error('SOURCE_FRESHNESS_REQUIRED');
    }
    const sourceTimestampMs = normalizedTimestampMs(snapshot.sourceTimestamp);
    const ageMs = Date.now() - sourceTimestampMs;
    if (ageMs < -30_000 || ageMs > snapshot.freshnessTtlMs) {
      throw new Error(`PROVIDER_SNAPSHOT_STALE:${ageMs}`);
    }
    if (!snapshot.exchangeFeeds.length) {
      throw new Error('EXCHANGE_FEED_OBSERVATION_REQUIRED');
    }
    const market = snapshot.consolidatedOHLCV;
    if (![market.open, market.high, market.low, market.close, market.volume].every(isFiniteNumber)) {
      throw new Error('OHLCV_OBSERVATION_INVALID');
    }
    if (market.close <= 0 || market.high < market.low || market.volume < 0) {
      throw new Error('OHLCV_OBSERVATION_OUT_OF_RANGE');
    }
    this.snapshot = {
      ...snapshot,
      timestamp: normalizedTimestampMs(snapshot.timestamp),
      sourceTimestamp: sourceTimestampMs,
      dataSource: 'LIVE',
    };
  }

  public hasLiveData(): boolean {
    if (!this.snapshot) return false;
    const ageMs = Date.now() - this.snapshot.sourceTimestamp;
    return ageMs >= -30_000 && ageMs <= this.snapshot.freshnessTtlMs;
  }

  public getDataSource(): 'LIVE' | 'STALE' | 'NO_DATA' {
    if (!this.snapshot) return 'NO_DATA';
    return this.hasLiveData() ? 'LIVE' : 'STALE';
  }

  public next(): DataIngestionSnapshot {
    const status = this.getDataSource();
    if (status !== 'LIVE' || !this.snapshot) {
      throw new Error(status === 'STALE' ? 'PROVIDER_SNAPSHOT_STALE' : 'NO_PROVIDER_SNAPSHOT');
    }
    return this.snapshot;
  }
}
