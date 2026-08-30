/**
 * useSystemsIntegration Hook
 * React hook for accessing the integrated quantum systems
 * Prime Sentinel: GARY LECKEY 02111991
 */

import { useState, useEffect, useCallback } from 'react';
import { systemsIntegration, type IntegratedSystemState } from '../core/systemsIntegration';
import { temporalLadder, type TemporalLadderState } from '../core/temporalLadder';

export interface UseSystemsIntegrationReturn {
  state: IntegratedSystemState | null;
  ladderState: TemporalLadderState | null;
  isInitialized: boolean;
  refresh: () => void;
  refreshAkashic: (iterations?: number) => void;
  getAkashicBoost: (coherence: number) => number;
}

export function useSystemsIntegration(): UseSystemsIntegrationReturn {
  const [state, setState] = useState<IntegratedSystemState | null>(null);
  const [ladderState, setLadderState] = useState<TemporalLadderState | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    // Initialize the systems integration
    systemsIntegration.initialize();
    setIsInitialized(true);

    // Subscribe to system updates
    const unsubscribeSystems = systemsIntegration.subscribe((newState) => {
      setState(newState);
    });

    // Subscribe to temporal ladder updates
    const unsubscribeLadder = temporalLadder.subscribe((newLadderState) => {
      setLadderState(newLadderState);
    });

    // Get initial state
    setState(systemsIntegration.getIntegratedState());
    setLadderState(temporalLadder.getState());

    return () => {
      unsubscribeSystems();
      unsubscribeLadder();
    };
  }, []);

  const refresh = useCallback(() => {
    setState(systemsIntegration.getIntegratedState());
    setLadderState(temporalLadder.getState());
  }, []);

  const refreshAkashic = useCallback((iterations: number = 7) => {
    systemsIntegration.refreshAkashicAttunement(iterations);
    setState(systemsIntegration.getIntegratedState());
  }, []);

  const getAkashicBoost = useCallback((coherence: number): number => {
    return systemsIntegration.calculateAkashicBoost(coherence);
  }, []);

  return {
    state,
    ladderState,
    isInitialized,
    refresh,
    refreshAkashic,
    getAkashicBoost
  };
}

/**
 * useQueenHiveBrowser Hook
 * Compatibility hook for provider-observed Queen Hive snapshots.
 */
import { getGlobalQueenHive, type QueenHiveState } from '../core/queenHiveBrowser';

export interface UseQueenHiveBrowserReturn {
  state: QueenHiveState | null;
  step: () => void;
  simulate: (steps: number) => void;
  reset: () => void;
  totalEquity: number | null;
  hiveCount: number | null;
  generation: number | null;
}

export function useQueenHiveBrowser(): UseQueenHiveBrowserReturn {
  const [state, setState] = useState<QueenHiveState | null>(null);
  const queenHive = getGlobalQueenHive();

  useEffect(() => {
    // Get initial state
    setState(queenHive.getState());

    // Subscribe to updates
    const unsubscribe = queenHive.subscribe((newState) => {
      setState(newState);
    });

    return unsubscribe;
  }, []);

  const step = useCallback(() => {
    queenHive.step();
  }, []);

  const simulate = useCallback((steps: number) => {
    queenHive.simulate(steps);
  }, []);

  const reset = useCallback(() => {
    queenHive.reset();
    setState(queenHive.getState());
  }, []);

  return {
    state,
    step,
    simulate,
    reset,
    totalEquity: state?.totalEquity ?? null,
    hiveCount: state?.totalHives ?? null,
    generation: state?.generation ?? null
  };
}

/**
 * useTemporalLadder Hook
 * Direct access to Temporal Ladder state
 */
export function useTemporalLadder(): {
  state: TemporalLadderState | null;
  systemStatuses: Array<{ name: string; active: boolean; health: number }>;
  hiveMindCoherence: number;
} {
  const [state, setState] = useState<TemporalLadderState | null>(null);

  useEffect(() => {
    setState(temporalLadder.getState());
    
    const unsubscribe = temporalLadder.subscribe((newState) => {
      setState(newState);
    });

    return unsubscribe;
  }, []);

  const systemStatuses = state 
    ? Array.from(state.systems.entries()).map(([name, status]) => ({
        name,
        active: status.active,
        health: status.health
      }))
    : [];

  return {
    state,
    systemStatuses,
    hiveMindCoherence: state?.hiveMindCoherence ?? 0
  };
}
