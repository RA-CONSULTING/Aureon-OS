#!/usr/bin/env tsx
/**
 * ALL PAIRS TESTNET TRADING
 * 
 * Trades on all 801 pairs available on Binance testnet
 * - Scans all available pairs
 * - Applies consciousness-based filtering
 * - Rotates through tradeable pairs systematically
 * - Manages concurrent trading sessions
 * 
 * Design:
 * - Discover all 801 testnet pairs
 * - Filter by minimum liquidity/volume
 * - Score each pair for opportunity
 * - Execute trades on qualified pairs in rotation
 * - Respect rate limits and resource constraints
 * 
 * Gary Leckey | November 23, 2025
 */

import '../core/environment';
import { BinanceClient } from '../core/binanceClient';
import { RealityField, LambdaState } from '../core/masterEquation';
import { AURIS_TAXONOMY, AurisAnimal } from '../core/aurisSymbolicTaxonomy';
import { RainbowBridge } from '../core/theRainbowBridge';
import { ThePrism } from '../core/thePrism';
import { writeFileSync, readFileSync, existsSync } from 'fs';

// Pattern to identify and exclude leveraged tokens from trading
// Matches: UP, DOWN, BULL, BEAR, 3L, 5S, etc.
const LEVERAGED_TOKEN_PATTERN = /(UP|DOWN|BULL|BEAR|[0-9]+(L|S))$/;

interface TradingPair {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  minNotional: number;
  lastPrice?: number;
  volume24h?: number;
  priceChange24h?: number;
  opportunity: number;
  coherence: number;
  votes: number;
  lastTraded?: number;
  tradeCount: number;
}

interface AllPairsConfig {
  apiKey: string;
  apiSecret: string;
  testnet: boolean;
  minCoherence: number;
  minVotes: number;
  minVolume24h: number;
  maxConcurrentPairs: number;
  cycleDelayMs: number;
  rotationIntervalMs: number;
  dryRun: boolean;
  targetPairCount: number; // 801 for testnet
}

interface TradingSession {
  startTime: number;
  pairsDiscovered: number;
  pairsTraded: Set<string>;
  totalTrades: number;
  successfulTrades: number;
  failedTrades: number;
  currentRotation: number;
}

class AllPairsTestnetTrader {
  private client: BinanceClient;
  private config: AllPairsConfig;
  private pairs: Map<string, TradingPair> = new Map();
  private session: TradingSession;
  private isRunning: boolean = false;
  private tradingQueue: string[] = [];

  constructor(config: Partial<AllPairsConfig> = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.BINANCE_API_KEY || '',
      apiSecret: config.apiSecret || process.env.BINANCE_API_SECRET || '',
      testnet: config.testnet ?? (!(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false")),
      minCoherence: config.minCoherence ?? 0.80, // Lower threshold for more pairs
      minVotes: config.minVotes ?? 5, // Require 5/9 votes minimum
      minVolume24h: config.minVolume24h ?? 10000, // $10K minimum 24h volume
      maxConcurrentPairs: config.maxConcurrentPairs ?? 10, // Trade 10 pairs at a time
      cycleDelayMs: config.cycleDelayMs ?? 5000, // 5 seconds between cycles
      rotationIntervalMs: config.rotationIntervalMs ?? 300000, // Rotate every 5 minutes
      dryRun: config.dryRun ?? (process.env.DRY_RUN === 'true'),
      targetPairCount: config.targetPairCount ?? 801,
    };

    if (!this.config.apiKey || !this.config.apiSecret) {
      throw new Error('❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set');
    }

    this.client = new BinanceClient({
      apiKey: this.config.apiKey,
      apiSecret: this.config.apiSecret,
      testnet: this.config.testnet,
    });

    this.session = {
      startTime: Date.now(),
      pairsDiscovered: 0,
      pairsTraded: new Set(),
      totalTrades: 0,
      successfulTrades: 0,
      failedTrades: 0,
      currentRotation: 0,
    };
  }

  /**
   * Discover all available trading pairs on testnet
   */
  async discoverPairs(): Promise<void> {
    console.log('\n📡 Discovering all testnet trading pairs...\n');

    try {
      const exchangeInfo = await this.client.getExchangeInfo();
      // Filter for active trading pairs, excluding leveraged tokens
      const symbols = exchangeInfo.symbols.filter((s: any) => 
        s.status === 'TRADING' &&
        !LEVERAGED_TOKEN_PATTERN.test(s.symbol)
      );

      console.log(`✅ Found ${symbols.length} active trading pairs`);
      this.session.pairsDiscovered = symbols.length;

      // Get 24h ticker data for all symbols
      console.log('📊 Fetching 24h market data...\n');
      const tickers = await this.client.get24hrTickers();
      const tickerMap = new Map(tickers.map(t => [t.symbol, t]));

      // Process each pair
      for (const symbol of symbols) {
        const ticker = tickerMap.get(symbol.symbol);
        
        // Extract minimum notional from filters
        let minNotional = 10; // Default $10 USDT
        if (symbol.filters) {
          const notionalFilter = symbol.filters.find((f: any) => f.filterType === 'MIN_NOTIONAL');
          if (notionalFilter) {
            minNotional = parseFloat(notionalFilter.minNotional);
          }
        }

        const pair: TradingPair = {
          symbol: symbol.symbol,
          baseAsset: symbol.baseAsset,
          quoteAsset: symbol.quoteAsset,
          minNotional,
          lastPrice: ticker ? parseFloat(ticker.lastPrice) : undefined,
          volume24h: ticker ? parseFloat(ticker.quoteVolume) : undefined,
          priceChange24h: ticker ? parseFloat(ticker.priceChangePercent) : undefined,
          opportunity: 0,
          coherence: 0,
          votes: 0,
          tradeCount: 0,
        };

        this.pairs.set(symbol.symbol, pair);
      }

      console.log(`✅ Loaded ${this.pairs.size} pairs into trading system\n`);

    } catch (error: any) {
      console.error('❌ Failed to discover pairs:', error.message);
      throw error;
    }
  }

  /**
   * Filter and score all pairs for trading opportunities
   */
  async scorePairs(): Promise<TradingPair[]> {
    console.log('🧠 Scoring all pairs with consciousness metrics...\n');

    const field = new RealityField();
    const bridge = new RainbowBridge();
    const prism = new ThePrism();

    const scoredPairs: TradingPair[] = [];
    let processed = 0;

    for (const [symbol, pair] of this.pairs) {
      processed++;
      
      // Show progress every 100 pairs
      if (processed % 100 === 0) {
        console.log(`   Progress: ${processed}/${this.pairs.size} pairs scored...`);
      }

      // Skip if insufficient volume
      if ((pair.volume24h || 0) < this.config.minVolume24h) {
        continue;
      }

      // Create market snapshot
      const snapshot = {
        symbol: pair.symbol,
        timestamp: Date.now(),
        price: pair.lastPrice || 0,
        volume: pair.volume24h || 0,
        trades: 0,
        volatility: Math.abs(pair.priceChange24h || 0),
        momentum: pair.priceChange24h || 0,
      };

      // Run consciousness check
      const state = field.step(snapshot);
      bridge.updateFromMarket(state.Lambda, state.coherence, 0);
      const bridgeState = bridge.getState();
      const prismState = prism.process(state, snapshot);

      // Run Lighthouse consensus
      const votes = this.calculateVotes(state.Lambda);

      // Update pair with consciousness metrics
      pair.coherence = state.coherence;
      pair.votes = votes;
      pair.opportunity = this.calculateOpportunity(pair, state, prismState.resonance);

      // Add to scored pairs if meets minimum criteria
      if (pair.coherence >= this.config.minCoherence && votes >= this.config.minVotes) {
        scoredPairs.push(pair);
      }
    }

    console.log(`\n✅ Found ${scoredPairs.length} qualified pairs for trading\n`);

    // Sort by opportunity score (highest first)
    scoredPairs.sort((a, b) => b.opportunity - a.opportunity);

    return scoredPairs;
  }

  /**
   * Calculate Lighthouse votes
   */
  private calculateVotes(Lambda: number): number {
    let votes = 0;
    const animals = Object.keys(AURIS_TAXONOMY) as AurisAnimal[];
    
    for (const animal of animals) {
      const node = AURIS_TAXONOMY[animal];
      const resonance = Math.abs(Math.sin(2 * Math.PI * node.frequency * Lambda));
      
      if (resonance >= 0.7) {
        votes++;
      }
    }
    
    return votes;
  }

  /**
   * Calculate opportunity score
   */
  private calculateOpportunity(
    pair: TradingPair,
    state: LambdaState,
    prismResonance: number
  ): number {
    const coherenceScore = state.coherence * 40;
    const voteScore = (pair.votes / 9) * 30;
    const prismScore = prismResonance * 20;
    const volumeScore = Math.min((pair.volume24h || 0) / 1000000, 1) * 10; // Up to $1M volume
    
    return coherenceScore + voteScore + prismScore + volumeScore;
  }

  /**
   * Execute trading rotation on all qualified pairs
   */
  async executeTradingRotation(qualifiedPairs: TradingPair[]): Promise<void> {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║                                                           ║');
    console.log('║       🌈 ALL PAIRS TESTNET TRADING - ACTIVE 🌈          ║');
    console.log('║                                                           ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    console.log(`📊 Trading Configuration:`);
    console.log(`   • Total Pairs Discovered: ${this.session.pairsDiscovered}`);
    console.log(`   • Qualified Pairs: ${qualifiedPairs.length}`);
    console.log(`   • Target Pairs: ${this.config.targetPairCount}`);
    console.log(`   • Max Concurrent: ${this.config.maxConcurrentPairs}`);
    console.log(`   • Min Coherence: ${(this.config.minCoherence * 100).toFixed(0)}%`);
    console.log(`   • Min Votes: ${this.config.minVotes}/9`);
    console.log(`   • Dry Run: ${this.config.dryRun ? 'YES' : 'NO'}`);
    console.log('');

    this.isRunning = true;
    let rotationCount = 0;

    while (this.isRunning) {
      rotationCount++;
      this.session.currentRotation = rotationCount;

      console.log(`\n${'═'.repeat(60)}`);
      console.log(`🔄 ROTATION #${rotationCount}`);
      console.log(`${'═'.repeat(60)}\n`);

      // Select pairs for this rotation
      const batchSize = Math.min(this.config.maxConcurrentPairs, qualifiedPairs.length);
      const batch = qualifiedPairs.slice(0, batchSize);

      console.log(`Trading ${batch.length} pairs in this rotation:\n`);

      // Process each pair in the batch
      for (const pair of batch) {
        await this.tradePair(pair);
        
        // Delay between pairs to respect rate limits
        await this.sleep(this.config.cycleDelayMs / batch.length);
      }

      // Rotate pairs to the back
      qualifiedPairs.push(...qualifiedPairs.splice(0, batchSize));

      // Display session stats
      this.displaySessionStats();

      // Wait before next rotation
      console.log(`\n⏳ Waiting ${this.config.rotationIntervalMs / 1000}s before next rotation...\n`);
      await this.sleep(this.config.rotationIntervalMs);
    }
  }

  /**
   * Execute trade on a single pair
   * 
   * IMPLEMENTATION REQUIRED:
   * This method currently marks pairs as qualified but does not place orders.
   * 
   * To implement order execution:
   * 1. Define position sizing strategy (e.g., fixed USDT amount, % of capital, Kelly criterion)
   * 2. Add entry logic (determine BUY/SELL based on Lambda direction)
   * 3. Implement order placement using this.client.placeOrder()
   * 4. Add exit logic (stop-loss, take-profit, time-based, coherence drop)
   * 5. Track open positions and P/L
   * 
   * Example implementation:
   * ```typescript
   * const positionSize = this.calculatePositionSize(pair);
   * const side = pair.Lambda > 0 ? 'BUY' : 'SELL';
   * const order = await this.client.placeOrder({
   *   symbol: pair.symbol,
   *   side,
   *   type: 'MARKET',
   *   quoteOrderQty: positionSize
   * });
   * // Track position, set exit conditions, etc.
   * ```
   * 
   * Timeline: Implementation depends on specific trading strategy requirements.
   * Framework is production-ready for testing filtering/rotation logic.
   */
  private async tradePair(pair: TradingPair): Promise<void> {
    console.log(`🎯 ${pair.symbol.padEnd(12)} | Γ=${(pair.coherence * 100).toFixed(1)}% | Votes=${pair.votes}/9 | Score=${pair.opportunity.toFixed(0)}`);

    if (this.config.dryRun) {
      console.log(`   [DRY RUN] Would trade ${pair.symbol}`);
      this.session.pairsTraded.add(pair.symbol);
      this.session.totalTrades++;
      pair.tradeCount++;
      pair.lastTraded = Date.now();
      return;
    }

    // Live trading - framework ready, order execution to be implemented
    try {
      // Mark as processed for rotation tracking
      // Actual order placement would go here (see TODO above)
      console.log(`   ℹ️  ${pair.symbol} qualified for trading (order execution: TODO)`);
      this.session.pairsTraded.add(pair.symbol);
      this.session.totalTrades++;
      this.session.successfulTrades++;
      pair.tradeCount++;
      pair.lastTraded = Date.now();
    } catch (error: any) {
      console.log(`   ❌ Error: ${error.message}`);
      this.session.failedTrades++;
    }
  }

  /**
   * Display session statistics
   */
  private displaySessionStats(): void {
    const runtime = (Date.now() - this.session.startTime) / 1000 / 60; // minutes
    
    console.log('\n' + '─'.repeat(60));
    console.log('📈 SESSION STATISTICS');
    console.log('─'.repeat(60));
    console.log(`Runtime: ${runtime.toFixed(1)} minutes`);
    console.log(`Rotations Completed: ${this.session.currentRotation}`);
    console.log(`Pairs Traded: ${this.session.pairsTraded.size}`);
    console.log(`Total Trades: ${this.session.totalTrades}`);
    console.log(`Success Rate: ${this.session.totalTrades > 0 ? ((this.session.successfulTrades / this.session.totalTrades) * 100).toFixed(1) : 0}%`);
    console.log('─'.repeat(60));
  }

  /**
   * Start the all-pairs trading system
   */
  async start(): Promise<void> {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║                                                           ║');
    console.log('║         🚀 ALL 801 PAIRS TESTNET TRADER 🚀              ║');
    console.log('║                                                           ║');
    console.log('║     AUREON Consciousness Applied to All Pairs           ║');
    console.log('║                                                           ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    if (!this.config.dryRun) {
      console.log('⚠️  NOTE: Order execution not yet implemented');
      console.log('   Framework will identify qualified pairs for trading');
      console.log('   See tradePair() method for implementation TODO\n');
    }

    try {
      // Step 1: Discover all pairs
      await this.discoverPairs();

      // Step 2: Score all pairs
      const qualifiedPairs = await this.scorePairs();

      if (qualifiedPairs.length === 0) {
        console.log('⚠️  No pairs meet the minimum criteria for trading');
        console.log('💡 Try lowering --min-coherence or --min-votes thresholds');
        return;
      }

      // Step 3: Save qualified pairs list
      this.saveQualifiedPairs(qualifiedPairs);

      // Step 4: Execute trading rotation
      await this.executeTradingRotation(qualifiedPairs);

    } catch (error: any) {
      console.error('\n❌ Trading system error:', error.message);
      throw error;
    }
  }

  /**
   * Save qualified pairs to file
   */
  private saveQualifiedPairs(pairs: TradingPair[]): void {
    const data = {
      timestamp: new Date().toISOString(),
      totalPairs: this.session.pairsDiscovered,
      qualifiedPairs: pairs.length,
      targetCount: this.config.targetPairCount,
      pairs: pairs.map(p => ({
        symbol: p.symbol,
        quoteAsset: p.quoteAsset,
        volume24h: p.volume24h,
        coherence: p.coherence,
        votes: p.votes,
        opportunity: p.opportunity,
      })),
    };

    const filepath = './testnet_qualified_pairs.json';
    writeFileSync(filepath, JSON.stringify(data, null, 2));
    console.log(`💾 Qualified pairs saved to: ${filepath}\n`);
  }

  /**
   * Stop trading
   */
  stop(): void {
    console.log('\n🛑 Stopping all-pairs trading...');
    this.isRunning = false;
    this.displaySessionStats();
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Main execution
 */
async function main() {
  const args = process.argv.slice(2);

  const config: Partial<AllPairsConfig> = {
    minCoherence: parseFloat(args.find(a => a.startsWith('--min-coherence='))?.split('=')[1] || '0.80'),
    minVotes: parseInt(args.find(a => a.startsWith('--min-votes='))?.split('=')[1] || '5'),
    minVolume24h: parseFloat(args.find(a => a.startsWith('--min-volume='))?.split('=')[1] || '10000'),
    maxConcurrentPairs: parseInt(args.find(a => a.startsWith('--max-concurrent='))?.split('=')[1] || '10'),
    cycleDelayMs: parseInt(args.find(a => a.startsWith('--cycle-delay='))?.split('=')[1] || '5000'),
    rotationIntervalMs: parseInt(args.find(a => a.startsWith('--rotation-interval='))?.split('=')[1] || '300000'),
  };

  const trader = new AllPairsTestnetTrader(config);

  // Graceful shutdown handlers
  process.on('SIGINT', () => {
    console.log('\n\n🛑 Received SIGINT - shutting down gracefully...');
    trader.stop();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    console.log('\n\n🛑 Received SIGTERM - shutting down gracefully...');
    trader.stop();
    process.exit(0);
  });

  await trader.start();
}

main().catch(error => {
  console.error('\n❌ Fatal error:', error.message);
  process.exit(1);
});

export default AllPairsTestnetTrader;
