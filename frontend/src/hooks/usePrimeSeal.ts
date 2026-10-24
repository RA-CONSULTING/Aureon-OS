/**
 * usePrimeSeal Hook
 * Provides real-time access to 10-9-1 Prime Seal state
 */

import { useState, useEffect } from 'react';
import { primeSealComputer, PrimeSealState, PrimeSealPacket } from '@/core/primeSealComputer';
import { unifiedBus } from '@/core/unifiedBus';
import { supabase } from '@/integrations/supabase/client';

export interface PrimeSealHookState {
  packet: PrimeSealPacket | null;
  isLocked: boolean;
  primeCoherence: number;
  latticePhase: number | null;
  unityCoherence: number;
  flowCoherence: number;
  anchorCoherence: number;
  lockReason: string;
  systemsContributing: string[];
  lastUpdate: number;
  isLoading: boolean;
  error: string | null;
}

export function usePrimeSeal(): PrimeSealHookState {
  const [state, setState] = useState<PrimeSealHookState>({
    packet: null,
    isLocked: false,
    primeCoherence: 0,
    latticePhase: null,
    unityCoherence: 0,
    flowCoherence: 0,
    anchorCoherence: 0,
    lockReason: 'Awaiting initialization...',
    systemsContributing: [],
    lastUpdate: 0,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    // Subscribe to Prime Seal computer updates
    const unsubscribeSeal = primeSealComputer.subscribe((sealState: PrimeSealState) => {
      setState(prev => ({
        ...prev,
        packet: sealState.packet,
        isLocked: sealState.isLocked,
        primeCoherence: sealState.packet.prime_coherence,
        latticePhase: sealState.packet.lattice_phase,
        unityCoherence: sealState.unityCoherence,
        flowCoherence: sealState.flowCoherence,
        anchorCoherence: sealState.anchorCoherence,
        lockReason: sealState.lockReason,
        systemsContributing: sealState.packet.systems_contributing,
        lastUpdate: Date.now(),
        isLoading: false,
      }));
    });

    // Subscribe to UnifiedBus and compute seal on each update
    const unsubscribeBus = unifiedBus.subscribe((snapshot) => {
      primeSealComputer.compute(snapshot);
    });

    // Compute initial state
    const snapshot = unifiedBus.snapshot();
    if (snapshot.totalSystems > 0) {
      primeSealComputer.compute(snapshot);
    }

    // Subscribe to realtime updates from database
    const channel = supabase
      .channel('prime_seal_packets_realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'prime_seal_packets',
        },
        (payload) => {
          const newPacket = payload.new as PrimeSealPacket;
          setState(prev => ({
            ...prev,
            packet: newPacket,
            isLocked: newPacket.seal_lock,
            primeCoherence: newPacket.prime_coherence,
            latticePhase: newPacket.lattice_phase,
            systemsContributing: newPacket.systems_contributing || [],
            lastUpdate: Date.now(),
          }));
        }
      )
      .subscribe();

    return () => {
      unsubscribeSeal();
      unsubscribeBus();
      channel.unsubscribe();
    };
  }, []);

  return state;
}
