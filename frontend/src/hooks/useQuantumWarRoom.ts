import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { temporalLadder, SYSTEMS } from '@/core/temporalLadder';
import { unifiedBus } from '@/core/unifiedBus';
import { useGlobalState, useGlobalTradingControls } from '@/hooks/useGlobalState';

export interface QuantumState {
  coherence: number | null;
  lambda: number | null;
  dominantNode: string | null;
  lighthouseSignal: number | null;
  prismLevel: number | null;
  prismState: string | null;
  isLHE: boolean | null;
  entanglement: number | null;
  superposition: number | null;
  waveFunction: number[] | null;
  dominantFrequency: number | null;
}

export type AssaultStatus = 'idle' | 'active' | 'emergency_stopped';

export interface WarRoomState {
  status: AssaultStatus;
  quantumState: QuantumState;
  tradesExecuted: number | null;
  netPnL: number | null;
  currentBalance: number | null;
  hiveMindCoherence: number | null;
}

const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

function createNoDataQuantumState(): QuantumState {
  return {
    coherence: null,
    lambda: null,
    dominantNode: null,
    lighthouseSignal: null,
    prismLevel: null,
    prismState: null,
    isLHE: null,
    entanglement: null,
    superposition: null,
    waveFunction: null,
    dominantFrequency: null,
  };
}

export function useQuantumWarRoom() {
  const globalState = useGlobalState();
  const { startTrading, stopTrading } = useGlobalTradingControls();
  const { toast } = useToast();

  const [state, setState] = useState<WarRoomState>({
    status: globalState.isActive ? 'active' : 'idle',
    quantumState: createNoDataQuantumState(),
    tradesExecuted: globalState.totalTrades,
    netPnL: globalState.totalPnl,
    currentBalance: globalState.totalEquity,
    hiveMindCoherence: null,
  });

  useEffect(() => {
    temporalLadder.registerSystem(SYSTEMS.QUANTUM_QUACKERS);
    return () => temporalLadder.unregisterSystem(SYSTEMS.QUANTUM_QUACKERS);
  }, []);

  useEffect(() => {
    setState((previous) => ({
      ...previous,
      status: globalState.isActive || globalState.isRunning ? 'active' : 'idle',
      tradesExecuted: finite(globalState.totalTrades) ? globalState.totalTrades : null,
      netPnL: finite(globalState.totalPnl) ? globalState.totalPnl : null,
      currentBalance: finite(globalState.totalEquity) ? globalState.totalEquity : null,
      quantumState: {
        ...previous.quantumState,
        coherence: finite(globalState.coherence) ? globalState.coherence : null,
        lambda: finite(globalState.lambda) ? globalState.lambda : null,
        dominantNode: globalState.dominantNode ?? null,
        lighthouseSignal: finite(globalState.lighthouseSignal) ? globalState.lighthouseSignal : null,
        prismLevel: finite(globalState.prismLevel) ? globalState.prismLevel : null,
        prismState: globalState.prismState ?? null,
        isLHE: finite(globalState.coherence) ? globalState.coherence > 0.945 : null,
        dominantFrequency: finite(globalState.prismOutput?.frequency) ? globalState.prismOutput.frequency : null,
      },
    }));
  }, [globalState]);

  useEffect(() => unifiedBus.subscribe((snapshot) => {
    const confidence = Object.keys(snapshot.states).length > 0 && finite(snapshot.consensusConfidence)
      ? snapshot.consensusConfidence
      : null;
    setState((previous) => ({
      ...previous,
      hiveMindCoherence: confidence,
      quantumState: {
        ...previous.quantumState,
        entanglement: confidence,
        superposition: null,
      },
    }));
  }), []);

  useEffect(() => {
    if (state.status !== 'active' || !finite(state.quantumState.coherence)) return;
    const interval = setInterval(() => {
      if (finite(state.quantumState.coherence)) {
        temporalLadder.heartbeat(SYSTEMS.QUANTUM_QUACKERS, state.quantumState.coherence);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [state.status, state.quantumState.coherence]);

  const launchAssault = useCallback(async () => {
    if (state.status === 'active') return;
    try {
      await startTrading();
      setState((previous) => ({ ...previous, status: 'active' }));
      temporalLadder.broadcast(SYSTEMS.QUANTUM_QUACKERS, 'ANALYSIS_STARTED', {
        observed_at: new Date().toISOString(),
      });
      toast({
        title: 'Live analysis started',
        description: 'Aureon is consuming provider-backed observations. Live orders still require explicit confirmation.',
      });
    } catch (error: any) {
      toast({ title: 'Launch failed', description: error.message, variant: 'destructive' });
    }
  }, [state.status, toast, startTrading]);

  const emergencyStop = useCallback(async () => {
    try {
      const { error } = await supabase.functions.invoke('emergency-stop');
      if (error) throw error;
      stopTrading();
      setState((previous) => ({ ...previous, status: 'emergency_stopped' }));
      temporalLadder.broadcast(SYSTEMS.QUANTUM_QUACKERS, 'EMERGENCY_STOP', {
        reason: 'manual_trigger',
        observed_at: new Date().toISOString(),
      });
      toast({ title: 'Emergency stop', description: 'All trading halted.', variant: 'destructive' });
    } catch (error: any) {
      toast({ title: 'Emergency stop failed', description: error.message, variant: 'destructive' });
    }
  }, [toast, stopTrading]);

  return { state, launchAssault, emergencyStop };
}
