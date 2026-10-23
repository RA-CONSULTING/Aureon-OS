"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.StreamBuilder = exports.BinanceWebSocket = void 0;
const ws_1 = __importDefault(require("ws"));
const events_1 = require("events");
// ============================================================================
// BINANCE WEBSOCKET CLIENT
// ============================================================================
class BinanceWebSocket extends events_1.EventEmitter {
    constructor() {
        super();
        this.ws = null;
        this.baseUrl = 'wss://stream.binance.com:9443';
        this.streams = new Set();
        this.subscriptionId = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start at 1 second
        this.pingInterval = null;
        this.isConnecting = false;
        this.isClosing = false;
        // Market data aggregation
        this.marketSnapshots = new Map();
        this.tradeBuffer = new Map();
        this.lastUpdateTime = new Map();
    }
    // ==========================================================================
    // CONNECTION MANAGEMENT
    // ==========================================================================
    async connect(streams = []) {
        if (this.ws && this.ws.readyState === ws_1.default.OPEN) {
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
            this.ws = new ws_1.default(url);
            // Setup event handlers
            this.ws.on('open', () => this.onOpen(streams));
            this.ws.on('message', (data) => this.onMessage(data));
            this.ws.on('error', (error) => this.onError(error));
            this.ws.on('close', (code, reason) => this.onClose(code, reason));
            this.ws.on('ping', (data) => this.onPing(data));
            this.ws.on('pong', (data) => this.onPong(data));
        }
        catch (error) {
            this.isConnecting = false;
            console.error('🌈 Connection failed:', error);
            throw error;
        }
    }
    onOpen(initialStreams) {
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
    onMessage(data) {
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
        }
        catch (error) {
            console.error('🌈 Message parse error:', error);
        }
    }
    onError(error) {
        console.error('🌈 WebSocket error:', error.message);
        this.emit('error', error);
    }
    onClose(code, reason) {
        console.log(`🌈 WebSocket CLOSED - Code: ${code}, Reason: ${reason.toString() || 'Unknown'}`);
        this.stopHeartbeat();
        this.ws = null;
        if (!this.isClosing && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
        this.emit('disconnected', { code, reason: reason.toString() });
    }
    onPing(data) {
        // Server sent ping - respond with pong
        if (this.ws && this.ws.readyState === ws_1.default.OPEN) {
            this.ws.pong(data);
        }
    }
    onPong(data) {
        // Server responded to our ping
        // console.log('🌈 Pong received');
    }
    // ==========================================================================
    // HEARTBEAT & RECONNECTION
    // ==========================================================================
    startHeartbeat() {
        this.stopHeartbeat();
        // Send ping every 20 seconds (Binance spec)
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === ws_1.default.OPEN) {
                this.ws.ping();
            }
        }, 20000);
    }
    stopHeartbeat() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
    scheduleReconnect() {
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
    subscribe(streamNames) {
        if (!this.ws || this.ws.readyState !== ws_1.default.OPEN) {
            console.warn('🌈 Cannot subscribe - WebSocket not connected');
            return;
        }
        const subscription = {
            method: 'SUBSCRIBE',
            params: streamNames,
            id: ++this.subscriptionId
        };
        this.ws.send(JSON.stringify(subscription));
        streamNames.forEach(s => this.streams.add(s));
        console.log(`🌈 Subscribed to: ${streamNames.join(', ')}`);
    }
    unsubscribe(streamNames) {
        if (!this.ws || this.ws.readyState !== ws_1.default.OPEN) {
            console.warn('🌈 Cannot unsubscribe - WebSocket not connected');
            return;
        }
        const subscription = {
            method: 'UNSUBSCRIBE',
            params: streamNames,
            id: ++this.subscriptionId
        };
        this.ws.send(JSON.stringify(subscription));
        streamNames.forEach(s => this.streams.delete(s));
        console.log(`🌈 Unsubscribed from: ${streamNames.join(', ')}`);
    }
    listSubscriptions() {
        if (!this.ws || this.ws.readyState !== ws_1.default.OPEN) {
            console.warn('🌈 Cannot list subscriptions - WebSocket not connected');
            return;
        }
        const request = {
            method: 'LIST_SUBSCRIPTIONS',
            id: ++this.subscriptionId
        };
        this.ws.send(JSON.stringify(request));
    }
    handleSubscriptionResponse(response) {
        if (response.result === null) {
            // Success
            this.emit('subscription-response', { id: response.id, success: true });
        }
        else if (response.result && Array.isArray(response.result)) {
            // List of subscriptions
            console.log(`🌈 Active subscriptions: ${response.result.join(', ')}`);
            this.emit('subscriptions-list', response.result);
        }
        else if (response.error) {
            // Error
            console.error('🌈 Subscription error (ID %s):', response.id, response.error);
            this.emit('subscription-error', response.error);
        }
    }
    // ==========================================================================
    // MARKET DATA PROCESSING
    // ==========================================================================
    processMarketEvent(stream, data) {
        const eventType = data.e;
        const symbol = data.s;
        // Update last update time
        this.lastUpdateTime.set(symbol, Date.now());
        // Emit specific event types
        switch (eventType) {
            case 'trade':
                this.processTrade(data);
                this.emit('trade', data);
                break;
            case 'aggTrade':
                this.processAggTrade(data);
                this.emit('aggTrade', data);
                break;
            case 'depthUpdate':
                this.processDepthUpdate(data);
                this.emit('depth', data);
                break;
            case '24hrMiniTicker':
                this.processMiniTicker(data);
                this.emit('miniTicker', data);
                break;
            case 'kline':
                this.processKline(data);
                this.emit('kline', data);
                break;
            default:
                // Book ticker has no 'e' field
                if (data.u && data.b && data.a) {
                    this.processBookTicker(data);
                    this.emit('bookTicker', data);
                }
        }
        // Emit generic market event
        this.emit('market-event', { stream, data });
    }
    processTrade(trade) {
        const { s: symbol, p: price, q: qty, T: time } = trade;
        // Buffer trades for momentum calculation
        if (!this.tradeBuffer.has(symbol)) {
            this.tradeBuffer.set(symbol, []);
        }
        const buffer = this.tradeBuffer.get(symbol);
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
    processAggTrade(aggTrade) {
        const { s: symbol, p: price, q: qty, T: time } = aggTrade;
        this.updateSnapshot(symbol, {
            price: parseFloat(price),
            volume: parseFloat(qty),
            timestamp: time
        });
    }
    processDepthUpdate(depth) {
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
    processBookTicker(ticker) {
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
    processMiniTicker(ticker) {
        const { s: symbol, c: close, v: volume, E: eventTime } = ticker;
        this.updateSnapshot(symbol, {
            price: parseFloat(close),
            volume: parseFloat(volume),
            timestamp: eventTime
        });
    }
    processKline(kline) {
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
    updateSnapshot(symbol, update) {
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
    getSnapshot(symbol) {
        return this.marketSnapshots.get(symbol);
    }
    getAllSnapshots() {
        return Array.from(this.marketSnapshots.values());
    }
    isConnected() {
        return this.ws !== null && this.ws.readyState === ws_1.default.OPEN;
    }
    getActiveStreams() {
        return Array.from(this.streams);
    }
    async disconnect() {
        this.isClosing = true;
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        console.log('🌈 WebSocket disconnected');
    }
}
exports.BinanceWebSocket = BinanceWebSocket;
// ============================================================================
// STREAM NAME BUILDERS
// ============================================================================
class StreamBuilder {
    /**
     * Trade stream - Raw trade information
     * Update: Real-time
     */
    static trade(symbol) {
        return `${symbol.toLowerCase()}@trade`;
    }
    /**
     * Aggregate trade stream - Aggregated for single taker order
     * Update: Real-time
     */
    static aggTrade(symbol) {
        return `${symbol.toLowerCase()}@aggTrade`;
    }
    /**
     * Diff depth stream - Order book updates
     * Update: 1000ms or 100ms
     */
    static depth(symbol, speed = '100ms') {
        return speed === '100ms'
            ? `${symbol.toLowerCase()}@depth@100ms`
            : `${symbol.toLowerCase()}@depth`;
    }
    /**
     * Partial book depth - Top N levels
     * Update: 1000ms or 100ms
     */
    static partialDepth(symbol, levels, speed = '100ms') {
        return speed === '100ms'
            ? `${symbol.toLowerCase()}@depth${levels}@100ms`
            : `${symbol.toLowerCase()}@depth${levels}`;
    }
    /**
     * Book ticker - Best bid/ask
     * Update: Real-time
     */
    static bookTicker(symbol) {
        return `${symbol.toLowerCase()}@bookTicker`;
    }
    /**
     * Mini ticker - 24hr rolling window
     * Update: 1000ms
     */
    static miniTicker(symbol) {
        return `${symbol.toLowerCase()}@miniTicker`;
    }
    /**
     * All market mini tickers
     * Update: 1000ms
     */
    static allMiniTickers() {
        return '!miniTicker@arr';
    }
    /**
     * Kline/Candlestick stream
     * Update: 1000ms for 1s, 2000ms for others
     */
    static kline(symbol, interval) {
        return `${symbol.toLowerCase()}@kline_${interval}`;
    }
    /**
     * Average price stream
     * Update: 1000ms
     */
    static avgPrice(symbol) {
        return `${symbol.toLowerCase()}@avgPrice`;
    }
    /**
     * Full ticker - 24hr statistics
     * Update: 1000ms
     */
    static ticker(symbol) {
        return `${symbol.toLowerCase()}@ticker`;
    }
    /**
     * All market tickers
     * Update: 1000ms
     */
    static allTickers() {
        return '!ticker@arr';
    }
    /**
     * Rolling window ticker
     * Update: 1000ms
     */
    static rollingTicker(symbol, windowSize) {
        return `${symbol.toLowerCase()}@ticker_${windowSize}`;
    }
    /**
     * Build AUREON default streams - optimized for Master Equation
     */
    static aureonDefaults(symbol) {
        return [
            StreamBuilder.aggTrade(symbol), // Price + momentum
            StreamBuilder.depth(symbol, '100ms'), // Order book dynamics
            StreamBuilder.miniTicker(symbol), // 24hr stats
            StreamBuilder.kline(symbol, '1m') // Candlestick pattern
        ];
    }
}
exports.StreamBuilder = StreamBuilder;
