/**
 * Multi-exchange production adapter. Missing or stale provider receipts are
 * represented as no_data; a previous balance is never relabelled as current.
 */

import { ExchangeType, EXCHANGE_FEES } from './unifiedExchangeClient';
import { temporalLadder, SYSTEMS } from './temporalLadder';
import { unifiedBus } from './unifiedBus';
import { supabase } from '@/integrations/supabase/client';

const MAX_BALANCE_AGE_MS = 5 * 60 * 1000;
const MAX_TICKER_AGE_MS = 5 * 60 * 1000;
const SUPPORTED_EXCHANGES: ExchangeType[] = ['binance', 'kraken', 'alpaca', 'capital'];

const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const fresh = (value: unknown, maxAgeMs: number): value is string => {
  if (typeof value !== 'string') return false;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) && Date.now() - timestamp >= 0 && Date.now() - timestamp <= maxAgeMs;
};

export interface ConsolidatedBalance {
  asset: string;
  balances: Record<string, { free: number; locked: number; total: number }>;
  totalFree: number;
  totalLocked: number;
  grandTotal: number;
  usdValue: number | null;
}

export interface ExchangeStatus {
  exchange: ExchangeType;
  connected: boolean;
  lastUpdate: number | null;
  balanceCount: number | null;
  totalUsdValue: number | null;
  truthStatus: 'live' | 'no_data';
  sourceTimestamp: string | null;
  generatedValues: false;
  error?: string;
}

export interface MultiExchangeState {
  exchanges: ExchangeStatus[];
  consolidatedBalances: ConsolidatedBalance[];
  totalEquityUsd: number | null;
  lastUpdate: number | null;
  truthStatus: 'real_derived' | 'no_data';
  sourceId: string | null;
  sourceTimestamp: string | null;
  generatedValues: false;
}

export interface ProviderTicker {
  symbol: string;
  price: number;
  bidPrice: number;
  askPrice: number;
  volume: number;
  timestamp: number;
  truthStatus: 'real_derived';
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

export class MultiExchangeClient {
  private statusCache = new Map<ExchangeType, ExchangeStatus>();
  private consolidatedBalances: ConsolidatedBalance[] = [];
  private listeners: Array<(state: MultiExchangeState) => void> = [];
  private updateInterval: ReturnType<typeof setInterval> | null = null;
  private isInitialized = false;
  private totalEquityUsd: number | null = null;
  private lastUpdate: number | null = null;
  private sourceId: string | null = null;
  private sourceTimestamp: string | null = null;

  public async initialize(): Promise<void> {
    if (this.isInitialized) return;
    temporalLadder.registerSystem(SYSTEMS.QUANTUM_QUACKERS);
    this.markNoData('Awaiting authenticated provider balances');
    this.startPeriodicUpdates();
    this.isInitialized = true;
  }

  public async fetchAllBalances(): Promise<MultiExchangeState> {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      this.markNoData('No authenticated session');
      return this.finishFetch();
    }

    try {
      const { data, error } = await supabase.functions.invoke('get-user-balances', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (error) throw error;
      if (data?.truthStatus !== 'real_derived' || data?.generatedValues !== false ||
          !finite(data?.totalEquityUsd) || data.totalEquityUsd < 0 || !Array.isArray(data?.balances)) {
        throw new Error('BALANCE_RESPONSE_NO_VERIFIED_EQUITY');
      }

      const liveRows = data.balances.filter((row: any) =>
        row?.connected === true && row?.truthStatus === 'live' && row?.generatedValues === false &&
        fresh(row?.sourceTimestamp, MAX_BALANCE_AGE_MS) && Array.isArray(row?.assets),
      );
      if (liveRows.length === 0) throw new Error('NO_FRESH_PROVIDER_BALANCE_RECEIPTS');

      this.statusCache.clear();
      for (const exchange of SUPPORTED_EXCHANGES) {
        const row = data.balances.find((candidate: any) => candidate?.exchange === exchange);
        const isLive = row?.connected === true && row?.truthStatus === 'live' &&
          row?.generatedValues === false && fresh(row?.sourceTimestamp, MAX_BALANCE_AGE_MS) &&
          Array.isArray(row?.assets);
        this.statusCache.set(exchange, isLive ? {
          exchange,
          connected: true,
          lastUpdate: Date.parse(row.sourceTimestamp),
          balanceCount: row.assets.length,
          totalUsdValue: finite(row.totalUsd) ? row.totalUsd : null,
          truthStatus: 'live',
          sourceTimestamp: row.sourceTimestamp,
          generatedValues: false,
          error: row.error,
        } : this.noDataStatus(exchange, row?.error ?? 'No fresh provider receipt'));
      }

      const assetMap = new Map<string, ConsolidatedBalance>();
      for (const row of liveRows) {
        for (const asset of row.assets) {
          const free = Number(asset.free);
          const locked = Number(asset.locked);
          if (!asset.asset || !finite(free) || !finite(locked) || free < 0 || locked < 0) continue;
          const usdValue = asset.valuationTruthStatus === 'real_derived' && finite(asset.usdValue)
            ? asset.usdValue
            : null;
          const existing = assetMap.get(asset.asset);
          if (existing) {
            existing.totalFree += free;
            existing.totalLocked += locked;
            existing.grandTotal += free + locked;
            existing.usdValue = finite(existing.usdValue) && finite(usdValue) ? existing.usdValue + usdValue : null;
            existing.balances[row.exchange] = { free, locked, total: free + locked };
          } else {
            assetMap.set(asset.asset, {
              asset: asset.asset,
              totalFree: free,
              totalLocked: locked,
              grandTotal: free + locked,
              usdValue,
              balances: { [row.exchange]: { free, locked, total: free + locked } },
            });
          }
        }
      }

      this.consolidatedBalances = Array.from(assetMap.values()).sort((a, b) =>
        (b.usdValue ?? Number.NEGATIVE_INFINITY) - (a.usdValue ?? Number.NEGATIVE_INFINITY),
      );
      this.totalEquityUsd = data.totalEquityUsd;
      const sourceTimes = liveRows.map((row: any) => row.sourceTimestamp).sort();
      this.sourceTimestamp = sourceTimes[0];
      this.sourceId = liveRows.map((row: any) => `${row.exchange}:account`).sort().join(',');
      this.lastUpdate = Date.now();
    } catch (error) {
      this.markNoData(error instanceof Error ? error.message : String(error));
    }

    return this.finishFetch();
  }

  private finishFetch(): MultiExchangeState {
    const state = this.getState();
    this.notifyListeners(state);
    const liveCount = state.exchanges.filter((exchange) => exchange.truthStatus === 'live').length;
    if (state.truthStatus === 'real_derived' && state.exchanges.length > 0) {
      const healthRatio = liveCount / state.exchanges.length;
      temporalLadder.heartbeat(SYSTEMS.QUANTUM_QUACKERS, healthRatio);
      unifiedBus.publish({
        systemName: 'MultiExchange',
        timestamp: Date.parse(state.sourceTimestamp as string),
        ready: liveCount > 0,
        coherence: healthRatio,
        confidence: healthRatio,
        signal: 'NEUTRAL',
        data: {
          truthStatus: state.truthStatus,
          sourceId: state.sourceId,
          sourceTimestamp: state.sourceTimestamp,
          generatedValues: false,
          totalEquityUsd: state.totalEquityUsd,
          connectedExchanges: liveCount,
          exchanges: state.exchanges,
        },
      });
    }
    return state;
  }

  public getAvailableBalanceForTrading(quoteAsset = 'USDT'): number | null {
    const quoteBalance = this.consolidatedBalances.find((balance) => balance.asset === quoteAsset);
    return quoteBalance && finite(quoteBalance.totalFree) ? quoteBalance.totalFree : null;
  }

  public calculatePositionSize(riskPercentage: number, quoteAsset = 'USDT'):
    { positionSizeUsd: number | null; availableBalance: number | null; riskAmount: number | null } {
    const availableBalance = this.getAvailableBalanceForTrading(quoteAsset);
    if (!finite(availableBalance) || !finite(this.totalEquityUsd) || !finite(riskPercentage) ||
        riskPercentage <= 0 || riskPercentage > 1) {
      return { positionSizeUsd: null, availableBalance, riskAmount: null };
    }
    const riskAmount = this.totalEquityUsd * riskPercentage;
    return {
      positionSizeUsd: Math.min(riskAmount, availableBalance * 0.95),
      availableBalance,
      riskAmount,
    };
  }

  public getConsolidatedBalances(): ConsolidatedBalance[] {
    return this.consolidatedBalances.map((balance) => ({ ...balance, balances: { ...balance.balances } }));
  }

  public getTotalEquityUsd(): number | null {
    return this.totalEquityUsd;
  }

  public getState(): MultiExchangeState {
    const hasFreshAggregate = this.sourceTimestamp !== null && fresh(this.sourceTimestamp, MAX_BALANCE_AGE_MS) &&
      finite(this.totalEquityUsd);
    return {
      exchanges: Array.from(this.statusCache.values()),
      consolidatedBalances: this.getConsolidatedBalances(),
      totalEquityUsd: hasFreshAggregate ? this.totalEquityUsd : null,
      lastUpdate: hasFreshAggregate ? this.lastUpdate : null,
      truthStatus: hasFreshAggregate ? 'real_derived' : 'no_data',
      sourceId: hasFreshAggregate ? this.sourceId : null,
      sourceTimestamp: hasFreshAggregate ? this.sourceTimestamp : null,
      generatedValues: false,
    };
  }

  public getBestExchangeForSymbol(_symbol: string): ExchangeType | null {
    let bestExchange: ExchangeType | null = null;
    let lowestFee = Number.POSITIVE_INFINITY;
    for (const status of this.statusCache.values()) {
      if (status.truthStatus !== 'live') continue;
      const fees = EXCHANGE_FEES[status.exchange];
      if (fees && fees.taker < lowestFee) {
        lowestFee = fees.taker;
        bestExchange = status.exchange;
      }
    }
    return bestExchange;
  }

  public async getTickersFromAllExchanges(symbol: string): Promise<Map<ExchangeType, ProviderTicker | null>> {
    const results = new Map<ExchangeType, ProviderTicker | null>(SUPPORTED_EXCHANGES.map((exchange) => [exchange, null]));
    const eligible = Array.from(this.statusCache.values())
      .filter((status) => status.truthStatus === 'live' && ['binance', 'kraken'].includes(status.exchange))
      .map((status) => status.exchange);
    if (eligible.length === 0) return results;

    const { data, error } = await supabase.functions.invoke('fetch-all-tickers', {
      body: { symbols: [symbol], exchanges: eligible, limit: 10 },
    });
    if (error || data?.truthStatus !== 'real_derived' || data?.generatedValues !== false || !Array.isArray(data?.tickers)) {
      return results;
    }
    for (const ticker of data.tickers) {
      const exchange = ticker.exchange as ExchangeType;
      if (!eligible.includes(exchange) || ticker.symbol !== symbol || ticker.truthStatus !== 'real_derived' ||
          ticker.generatedValues !== false || !fresh(ticker.sourceTimestamp, MAX_TICKER_AGE_MS) ||
          ![ticker.price, ticker.bidPrice, ticker.askPrice, ticker.volume, ticker.timestamp].every(finite) ||
          ticker.price <= 0 || ticker.bidPrice <= 0 || ticker.askPrice <= 0 || ticker.askPrice < ticker.bidPrice) continue;
      results.set(exchange, {
        symbol,
        price: ticker.price,
        bidPrice: ticker.bidPrice,
        askPrice: ticker.askPrice,
        volume: ticker.volume,
        timestamp: ticker.timestamp,
        truthStatus: 'real_derived',
        sourceId: ticker.sourceId,
        sourceTimestamp: ticker.sourceTimestamp,
        generatedValues: false,
      });
    }
    return results;
  }

  public subscribe(listener: (state: MultiExchangeState) => void): () => void {
    this.listeners.push(listener);
    return () => { this.listeners = this.listeners.filter((candidate) => candidate !== listener); };
  }

  private notifyListeners(state: MultiExchangeState): void {
    this.listeners.forEach((listener) => listener(state));
  }

  private noDataStatus(exchange: ExchangeType, error: string): ExchangeStatus {
    return {
      exchange,
      connected: false,
      lastUpdate: null,
      balanceCount: null,
      totalUsdValue: null,
      truthStatus: 'no_data',
      sourceTimestamp: null,
      generatedValues: false,
      error,
    };
  }

  private markNoData(error: string): void {
    this.statusCache.clear();
    SUPPORTED_EXCHANGES.forEach((exchange) => this.statusCache.set(exchange, this.noDataStatus(exchange, error)));
    this.consolidatedBalances = [];
    this.totalEquityUsd = null;
    this.lastUpdate = null;
    this.sourceId = null;
    this.sourceTimestamp = null;
  }

  private startPeriodicUpdates(): void {
    if (this.updateInterval) return;
    this.updateInterval = setInterval(() => this.fetchAllBalances().catch(console.error), 30_000);
    this.fetchAllBalances().catch(console.error);
  }

  public destroy(): void {
    if (this.updateInterval) clearInterval(this.updateInterval);
    this.updateInterval = null;
    this.listeners = [];
    this.markNoData('Client destroyed');
    this.isInitialized = false;
  }
}

export const multiExchangeClient = new MultiExchangeClient();
