#!/usr/bin/env tsx
/**
 * LIST ALL TRADABLE PAIRS ON BINANCE
 * 
 * Fetches complete list of trading pairs with filters:
 * - USDT pairs (most liquid)
 * - USDC pairs (alternative stablecoin)
 * - Status: TRADING only
 * - Volume, volatility, spread metrics
 */
import 'dotenv/config';
import { BinanceClient } from '../core/binanceClient';

interface PairInfo {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  status: string;
  volume24h?: number;
  priceChange24h?: number;
  price?: number;
  high24h?: number;
  low24h?: number;
  volatility?: number;
}

async function main() {
  const quoteFilter = process.env.QUOTE_FILTER || 'USDT,USDC,BUSD,FDUSD'; // Stablecoins
  const minVolume = Number(process.env.MIN_VOLUME || 0); // Minimum 24h volume
  const showMetrics = process.env.SHOW_METRICS !== 'false';
  
  console.log('\n🌐 SCANNING BINANCE EXCHANGE...\n');
  
  const testnet = false; // Use mainnet for complete list
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    console.error('❌ API credentials required in .env');
    process.exit(1);
  }
  
  const client = new BinanceClient({ apiKey, apiSecret, testnet });
  
  console.log('Fetching exchange info...');
  const exchangeInfo = await client.getExchangeInfo();
  
  const quoteAssets = quoteFilter.split(',');
  const tradingPairs: PairInfo[] = [];
  
  // Filter trading pairs
  for (const symbolInfo of exchangeInfo.symbols) {
    if (symbolInfo.status !== 'TRADING') continue;
    if (!quoteAssets.includes(symbolInfo.quoteAsset)) continue;
    
    tradingPairs.push({
      symbol: symbolInfo.symbol,
      baseAsset: symbolInfo.baseAsset,
      quoteAsset: symbolInfo.quoteAsset,
      status: symbolInfo.status
    });
  }
  
  console.log(`Found ${tradingPairs.length} active trading pairs\n`);
  
  if (showMetrics) {
    console.log('Fetching 24h statistics for all pairs...');
    const stats24h = await fetch('https://api.binance.com/api/v3/ticker/24hr')
      .then(r => r.json()) as any[];
    
    const statsMap = new Map(stats24h.map(s => [s.symbol, s]));
    
    // Enrich with metrics
    for (const pair of tradingPairs) {
      const stats = statsMap.get(pair.symbol);
      if (stats) {
        pair.volume24h = Number(stats.volume);
        pair.priceChange24h = Number(stats.priceChangePercent);
        pair.price = Number(stats.lastPrice);
        pair.high24h = Number(stats.highPrice);
        pair.low24h = Number(stats.lowPrice);
        pair.volatility = pair.price > 0 
          ? ((pair.high24h! - pair.low24h!) / pair.price) * 100 
          : 0;
      }
    }
    
    // Filter by volume
    const filtered = tradingPairs.filter(p => 
      !minVolume || (p.volume24h && p.volume24h >= minVolume)
    );
    
    // Sort by volume
    filtered.sort((a, b) => (b.volume24h || 0) - (a.volume24h || 0));
    
    console.log(`\n📊 TOP PAIRS BY VOLUME (min: ${minVolume}):\n`);
    console.log('SYMBOL'.padEnd(15) + 'BASE'.padEnd(10) + 'QUOTE'.padEnd(8) + 'VOLUME'.padEnd(15) + 'CHANGE%'.padEnd(10) + 'VOL%'.padEnd(10) + 'PRICE');
    console.log('─'.repeat(80));
    
    for (const pair of filtered.slice(0, 100)) {
      const volumeStr = pair.volume24h 
        ? pair.volume24h > 1000000 
          ? `${(pair.volume24h / 1000000).toFixed(2)}M`
          : pair.volume24h > 1000
            ? `${(pair.volume24h / 1000).toFixed(2)}K`
            : pair.volume24h.toFixed(0)
        : 'N/A';
      
      const changeStr = pair.priceChange24h !== undefined
        ? `${pair.priceChange24h > 0 ? '+' : ''}${pair.priceChange24h.toFixed(2)}%`
        : 'N/A';
      
      const volStr = pair.volatility !== undefined
        ? `${pair.volatility.toFixed(2)}%`
        : 'N/A';
      
      const priceStr = pair.price !== undefined
        ? `$${pair.price.toFixed(pair.price < 1 ? 6 : 2)}`
        : 'N/A';
      
      console.log(
        pair.symbol.padEnd(15) +
        pair.baseAsset.padEnd(10) +
        pair.quoteAsset.padEnd(8) +
        volumeStr.padEnd(15) +
        changeStr.padEnd(10) +
        volStr.padEnd(10) +
        priceStr
      );
    }
    
    // Statistics
    console.log(`\n\n📈 STATISTICS:`);
    console.log(`Total Pairs: ${filtered.length}`);
    console.log(`Avg Volume: ${(filtered.reduce((s, p) => s + (p.volume24h || 0), 0) / filtered.length).toFixed(0)}`);
    console.log(`Avg Volatility: ${(filtered.reduce((s, p) => s + (p.volatility || 0), 0) / filtered.length).toFixed(2)}%`);
    
    // Group by quote asset
    console.log(`\n📊 BY QUOTE ASSET:`);
    for (const quote of quoteAssets) {
      const count = filtered.filter(p => p.quoteAsset === quote).length;
      console.log(`  ${quote}: ${count} pairs`);
    }
    
    // High volatility coins (>5%)
    const highVol = filtered.filter(p => p.volatility && p.volatility > 5);
    console.log(`\n🔥 HIGH VOLATILITY (>5%): ${highVol.length} pairs`);
    highVol.slice(0, 20).forEach(p => {
      console.log(`  ${p.symbol.padEnd(15)} ${p.volatility!.toFixed(2)}% vol | ${p.priceChange24h!.toFixed(2)}% change`);
    });
    
    // Export to JSON
    const exportData = {
      timestamp: new Date().toISOString(),
      totalPairs: filtered.length,
      quoteAssets: quoteAssets,
      minVolume: minVolume,
      pairs: filtered.map(p => ({
        symbol: p.symbol,
        base: p.baseAsset,
        quote: p.quoteAsset,
        volume: p.volume24h,
        change: p.priceChange24h,
        volatility: p.volatility,
        price: p.price
      }))
    };
    
    const fs = await import('fs');
    fs.writeFileSync('tradable_pairs.json', JSON.stringify(exportData, null, 2));
    console.log(`\n💾 Exported to tradable_pairs.json`);
    
  } else {
    // Simple list without metrics
    console.log('SYMBOL'.padEnd(15) + 'BASE'.padEnd(10) + 'QUOTE');
    console.log('─'.repeat(35));
    
    tradingPairs.forEach(p => {
      console.log(p.symbol.padEnd(15) + p.baseAsset.padEnd(10) + p.quoteAsset);
    });
  }
  
  console.log(`\n✅ Complete\n`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
