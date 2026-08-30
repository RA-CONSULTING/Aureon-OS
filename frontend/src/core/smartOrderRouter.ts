/**
 * Smart Order Router (SOR)
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Finds best execution across multiple exchanges
 * Fee-aware routing for optimal trade execution
 */

import { ExchangeType, ExchangeTicker, EXCHANGE_FEES, EXCHANGE_FEE_DETAILS } from './unifiedExchangeClient';
import { multiExchangeClient } from './multiExchangeClient';

// Smart routing configuration - synced with Python CONFIG
const ROUTING_CONFIG = {
  slippagePct: 0.0010,        // 0.10% estimated slippage
  spreadCostPct: 0.0005,      // 0.05% spread cost
  exchangePriority: ['binance', 'kraken', 'capital', 'alpaca'] as ExchangeType[],
  alpacaAnalyticsOnly: true,  // Alpaca for market data only (no trades)
};

export interface OrderQuote {
  exchange: ExchangeType;
  symbol: string;
  side: 'BUY' | 'SELL';
  price: number;
  estimatedFee: number;
  effectivePrice: number; // Price after fees
  spread: number;
  available: boolean;
  timestamp: number;
  truthStatus: 'real_derived';
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

export interface RoutingDecision {
  recommendedExchange: ExchangeType;
  quotes: OrderQuote[];
  bestQuote: OrderQuote;
  savings: number; // vs worst quote
  reasoning: string;
}

export interface SplitOrderPlan {
  totalQuantity: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  splits: Array<{
    exchange: ExchangeType;
    quantity: number;
    estimatedPrice: number;
    estimatedFee: number;
  }>;
  totalEstimatedCost: number;
  estimatedSavings: number;
}

export class SmartOrderRouter {
  private lastRoutingDecision: RoutingDecision | null = null;

  constructor() {
    console.log('🚀 Smart Order Router initialized');
  }

  /**
   * Get best quote across all exchanges
   */
  public async getBestQuote(
    symbol: string,
    side: 'BUY' | 'SELL',
    quantity: number
  ): Promise<RoutingDecision> {
    // Get tickers from all exchanges
    const tickers = await multiExchangeClient.getTickersFromAllExchanges(symbol);
    
    const quotes: OrderQuote[] = [];

    for (const [exchange, ticker] of tickers.entries()) {
      if (!ticker) continue;

      const fees = EXCHANGE_FEES[exchange];
      const feeRate = fees.taker; // Assume taker for market orders
      
      // Use appropriate price based on side
      const price = side === 'BUY' ? ticker.askPrice : ticker.bidPrice;
      const estimatedFee = price * quantity * feeRate;
      
      // Effective price includes fee
      const effectivePrice = side === 'BUY'
        ? price * (1 + feeRate)
        : price * (1 - feeRate);

      quotes.push({
        exchange,
        symbol,
        side,
        price,
        estimatedFee,
        effectivePrice,
        spread: ticker.askPrice - ticker.bidPrice,
        available: true,
        timestamp: ticker.timestamp,
        truthStatus: ticker.truthStatus,
        sourceId: ticker.sourceId,
        sourceTimestamp: ticker.sourceTimestamp,
        generatedValues: false,
      });
    }

    if (quotes.length === 0) {
      throw new Error(`NO_LIVE_ROUTING_QUOTES:${symbol}`);
    }

    // Sort by effective price (best first)
    quotes.sort((a, b) => {
      if (side === 'BUY') {
        return a.effectivePrice - b.effectivePrice; // Lower is better for buying
      } else {
        return b.effectivePrice - a.effectivePrice; // Higher is better for selling
      }
    });

    const bestQuote = quotes[0];
    const worstQuote = quotes[quotes.length - 1];
    
    // Calculate savings
    const savings = Math.abs(bestQuote.effectivePrice - worstQuote.effectivePrice) * quantity;

    const decision: RoutingDecision = {
      recommendedExchange: bestQuote.exchange,
      quotes,
      bestQuote,
      savings,
      reasoning: this.generateReasoning(bestQuote, quotes, side)
    };

    this.lastRoutingDecision = decision;
    return decision;
  }

  /**
   * Plan a split order across multiple exchanges
   */
  public async planSplitOrder(
    symbol: string,
    side: 'BUY' | 'SELL',
    totalQuantity: number,
    maxSplits: number = 2
  ): Promise<SplitOrderPlan> {
    const decision = await this.getBestQuote(symbol, side, totalQuantity);
    
    // If only one exchange available, no split needed
    if (decision.quotes.length <= 1 || maxSplits <= 1) {
      return {
        totalQuantity,
        symbol,
        side,
        splits: [{
          exchange: decision.bestQuote.exchange,
          quantity: totalQuantity,
          estimatedPrice: decision.bestQuote.price,
          estimatedFee: decision.bestQuote.estimatedFee
        }],
        totalEstimatedCost: decision.bestQuote.effectivePrice * totalQuantity,
        estimatedSavings: 0
      };
    }

    // For now, simple 50/50 split between top 2 exchanges
    const splits: SplitOrderPlan['splits'] = [];
    const usableQuotes = decision.quotes.slice(0, maxSplits);
    const quantityPerExchange = totalQuantity / usableQuotes.length;

    for (const quote of usableQuotes) {
      const fees = EXCHANGE_FEES[quote.exchange];
      splits.push({
        exchange: quote.exchange,
        quantity: quantityPerExchange,
        estimatedPrice: quote.price,
        estimatedFee: quote.price * quantityPerExchange * fees.taker
      });
    }

    const totalEstimatedCost = splits.reduce(
      (sum, split) => sum + (split.estimatedPrice * split.quantity) + split.estimatedFee,
      0
    );

    // Compare to single exchange execution
    const singleExchangeCost = decision.bestQuote.effectivePrice * totalQuantity;
    const estimatedSavings = singleExchangeCost - totalEstimatedCost;

    return {
      totalQuantity,
      symbol,
      side,
      splits,
      totalEstimatedCost,
      estimatedSavings: Math.max(0, estimatedSavings)
    };
  }

  /**
   * Quick route - returns best exchange without full analysis
   */
  public quickRoute(symbol: string): ExchangeType | null {
    return multiExchangeClient.getBestExchangeForSymbol(symbol);
  }

  /**
   * Get last routing decision
   */
  public getLastDecision(): RoutingDecision | null {
    return this.lastRoutingDecision;
  }

  /**
   * Calculate fee impact
   */
  public calculateFeeImpact(
    exchange: ExchangeType,
    orderValue: number,
    isMaker: boolean = false
  ): number {
    const fees = EXCHANGE_FEES[exchange];
    const feeRate = isMaker ? fees.maker : fees.taker;
    return orderValue * feeRate;
  }

  /**
   * Compare fees across exchanges
   */
  public compareFees(orderValue: number): Record<ExchangeType, { maker: number; taker: number }> {
    const comparison: Record<string, { maker: number; taker: number }> = {};

    for (const [exchange, fees] of Object.entries(EXCHANGE_FEES)) {
      comparison[exchange] = {
        maker: orderValue * fees.maker,
        taker: orderValue * fees.taker
      };
    }

    return comparison as Record<ExchangeType, { maker: number; taker: number }>;
  }

  private generateReasoning(
    bestQuote: OrderQuote,
    allQuotes: OrderQuote[],
    side: 'BUY' | 'SELL'
  ): string {
    const reasons: string[] = [];

    // Best price
    reasons.push(`${bestQuote.exchange} offers best ${side === 'BUY' ? 'ask' : 'bid'} price: $${bestQuote.price.toFixed(4)}`);

    // Fee advantage
    const fees = EXCHANGE_FEES[bestQuote.exchange];
    reasons.push(`Fee rate: ${(fees.taker * 100).toFixed(2)}%`);

    // Spread info
    if (bestQuote.spread > 0) {
      reasons.push(`Spread: $${bestQuote.spread.toFixed(4)}`);
    }

    // Compare to others
    if (allQuotes.length > 1) {
      const otherExchanges = allQuotes.slice(1).map(q => q.exchange).join(', ');
      reasons.push(`Better than: ${otherExchanges}`);
    }

    return reasons.join(' | ');
  }
}

// Singleton instance
export const smartOrderRouter = new SmartOrderRouter();
