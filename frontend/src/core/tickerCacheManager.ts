/**
 * Ticker Cache Manager
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Fetches and caches ALL 800+ pairs from exchanges
 * Provides real-time ticker data for opportunity scanning
 * 
 * Gap Closure: Wired to Binance WebSocket for real-time updates
 */

import { supabase } from '@/integrations/supabase/client';
import { unifiedBus } from './unifiedBus';
import { temporalLadder, SYSTEMS } from './temporalLadder';
import { BinanceWebSocketClient, type MarketData } from './binanceWebSocket';

export interface CachedTicker {
  symbol: string;
  exchange: string;
  price: number;
  bidPrice: number;
  askPrice: number;
  volume: number;
  volumeUsd: number;
  high24h: number;
  low24h: number;
  priceChange24h: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
  dataSource: 'live' | 'cached' | 'stale' | 'websocket';
  truthStatus: 'real_derived';
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

export interface TickerCacheStats {
  totalTickers: number;
  liveTickers: number;
  staleTickers: number;
  websocketTickers: number;
  lastFullRefresh: number | null;
  avgVolatility: number | null;
  topGainers: string[];
  topLosers: string[];
  highVolume: string[];
  websocketConnected: boolean;
}

const REFRESH_INTERVAL_MS = 10000; // 10 seconds
const STALE_THRESHOLD_MS = 60000; // 1 minute
const MIN_VOLUME_USD = 100000; // Filter out low volume pairs

class TickerCacheManager {
  private cache: Map<string, CachedTicker> = new Map();
  private lastRefresh: number | null = null;
  private isRefreshing: boolean = false;
  private refreshInterval: ReturnType<typeof setInterval> | null = null;
  private listeners: Array<(tickers: CachedTicker[]) => void> = [];
  private isInitialized: boolean = false;
  
  // WebSocket client for real-time updates
  private wsClient: BinanceWebSocketClient | null = null;
  private wsConnected: boolean = false;

  constructor() {
    console.log('📊 Ticker Cache Manager initializing...');
  }

  /**
   * Initialize and start automatic refresh + WebSocket connection
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) return;

    temporalLadder.registerSystem(SYSTEMS.DATA_INGESTION);

    // Initial fetch via REST
    await this.refreshAll();

    // Start periodic refresh as backup
    this.refreshInterval = setInterval(() => {
      this.refreshAll().catch(console.error);
    }, REFRESH_INTERVAL_MS);

    // Initialize WebSocket for real-time BTCUSDT updates
    this.initializeWebSocket();

    this.isInitialized = true;
    console.log(`📊 Ticker Cache Manager initialized with ${this.cache.size} pairs + WebSocket`);
  }

  /**
   * Initialize Binance WebSocket for real-time price updates
   * Gap Closure: Wire WebSocket to orchestrator
   */
  private initializeWebSocket(): void {
    this.wsClient = new BinanceWebSocketClient('btcusdt');
    
    this.wsClient.onConnect(() => {
      console.log('📡 [TickerCache] WebSocket connected - real-time updates active');
      this.wsConnected = true;
    });
    
    this.wsClient.onDisconnect(() => {
      console.log('📡 [TickerCache] WebSocket disconnected');
      this.wsConnected = false;
    });
    
    this.wsClient.onError((error) => {
      console.warn('📡 [TickerCache] WebSocket error:', error.message);
      this.wsConnected = false;
    });
    
    this.wsClient.onData((data: MarketData) => {
      this.updateFromWebSocket('BTCUSDT', data);
    });
    
    // Connect
    this.wsClient.connect();
  }

  /**
   * Update ticker from WebSocket data
   */
  public updateFromWebSocket(symbol: string, data: MarketData): void {
    const key = `binance:${symbol}`;
    const updated: CachedTicker = {
      symbol,
      exchange: 'binance',
      price: data.price,
      bidPrice: data.bidPrice,
      askPrice: data.askPrice,
      volume: data.volume,
      volumeUsd: data.volumeUsd,
      high24h: data.high24h,
      low24h: data.low24h,
      priceChange24h: data.priceChange24h,
      volatility: data.volatility,
      momentum: data.momentum,
      spread: data.spread,
      timestamp: data.timestamp,
      dataSource: 'websocket',
      truthStatus: data.truthStatus,
      sourceId: data.sourceId,
      sourceTimestamp: data.sourceTimestamp,
      generatedValues: false,
    };
    
    this.cache.set(key, updated);
    this.notifyListeners();
  }

  /**
   * Check if WebSocket is connected
   */
  public isWebSocketConnected(): boolean {
    return this.wsConnected && this.wsClient?.isConnected() || false;
  }

  /**
   * Refresh all tickers from exchanges
   */
  public async refreshAll(): Promise<void> {
    if (this.isRefreshing) return;
    this.isRefreshing = true;

    const startTime = Date.now();
    try {
      console.log('[TickerCache] Refreshing all tickers...');

      const { data, error } = await supabase.functions.invoke('fetch-all-tickers', {
        body: { 
          exchanges: ['binance', 'kraken'],
          limit: 500 // Top 500 by volume
        }
      });

      if (error) {
        console.error('[TickerCache] API error:', error);
        return;
      }

      if (data?.success && Array.isArray(data.tickers)) {
        // Update cache
        for (const ticker of data.tickers) {
          const sourceTime = Date.parse(String(ticker.sourceTimestamp || ''));
          if (ticker.truthStatus !== 'real_derived' || ticker.generatedValues !== false ||
              !ticker.sourceId || !Number.isFinite(sourceTime) || Date.now() - sourceTime > STALE_THRESHOLD_MS) {
            continue;
          }
          const key = `${ticker.exchange}:${ticker.symbol}`;
          this.cache.set(key, {
            ...ticker,
            dataSource: 'live',
          });
        }

        this.lastRefresh = Date.now();

        // Mark old entries as stale
        for (const [key, ticker] of this.cache.entries()) {
          if (Date.now() - ticker.timestamp > STALE_THRESHOLD_MS) {
            this.cache.set(key, { ...ticker, dataSource: 'stale' });
          }
        }

        const elapsed = Date.now() - startTime;
        console.log(`[TickerCache] ✅ Refreshed ${data.tickers.length} tickers in ${elapsed}ms`);

        // Publish to UnifiedBus
        this.publishToUnifiedBus();

        // Notify listeners
        this.notifyListeners();

        // Heartbeat to Temporal Ladder
        const acceptedRatio = data.tickers.length > 0 ? this.getAllTickers().filter(t => t.dataSource !== 'stale').length / data.tickers.length : 0;
        temporalLadder.heartbeat(SYSTEMS.DATA_INGESTION, acceptedRatio);
      }
    } catch (error) {
      console.error('[TickerCache] Refresh error:', error);
      temporalLadder.unregisterSystem(SYSTEMS.DATA_INGESTION);
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Get all tickers from cache
   */
  public getAllTickers(): CachedTicker[] {
    const now = Date.now();
    return Array.from(this.cache.values()).map((ticker) =>
      now - ticker.timestamp > STALE_THRESHOLD_MS ? { ...ticker, dataSource: 'stale' as const } : ticker,
    );
  }

  /**
   * Get tickers filtered by volume
   */
  public getHighVolumeTickers(minVolumeUsd: number = MIN_VOLUME_USD): CachedTicker[] {
    return this.getAllTickers()
      .filter(t => t.volumeUsd >= minVolumeUsd)
      .sort((a, b) => b.volumeUsd - a.volumeUsd);
  }

  /**
   * Get ticker for specific symbol
   */
  public getTicker(symbol: string, exchange: string = 'binance'): CachedTicker | undefined {
    const ticker = this.cache.get(`${exchange}:${symbol}`);
    return ticker && Date.now() - ticker.timestamp <= STALE_THRESHOLD_MS ? ticker : undefined;
  }

  /**
   * Get tickers sorted by volatility (best opportunities)
   */
  public getVolatileTickers(minVolatility: number = 0.02): CachedTicker[] {
    return this.getAllTickers()
      .filter(t => t.volatility >= minVolatility && t.volumeUsd >= MIN_VOLUME_USD)
      .sort((a, b) => b.volatility - a.volatility);
  }

  /**
   * Get top gainers
   */
  public getTopGainers(limit: number = 20): CachedTicker[] {
    return this.getAllTickers()
      .filter(t => t.volumeUsd >= MIN_VOLUME_USD)
      .sort((a, b) => b.priceChange24h - a.priceChange24h)
      .slice(0, limit);
  }

  /**
   * Get top losers
   */
  public getTopLosers(limit: number = 20): CachedTicker[] {
    return this.getAllTickers()
      .filter(t => t.volumeUsd >= MIN_VOLUME_USD)
      .sort((a, b) => a.priceChange24h - b.priceChange24h)
      .slice(0, limit);
  }

  /**
   * Get cache statistics
   */
  public getStats(): TickerCacheStats {
    const tickers = this.getAllTickers();
    const now = Date.now();
    
    const liveTickers = tickers.filter(t => t.dataSource === 'live').length;
    const staleTickers = tickers.filter(t => now - t.timestamp > STALE_THRESHOLD_MS).length;
    const websocketTickers = tickers.filter(t => t.dataSource === 'websocket').length;
    
    const avgVolatility = tickers.length > 0
      ? tickers.reduce((sum, t) => sum + t.volatility, 0) / tickers.length 
      : null;

    return {
      totalTickers: tickers.length,
      liveTickers,
      staleTickers,
      websocketTickers,
      lastFullRefresh: this.lastRefresh,
      avgVolatility,
      topGainers: this.getTopGainers(5).map(t => t.symbol),
      topLosers: this.getTopLosers(5).map(t => t.symbol),
      highVolume: this.getHighVolumeTickers(1000000).slice(0, 10).map(t => t.symbol),
      websocketConnected: this.wsConnected,
    };
  }

  /**
   * Check if cache is fresh
   */
  public isFresh(): boolean {
    return this.lastRefresh !== null && Date.now() - this.lastRefresh < STALE_THRESHOLD_MS;
  }

  /**
   * Subscribe to ticker updates
   */
  public subscribe(listener: (tickers: CachedTicker[]) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners(): void {
    const tickers = this.getAllTickers();
    for (const listener of this.listeners) {
      try {
        listener(tickers);
      } catch (error) {
        console.error('[TickerCache] Listener error:', error);
      }
    }
  }

  private publishToUnifiedBus(): void {
    const stats = this.getStats();
    const observedTickers = this.getAllTickers();
    if (stats.totalTickers === 0 || observedTickers.length === 0) return;
    const sourceTimestamp = observedTickers.map((ticker) => ticker.sourceTimestamp).sort()[0];
    const sourceId = Array.from(new Set(observedTickers.map((ticker) => ticker.sourceId))).sort().join(',');
    const dataCompleteness = stats.liveTickers / stats.totalTickers;
    
    unifiedBus.publish({
      systemName: 'TickerCache',
      timestamp: Date.parse(sourceTimestamp),
      ready: this.isFresh(),
      coherence: dataCompleteness,
      confidence: dataCompleteness,
      signal: 'NEUTRAL',
      data: {
        totalTickers: stats.totalTickers,
        liveTickers: stats.liveTickers,
        staleTickers: stats.staleTickers,
        avgVolatility: stats.avgVolatility,
        topGainers: stats.topGainers,
        topLosers: stats.topLosers,
        highVolume: stats.highVolume,
        lastRefresh: this.lastRefresh,
        truthStatus: 'real_derived',
        sourceId,
        sourceTimestamp,
        generatedValues: false,
      },
    });
  }

  /**
   * Cleanup
   */
  public destroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
    
    // Disconnect WebSocket
    if (this.wsClient) {
      this.wsClient.disconnect();
      this.wsClient = null;
    }
    
    this.cache.clear();
    this.listeners = [];
    this.isInitialized = false;
    this.wsConnected = false;
  }
}

export const tickerCacheManager = new TickerCacheManager();
