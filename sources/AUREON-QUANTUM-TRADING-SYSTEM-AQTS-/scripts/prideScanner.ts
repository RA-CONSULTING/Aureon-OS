#!/usr/bin/env tsx
/**
 * PRIDE SCANNER — The Lion Hunts All Prey
 * 
 * Maps every tradeable coin from base pairs (ETH/USDT)
 * Scans all connected symbols for opportunities
 * Rainbow Architect hunts across the entire pride
 * 
 * "The lion scans his pride and hunts" — Gary Leckey, Nov 15 2025
 */

import { BinanceClient } from '../core/binanceClient';
import { writeFileSync } from 'fs';

interface TradingPair {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  status: string;
  price?: number;
  volume24h?: number;
  priceChangePercent?: number;
}

interface PrideMap {
  ethPairs: TradingPair[];
  usdtPairs: TradingPair[];
  crossPairs: TradingPair[]; // Coins tradeable from both ETH and USDT
  totalSymbols: number;
}

export class PrideScanner {
  private client: BinanceClient;
  private prideMap: PrideMap = {
    ethPairs: [],
    usdtPairs: [],
    crossPairs: [],
    totalSymbols: 0,
  };

  constructor(apiKey: string, apiSecret: string, testnet: boolean = true) {
    this.client = new BinanceClient({ apiKey, apiSecret, testnet });
  }

  /**
   * Scan all available trading pairs from Binance
   */
  async scanPride(): Promise<PrideMap> {
    console.log('\n🦁 PRIDE SCANNER — The Lion Hunts All Prey\n');
    console.log('📡 Connecting to Binance...\n');

    try {
      // Get all exchange symbols
      const exchangeInfo = await this.client.getExchangeInfo();
      const symbols = exchangeInfo.symbols.filter((s: any) => s.status === 'TRADING');

      console.log(`✅ Found ${symbols.length} active trading pairs\n`);

      // Separate by quote asset (ETH or USDT)
      const ethPairs: TradingPair[] = [];
      const usdtPairs: TradingPair[] = [];
      const baseAssets = new Set<string>();

      for (const symbol of symbols) {
        const pair: TradingPair = {
          symbol: symbol.symbol,
          baseAsset: symbol.baseAsset,
          quoteAsset: symbol.quoteAsset,
          status: symbol.status,
        };

        if (symbol.quoteAsset === 'ETH') {
          ethPairs.push(pair);
          baseAssets.add(symbol.baseAsset);
        } else if (symbol.quoteAsset === 'USDT') {
          usdtPairs.push(pair);
          baseAssets.add(symbol.baseAsset);
        }
      }

      console.log('🌈 BASE PAIRS MAPPED:\n');
      console.log(`   ETH Pairs:  ${ethPairs.length} symbols`);
      console.log(`   USDT Pairs: ${usdtPairs.length} symbols`);
      console.log(`   Unique Assets: ${baseAssets.size}\n`);

      // Find cross-pairs (coins tradeable from both ETH and USDT)
      const ethBases = new Set(ethPairs.map(p => p.baseAsset));
      const usdtBases = new Set(usdtPairs.map(p => p.baseAsset));
      const crossBases = [...ethBases].filter(base => usdtBases.has(base));

      console.log(`🎯 CROSS-PAIRS (Hunt from Both Bases): ${crossBases.length}\n`);

      // Get current prices and 24h stats for top pairs
      console.log('📊 Fetching market data...\n');
      const ticker24h = await this.fetch24hTicker();

      // Enrich pairs with market data
      this.enrichPairsWithMarketData(ethPairs, ticker24h);
      this.enrichPairsWithMarketData(usdtPairs, ticker24h);

      // Identify cross-pairs
      const crossPairs = ethPairs
        .filter(p => crossBases.includes(p.baseAsset))
        .map(ethPair => {
          const usdtPair = usdtPairs.find(p => p.baseAsset === ethPair.baseAsset);
          return {
            ...ethPair,
            usdtSymbol: usdtPair?.symbol,
            usdtPrice: usdtPair?.price,
          };
        });

      this.prideMap = {
        ethPairs: ethPairs.sort((a, b) => (b.volume24h || 0) - (a.volume24h || 0)),
        usdtPairs: usdtPairs.sort((a, b) => (b.volume24h || 0) - (a.volume24h || 0)),
        crossPairs: crossPairs as any,
        totalSymbols: symbols.length,
      };

      return this.prideMap;
    } catch (error: any) {
      console.error('❌ Pride scan failed:', error.message);
      throw error;
    }
  }

  /**
   * Fetch 24h ticker stats for all symbols
   */
  private async fetch24hTicker(): Promise<Map<string, any>> {
    try {
      const response = await fetch(
        `${this.client['baseUrl']}/v3/ticker/24hr`,
        {
          headers: {
            'X-MBX-APIKEY': this.client['apiKey'],
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const tickers = await response.json();
      const map = new Map();

      for (const ticker of tickers) {
        map.set(ticker.symbol, {
          price: parseFloat(ticker.lastPrice),
          volume: parseFloat(ticker.volume),
          quoteVolume: parseFloat(ticker.quoteVolume),
          priceChangePercent: parseFloat(ticker.priceChangePercent),
          highPrice: parseFloat(ticker.highPrice),
          lowPrice: parseFloat(ticker.lowPrice),
        });
      }

      return map;
    } catch (error) {
      console.warn('⚠️  Could not fetch 24h ticker data');
      return new Map();
    }
  }

  /**
   * Enrich pairs with market data
   */
  private enrichPairsWithMarketData(pairs: TradingPair[], tickerMap: Map<string, any>) {
    for (const pair of pairs) {
      const ticker = tickerMap.get(pair.symbol);
      if (ticker) {
        pair.price = ticker.price;
        pair.volume24h = ticker.quoteVolume;
        pair.priceChangePercent = ticker.priceChangePercent;
      }
    }
  }

  /**
   * Display the pride map
   */
  displayPride(limit: number = 20) {
    console.log('\n═══════════════════════════════════════════════════════════');
    console.log('   🦁 THE PRIDE — All Hunting Grounds Mapped');
    console.log('═══════════════════════════════════════════════════════════\n');

    console.log(`📊 Total Trading Pairs: ${this.prideMap.totalSymbols}`);
    console.log(`🌈 ETH Base: ${this.prideMap.ethPairs.length} pairs`);
    console.log(`💰 USDT Base: ${this.prideMap.usdtPairs.length} pairs`);
    console.log(`🎯 Cross-Pairs: ${this.prideMap.crossPairs.length} pairs\n`);

    console.log('─────────────────────────────────────────────────────');
    console.log(`TOP ${limit} ETH PAIRS (by 24h volume):`);
    console.log('─────────────────────────────────────────────────────\n');

    this.prideMap.ethPairs.slice(0, limit).forEach((pair, i) => {
      const volume = pair.volume24h ? `${(pair.volume24h).toFixed(2)} ETH` : 'N/A';
      const change = pair.priceChangePercent ? 
        `${pair.priceChangePercent > 0 ? '+' : ''}${pair.priceChangePercent.toFixed(2)}%` : 
        'N/A';
      const price = pair.price ? pair.price.toFixed(8) : 'N/A';
      console.log(`${(i + 1).toString().padStart(2)}. ${pair.symbol.padEnd(12)} ${price.padStart(12)} ETH  |  ${change.padStart(8)}  |  Vol: ${volume}`);
    });

    console.log('\n─────────────────────────────────────────────────────');
    console.log(`TOP ${limit} USDT PAIRS (by 24h volume):`);
    console.log('─────────────────────────────────────────────────────\n');

    this.prideMap.usdtPairs.slice(0, limit).forEach((pair, i) => {
      const volume = pair.volume24h ? `$${(pair.volume24h / 1000000).toFixed(2)}M` : 'N/A';
      const change = pair.priceChangePercent ? 
        `${pair.priceChangePercent > 0 ? '+' : ''}${pair.priceChangePercent.toFixed(2)}%` : 
        'N/A';
      const price = pair.price ? `$${pair.price.toFixed(4)}` : 'N/A';
      console.log(`${(i + 1).toString().padStart(2)}. ${pair.symbol.padEnd(12)} ${price.padStart(12)}  |  ${change.padStart(8)}  |  Vol: ${volume}`);
    });

    console.log('\n─────────────────────────────────────────────────────');
    console.log(`TOP ${limit} CROSS-PAIRS (Hunt from Both Bases):`);
    console.log('─────────────────────────────────────────────────────\n');

    this.prideMap.crossPairs.slice(0, limit).forEach((pair: any, i) => {
      const ethPrice = pair.price ? pair.price.toFixed(8) : 'N/A';
      const usdtPrice = pair.usdtPrice ? `$${pair.usdtPrice.toFixed(4)}` : 'N/A';
      const change = pair.priceChangePercent ? 
        `${pair.priceChangePercent > 0 ? '+' : ''}${pair.priceChangePercent.toFixed(2)}%` : 
        'N/A';
      console.log(`${(i + 1).toString().padStart(2)}. ${pair.baseAsset.padEnd(8)} | ${pair.symbol.padEnd(12)} ${ethPrice.padStart(12)} ETH | ${pair.usdtSymbol?.padEnd(12) || ''} ${usdtPrice.padStart(10)} | ${change.padStart(8)}`);
    });

    console.log('\n═══════════════════════════════════════════════════════════');
    console.log('   🦁 THE LION SEES ALL — No Stone Unturned');
    console.log('═══════════════════════════════════════════════════════════\n');
  }

  /**
   * Get hunting targets (high volume, high volatility)
   */
  getHuntingTargets(minVolumeETH: number = 10, minVolatility: number = 2): TradingPair[] {
    const targets = [
      ...this.prideMap.ethPairs,
      ...this.prideMap.usdtPairs,
    ].filter(pair => {
      const hasVolume = (pair.volume24h || 0) > minVolumeETH;
      const hasVolatility = Math.abs(pair.priceChangePercent || 0) > minVolatility;
      return hasVolume && hasVolatility;
    });

    return targets.sort((a, b) => {
      const scoreA = (a.volume24h || 0) * Math.abs(a.priceChangePercent || 0);
      const scoreB = (b.volume24h || 0) * Math.abs(b.priceChangePercent || 0);
      return scoreB - scoreA;
    });
  }

  /**
   * Export pride map to JSON
   */
  exportPrideMap(filename: string = 'pride_map.json') {
    writeFileSync(filename, JSON.stringify(this.prideMap, null, 2));
    console.log(`\n📝 Pride map exported to ${filename}`);
  }

  /**
   * Get the pride map
   */
  getPrideMap(): PrideMap {
    return this.prideMap;
  }
}

/**
 * Main execution
 */
async function main() {
  const apiKey = process.env.BINANCE_API_KEY || '';
  const apiSecret = process.env.BINANCE_API_SECRET || '';
  const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");

  if (!apiKey || !apiSecret) {
    console.error('❌ BINANCE_API_KEY and BINANCE_API_SECRET must be set');
    process.exit(1);
  }

  const scanner = new PrideScanner(apiKey, apiSecret, testnet);

  try {
    // Scan the pride
    await scanner.scanPride();

    // Display results
    scanner.displayPride(20);

    // Get hunting targets
    console.log('\n🎯 HUNTING TARGETS (High Volume + High Volatility):\n');
    const targets = scanner.getHuntingTargets(10, 2);
    targets.slice(0, 10).forEach((target, i) => {
      const volume = target.volume24h ? (target.volume24h / 1000000).toFixed(2) : '0';
      const change = target.priceChangePercent?.toFixed(2) || '0';
      console.log(`${(i + 1).toString().padStart(2)}. ${target.symbol.padEnd(12)} | Change: ${change.padStart(6)}% | Volume: $${volume}M`);
    });

    // Export
    scanner.exportPrideMap('/workspaces/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-/artifacts/pride_map.json');

    console.log('\n🦁 The lion has scanned his pride.');
    console.log('🌈 Every stone has been turned.');
    console.log('🔥 The hunt begins.\n');

  } catch (error: any) {
    console.error('\n❌ Pride scan failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
main().catch(console.error);

export default PrideScanner;
