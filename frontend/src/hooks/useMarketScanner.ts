import { useState, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { assertFreshProvenance, type DataProvenance } from '@/core/liveDataContract';

export interface MarketOpportunity extends DataProvenance {
  symbol: string;
  exchange: string;
  baseAsset: string;
  price: number;
  volume24h: number;
  volumeUsd: number;
  bidPrice: number;
  askPrice: number;
  priceChange24h: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
  opportunityScore: number;
}

export function useMarketScanner() {
  const [opportunities, setOpportunities] = useState<MarketOpportunity[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [lastScan, setLastScan] = useState<Date | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [totalPairs, setTotalPairs] = useState(0);

  const scanMarket = useCallback(async () => {
    setIsScanning(true);
    setLastError(null);
    try {
      const { data, error } = await supabase.functions.invoke('fetch-all-tickers', {
        body: { exchanges: ['binance', 'kraken'], limit: 500 },
      });
      if (error || !data?.success || !Array.isArray(data.tickers)) {
        throw new Error(error?.message || data?.error || 'NO_DATA: live ticker scan failed');
      }

      const liveRows: MarketOpportunity[] = [];
      for (const ticker of data.tickers) {
        try {
          assertFreshProvenance(ticker);
          const values = [
            ticker.price, ticker.volume, ticker.volumeUsd, ticker.bidPrice, ticker.askPrice,
            ticker.priceChange24h, ticker.volatility, ticker.momentum, ticker.spread, ticker.timestamp,
          ];
          if (!values.every(Number.isFinite) || ticker.price <= 0 || ticker.volume < 0 || ticker.volumeUsd < 0) continue;
          const volumeScore = Math.log10(Math.max(1, ticker.volumeUsd)) / 10;
          const opportunityScore = ticker.volatility * 0.4 + volumeScore * 0.3 + Math.abs(ticker.momentum) * 0.3;
          liveRows.push({
            symbol: ticker.symbol,
            exchange: ticker.exchange,
            baseAsset: String(ticker.symbol).replace(/(USDT|USD)$/i, ''),
            price: ticker.price,
            volume24h: ticker.volume,
            volumeUsd: ticker.volumeUsd,
            bidPrice: ticker.bidPrice,
            askPrice: ticker.askPrice,
            priceChange24h: ticker.priceChange24h,
            volatility: ticker.volatility,
            momentum: ticker.momentum,
            spread: ticker.spread,
            timestamp: ticker.timestamp,
            opportunityScore,
            truthStatus: 'real_derived',
            sourceId: ticker.sourceId,
            sourceTimestamp: ticker.sourceTimestamp,
            generatedValues: false,
          });
        } catch {
          // Invalid rows remain absent; they are never converted into fallback values.
        }
      }
      liveRows.sort((a, b) => b.opportunityScore - a.opportunityScore);
      if (liveRows.length === 0) throw new Error('NO_DATA: provider returned no valid fresh ticker rows');
      setOpportunities(liveRows.slice(0, 100));
      setTotalPairs(liveRows.length);
      setLastScan(new Date(Math.max(...liveRows.map((row) => row.timestamp))));
    } catch (error) {
      setOpportunities([]);
      setTotalPairs(0);
      setLastScan(null);
      setLastError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsScanning(false);
    }
  }, []);

  return { opportunities, isScanning, lastScan, lastError, totalPairs, scanMarket };
}
