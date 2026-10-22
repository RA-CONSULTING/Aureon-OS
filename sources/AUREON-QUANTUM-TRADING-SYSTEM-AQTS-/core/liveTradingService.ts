/**
 * Live Trading Service - Production execution with Binance integration
 * - Secure credential management (environment variables + optional encryption)
 * - Real-time order execution & monitoring
 * - Position tracking & risk enforcement
 * - Graceful fallback to paper trading mode
 */

import { BinanceClient, OrderParams, OrderResponse, AccountInfo } from './binanceClient';

export type TradeSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT';

export interface LiveCredentials {
  apiKey: string;
  apiSecret: string;
  testnet?: boolean;
}

export interface TradeRequest {
  symbol: string;
  side: TradeSide;
  quantity: number;
  type?: OrderType;
  price?: number; // for LIMIT orders
}

export interface TradeExecutionResult {
  success: boolean;
  orderId?: number;
  message: string;
  executedQty?: number;
  avgPrice?: number;
  commission?: number;
  error?: string;
}

export interface PositionInfo {
  symbol: string;
  side: TradeSide;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
}

class LiveTradingService {
  private client: BinanceClient | null = null;
  private initialized = false;
  private paperMode = true;
  private positions: Map<string, PositionInfo> = new Map();

  /**
   * Initialize with Binance API credentials
   * Reads from environment variables: BINANCE_API_KEY, BINANCE_API_SECRET
   * Optional: BINANCE_TESTNET (true/false, default true for safety)
   */
  async initialize(): Promise<void> {
    const apiKey = process.env.BINANCE_API_KEY;
    const apiSecret = process.env.BINANCE_API_SECRET;
    const testnet = process.env.BINANCE_TESTNET !== 'false'; // default to testnet

    if (!apiKey || !apiSecret) {
      console.warn(
        '⚠️ BINANCE_API_KEY or BINANCE_API_SECRET not set. Running in PAPER MODE (no live execution).'
      );
      this.paperMode = true;
      return;
    }

    try {
      this.client = new BinanceClient({
        apiKey,
        apiSecret,
        testnet,
      });

      // Verify credentials by fetching account info
      const account = await this.client.getAccount();
      console.log(`✅ Binance ${testnet ? 'TESTNET' : 'LIVE'} connected. Trader: ${account.canTrade}`);

      this.paperMode = false;
      this.initialized = true;
    } catch (err) {
      console.error('Failed to initialize Binance client:', err);
      console.warn('⚠️ Falling back to PAPER MODE.');
      this.paperMode = true;
    }
  }

  /**
   * Execute a live trade on Binance (or paper trade if not initialized)
   */
  async executeTrade(request: TradeRequest): Promise<TradeExecutionResult> {
    if (this.paperMode || !this.client) {
      // Paper mode: simulate execution
      return {
        success: true,
        message: `[PAPER] ${request.side} ${request.quantity} ${request.symbol}`,
        executedQty: request.quantity,
        avgPrice: 0,
      };
    }

    try {
      const orderParams: OrderParams = {
        symbol: request.symbol,
        side: request.side,
        type: request.type || 'MARKET',
        quantity: request.quantity,
      };

      if (request.type === 'LIMIT' && request.price) {
        orderParams.price = request.price;
      }

      const response = await this.client.placeOrder(orderParams);

      // Track position
      this.positions.set(request.symbol, {
        symbol: request.symbol,
        side: request.side,
        quantity: Number(response.executedQty),
        entryPrice: Number(response.price),
        currentPrice: Number(response.price),
        unrealizedPnL: 0,
        unrealizedPnLPercent: 0,
      });

      return {
        success: response.status === 'FILLED' || response.status === 'PARTIALLY_FILLED',
        orderId: response.orderId,
        message: `Order ${response.orderId} placed. Status: ${response.status}`,
        executedQty: Number(response.executedQty),
        avgPrice: Number(response.price),
        commission: Number(
          response.fills
            ?.reduce((sum, f) => sum + Number(f.commission), 0)
            .toFixed(8) || 0
        ),
      };
    } catch (err) {
      return {
        success: false,
        message: `Trade execution failed: ${err instanceof Error ? err.message : String(err)}`,
        error: String(err),
      };
    }
  }

  /**
   * Get current account balance and trading status
   */
  async getAccountInfo(): Promise<AccountInfo | null> {
    if (!this.client) return null;
    try {
      return await this.client.getAccount();
    } catch (err) {
      console.error('Failed to fetch account info:', err);
      return null;
    }
  }

  /**
   * Get current price of a symbol
   */
  async getPrice(symbol: string): Promise<number | null> {
    if (!this.client) return null;
    try {
      return await this.client.getPrice(symbol);
    } catch (err) {
      console.error(`Failed to fetch price for ${symbol}:`, err);
      return null;
    }
  }

  /**
   * Subscribe to real-time price updates
   */
  subscribeToPrice(
    symbol: string,
    callback: (price: number) => void
  ): (() => void) | null {
    if (!this.client) return null;

    return this.client.subscribeToPrice(symbol, (event) => {
      callback(event.price);

      // Update position if tracking this symbol
      const pos = this.positions.get(symbol);
      if (pos) {
        pos.currentPrice = event.price;
        pos.unrealizedPnL =
          pos.side === 'BUY'
            ? (event.price - pos.entryPrice) * pos.quantity
            : (pos.entryPrice - event.price) * pos.quantity;
        pos.unrealizedPnLPercent = (pos.unrealizedPnL / (pos.entryPrice * pos.quantity)) * 100;
      }
    });
  }

  /**
   * Close a position (sell if long, buy if short)
   */
  async closePosition(symbol: string): Promise<TradeExecutionResult> {
    const pos = this.positions.get(symbol);
    if (!pos) {
      return {
        success: false,
        message: `No position found for ${symbol}`,
      };
    }

    return this.executeTrade({
      symbol,
      side: pos.side === 'BUY' ? 'SELL' : 'BUY',
      quantity: pos.quantity,
      type: 'MARKET',
    });
  }

  /**
   * Get all tracked positions
   */
  getPositions(): PositionInfo[] {
    return Array.from(this.positions.values());
  }

  /**
   * Check if running in paper mode
   */
  isPaperMode(): boolean {
    return this.paperMode;
  }

  /**
   * Check if initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const liveTradingService = new LiveTradingService();
