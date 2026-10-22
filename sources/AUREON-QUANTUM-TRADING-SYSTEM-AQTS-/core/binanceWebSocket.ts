/**
 * AUREON QUANTUM TRADING SYSTEM (AQTS)
 * Binance WebSocket Market Data Streams
 * 
 * "Taste the Rainbow" - Real-time sensory perception of market dynamics
 * 
 * Streams:
 * - Trade streams (@trade) - Raw trade information, real-time
 * - Aggregate trades (@aggTrade) - Aggregated taker orders
 * - Depth streams (@depth) - Order book updates (100ms)
 * - Best bid/ask (@bookTicker) - Top of book in real-time
 * - Mini ticker (@miniTicker) - 24hr rolling window stats
 * - Kline streams (@kline_1m) - Candlestick updates
 * 
 * Architecture:
 * - Single WebSocket connection with combined streams
 * - Auto-reconnect with exponential backoff
 * - Heartbeat ping/pong (20s intervals)
 * - Stream subscription management
 * - Rate limit: 5 messages/second, max 1024 streams
 */

import WebSocket from 'ws';
import { EventEmitter } from 'events';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface TradeEvent {
  e: 'trade';
  E: number;           // Event time
  s: string;           // Symbol
  t: number;           // Trade ID
  p: string;           // Price
  q: string;           // Quantity
  T: number;           // Trade time
  m: boolean;          // Is buyer maker?
  M: boolean;          // Ignore
}

export interface AggTradeEvent {
  e: 'aggTrade';
  E: number;           // Event time
  s: string;           // Symbol
  a: number;           // Aggregate trade ID
  p: string;           // Price
  q: string;           // Quantity
  f: number;           // First trade ID
  l: number;           // Last trade ID
  T: number;           // Trade time
  m: boolean;          // Is buyer maker?
  M: boolean;          // Ignore
}

export interface DepthUpdateEvent {
  e: 'depthUpdate';
  E: number;           // Event time
  s: string;           // Symbol
  U: number;           // First update ID
  u: number;           // Final update ID
  b: [string, string][]; // Bids [[price, qty]]
  a: [string, string][]; // Asks [[price, qty]]
}

export interface BookTickerEvent {
  u: number;           // Order book update ID
  s: string;           // Symbol
  b: string;           // Best bid price
  B: string;           // Best bid qty
  a: string;           // Best ask price
  A: string;           // Best ask qty
}

export interface MiniTickerEvent {
  e: '24hrMiniTicker';
  E: number;           // Event time
  s: string;           // Symbol
  c: string;           // Close price
  o: string;           // Open price
  h: string;           // High price
  l: string;           // Low price
  v: string;           // Total traded base volume
  q: string;           // Total traded quote volume
}

export interface KlineEvent {
  e: 'kline';
  E: number;           // Event time
  s: string;           // Symbol
  k: {
    t: number;         // Kline start time
    T: number;         // Kline close time
    s: string;         // Symbol
    i: string;         // Interval
    f: number;         // First trade ID
    L: number;         // Last trade ID
    o: string;         // Open price
    c: string;         // Close price
    h: string;         // High price
    l: string;         // Low price
    v: string;         // Volume
    n: number;         // Number of trades
    x: boolean;        // Is kline closed?
    q: string;         // Quote volume
    V: string;         // Taker buy base volume
    Q: string;         // Taker buy quote volume
    B: string;         // Ignore
  };
}

export type MarketEvent = TradeEvent | AggTradeEvent | DepthUpdateEvent | BookTickerEvent | MiniTickerEvent | KlineEvent;

export interface StreamSubscription {
  method: 'SUBSCRIBE' | 'UNSUBSCRIBE';
  params: string[];
  id: number;
}

export interface MarketSnapshot {
  symbol: string;
  timestamp: number;
  price: number;
  volume: number;
  trades: number;
  bidPrice?: number;
  askPrice?: number;
  spread?: number;
  volatility?: number;
  momentum?: number;
}

// ============================================================================
// BINANCE WEBSOCKET CLIENT
// ============================================================================

export class BinanceWebSocket extends EventEmitter {
  private ws: WebSocket | null = null;
  private baseUrl = 'wss://stream.binance.com:9443';
  private streams: Set<string> = new Set();
  private subscriptionId = 0;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start at 1 second
  private pingInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isClosing = false;
  
  // Market data aggregation
  private marketSnapshots = new Map<string, MarketSnapshot>();
  private tradeBuffer = new Map<string, TradeEvent[]>();
  private lastUpdateTime = new Map<string, number>();

  constructor() {
    super();
  }

  // ==========================================================================
  // CONNECTION MANAGEMENT
  // ==========================================================================

  public async connect(streams: string[] = []): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('🌈 WebSocket already connected');
      return;
    }

    if (this.isConnecting) {
      console.log('🌈 Connection already in progress...');
      return;
    }

    this.isConnecting = true;
    this.isClosing = false;

    try {
      // Build connection URL with combined streams
      const url = streams.length > 0
        ? `${this.baseUrl}/stream?streams=${streams.join('/')}`
        : `${this.baseUrl}/ws`;

      console.log(`🌈 Connecting to Binance WebSocket...`);
      console.log(`   URL: ${url}`);
      
      this.ws = new WebSocket(url);

      // Setup event handlers
      this.ws.on('open', () => this.onOpen(streams));
      this.ws.on('message', (data) => this.onMessage(data));
      this.ws.on('error', (error) => this.onError(error));
      this.ws.on('close', (code, reason) => this.onClose(code, reason));
      this.ws.on('ping', (data) => this.onPing(data));
      this.ws.on('pong', (data) => this.onPong(data));

    } catch (error) {
      this.isConnecting = false;
      console.error('🌈 Connection failed:', error);
      throw error;
    }
  }

  private onOpen(initialStreams: string[]): void {
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;

    console.log('🌈 WebSocket CONNECTED - Tasting the rainbow...');
    
    // Store initial streams
    initialStreams.forEach(s => this.streams.add(s));

    // Start heartbeat (ping every 20s as per Binance spec)
    this.startHeartbeat();

    this.emit('connected');
  }

  private onMessage(data: WebSocket.Data): void {
    try {
      const message = JSON.parse(data.toString());

      // Handle subscription responses
      if (message.result !== undefined && message.id !== undefined) {
        this.handleSubscriptionResponse(message);
        return;
      }

      // Handle combined stream format
      if (message.stream && message.data) {
        this.processMarketEvent(message.stream, message.data);
        return;
      }

      // Handle single stream format
      if (message.e) {
        this.processMarketEvent('single', message);
        return;
      }

    } catch (error) {
      console.error('🌈 Message parse error:', error);
    }
  }

  private onError(error: Error): void {
    console.error('🌈 WebSocket error:', error.message);
    this.emit('error', error);
  }

  private onClose(code: number, reason: Buffer): void {
    console.log(`🌈 WebSocket CLOSED - Code: ${code}, Reason: ${reason.toString() || 'Unknown'}`);
    
    this.stopHeartbeat();
    this.ws = null;

    if (!this.isClosing && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    }

    this.emit('disconnected', { code, reason: reason.toString() });
  }

  private onPing(data: Buffer): void {
    // Server sent ping - respond with pong
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.pong(data);
    }
  }

  private onPong(data: Buffer): void {
    // Server responded to our ping
    // console.log('🌈 Pong received');
  }

  // ==========================================================================
  // HEARTBEAT & RECONNECTION
  // ==========================================================================

  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    // Send ping every 20 seconds (Binance spec)
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.ping();
      }
    }, 20000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 60000);
    
    console.log(`🌈 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      const streamArray = Array.from(this.streams);
      this.connect(streamArray);
    }, delay);
  }

  // ==========================================================================
  // STREAM SUBSCRIPTION MANAGEMENT
  // ==========================================================================

  public subscribe(streamNames: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('🌈 Cannot subscribe - WebSocket not connected');
      return;
    }

    const subscription: StreamSubscription = {
      method: 'SUBSCRIBE',
      params: streamNames,
      id: ++this.subscriptionId
    };

    this.ws.send(JSON.stringify(subscription));
    streamNames.forEach(s => this.streams.add(s));
    
    console.log(`🌈 Subscribed to: ${streamNames.join(', ')}`);
  }

  public unsubscribe(streamNames: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('🌈 Cannot unsubscribe - WebSocket not connected');
      return;
    }

    const subscription: StreamSubscription = {
      method: 'UNSUBSCRIBE',
      params: streamNames,
      id: ++this.subscriptionId
    };

    this.ws.send(JSON.stringify(subscription));
    streamNames.forEach(s => this.streams.delete(s));
    
    console.log(`🌈 Unsubscribed from: ${streamNames.join(', ')}`);
  }

  public listSubscriptions(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('🌈 Cannot list subscriptions - WebSocket not connected');
      return;
    }

    const request = {
      method: 'LIST_SUBSCRIPTIONS',
      id: ++this.subscriptionId
    };

    this.ws.send(JSON.stringify(request));
  }

  private handleSubscriptionResponse(response: any): void {
    if (response.result === null) {
      // Success
      this.emit('subscription-response', { id: response.id, success: true });
    } else if (response.result && Array.isArray(response.result)) {
      // List of subscriptions
      console.log(`🌈 Active subscriptions: ${response.result.join(', ')}`);
      this.emit('subscriptions-list', response.result);
    } else if (response.error) {
      // Error
      console.error('🌈 Subscription error (ID %s):', response.id, response.error);
      this.emit('subscription-error', response.error);
    }
  }

  // ==========================================================================
  // MARKET DATA PROCESSING
  // ==========================================================================

  private processMarketEvent(stream: string, data: any): void {
    const eventType = data.e;
    const symbol = data.s;

    // Update last update time
    this.lastUpdateTime.set(symbol, Date.now());

    // Emit specific event types
    switch (eventType) {
      case 'trade':
        this.processTrade(data as TradeEvent);
        this.emit('trade', data);
        break;
      
      case 'aggTrade':
        this.processAggTrade(data as AggTradeEvent);
        this.emit('aggTrade', data);
        break;
      
      case 'depthUpdate':
        this.processDepthUpdate(data as DepthUpdateEvent);
        this.emit('depth', data);
        break;
      
      case '24hrMiniTicker':
        this.processMiniTicker(data as MiniTickerEvent);
        this.emit('miniTicker', data);
        break;
      
      case 'kline':
        this.processKline(data as KlineEvent);
        this.emit('kline', data);
        break;
      
      default:
        // Book ticker has no 'e' field
        if (data.u && data.b && data.a) {
          this.processBookTicker(data as BookTickerEvent);
          this.emit('bookTicker', data);
        }
    }

    // Emit generic market event
    this.emit('market-event', { stream, data });
  }

  private processTrade(trade: TradeEvent): void {
    const { s: symbol, p: price, q: qty, T: time } = trade;
    
    // Buffer trades for momentum calculation
    if (!this.tradeBuffer.has(symbol)) {
      this.tradeBuffer.set(symbol, []);
    }
    
    const buffer = this.tradeBuffer.get(symbol)!;
    buffer.push(trade);
    
    // Keep only last 100 trades
    if (buffer.length > 100) {
      buffer.shift();
    }

    // Update market snapshot
    this.updateSnapshot(symbol, {
      price: parseFloat(price),
      volume: parseFloat(qty),
      timestamp: time
    });
  }

  private processAggTrade(aggTrade: AggTradeEvent): void {
    const { s: symbol, p: price, q: qty, T: time } = aggTrade;
    
    this.updateSnapshot(symbol, {
      price: parseFloat(price),
      volume: parseFloat(qty),
      timestamp: time
    });
  }

  private processDepthUpdate(depth: DepthUpdateEvent): void {
    const { s: symbol, b: bids, a: asks } = depth;
    
    if (bids.length > 0 && asks.length > 0) {
      const bestBid = parseFloat(bids[0][0]);
      const bestAsk = parseFloat(asks[0][0]);
      const spread = bestAsk - bestBid;
      
      this.updateSnapshot(symbol, {
        bidPrice: bestBid,
        askPrice: bestAsk,
        spread: spread
      });
    }
  }

  private processBookTicker(ticker: BookTickerEvent): void {
    const { s: symbol, b: bidPrice, a: askPrice } = ticker;
    
    const bid = parseFloat(bidPrice);
    const ask = parseFloat(askPrice);
    const spread = ask - bid;
    
    this.updateSnapshot(symbol, {
      bidPrice: bid,
      askPrice: ask,
      spread: spread
    });
  }

  private processMiniTicker(ticker: MiniTickerEvent): void {
    const { s: symbol, c: close, v: volume, E: eventTime } = ticker;
    
    this.updateSnapshot(symbol, {
      price: parseFloat(close),
      volume: parseFloat(volume),
      timestamp: eventTime
    });
  }

  private processKline(kline: KlineEvent): void {
    const { s: symbol, k } = kline;
    
    if (k.x) { // Only process closed klines
      const { c: close, v: volume, n: trades } = k;
      
      this.updateSnapshot(symbol, {
        price: parseFloat(close),
        volume: parseFloat(volume),
        trades: trades
      });
    }
  }

  private updateSnapshot(symbol: string, update: Partial<MarketSnapshot>): void {
    let snapshot = this.marketSnapshots.get(symbol);
    
    if (!snapshot) {
      snapshot = {
        symbol,
        timestamp: Date.now(),
        price: 0,
        volume: 0,
        trades: 0
      };
      this.marketSnapshots.set(symbol, snapshot);
    }

    // Merge update
    Object.assign(snapshot, update);
    snapshot.timestamp = Date.now();

    // Calculate volatility and momentum if we have trade history
    const tradeBuffer = this.tradeBuffer.get(symbol);
    if (tradeBuffer && tradeBuffer.length >= 10) {
      const prices = tradeBuffer.map(t => parseFloat(t.p));
      const recent = prices.slice(-10);
      
      const avgPrice = recent.reduce((a, b) => a + b, 0) / recent.length;
      const variance = recent.reduce((sum, p) => sum + Math.pow(p - avgPrice, 2), 0) / recent.length;
      snapshot.volatility = Math.sqrt(variance) / avgPrice; // Coefficient of variation
      
      const oldPrice = recent[0];
      const newPrice = recent[recent.length - 1];
      snapshot.momentum = (newPrice - oldPrice) / oldPrice;
    }

    this.emit('snapshot-update', snapshot);
  }

  // ==========================================================================
  // PUBLIC API
  // ==========================================================================

  public getSnapshot(symbol: string): MarketSnapshot | undefined {
    return this.marketSnapshots.get(symbol);
  }

  public getAllSnapshots(): MarketSnapshot[] {
    return Array.from(this.marketSnapshots.values());
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  public getActiveStreams(): string[] {
    return Array.from(this.streams);
  }

  public async disconnect(): Promise<void> {
    this.isClosing = true;
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    console.log('🌈 WebSocket disconnected');
  }
}

// ============================================================================
// STREAM NAME BUILDERS
// ============================================================================

export class StreamBuilder {
  /**
   * Trade stream - Raw trade information
   * Update: Real-time
   */
  static trade(symbol: string): string {
    return `${symbol.toLowerCase()}@trade`;
  }

  /**
   * Aggregate trade stream - Aggregated for single taker order
   * Update: Real-time
   */
  static aggTrade(symbol: string): string {
    return `${symbol.toLowerCase()}@aggTrade`;
  }

  /**
   * Diff depth stream - Order book updates
   * Update: 1000ms or 100ms
   */
  static depth(symbol: string, speed: '100ms' | '1000ms' = '100ms'): string {
    return speed === '100ms' 
      ? `${symbol.toLowerCase()}@depth@100ms`
      : `${symbol.toLowerCase()}@depth`;
  }

  /**
   * Partial book depth - Top N levels
   * Update: 1000ms or 100ms
   */
  static partialDepth(symbol: string, levels: 5 | 10 | 20, speed: '100ms' | '1000ms' = '100ms'): string {
    return speed === '100ms'
      ? `${symbol.toLowerCase()}@depth${levels}@100ms`
      : `${symbol.toLowerCase()}@depth${levels}`;
  }

  /**
   * Book ticker - Best bid/ask
   * Update: Real-time
   */
  static bookTicker(symbol: string): string {
    return `${symbol.toLowerCase()}@bookTicker`;
  }

  /**
   * Mini ticker - 24hr rolling window
   * Update: 1000ms
   */
  static miniTicker(symbol: string): string {
    return `${symbol.toLowerCase()}@miniTicker`;
  }

  /**
   * All market mini tickers
   * Update: 1000ms
   */
  static allMiniTickers(): string {
    return '!miniTicker@arr';
  }

  /**
   * Kline/Candlestick stream
   * Update: 1000ms for 1s, 2000ms for others
   */
  static kline(symbol: string, interval: '1s' | '1m' | '3m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '6h' | '8h' | '12h' | '1d' | '3d' | '1w' | '1M'): string {
    return `${symbol.toLowerCase()}@kline_${interval}`;
  }

  /**
   * Average price stream
   * Update: 1000ms
   */
  static avgPrice(symbol: string): string {
    return `${symbol.toLowerCase()}@avgPrice`;
  }

  /**
   * Full ticker - 24hr statistics
   * Update: 1000ms
   */
  static ticker(symbol: string): string {
    return `${symbol.toLowerCase()}@ticker`;
  }

  /**
   * All market tickers
   * Update: 1000ms
   */
  static allTickers(): string {
    return '!ticker@arr';
  }

  /**
   * Rolling window ticker
   * Update: 1000ms
   */
  static rollingTicker(symbol: string, windowSize: '1h' | '4h' | '1d'): string {
    return `${symbol.toLowerCase()}@ticker_${windowSize}`;
  }

  /**
   * Build AUREON default streams - optimized for Master Equation
   */
  static aureonDefaults(symbol: string): string[] {
    return [
      StreamBuilder.aggTrade(symbol),      // Price + momentum
      StreamBuilder.depth(symbol, '100ms'), // Order book dynamics
      StreamBuilder.miniTicker(symbol),     // 24hr stats
      StreamBuilder.kline(symbol, '1m')     // Candlestick pattern
    ];
  }
}
