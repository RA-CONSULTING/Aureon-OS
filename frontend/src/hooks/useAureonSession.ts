import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { unifiedOrchestrator, type OrchestrationResult } from '@/core/unifiedOrchestrator';
import { unifiedBus, type BusSnapshot } from '@/core/unifiedBus';
import { temporalLadder, SYSTEMS } from '@/core/temporalLadder';
import { multiExchangeClient, type MultiExchangeState } from '@/core/multiExchangeClient';
import { thePrism, type PrismOutput } from '@/core/thePrism';
import { toast } from 'sonner';

export interface QuantumState {
  coherence: number;
  lambda: number;
  lighthouseSignal: number;
  dominantNode: string;
  prismLevel: number;
  prismState: string;
  substrate: number;
  observer: number;
  echo: number;
}

export interface TradingState {
  isActive: boolean;
  totalEquity: number;
  availableBalance: number;
  totalTrades: number;
  winningTrades: number;
  totalPnl: number;
  gasTankBalance: number;
  recentTrades: Array<{
    time: string;
    side: string;
    symbol: string;
    quantity: number;
    pnl: number;
    success: boolean;
  }>;
}

export interface SystemStatus {
  masterEquation: boolean;
  lighthouse: boolean;
  rainbowBridge: boolean;
  elephantMemory: boolean;
  orderRouter: boolean;
}

export interface BusState {
  snapshot: BusSnapshot | null;
  consensusSignal: string;
  consensusConfidence: number;
  systemsReady: number;
}

export interface ExchangeState {
  totalEquityUsd: number;
  exchanges: Array<{ exchange: string; connected: boolean; totalUsdValue: number }>;
}

export interface PrismState {
  output: PrismOutput | null;
  frequency: number;
  resonance: number;
  isLoveLocked: boolean;
}

export interface RoutingState {
  recommendedExchange: string | null;
  positionSizeUsd: number;
  availableBalance: number;
  reasoning: string | null;
}

export interface MarketData {
  price: number;
  volume: number;
  volatility: number;
  momentum: number;
  spread: number;
  timestamp: number;
  truthStatus: 'live' | 'real_derived';
  sourceId: string;
  sourceTimestamp: string;
  generatedValues: false;
}

export function useAureonSession(userId: string | null) {
  const [quantumState, setQuantumState] = useState<QuantumState>({
    coherence: null,
    lambda: null,
    lighthouseSignal: null,
    dominantNode: null,
    prismLevel: null,
    prismState: null,
    substrate: null,
    observer: null,
    echo: null,
  });

  const [prismState, setPrismState] = useState<PrismState>({
    output: null,
    frequency: null,
    resonance: null,
    isLoveLocked: null,
  });

  const [marketData, setMarketData] = useState<MarketData | null>(null);

  const [routingState, setRoutingState] = useState<RoutingState>({
    recommendedExchange: null,
    positionSizeUsd: null,
    availableBalance: null,
    reasoning: null
  });
  
  const [tradingState, setTradingState] = useState<TradingState>({
    isActive: false,
    totalEquity: null,
    availableBalance: null,
    totalTrades: 0,
    winningTrades: 0,
    totalPnl: null,
    gasTankBalance: null,
    recentTrades: []
  });
  
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    masterEquation: false,
    lighthouse: false,
    rainbowBridge: false,
    elephantMemory: false,
    orderRouter: false
  });

  const [busState, setBusState] = useState<BusState>({
    snapshot: null,
    consensusSignal: null,
    consensusConfidence: null,
    systemsReady: 0
  });

  const [exchangeState, setExchangeState] = useState<ExchangeState>({
    totalEquityUsd: null,
    exchanges: []
  });
  
  const [lastSignal, setLastSignal] = useState<string | null>(null);
  const [nextCheckIn, setNextCheckIn] = useState(3);
  const [lastDecision, setLastDecision] = useState<OrchestrationResult | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);
  const busUnsubRef = useRef<(() => void) | null>(null);
  const exchangeUnsubRef = useRef<(() => void) | null>(null);

  // Fetch real market data via edge function
  const fetchMarketData = useCallback(async (symbol: string = 'BTCUSDT') => {
    const { data, error } = await supabase.functions.invoke('get-user-market-data', {
      body: { symbol }
    });

    if (error) {
      console.error('[Aureon] Market data fetch failed - NO SIMULATION FALLBACK:', error);
      throw new Error(`LIVE_DATA_REQUIRED: Failed to fetch market data for ${symbol}. Check exchange credentials.`);
    }
    
    const sourceAgeMs = Date.now() - Date.parse(String(data?.sourceTimestamp || ''));
    if (!data || !Number.isFinite(Number(data.price)) || Number(data.price) <= 0 ||
        !['live', 'real_derived'].includes(String(data.truthStatus)) ||
        !data.sourceId || data.generatedValues !== false ||
        !Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > 300000) {
      throw new Error(`LIVE_DATA_REQUIRED: Invalid market data response for ${symbol}. No simulation allowed.`);
    }
    
    return data;
  }, []);

  // Initialize all systems
  const initializeSystems = useCallback(async () => {
    try {
      // Initialize multi-exchange client
      await multiExchangeClient.initialize();

      // Subscribe to UnifiedBus updates
      busUnsubRef.current = unifiedBus.subscribe((snapshot) => {
        setBusState({
          snapshot,
          consensusSignal: snapshot.consensusSignal,
          consensusConfidence: snapshot.consensusConfidence,
          systemsReady: snapshot.systemsReady
        });
        setSystemStatus({
          masterEquation: snapshot.states.MasterEquation?.ready === true,
          lighthouse: snapshot.states.Lighthouse?.ready === true,
          rainbowBridge: snapshot.states.RainbowBridge?.ready === true,
          elephantMemory: snapshot.states.ElephantMemory?.ready === true,
          orderRouter: snapshot.states.SmartRouter?.ready === true,
        });
      });

      // Subscribe to exchange updates
      exchangeUnsubRef.current = multiExchangeClient.subscribe((state: MultiExchangeState) => {
        setExchangeState({
          totalEquityUsd: state.totalEquityUsd,
          exchanges: state.exchanges.map(e => ({
            exchange: e.exchange,
            connected: e.connected,
            totalUsdValue: e.totalUsdValue
          }))
        });
      });

      console.log('[Aureon] Connectors initialized; systems remain offline until evidence is published');
      return true;
    } catch (error) {
      console.error('[Aureon] Failed to initialize systems:', error);
      return false;
    }
  }, []);

  // Run quantum computation cycle using UnifiedOrchestrator
  const runQuantumCycle = useCallback(async () => {
    if (!userId) return;

    try {
      // Fetch real market data
      const marketData = await fetchMarketData('BTCUSDT');

      // Run unified orchestrator cycle (handles all systems + bus + consensus)
      const result = await unifiedOrchestrator.runCycle(marketData, 'BTCUSDT');
      setLastDecision(result);

      // Store market data for Prism
      setMarketData(marketData);

      // Update quantum state from orchestration result
      if (result.lambdaState) {
        // Run The Prism transformation
        const prismOutput = thePrism.transform({
          lambda: result.lambdaState.lambda,
          coherence: result.lambdaState.coherence,
          substrate: result.lambdaState.substrate,
          observer: result.lambdaState.observer,
          echo: result.lambdaState.echo,
          volatility: marketData.volatility,
          momentum: marketData.momentum,
          baseFrequency: result.rainbowState?.frequency || 396
        });

        setPrismState({
          output: prismOutput,
          frequency: prismOutput.frequency,
          resonance: prismOutput.resonance,
          isLoveLocked: prismOutput.isLoveLocked
        });

        const newQuantumState: QuantumState = {
          coherence: result.lambdaState.coherence,
          lambda: result.lambdaState.lambda,
          lighthouseSignal: result.lighthouseState?.L || 0,
          dominantNode: result.lambdaState.dominantNode,
          prismLevel: prismOutput.level,
          prismState: prismOutput.state,
          substrate: result.lambdaState.substrate,
          observer: result.lambdaState.observer,
          echo: result.lambdaState.echo
        };
        
        setQuantumState(newQuantumState);

        // Send heartbeat to Temporal Ladder
        temporalLadder.heartbeat(SYSTEMS.MASTER_EQUATION, result.lambdaState.coherence);
        temporalLadder.heartbeat(SYSTEMS.HARMONIC_NEXUS, result.busSnapshot.consensusConfidence);

        // Update routing state from orchestration result
        if (result.routingDecision) {
          setRoutingState({
            recommendedExchange: result.routingDecision.recommendedExchange,
            positionSizeUsd: result.positionSizing?.positionSizeUsd ?? null,
            availableBalance: result.positionSizing?.availableBalance ?? null,
            reasoning: result.routingDecision.reasoning
          });
        }

        // Update database
        await supabase
          .from('aureon_user_sessions')
          .update({
            current_coherence: newQuantumState.coherence,
            current_lambda: newQuantumState.lambda,
            current_lighthouse_signal: newQuantumState.lighthouseSignal,
            dominant_node: newQuantumState.dominantNode,
            prism_level: newQuantumState.prismLevel,
            prism_state: newQuantumState.prismState,
            last_quantum_update_at: marketData.sourceTimestamp,
            measurement_truth_status: 'real_derived',
            measurement_source_id: marketData.sourceId,
            measurement_source_timestamp: marketData.sourceTimestamp,
            measurement_collected_at: new Date().toISOString(),
            measurement_generated_values: false,
          })
          .eq('user_id', userId);
      }

      // A decision is not a trade. Counts, P&L, quantities, and success remain
      // unchanged until an exchange execution receipt is read back.
      if (result.finalDecision.action !== 'HOLD') {
        setLastSignal(`${result.finalDecision.action} BTCUSDT @ $${marketData.price.toFixed(2)} (advisory; not executed)`);
      }
      
    } catch (error) {
      console.error('[Aureon] Quantum cycle error:', error);
    }
  }, [userId, fetchMarketData, tradingState.gasTankBalance]);

  // Start autonomous trading
  const startTrading = useCallback(async () => {
    if (!userId) return;
    
    const initialized = await initializeSystems();
    if (!initialized) {
      toast.error('Failed to initialize quantum systems');
      return;
    }
    
    setTradingState(prev => ({ ...prev, isActive: true }));
    
    // Broadcast trading started
    temporalLadder.broadcast(SYSTEMS.QUANTUM_QUACKERS, 'TRADING_STARTED', { userId });
    
    // Run quantum cycle every 3 seconds
    intervalRef.current = setInterval(runQuantumCycle, 3000);
    
    // Countdown timer
    countdownRef.current = setInterval(() => {
      setNextCheckIn(prev => prev <= 1 ? 3 : prev - 1);
    }, 1000);
    
    // Run immediately
    runQuantumCycle();
    
    toast.success('Autonomous trading activated');
  }, [userId, initializeSystems, runQuantumCycle]);

  // Stop trading
  const stopTrading = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    if (busUnsubRef.current) {
      busUnsubRef.current();
      busUnsubRef.current = null;
    }
    if (exchangeUnsubRef.current) {
      exchangeUnsubRef.current();
      exchangeUnsubRef.current = null;
    }
    
    // Unregister from Temporal Ladder
    temporalLadder.unregisterSystem(SYSTEMS.MASTER_EQUATION);
    temporalLadder.unregisterSystem(SYSTEMS.HARMONIC_NEXUS);
    
    setTradingState(prev => ({ ...prev, isActive: false }));
    setSystemStatus({
      masterEquation: false,
      lighthouse: false,
      rainbowBridge: false,
      elephantMemory: false,
      orderRouter: false
    });
    
    toast.info('Trading stopped');
  }, []);

  // Load provider-backed session data. Missing rows remain no_data.
  useEffect(() => {
    if (!userId) return;

    const loadSession = async () => {
      const { data, error } = await supabase
        .from('aureon_user_sessions')
        .select('*')
        .eq('user_id', userId)
        .single();

      if (error && error.code === 'PGRST116') {
        console.info('[Aureon] No session exists; provider setup is required');
        return;
      }

      if (data) {
        const hasMeasurements = ['live', 'real_derived'].includes(String(data.measurement_truth_status));
        if (hasMeasurements) {
          setQuantumState({
            coherence: data.current_coherence == null ? null : Number(data.current_coherence),
            lambda: data.current_lambda == null ? null : Number(data.current_lambda),
            lighthouseSignal: data.current_lighthouse_signal == null ? null : Number(data.current_lighthouse_signal),
            dominantNode: data.dominant_node ?? null,
            prismLevel: data.prism_level ?? null,
            prismState: data.prism_state ?? null,
            substrate: null,
            observer: null,
            echo: null,
          });
        }
        
        setTradingState({
          isActive: data.is_trading_active === true,
          totalEquity: data.total_equity_usd == null ? null : Number(data.total_equity_usd),
          availableBalance: data.available_balance_usdt == null ? null : Number(data.available_balance_usdt),
          totalTrades: data.total_trades ?? null,
          winningTrades: data.winning_trades ?? null,
          totalPnl: data.total_pnl_usdt == null ? null : Number(data.total_pnl_usdt),
          gasTankBalance: data.gas_tank_balance == null ? null : Number(data.gas_tank_balance),
          recentTrades: Array.isArray(data.recent_trades) ? data.recent_trades as any[] : [],
        });
      }
    };

    loadSession();

    // Subscribe to realtime updates
    const channel = supabase
      .channel(`aureon_session_${userId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'aureon_user_sessions',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          const data = payload.new as any;
          if (!['live', 'real_derived'].includes(String(data.measurement_truth_status))) return;
          setTradingState(prev => ({
            ...prev,
            totalEquity: data.total_equity_usd == null ? prev.totalEquity : Number(data.total_equity_usd),
          }));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      stopTrading();
    };
  }, [userId]);

  return {
    quantumState,
    tradingState,
    systemStatus,
    busState,
    exchangeState,
    prismState,
    marketData,
    routingState,
    lastSignal,
    nextCheckIn,
    lastDecision,
    startTrading,
    stopTrading
  };
}
