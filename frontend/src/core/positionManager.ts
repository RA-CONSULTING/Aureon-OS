/**
 * Position Manager
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Tracks active positions with TP/SL and trailing stops
 * Like Python aureon_unified_ecosystem.py position management
 */

import { temporalLadder, SYSTEMS } from './temporalLadder';
import { trailingStopManager } from './trailingStopManager';
import { supabase } from '@/integrations/supabase/client';

export interface Position {
  id: string;
  symbol: string;
  exchange: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  quantity: number;
  positionSizeUsd: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  takeProfitPrice: number;
  stopLossPrice: number;
  trailingStopActive: boolean;
  trailingStopPrice: number | null;
  entryTime: number;
  holdDurationMs: number;
  exchange_order_id?: string;
  coherenceAtEntry: number | null;
  qgitaTierAtEntry: number | null;
  priceSourceId: string;
  priceSourceTimestamp: string;
}

export interface PositionManagerState {
  positions: Position[];
  totalPositions: number;
  totalExposureUsd: number;
  totalUnrealizedPnl: number;
  maxPositions: number;
  positionsAtRisk: number; // Positions near stop loss
}

const MAX_POSITIONS = 15;
const TRAILING_ACTIVATION_PCT = 0.5; // Activate trailing at 0.5% profit

class PositionManager {
  private positions: Map<string, Position> = new Map();
  private isInitialized: boolean = false;

  constructor() {
    console.log('📈 Position Manager ready; awaiting provider-backed positions');
  }

  /**
   * Initialize and load existing positions from DB
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Load open positions from trading_positions table
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const { data, error } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('user_id', session.user.id)
        .eq('status', 'open');

      if (!error && data) {
        for (const row of data) {
          const required = [
            row.entry_price, row.quantity, row.position_value_usdt, row.current_price,
            row.unrealized_pnl, row.take_profit_price, row.stop_loss_price,
          ];
          const openedAt = Date.parse(String(row.source_timestamp || ''));
          if (row.truth_status !== 'live' || row.generated_values !== false || !row.source_id ||
              !required.every(Number.isFinite) || !Number.isFinite(openedAt)) continue;
          const position: Position = {
            id: row.id,
            symbol: row.symbol,
            exchange: row.exchange,
            side: row.side as 'LONG' | 'SHORT',
            entryPrice: row.entry_price,
            quantity: row.quantity,
            positionSizeUsd: row.position_value_usdt,
            currentPrice: row.current_price,
            unrealizedPnl: row.unrealized_pnl,
            unrealizedPnlPct: row.position_value_usdt > 0 ? (row.unrealized_pnl / row.position_value_usdt) * 100 : null,
            takeProfitPrice: row.take_profit_price,
            stopLossPrice: row.stop_loss_price,
            trailingStopActive: false,
            trailingStopPrice: null,
            entryTime: openedAt,
            holdDurationMs: Date.now() - openedAt,
            coherenceAtEntry: null,
            qgitaTierAtEntry: null,
            priceSourceId: row.source_id,
            priceSourceTimestamp: row.source_timestamp,
          };
          this.positions.set(position.id, position);
        }
        console.log(`[PositionManager] Loaded ${data.length} open positions`);
        if (this.positions.size > 0) temporalLadder.registerSystem(SYSTEMS.POSITION_MANAGER);
      }
    } catch (error) {
      console.error('[PositionManager] Init error:', error);
    }

    this.isInitialized = true;
  }

  /**
   * Open a new position
   */
  public async openPosition(params: {
    symbol: string;
    exchange: string;
    side: 'LONG' | 'SHORT';
    entryPrice: number;
    quantity: number;
    positionSizeUsd: number;
    coherenceAtEntry: number;
    qgitaTierAtEntry: number;
    exchangeOrderId?: string;
    takeProfitPct?: number;
    stopLossPct?: number;
  }): Promise<Position | null> {
    // A frontend model cannot create a live position. The execute-trade/OMS
    // receipt path owns both the exchange order and the database position row.
    throw new Error('PROVIDER_ORDER_RECEIPT_REQUIRED: open positions through a live execution function');
  }

  /**
   * Update position with new price
   */
  public updatePrice(ticker: {
    symbol: string;
    price: number;
    truthStatus: 'real_derived';
    sourceId: string;
    sourceTimestamp: string;
    generatedValues: false;
  }): Position | null {
    const sourceTime = Date.parse(ticker.sourceTimestamp);
    if (!Number.isFinite(ticker.price) || ticker.price <= 0 || !ticker.sourceId ||
        ticker.truthStatus !== 'real_derived' || ticker.generatedValues !== false ||
        !Number.isFinite(sourceTime) || Date.now() - sourceTime > 60_000) {
      return null;
    }

    for (const position of this.positions.values()) {
      if (position.symbol !== ticker.symbol) continue;

      const symbol = ticker.symbol;
      const currentPrice = ticker.price;

      // Calculate unrealized P&L
      const priceDiff = position.side === 'LONG'
        ? currentPrice - position.entryPrice
        : position.entryPrice - currentPrice;

      position.currentPrice = currentPrice;
      position.priceSourceId = ticker.sourceId;
      position.priceSourceTimestamp = ticker.sourceTimestamp;
      position.unrealizedPnl = priceDiff * position.quantity;
      position.unrealizedPnlPct = (priceDiff / position.entryPrice) * 100;
      position.holdDurationMs = Date.now() - position.entryTime;

      // Check for trailing stop activation
      if (!position.trailingStopActive && position.unrealizedPnlPct >= TRAILING_ACTIVATION_PCT) {
        position.trailingStopActive = true;
        console.log(`[PositionManager] 🎯 Trailing stop activated for ${symbol} at ${position.unrealizedPnlPct.toFixed(2)}% profit`);
      }

      // Update trailing stop price
      if (position.trailingStopActive) {
        const trailingUpdate = trailingStopManager.updateStop(symbol, currentPrice);
        if (trailingUpdate.stop) {
          position.trailingStopPrice = trailingUpdate.stop.trailPrice;
          position.stopLossPrice = trailingUpdate.stop.trailPrice;
        }

        if (trailingUpdate.triggered) {
          console.log(`[PositionManager] ⚠️ Trailing stop triggered for ${symbol}`);
          return position;
        }
      }

      // Check take profit / stop loss
      if (this.shouldClose(position, currentPrice)) {
        return position;
      }

      return position;
    }
    return null;
  }

  /**
   * Check if position should be closed
   */
  private shouldClose(position: Position, currentPrice: number): boolean {
    if (position.side === 'LONG') {
      // Take profit hit
      if (currentPrice >= position.takeProfitPrice) {
        console.log(`[PositionManager] 🎯 TP HIT: ${position.symbol} @ ${currentPrice}`);
        return true;
      }
      // Stop loss hit
      if (currentPrice <= position.stopLossPrice) {
        console.log(`[PositionManager] 🛑 SL HIT: ${position.symbol} @ ${currentPrice}`);
        return true;
      }
    } else {
      // Short position - inverted
      if (currentPrice <= position.takeProfitPrice) {
        console.log(`[PositionManager] 🎯 TP HIT: ${position.symbol} @ ${currentPrice}`);
        return true;
      }
      if (currentPrice >= position.stopLossPrice) {
        console.log(`[PositionManager] 🛑 SL HIT: ${position.symbol} @ ${currentPrice}`);
        return true;
      }
    }
    return false;
  }

  /**
   * Close a position
   */
  public async closePosition(positionId: string, exitPrice: number, reason: string = 'manual'): Promise<Position | null> {
    throw new Error('PROVIDER_CLOSE_ORDER_RECEIPT_REQUIRED: closing a local model must not mark a live position closed');
  }

  /**
   * Check all positions for TP/SL exits
   * Returns positions that should be closed
   */
  public checkAllPositions(): Position[] {
    const toClose: Position[] = [];
    
    for (const position of this.positions.values()) {
      const observedAt = Date.parse(position.priceSourceTimestamp);
      if (Number.isFinite(observedAt) && Date.now() - observedAt <= 60_000 &&
          this.shouldClose(position, position.currentPrice)) {
        toClose.push(position);
      }
    }
    
    return toClose;
  }

  /**
   * Get all positions
   */
  public getPositions(): Position[] {
    return Array.from(this.positions.values());
  }

  /**
   * Get position by symbol
   */
  public getPosition(symbol: string): Position | undefined {
    for (const pos of this.positions.values()) {
      if (pos.symbol === symbol) return pos;
    }
    return undefined;
  }

  /**
   * Get position count
   */
  public getPositionCount(): number {
    return this.positions.size;
  }

  /**
   * Check if can open new position
   */
  public canOpenPosition(): boolean {
    return this.positions.size < MAX_POSITIONS;
  }

  /**
   * Get state
   */
  public getState(): PositionManagerState {
    const positions = this.getPositions();
    const totalExposureUsd = positions.reduce((sum, p) => sum + p.positionSizeUsd, 0);
    const totalUnrealizedPnl = positions.reduce((sum, p) => sum + p.unrealizedPnl, 0);
    const positionsAtRisk = positions.filter(p => p.unrealizedPnlPct < -0.5).length;

    return {
      positions,
      totalPositions: positions.length,
      totalExposureUsd,
      totalUnrealizedPnl,
      maxPositions: MAX_POSITIONS,
      positionsAtRisk,
    };
  }
}

export const positionManager = new PositionManager();
