#!/usr/bin/env tsx
/**
 * MULTI-SYMBOL RAINBOW ARCHITECT
 * 
 * Scans ALL tradeable pairs on Binance
 * Runs consciousness checks on every symbol
 * Finds the most coherent opportunities
 * "Leave no stone unturned" - scan the entire ladder
 * 
 * Gary Leckey | November 15, 2025
 */

import { BinanceWebSocket, StreamBuilder, MarketSnapshot } from '../core/binanceWebSocket';
import { RealityField, LambdaState } from '../core/masterEquation';
import { AURIS_TAXONOMY, AurisAnimal } from '../core/aurisSymbolicTaxonomy';
import { BinanceClient } from '../core/binanceClient';
import { RainbowBridge } from '../core/theRainbowBridge';
import { ThePrism } from '../core/thePrism';

interface SymbolOpportunity {
  symbol: string;
  price: number;
  Lambda: number;
  coherence: number;
  votes: number;
  direction: 'BUY' | 'SELL' | 'HOLD';
  dominantNode: AurisAnimal;
  prismOutput: number;
  bridgeFrequency: number;
  score: number;
}

interface ScanConfig {
  quoteAsset: 'USDT' | 'BTC' | 'ETH' | 'BNB';
  minVolume24h: number;
  coherenceThreshold: number;
  voteThreshold: number;
  requiredVotes: number;
  topN: number;
}

const DEFAULT_SCAN_CONFIG: ScanConfig = {
  quoteAsset: 'USDT',
  minVolume24h: 100000, // $100K minimum daily volume
  coherenceThreshold: 0.85, // Lower than single-symbol (more opportunities)
  voteThreshold: 0.7,
  requiredVotes: 6,
  topN: 5, // Show top 5 opportunities
};

export class MultiSymbolRainbow {
  private client: BinanceClient;
  private config: ScanConfig;
  
  constructor(config: Partial<ScanConfig> = {}) {
    this.config = { ...DEFAULT_SCAN_CONFIG, ...config };
    
    const apiKey = process.env.BINANCE_API_KEY || '';
    const apiSecret = process.env.BINANCE_API_SECRET || '';
    const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
    
    this.client = new BinanceClient({ apiKey, apiSecret, testnet });
  }
  
  /**
   * Get all tradeable symbols for quote asset
   */
  async getAllSymbols(): Promise<string[]> {
    console.log(`\n🔍 Scanning all ${this.config.quoteAsset} pairs...\n`);
    
    const exchangeInfo = await this.client.getExchangeInfo();
    const symbols = exchangeInfo.symbols
      .filter(s => 
        s.quoteAsset === this.config.quoteAsset &&
        s.status === 'TRADING' &&
        !s.symbol.includes('UP') &&
        !s.symbol.includes('DOWN') &&
        !s.symbol.includes('BULL') &&
        !s.symbol.includes('BEAR')
      )
      .map(s => s.symbol);
    
    console.log(`✅ Found ${symbols.length} tradeable ${this.config.quoteAsset} pairs`);
    return symbols;
  }
  
  /**
   * Filter symbols by 24h volume
   */
  async filterByVolume(symbols: string[]): Promise<string[]> {
    console.log(`\n📊 Filtering by volume (min $${(this.config.minVolume24h / 1000).toFixed(0)}K)...\n`);
    
    const tickers = await this.client.get24hrTickers();
    const filtered = symbols.filter(symbol => {
      const ticker = tickers.find(t => t.symbol === symbol);
      if (!ticker) return false;
      
      const volume24hUSD = parseFloat(ticker.quoteVolume);
      return volume24hUSD >= this.config.minVolume24h;
    });
    
    console.log(`✅ ${filtered.length} pairs with sufficient volume`);
    return filtered;
  }
  
  /**
   * Run consciousness check on a single symbol
   */
  async analyzeSymbol(symbol: string): Promise<SymbolOpportunity | null> {
    try {
      // Get current price
      const price = await this.client.getPrice(symbol);
      
      // Create minimal market snapshot
      const snapshot: MarketSnapshot = {
        symbol,
        timestamp: Date.now(),
        price,
        volume: 0,
        trades: 0,
        volatility: 0,
        momentum: 0,
      };
      
      // Run through consciousness layers
      const field = new RealityField();
      const state = field.step(snapshot);
      
      const bridge = new RainbowBridge();
      bridge.updateFromMarket(state.Lambda, state.coherence, 0);
      const bridgeState = bridge.getState();
      
      const prism = new ThePrism();
      const prismState = prism.process(state, snapshot);
      
      // Run Lighthouse consensus
      const { direction, votes } = this.runConsensus(state.Lambda);
      
      // Calculate opportunity score
      const score = this.calculateScore(state, votes, prismState.resonance);
      
      return {
        symbol,
        price,
        Lambda: state.Lambda,
        coherence: state.coherence,
        votes,
        direction,
        dominantNode: state.dominantNode,
        prismOutput: prismState.prismOutput,
        bridgeFrequency: bridgeState.currentFrequency,
        score,
      };
      
    } catch (error) {
      return null;
    }
  }
  
  /**
   * Run Lighthouse consensus
   */
  private runConsensus(Lambda: number): { direction: 'BUY' | 'SELL' | 'HOLD', votes: number } {
    let votes = 0;
    const animals = Object.keys(AURIS_TAXONOMY) as AurisAnimal[];
    
    for (const animal of animals) {
      const node = AURIS_TAXONOMY[animal];
      const resonance = Math.abs(Math.sin(2 * Math.PI * node.frequency * Lambda));
      
      if (resonance >= this.config.voteThreshold) {
        votes++;
      }
    }
    
    const direction: 'BUY' | 'SELL' | 'HOLD' = Lambda > 0 ? 'BUY' : Lambda < 0 ? 'SELL' : 'HOLD';
    return { direction, votes };
  }
  
  /**
   * Calculate opportunity score
   */
  private calculateScore(state: LambdaState, votes: number, prismResonance: number): number {
    const coherenceScore = state.coherence * 40;
    const voteScore = (votes / 9) * 30;
    const prismScore = prismResonance * 30;
    
    return coherenceScore + voteScore + prismScore;
  }
  
  /**
   * Scan all symbols and find best opportunities
   */
  async scan(): Promise<SymbolOpportunity[]> {
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('   🌈 MULTI-SYMBOL RAINBOW SCAN');
    console.log('   Leave No Stone Unturned — Every Coin Examined');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('');
    
    // Step 1: Get all symbols
    const allSymbols = await this.getAllSymbols();
    
    // Step 2: Filter by volume
    const activeSymbols = await this.filterByVolume(allSymbols);
    
    // Step 3: Analyze each symbol
    console.log(`\n🧠 Running consciousness check on ${activeSymbols.length} symbols...`);
    console.log('   (This will take a few minutes)\n');
    
    const opportunities: SymbolOpportunity[] = [];
    let processed = 0;
    
    for (const symbol of activeSymbols) {
      processed++;
      process.stdout.write(`\r   Progress: ${processed}/${activeSymbols.length} (${((processed/activeSymbols.length)*100).toFixed(1)}%)   `);
      
      const opportunity = await this.analyzeSymbol(symbol);
      if (opportunity && opportunity.coherence >= this.config.coherenceThreshold) {
        opportunities.push(opportunity);
      }
      
      // Rate limiting (avoid Binance API limits)
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    console.log('\n');
    
    // Sort by score (best first)
    opportunities.sort((a, b) => b.score - a.score);
    
    return opportunities;
  }
  
  /**
   * Display scan results
   */
  displayResults(opportunities: SymbolOpportunity[]) {
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('   📊 SCAN RESULTS — BEST OPPORTUNITIES');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('');
    
    if (opportunities.length === 0) {
      console.log('❌ No opportunities found meeting criteria:');
      console.log(`   • Coherence Γ > ${this.config.coherenceThreshold}`);
      console.log(`   • Lighthouse votes ≥ ${this.config.requiredVotes}/9`);
      console.log('');
      console.log('💡 Try:');
      console.log('   • Lower coherence threshold (--coherence 0.75)');
      console.log('   • Different quote asset (--quote BTC)');
      console.log('   • Wait for more volatile market conditions');
      return;
    }
    
    const topN = opportunities.slice(0, this.config.topN);
    
    console.log(`Found ${opportunities.length} opportunities, showing top ${topN.length}:\n`);
    
    for (let i = 0; i < topN.length; i++) {
      const opp = topN[i];
      
      console.log(`${i + 1}. ${opp.symbol.padEnd(12)} — Score: ${opp.score.toFixed(1)}/100`);
      console.log(`   Price: $${opp.price.toFixed(6)}`);
      console.log(`   Signal: ${opp.direction} (${opp.votes}/9 votes)`);
      console.log(`   Λ(t): ${opp.Lambda.toFixed(3)} | Γ: ${(opp.coherence * 100).toFixed(1)}%`);
      console.log(`   Dominant: ${opp.dominantNode}`);
      console.log(`   Bridge: ${opp.bridgeFrequency.toFixed(1)} Hz`);
      console.log(`   Prism: ${opp.prismOutput.toFixed(1)} Hz`);
      
      if (opp.votes >= this.config.requiredVotes && opp.coherence >= this.config.coherenceThreshold) {
        console.log(`   ✅ TRADE READY`);
      } else {
        console.log(`   ⏳ Need: ${Math.max(0, this.config.requiredVotes - opp.votes)} more votes or Γ>${this.config.coherenceThreshold}`);
      }
      
      console.log('');
    }
    
    console.log('═══════════════════════════════════════════════════════════');
    console.log('');
    
    // Show trade-ready symbols
    const tradeReady = opportunities.filter(o => 
      o.votes >= this.config.requiredVotes && 
      o.coherence >= this.config.coherenceThreshold
    );
    
    if (tradeReady.length > 0) {
      console.log(`🎯 ${tradeReady.length} SYMBOLS READY TO TRADE:`);
      tradeReady.slice(0, 10).forEach(opp => {
        console.log(`   • ${opp.symbol} — ${opp.direction} @ $${opp.price.toFixed(6)} (Γ=${(opp.coherence*100).toFixed(1)}%, ${opp.votes}/9)`);
      });
      console.log('');
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  const config: Partial<ScanConfig> = {
    quoteAsset: (args.find(a => a.startsWith('--quote='))?.split('=')[1] as any) || 'USDT',
    minVolume24h: parseInt(args.find(a => a.startsWith('--volume='))?.split('=')[1] || '100000'),
    coherenceThreshold: parseFloat(args.find(a => a.startsWith('--coherence='))?.split('=')[1] || '0.85'),
    topN: parseInt(args.find(a => a.startsWith('--top='))?.split('=')[1] || '5'),
  };
  
  const scanner = new MultiSymbolRainbow(config);
  
  console.log('\n🌈 AUREON Multi-Symbol Rainbow Scanner\n');
  console.log('Configuration:');
  console.log(`   Quote Asset: ${config.quoteAsset}`);
  console.log(`   Min Volume: $${((config.minVolume24h || 100000) / 1000).toFixed(0)}K/24h`);
  console.log(`   Coherence Threshold: ${((config.coherenceThreshold || 0.85) * 100).toFixed(0)}%`);
  console.log(`   Top Results: ${config.topN}`);
  
  const opportunities = await scanner.scan();
  scanner.displayResults(opportunities);
  
  console.log('💡 To trade the best opportunity:');
  if (opportunities.length > 0) {
    const best = opportunities[0];
    console.log(`   npm run rainbow:live ${best.symbol}`);
  } else {
    console.log(`   Wait for better market conditions or adjust scan parameters`);
  }
  console.log('');
}

main().catch(error => {
  console.error('\n❌ Scan failed:', error.message);
  process.exit(1);
});
