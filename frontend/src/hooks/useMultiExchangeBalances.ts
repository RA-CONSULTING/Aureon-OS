/**
 * Multi-Exchange Balances Hook
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * React hook for managing multi-exchange balances using authenticated get-user-balances
 */

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { finiteOrNull } from '@/lib/reading';
import { smartOrderRouter, RoutingDecision } from '../core/smartOrderRouter';
import { ExchangeType } from '../core/unifiedExchangeClient';

export interface ExchangeBalance {
  exchange: string;
  connected: boolean;
  assets: Array<{ asset: string; free: number; locked: number; usdValue: number }>;
  totalUsd: number;
  error?: string;
}

export interface ConsolidatedBalance {
  asset: string;
  totalFree: number;
  totalLocked: number;
  grandTotal: number;
  usdValue: number;
  balances: Record<string, { free: number; locked: number }>;
}

export interface ExchangeStatus {
  exchange: ExchangeType;
  connected: boolean;
  lastUpdate: number;
  balanceCount: number;
  totalUsdValue: number | null;
}

export interface MultiExchangeState {
  exchanges: ExchangeStatus[];
  consolidatedBalances: ConsolidatedBalance[];
  totalEquityUsd: number | null;
  lastUpdate: number;
}

export interface UseMultiExchangeBalancesResult {
  state: MultiExchangeState | null;
  consolidatedBalances: ConsolidatedBalance[];
  exchangeStatuses: ExchangeStatus[];
  totalEquityUsd: number | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  getRouting: (symbol: string, side: 'BUY' | 'SELL', quantity: number) => Promise<RoutingDecision | null>;
  lastRoutingDecision: RoutingDecision | null;
  getPositionSize: (riskPercentage?: number) => { positionSizeUsd: number | null; availableBalance: number | null; riskAmount: number | null };
}

export function useMultiExchangeBalances(): UseMultiExchangeBalancesResult {
  const [state, setState] = useState<MultiExchangeState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRoutingDecision, setLastRoutingDecision] = useState<RoutingDecision | null>(null);

  const fetchBalances = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const { data, error: fnError } = await supabase.functions.invoke('get-user-balances', {
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });

      if (fnError) {
        throw new Error(fnError.message || 'Failed to fetch balances');
      }

      if (data?.success) {
        const balances: ExchangeBalance[] = data.balances || [];
        
        // Build consolidated balances
        const assetMap = new Map<string, ConsolidatedBalance>();
        
        for (const exchange of balances) {
          if (!exchange.connected) continue;
          
          for (const asset of exchange.assets) {
            const existing = assetMap.get(asset.asset);
            if (existing) {
              existing.totalFree += asset.free;
              existing.totalLocked += asset.locked;
              existing.grandTotal += asset.free + asset.locked;
              existing.usdValue += asset.usdValue;
              existing.balances[exchange.exchange] = { free: asset.free, locked: asset.locked };
            } else {
              assetMap.set(asset.asset, {
                asset: asset.asset,
                totalFree: asset.free,
                totalLocked: asset.locked,
                grandTotal: asset.free + asset.locked,
                usdValue: asset.usdValue,
                balances: { [exchange.exchange]: { free: asset.free, locked: asset.locked } }
              });
            }
          }
        }

        // Build exchange statuses
        const exchangeStatuses: ExchangeStatus[] = balances.map(b => ({
          exchange: b.exchange as ExchangeType,
          connected: b.connected,
          lastUpdate: Date.now(),
          balanceCount: b.assets.length,
          totalUsdValue: finiteOrNull(b.totalUsd)
        }));

        setState({
          exchanges: exchangeStatuses,
          consolidatedBalances: Array.from(assetMap.values()).sort((a, b) => b.usdValue - a.usdValue),
          totalEquityUsd: finiteOrNull(data.totalEquityUsd),
          lastUpdate: Date.now()
        });
      } else {
        throw new Error(data?.error || 'Failed to fetch balances');
      }
    } catch (err) {
      console.error('[useMultiExchangeBalances] Error:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch balances');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBalances();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchBalances, 30000);
    return () => clearInterval(interval);
  }, [fetchBalances]);

  const getRouting = useCallback(async (
    symbol: string,
    side: 'BUY' | 'SELL',
    quantity: number
  ): Promise<RoutingDecision | null> => {
    try {
      const decision = await smartOrderRouter.getBestQuote(symbol, side, quantity);
      setLastRoutingDecision(decision);
      return decision;
    } catch (err) {
      console.error('Routing error:', err);
      return null;
    }
  }, []);

  const getPositionSize = useCallback((riskPercentage: number = 0.02) => {
    const totalEquity = finiteOrNull(state?.totalEquityUsd);
    if (totalEquity == null || !Number.isFinite(riskPercentage)) {
      return { positionSizeUsd: null, availableBalance: totalEquity, riskAmount: null };
    }
    const riskAmount = totalEquity * riskPercentage;
    return {
      positionSizeUsd: riskAmount * 10,
      availableBalance: totalEquity,
      riskAmount
    };
  }, [state?.totalEquityUsd]);

  return {
    state,
    consolidatedBalances: state?.consolidatedBalances || [],
    exchangeStatuses: state?.exchanges || [],
    totalEquityUsd: finiteOrNull(state?.totalEquityUsd),
    isLoading,
    error,
    refresh: fetchBalances,
    getRouting,
    lastRoutingDecision,
    getPositionSize
  };
}

/**
 * Hook for getting balance for a specific asset across exchanges
 */
export function useAssetBalance(asset: string) {
  const { consolidatedBalances } = useMultiExchangeBalances();
  
  const balance = consolidatedBalances.find(b => b.asset === asset);
  
  return {
    asset,
    totalFree: finiteOrNull(balance?.totalFree),
    totalLocked: finiteOrNull(balance?.totalLocked),
    grandTotal: finiteOrNull(balance?.grandTotal),
    usdValue: finiteOrNull(balance?.usdValue),
    byExchange: balance?.balances || {}
  };
}

/**
 * Hook for exchange status only
 */
export function useExchangeStatus(exchange: ExchangeType) {
  const { exchangeStatuses } = useMultiExchangeBalances();
  
  return exchangeStatuses.find(s => s.exchange === exchange) || {
    exchange,
    connected: false,
    lastUpdate: 0,
    balanceCount: 0,
    totalUsdValue: 0
  };
}
