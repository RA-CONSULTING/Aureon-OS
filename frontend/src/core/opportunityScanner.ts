/**
 * Opportunity Scanner
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Scans all cached tickers and scores them for trading opportunities
 * Like Python aureon_unified_ecosystem.py _find_opportunities()
 */

import { tickerCacheManager, type CachedTicker } from './tickerCacheManager';
import { elephantMemory } from './elephantMemory';
import { unifiedBus } from './unifiedBus';
import { temporalLadder, SYSTEMS } from './temporalLadder';
import type { MarketSnapshot } from './aurisNodes';

export interface ScoredOpportunity {
  symbol: string;
  exchange: string;
  score: number;
  tier: 1 | 2 | 3;
  price: number;
  volume24h: number;
  volumeUsd: number;
  volatility: number;
  momentum: number;
  priceChange24h: number;
  spread: number;
  direction: 'LONG' | 'SHORT';
  reason: string;
  isBlacklisted: boolean;
  marketSnapshot: MarketSnapshot;
}

export interface ScanResult {
  timestamp: number;
  totalScanned: number;
  opportunities: ScoredOpportunity[];
  topOpportunity: ScoredOpportunity | null;
  scanDurationMs: number;
}

// Scoring weights aligned with Python ecosystem
const SCORING_WEIGHTS = {
  volumeWeight: 0.25,       // Higher volume = more liquidity
  volatilityWeight: 0.30,   // Higher volatility = more opportunity
  momentumWeight: 0.25,     // Strong momentum = trend
  spreadWeight: 0.10,       // Tighter spread = lower cost
  priceChangeWeight: 0.10,  // Recent moves = activity
};

// Thresholds for opportunity tiers
const TIER_THRESHOLDS = {
  tier1: 0.75, // Top tier - immediate execution
  tier2: 0.55, // Good opportunity
  tier3: 0.35, // Marginal opportunity
};

// Filters
const MIN_VOLUME_USD = 500000;   // $500k minimum
const MIN_VOLATILITY = 0.015;    // 1.5% minimum daily range
const MAX_SPREAD = 0.005;        // 0.5% max spread
const AVOID_STABLECOINS = ['USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'FDUSDUSDT'];

class OpportunityScanner {
  private lastScan: ScanResult | null = null;
  private isScanning: boolean = false;

  constructor() {
    temporalLadder.registerSystem(SYSTEMS.OPPORTUNITY_SCANNER);
    console.log('🎯 Opportunity Scanner initialized');
  }

  /**
   * Scan all tickers and score opportunities
   */
  public async scan(): Promise<ScanResult> {
    if (this.isScanning) {
      return this.lastScan || this.createEmptyResult();
    }

    this.isScanning = true;
    const startTime = Date.now();

    try {
      // Get all high-volume tickers from cache
      const tickers = tickerCacheManager.getHighVolumeTickers(MIN_VOLUME_USD);
      
      if (tickers.length === 0) {
        console.log('[OpportunityScanner] No tickers available, refreshing cache...');
        await tickerCacheManager.refreshAll();
        return this.createEmptyResult();
      }

      const opportunities: ScoredOpportunity[] = [];

      for (const ticker of tickers) {
        // Skip stablecoins
        if (AVOID_STABLECOINS.includes(ticker.symbol)) continue;

        // Skip low volatility
        if (ticker.volatility < MIN_VOLATILITY) continue;

        // Skip wide spreads
        if (ticker.spread > MAX_SPREAD) continue;

        // Check if blacklisted by Elephant Memory
        const avoidance = elephantMemory.shouldAvoid(ticker.symbol);

        // Score the opportunity
        const scored = this.scoreOpportunity(ticker, avoidance.avoid);
        
        if (scored.score >= TIER_THRESHOLDS.tier3) {
          opportunities.push(scored);
        }
      }

      // Sort by score descending
      opportunities.sort((a, b) => b.score - a.score);

      const result: ScanResult = {
        timestamp: Date.now(),
        totalScanned: tickers.length,
        opportunities: opportunities.slice(0, 50), // Top 50
        topOpportunity: opportunities[0] || null,
        scanDurationMs: Date.now() - startTime,
      };

      this.lastScan = result;

      // Publish to UnifiedBus
      this.publishToUnifiedBus(result);

      // Heartbeat
      temporalLadder.heartbeat(SYSTEMS.OPPORTUNITY_SCANNER, 
        result.opportunities.length > 0 ? 0.9 : 0.5);

      console.log(`[OpportunityScanner] ✅ Scanned ${result.totalScanned} pairs, found ${result.opportunities.length} opportunities in ${result.scanDurationMs}ms`);

      if (result.topOpportunity) {
        console.log(`[OpportunityScanner] 🎯 TOP: ${result.topOpportunity.symbol} | Score: ${result.topOpportunity.score.toFixed(2)} | ${result.topOpportunity.direction} | ${result.topOpportunity.reason}`);
      }

      return result;
    } catch (error) {
      console.error('[OpportunityScanner] Scan error:', error);
      return this.createEmptyResult();
    } finally {
      this.isScanning = false;
    }
  }

  /**
   * Score a single ticker as an opportunity
   */
  private scoreOpportunity(ticker: CachedTicker, isBlacklisted: boolean): ScoredOpportunity {
    // Normalize metrics to 0-1 scale
    const volumeScore = Math.min(Math.log10(ticker.volumeUsd) / 10, 1); // Log scale, max at $10B
    const volatilityScore = Math.min(ticker.volatility / 0.10, 1); // Max at 10%
    const momentumScore = Math.min(Math.abs(ticker.momentum) / 0.05, 1); // Max at 5%
    const spreadScore = 1 - Math.min(ticker.spread / MAX_SPREAD, 1); // Invert - lower is better
    const priceChangeScore = Math.min(Math.abs(ticker.priceChange24h) / 10, 1); // Max at 10%

    // Calculate weighted score
    let score = 
      volumeScore * SCORING_WEIGHTS.volumeWeight +
      volatilityScore * SCORING_WEIGHTS.volatilityWeight +
      momentumScore * SCORING_WEIGHTS.momentumWeight +
      spreadScore * SCORING_WEIGHTS.spreadWeight +
      priceChangeScore * SCORING_WEIGHTS.priceChangeWeight;

    // Penalize if blacklisted
    if (isBlacklisted) {
      score *= 0.3;
    }

    // Determine direction based on momentum
    const direction: 'LONG' | 'SHORT' = ticker.momentum >= 0 ? 'LONG' : 'SHORT';

    // Determine tier
    let tier: 1 | 2 | 3;
    if (score >= TIER_THRESHOLDS.tier1) tier = 1;
    else if (score >= TIER_THRESHOLDS.tier2) tier = 2;
    else tier = 3;

    // Build reason string
    const reasons: string[] = [];
    if (volatilityScore > 0.6) reasons.push('HIGH_VOLATILITY');
    if (volumeScore > 0.7) reasons.push('HIGH_VOLUME');
    if (momentumScore > 0.5) reasons.push('STRONG_MOMENTUM');
    if (spreadScore > 0.8) reasons.push('TIGHT_SPREAD');
    if (Math.abs(ticker.priceChange24h) > 3) reasons.push(ticker.priceChange24h > 0 ? 'BULLISH_24H' : 'BEARISH_24H');
    if (isBlacklisted) reasons.push('BLACKLISTED');

    // Create market snapshot for orchestrator
    const marketSnapshot: MarketSnapshot = {
      price: ticker.price,
      volume: ticker.volumeUsd,
      volatility: ticker.volatility,
      momentum: ticker.momentum,
      spread: ticker.spread,
      timestamp: ticker.timestamp,
      truthStatus: ticker.truthStatus,
      sourceId: ticker.sourceId,
      sourceTimestamp: ticker.sourceTimestamp,
      generatedValues: false,
    };

    return {
      symbol: ticker.symbol,
      exchange: ticker.exchange,
      score,
      tier,
      price: ticker.price,
      volume24h: ticker.volume,
      volumeUsd: ticker.volumeUsd,
      volatility: ticker.volatility,
      momentum: ticker.momentum,
      priceChange24h: ticker.priceChange24h,
      spread: ticker.spread,
      direction,
      reason: reasons.join(', ') || 'STANDARD',
      isBlacklisted,
      marketSnapshot,
    };
  }

  /**
   * Get cached last scan
   */
  public getLastScan(): ScanResult | null {
    return this.lastScan;
  }

  /**
   * Get top N opportunities
   */
  public getTopOpportunities(n: number = 10): ScoredOpportunity[] {
    return this.lastScan?.opportunities.slice(0, n) || [];
  }

  /**
   * Get best opportunity for immediate execution
   */
  public getBestOpportunity(): ScoredOpportunity | null {
    const opportunities = this.lastScan?.opportunities || [];
    // Return first non-blacklisted tier 1 or 2 opportunity
    return opportunities.find(o => !o.isBlacklisted && o.tier <= 2) || null;
  }

  private createEmptyResult(): ScanResult {
    return {
      timestamp: Date.now(),
      totalScanned: 0,
      opportunities: [],
      topOpportunity: null,
      scanDurationMs: 0,
    };
  }

  private publishToUnifiedBus(result: ScanResult): void {
    const topOpp = result.topOpportunity;
    
    unifiedBus.publish({
      systemName: 'OpportunityScanner',
      timestamp: Date.now(),
      ready: result.opportunities.length > 0,
      coherence: result.opportunities.length > 0 ? (topOpp?.score || 0.5) : 0.3,
      confidence: result.topOpportunity ? 0.85 : 0.4,
      signal: topOpp?.direction === 'LONG' ? 'BUY' : topOpp?.direction === 'SHORT' ? 'SELL' : 'NEUTRAL',
      data: {
        totalScanned: result.totalScanned,
        opportunitiesFound: result.opportunities.length,
        tier1Count: result.opportunities.filter(o => o.tier === 1).length,
        tier2Count: result.opportunities.filter(o => o.tier === 2).length,
        topSymbol: topOpp?.symbol || null,
        topScore: topOpp?.score || 0,
        topDirection: topOpp?.direction || null,
        scanDurationMs: result.scanDurationMs,
      },
    });
  }
}

export const opportunityScanner = new OpportunityScanner();
