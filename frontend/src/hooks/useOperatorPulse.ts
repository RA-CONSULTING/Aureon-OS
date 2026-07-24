/**
 * useOperatorPulse — polls the operator's one-call vitals (`GET /api/pulse`) and
 * reports an HONEST connection state the whole UI can trust.
 *
 * Returns `offline: true` the moment the gateway is unreachable (transport
 * failure / timeout), distinct from a reachable-but-degraded backend. Dashboards
 * use this to show real numbers when live and a clear "backend offline" notice
 * otherwise — never fabricated data.
 */
import { useEffect, useRef, useState } from "react";

import { ApiError, fetchPulse, type OperatorPulse } from "@/services/apiClient";

export interface PulseState {
  pulse: OperatorPulse | null;
  /** true when the operator backend is unreachable (gateway down / timeout). */
  offline: boolean;
  /** true until the first poll resolves. */
  loading: boolean;
  /** last error message, if any (offline or HTTP). */
  error: string | null;
  /** epoch ms of the last successful read, or null if never. */
  lastOkAt: number | null;
}

const DEFAULT_INTERVAL_MS = 15_000;

export function useOperatorPulse(intervalMs: number = DEFAULT_INTERVAL_MS): PulseState {
  const [state, setState] = useState<PulseState>({
    pulse: null,
    offline: false,
    loading: true,
    error: null,
    lastOkAt: null,
  });
  const lastOk = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const pulse = await fetchPulse();
        if (cancelled) return;
        lastOk.current = Date.now();
        setState({ pulse, offline: false, loading: false, error: null, lastOkAt: lastOk.current });
      } catch (err) {
        if (cancelled) return;
        const offline = err instanceof ApiError ? err.offline : true;
        const message = err instanceof Error ? err.message : "unknown error";
        setState((prev) => ({
          // keep the last-known pulse visible but flag the state honestly
          pulse: prev.pulse,
          offline,
          loading: false,
          error: message,
          lastOkAt: lastOk.current,
        }));
      }
    };
    poll();
    const t = window.setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [intervalMs]);

  return state;
}
