/**
 * useHncCoherence — the REAL HNC coherence (Γ) from the operator, live.
 *
 * The operator's /api/pulse exposes the organism's blended unification coherence
 * (`organism.unification.blended.coherence_gamma`) — a genuine backend-computed
 * value, not an in-browser simulation. This hook surfaces it (0..1) for any
 * dashboard that wants to show real coherence instead of a random walk. Returns
 * `gamma: null` when the value is absent or the backend is offline, so callers
 * degrade honestly.
 */
import { useOperatorPulse } from "@/hooks/useOperatorPulse";
import type { OperatorPulse } from "@/services/apiClient";

/** Dig out organism.unification.blended.coherence_gamma defensively. */
function readCoherenceGamma(pulse: OperatorPulse | null): number | null {
  const organism = pulse?.organism as Record<string, unknown> | undefined;
  const unification = organism?.unification as Record<string, unknown> | undefined;
  const blended = unification?.blended as Record<string, unknown> | undefined;
  const g = blended?.coherence_gamma;
  return typeof g === "number" && Number.isFinite(g) ? g : null;
}

export interface HncCoherence {
  /** Coherence Γ in [0,1], or null when unavailable/offline. */
  gamma: number | null;
  /** true when the operator backend is unreachable. */
  offline: boolean;
  loading: boolean;
}

export function useHncCoherence(): HncCoherence {
  const { pulse, offline, loading } = useOperatorPulse();
  return { gamma: readCoherenceGamma(pulse), offline, loading };
}
