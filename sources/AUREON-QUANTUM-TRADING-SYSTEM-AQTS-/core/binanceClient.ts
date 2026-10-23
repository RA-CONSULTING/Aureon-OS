/**
 * Binance API Client - Production-grade live trading integration
 * - REST API for account info, order placement, execution
 * - WebSocket for real-time price feeds & order updates
 * - Secure credential management with encryption
 * - Testnet/Live mode toggle
 */

import crypto from 'crypto';

export interface BinanceConfig {
  apiKey: string;
  apiSecret: string;
  testnet?: boolean;
  recvWindow?: number;
}

export interface OrderParams {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity?: number; // optional when quoteOrderQty provided
  price?: number; // required for LIMIT orders
  timeInForce?: 'GTC' | 'IOC' | 'FOK'; // Good Till Cancel, Immediate or Cancel, Fill or Kill
  // For MARKET orders, Binance allows spending by quote amount instead of base quantity
  // e.g., for ADAETH, quoteOrderQty is in ETH
  quoteOrderQty?: number;
}

export interface OrderResponse {
  symbol: string;
  orderId: number;
  clientOrderId: string;
  transactTime: number;
  price: string;
  origQty: string;
  executedQty: string;
  cummulativeQuoteQty: string;
  status: 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' | 'PENDING_CANCEL' | 'REJECTED' | 'EXPIRED';
  timeInForce: string;
  type: string;
  side: string;
  fills: Array<{ price: string; qty: string; commission: string; commissionAsset: string }>;
}

export interface AccountInfo {
  makerCommission: number;
  takerCommission: number;
  buyerCommission: number;
  sellerCommission: number;
  canTrade: boolean;
  canWithdraw: boolean;
  canDeposit: boolean;
  updateTime: number;
  balances: Array<{ asset: string; free: string; locked: string }>;
}

export interface PriceTickerEvent {
  symbol: string;
  price: number;
  time: number;
}

export class BinanceClient {
  private apiKey: string;
  private apiSecret: string;
  private baseUrl: string;
  private wsBaseUrl: string;
  private recvWindow: number = 5000;

  constructor(config: BinanceConfig) {
    this.apiKey = config.apiKey;
    this.apiSecret = config.apiSecret;
    this.recvWindow = config.recvWindow || 5000;

    if (config.testnet) {
      this.baseUrl = 'https://testnet.binance.vision/api';
      this.wsBaseUrl = 'wss://stream.testnet.binance.vision:9443/ws';
    } else {
      this.baseUrl = 'https://api.binance.com/api';
      this.wsBaseUrl = 'wss://stream.binance.com:9443/ws';
    }
  }

  /**
   * Sign request parameters using HMAC-SHA256
   */
  private signParams(params: Record<string, string | number>): string {
    const queryString = this.buildQueryString(params);
    const signature = crypto
      .createHmac('sha256', this.apiSecret)
      .update(queryString)
      .digest('hex');
    return `${queryString}&signature=${signature}`;
  }

  /**
   * Build query string from params object
   */
  private buildQueryString(params: Record<string, string | number>): string {
    return Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
      .join('&');
  }

  /**
   * Make authenticated request to Binance REST API
   */
  private async request<T>(
    method: 'GET' | 'POST' | 'DELETE',
    endpoint: string,
    params?: Record<string, string | number>
  ): Promise<T> {
    const timestamp = Date.now();
    const fullParams = { timestamp, ...params };
    const signedParams = this.signParams(fullParams);
    const url = `${this.baseUrl}${endpoint}?${signedParams}`;

    const response = await fetch(url, {
      method,
      headers: {
        'X-MBX-APIKEY': this.apiKey,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`Binance API error (${response.status}): ${JSON.stringify(errorData)}`);
    }

    return response.json();
  }

  /**
   * Get account information (balances, trading status)
   */
  async getAccount(): Promise<AccountInfo> {
    return this.request<AccountInfo>('GET', '/v3/account');
  }

  /**
   * Get current price of a symbol (public endpoint, no auth required)
   */
  async getPrice(symbol: string): Promise<number> {
    const url = `${this.baseUrl}/v3/ticker/price?symbol=${symbol}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Binance API error (${response.status}): Failed to fetch price`);
    }
    const data = (await response.json()) as { symbol: string; price: string };
    return Number(data.price);
  }

  /**
   * Get 24h ticker stats (volume, price change, etc)
   */
  async get24hStats(symbol: string): Promise<{
    symbol: string;
    priceChange: string;
    priceChangePercent: string;
    weightedAvgPrice: string;
    prevClosePrice: string;
    lastPrice: string;
    bidPrice: string;
    askPrice: string;
    highPrice: string;
    lowPrice: string;
    volume: string;
    quoteAssetVolume: string;
    count: number;
  }> {
    return this.request('GET', '/v3/ticker/24hr', { symbol });
  }

  /**
   * Get 24h ticker stats for all symbols
   */
  async get24hrTickers(): Promise<Array<{
    symbol: string;
    priceChange: string;
    priceChangePercent: string;
    weightedAvgPrice: string;
    prevClosePrice: string;
    lastPrice: string;
    bidPrice: string;
    askPrice: string;
    highPrice: string;
    lowPrice: string;
    volume: string;
    quoteVolume: string;
    quoteAssetVolume: string;
    count: number;
  }>> {
    const url = `${this.baseUrl}/v3/ticker/24hr`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Binance API error (${response.status}): Failed to fetch 24h tickers`);
    }
    return response.json();
  }

  /**
   * Get exchange info (symbols, filters)
   */
  async getExchangeInfo(symbols?: string[]): Promise<any> {
    const url = symbols && symbols.length
      ? `${this.baseUrl}/v3/exchangeInfo?symbols=${encodeURIComponent(JSON.stringify(symbols))}`
      : `${this.baseUrl}/v3/exchangeInfo`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Binance API error (${resp.status}): Failed to fetch exchangeInfo`);
    }
    return resp.json();
  }

  /**
   * Get order book depth (public endpoint) for liquidity checks
   */
  async getOrderBook(
    symbol: string,
    limit: 5 | 10 | 20 | 50 | 100 | 500 | 1000 = 10
  ): Promise<{ lastUpdateId: number; bids: [string, string][]; asks: [string, string][] }> {
    const url = `${this.baseUrl}/v3/depth?symbol=${symbol}&limit=${limit}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Binance API error (${resp.status}): Failed to fetch order book for ${symbol}`);
    }
    return resp.json();
  }

  /**
   * Place a market or limit order
   */
  async placeOrder(order: OrderParams): Promise<OrderResponse> {
    const params: Record<string, string | number> = {
      symbol: order.symbol,
      side: order.side,
      type: order.type,
    };

    // Prefer quoteOrderQty for MARKET orders when provided; otherwise use quantity
    if (order.type === 'MARKET' && order.quoteOrderQty && order.quoteOrderQty > 0) {
      params.quoteOrderQty = order.quoteOrderQty;
    } else if (order.quantity && order.quantity > 0) {
      params.quantity = order.quantity;
    }

    if (order.type === 'LIMIT') {
      if (!order.price) throw new Error('Price required for LIMIT orders');
      params.price = order.price;
      params.timeInForce = order.timeInForce || 'GTC';
    }

    return this.request<OrderResponse>('POST', '/v3/order', params);
  }

  /**
   * Cancel an open order
   */
  async cancelOrder(symbol: string, orderId: number): Promise<OrderResponse> {
    return this.request<OrderResponse>('DELETE', '/v3/order', {
      symbol,
      orderId,
    });
  }

  /**
   * Get order status
   */
  async getOrder(symbol: string, orderId: number): Promise<OrderResponse> {
    return this.request<OrderResponse>('GET', '/v3/order', {
      symbol,
      orderId,
    });
  }

  /**
   * Get all open orders (or specific symbol)
   */
  async getOpenOrders(symbol?: string): Promise<OrderResponse[]> {
    return this.request<OrderResponse[]>('GET', '/v3/openOrders', symbol ? { symbol } : {});
  }

  /**
   * Get account trade list for a symbol (requires auth)
   */
  async getMyTrades(symbol: string, limit: number = 20): Promise<Array<any>> {
    return this.request<Array<any>>('GET', '/v3/myTrades', { symbol, limit });
  }

  /**
   * Subscribe to real-time price updates via WebSocket
   * Returns a subscription handle that can be closed
   */
  subscribeToPrice(symbol: string, callback: (event: PriceTickerEvent) => void): () => void {
    const streamName = `${symbol.toLowerCase()}@trade`;
    const ws = new WebSocket(`${this.wsBaseUrl}/${streamName}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callback({
          symbol: data.s,
          price: Number(data.p),
          time: data.T,
        });
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error(`WebSocket error for ${symbol}:`, err);
    };

    // Return unsubscribe function
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }

  /**
   * Subscribe to multiple price streams with a single WebSocket connection
   */
  subscribeToMultiplePrices(
    symbols: string[],
    callback: (event: PriceTickerEvent) => void
  ): () => void {
    const streams = symbols.map((s) => `${s.toLowerCase()}@trade`);
    const streamParam = streams.join('/');
    const ws = new WebSocket(`${this.wsBaseUrl}/stream?streams=${streamParam}`);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.data) {
          const data = message.data;
          callback({
            symbol: data.s,
            price: Number(data.p),
            time: data.T,
          });
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }

  /**
   * Get Binance server time (for sync validation)
   */
  async getServerTime(): Promise<number> {
    const data = await this.request<{ serverTime: number }>('GET', '/v3/time');
    return data.serverTime;
  }
}
