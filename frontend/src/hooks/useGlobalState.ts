/**
 * React hook to subscribe to GlobalSystemsManager state
 * 
 * This hook provides reactive access to the global state without
 * causing re-initialization of systems when components mount/unmount.
 */

import { useState, useEffect, useCallback } from 'react';
import { globalSystemsManager, type GlobalState } from '@/core/globalSystemsManager';

/**
 * Subscribe to the entire global state
 */
export function useGlobalState(): GlobalState {
  const [state, setState] = useState<GlobalState>(globalSystemsManager.getState());
  
  useEffect(() => {
    const unsubscribe = globalSystemsManager.subscribe((newState) => {
      setState(newState);
    });
    
    return unsubscribe;
  }, []);
  
  return state;
}

/**
 * Subscribe to a specific slice of global state
 */
export function useGlobalStateSelector<T>(selector: (state: GlobalState) => T): T {
  const [selected, setSelected] = useState<T>(() => selector(globalSystemsManager.getState()));
  
  useEffect(() => {
    const unsubscribe = globalSystemsManager.subscribe((newState) => {
      const newSelected = selector(newState);
      setSelected(newSelected);
    });
    
    return unsubscribe;
  }, [selector]);
  
  return selected;
}

/**
 * Get trading controls from global state
 */
export function useGlobalTradingControls() {
  const startTrading = useCallback(() => {
    globalSystemsManager.startTrading();
  }, []);
  
  const stopTrading = useCallback(() => {
    globalSystemsManager.stopTrading();
  }, []);
  
  return { startTrading, stopTrading };
}

/**
 * Get quantum state from global state
 */
export function useQuantumState() {
  return useGlobalStateSelector((state) => ({
    coherence: state.coherence,
    lambda: state.lambda,
    lighthouseSignal: state.lighthouseSignal,
    dominantNode: state.dominantNode,
    prismLevel: state.prismLevel,
    prismState: state.prismState,
    substrate: state.substrate,
    observer: state.observer,
    echo: state.echo,
    prismOutput: state.prismOutput,
    // 🦆🪐 Platypus Planetary Coherence
    planetaryCoherence: state.planetaryCoherence,
    planetaryCascade: state.planetaryCascade,
    lighthouseActive: state.lighthouseActive,
    topAlignedPlanets: state.topAlignedPlanets,
  }));
}

/**
 * 🦆🪐 Get Platypus planetary coherence state
 */
export function usePlatypusState() {
  return useGlobalStateSelector((state) => ({
    platypusState: state.platypusState,
    planetaryCoherence: state.planetaryCoherence,
    planetaryCascade: state.planetaryCascade,
    lighthouseActive: state.lighthouseActive,
    topAlignedPlanets: state.topAlignedPlanets,
  }));
}

/**
 * Get trading state from global state
 */
export function useTradingState() {
  return useGlobalStateSelector((state) => ({
    isActive: state.isActive,
    totalEquity: state.totalEquity,
    availableBalance: state.availableBalance,
    totalTrades: state.totalTrades,
    winningTrades: state.winningTrades,
    totalPnl: state.totalPnl,
    totalPnlNote: state.totalPnlNote,
    availableBalanceNote: state.availableBalanceNote,
    gasTankBalance: state.gasTankBalance,
    recentTrades: state.recentTrades,
    lastSignal: state.lastSignal,
    lastDecision: state.lastDecision,
    nextCheckIn: state.nextCheckIn,
  }));
}

/**
 * Get system status from global state
 */
export function useSystemStatus() {
  return useGlobalStateSelector((state) => ({
    systemStatus: state.systemStatus,
    ecosystemHealth: state.ecosystemHealth,
    isInitialized: state.isInitialized,
    isRunning: state.isRunning,
    busSnapshot: state.busSnapshot,
    consensusSignal: state.consensusSignal,
    consensusConfidence: state.consensusConfidence,
  }));
}

/**
 * Get auth state from global state
 */
export function useGlobalAuth() {
  return useGlobalStateSelector((state) => ({
    userId: state.userId,
    userEmail: state.userEmail,
    isAuthenticated: state.isAuthenticated,
  }));
}

/**
 * Get market data from global state
 */
export function useMarketData() {
  return useGlobalStateSelector((state) => state.marketData);
}

/**
 * Get exchange state from global state
 */
export function useExchangeState() {
  return useGlobalStateSelector((state) => state.exchangeState);
}
