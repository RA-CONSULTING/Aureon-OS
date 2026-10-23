import { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';

export interface MarginSentiment {
  crossMargin: {
    marginLevel: number;
    totalAssetOfBtc: number;
    totalLiabilityOfBtc: number;
    totalNetAssetOfBtc: number;
    riskLevel: string;
  };
  isolatedMargin: any | null;
  collateralRatio: any[];
  interestRate: any | null;
  recentLiquidations: {
    count: number;
    totalVolume: number;
    avgPrice: number;
  };
  sentiment: {
    leverageRisk: number; // 0-1, higher = more risk
    liquidationPressure: number; // 0-1, higher = more pressure
    borrowingCost: number;
    marketHealth: number; // 0-1, higher = healthier
  };
}

export const useBinanceMarginData = (symbol: string = 'BTC', refreshInterval: number = 30000) => {
  const [marginData, setMarginData] = useState<MarginSentiment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMarginData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      console.log('[useBinanceMarginData] Fetching margin data for:', symbol);
      
      const { data, error: functionError } = await supabase.functions.invoke('fetch-binance-margin-data', {
        body: { symbol },
      });

      if (functionError) throw functionError;
      if (data.error) throw new Error(data.error);

      setMarginData(data);
      
      console.log('[useBinanceMarginData] Margin data fetched:', {
        marketHealth: data.sentiment.marketHealth,
        leverageRisk: data.sentiment.leverageRisk,
        liquidations: data.recentLiquidations.count,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch margin data';
      console.error('[useBinanceMarginData] Error:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMarginData();

    if (refreshInterval > 0) {
      const interval = setInterval(fetchMarginData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [symbol, refreshInterval]);

  return {
    marginData,
    isLoading,
    error,
    refetch: fetchMarginData,
  };
};