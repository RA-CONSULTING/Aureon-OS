import { useState, useEffect, useCallback, useRef } from 'react';
import { useMarketScanner, type MarketOpportunity } from './useMarketScanner';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { QGITASignalGenerator } from '@/core/qgitaSignalGenerator';
import { MasterEquation } from '@/core/masterEquation';
import type { MarketSnapshot } from '@/core/aurisNodes';

const LIGHTHOUSE_THRESHOLD = 0.945;

export function useAutonomousTrading() {
  const [isActive, setIsActive] = useState(false);
  const [tradesExecuted, setTradesExecuted] = useState(0);
  const [executionReceipts, setExecutionReceipts] = useState<any[]>([]);
  const { opportunities, scanMarket, isScanning, totalPairs, lastError } = useMarketScanner();
  const { toast } = useToast();
  const signalGenerator = useRef(new QGITASignalGenerator());
  const masterEquation = useRef(new MasterEquation());
  const processingRef = useRef(false);
  const liveExecutionConfirmedRef = useRef(false);

  const processOpportunity = useCallback(async (opp: MarketOpportunity) => {
    if (!liveExecutionConfirmedRef.current) return;
    const snapshot: MarketSnapshot = {
      price: opp.price,
      volume: opp.volume24h,
      volatility: opp.volatility,
      momentum: opp.momentum,
      spread: opp.spread,
      timestamp: opp.timestamp,
      truthStatus: opp.truthStatus,
      sourceId: opp.sourceId,
      sourceTimestamp: opp.sourceTimestamp,
      generatedValues: false,
    };
    const lambdaState = await masterEquation.current.step(snapshot);
    if (lambdaState.coherence < LIGHTHOUSE_THRESHOLD) return;

    const signal = signalGenerator.current.generateSignal(
      snapshot.timestamp,
      snapshot.price,
      snapshot.volume,
      lambdaState.lambda,
      lambdaState.coherence,
      lambdaState.substrate,
      lambdaState.observer,
      lambdaState.echo,
      snapshot,
    );
    if (!signal || !signal.lighthouse.isLHE || signal.tier !== 1 || signal.signalType === 'HOLD') return;

    const { data, error } = await supabase.functions.invoke('execute-trade', {
      body: {
        liveExecutionConfirmed: true,
        symbol: opp.symbol,
        signalType: signal.signalType === 'BUY' ? 'LONG' : 'SHORT',
        coherence: lambdaState.coherence,
        lighthouseValue: signal.lighthouse.L,
        lighthouseConfidence: signal.confidence,
        prismLevel: signal.tier,
        currentPrice: opp.price,
        truthStatus: opp.truthStatus,
        sourceId: opp.sourceId,
        sourceTimestamp: opp.sourceTimestamp,
        generatedValues: false,
      },
    });
    if (error || !data?.success || data?.truthStatus !== 'live' || data?.generatedValues !== false) {
      throw new Error(error?.message || data?.error || 'LIVE_EXECUTION_RECEIPT_REQUIRED');
    }
    setTradesExecuted((count) => count + 1);
    setExecutionReceipts((receipts) => [...receipts, data].slice(-100));
  }, []);

  useEffect(() => {
    if (!isActive || processingRef.current || opportunities.length === 0) return;
    let cancelled = false;
    const run = async () => {
      processingRef.current = true;
      try {
        for (const opportunity of opportunities.slice(0, 20)) {
          if (cancelled || !liveExecutionConfirmedRef.current) break;
          try {
            await processOpportunity(opportunity);
          } catch (error) {
            console.error(`[AutonomousTrading] ${opportunity.symbol}:`, error);
          }
        }
      } finally {
        processingRef.current = false;
      }
    };
    run();
    return () => { cancelled = true; };
  }, [opportunities, isActive, processOpportunity]);

  useEffect(() => {
    if (!isActive) return;
    scanMarket();
    const interval = setInterval(scanMarket, 30_000);
    return () => clearInterval(interval);
  }, [isActive, scanMarket]);

  const start = useCallback(() => {
    const confirmed = window.confirm(
      'LIVE EXECUTION: this can submit real Binance market orders using real funds. Continue with autonomous execution for this active session?',
    );
    if (!confirmed) return;
    liveExecutionConfirmedRef.current = true;
    setIsActive(true);
    toast({
      title: 'Live autonomous execution enabled',
      description: 'Only fresh provider tickers, real-derived QGITA signals, and provider order receipts are accepted.',
    });
  }, [toast]);

  const stop = useCallback(() => {
    liveExecutionConfirmedRef.current = false;
    setIsActive(false);
    toast({
      title: 'Autonomous execution stopped',
      description: `${tradesExecuted} provider-confirmed order receipts recorded this session.`,
    });
  }, [tradesExecuted, toast]);

  return {
    isActive,
    isScanning,
    tradesExecuted,
    totalProfit: null,
    totalFees: null,
    netProfit: null,
    executionReceipts,
    opportunities: opportunities.slice(0, 20),
    totalPairs,
    lastError,
    start,
    stop,
  };
}
