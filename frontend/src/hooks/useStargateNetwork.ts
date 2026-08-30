import { useState, useEffect, useCallback } from 'react';
import {
  stargateLayer,
  StargateActivation,
  NetworkMetrics,
  StargateNodeObservation,
} from '@/core/stargateLattice';
import { usePrimelinesProtocol } from './usePrimelinesProtocol';

const NO_STARGATE_OBSERVATIONS: StargateNodeObservation[] = [];

export function useStargateNetwork(
  observations: StargateNodeObservation[] = NO_STARGATE_OBSERVATIONS,
) {
  const [activations, setActivations] = useState<StargateActivation[]>([]);
  const [metrics, setMetrics] = useState<NetworkMetrics | null>(null);
  const [isActive, setIsActive] = useState(false);
  const { invokeProtocol } = usePrimelinesProtocol();

  const pingNetwork = useCallback(async () => {
    try {
      const newActivations = stargateLayer.activateAllNodes(observations);
      const newMetrics = stargateLayer.calculateNetworkMetrics(newActivations);
      const activeNodes = newActivations.filter(a => a.status === 'ACTIVE').length;

      setActivations(newActivations);
      setMetrics(newMetrics);
      setIsActive(activeNodes > 0);

      // Missing telemetry remains no_data and is never published as a network state.
      if (
        activeNodes === 0 ||
        newMetrics.avgCoherence === null ||
        newMetrics.avgEnergyFlow === null ||
        newMetrics.avgLatency === null ||
        newMetrics.networkStrength === null
      ) {
        return;
      }

      const frequencyLocks = newActivations
        .filter(a => a.status === 'ACTIVE' && a.frequencyLock !== null)
        .map(a => a.frequencyLock as number);
      const avgFrequency = frequencyLocks.length > 0
        ? frequencyLocks.reduce((sum, value) => sum + value, 0) / frequencyLocks.length
        : null;
      const phaseLocks = activeNodes * (activeNodes - 1) / 2;
      const resonanceQuality = newMetrics.networkStrength * newMetrics.avgCoherence;

      await invokeProtocol({
        operation: 'SYNC_HARMONIC_NEXUS',
        payload: {
          stargateNetwork: {
            activations: newActivations,
            metrics: {
              ...newMetrics,
              avgFrequency,
              phaseLocks,
              resonanceQuality,
            },
            gridEnergy: stargateLayer.calculateGridEnergy(),
          },
        },
        requireValidation: false,
      });
    } catch (error) {
      setIsActive(false);
      console.error('Stargate network observation error:', error);
    }
  }, [invokeProtocol, observations]);

  useEffect(() => {
    void pingNetwork();

    // Revalidate freshness without inventing values between observations.
    const interval = setInterval(() => void pingNetwork(), 30_000);
    return () => {
      clearInterval(interval);
      setIsActive(false);
    };
  }, [pingNetwork]);

  return {
    activations,
    metrics,
    isActive,
    gridEnergy: stargateLayer.calculateGridEnergy(),
  };
}
