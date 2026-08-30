/**
 * useSetupStatus — the one honest read of "is this account ready to use?".
 *
 * Fetches the live provider surface (`/api/providers`) and reduces it to the few
 * booleans the onboarding flow needs: is the backend reachable, does the current
 * account have a model key configured, and is a model actually live. Shared by the
 * Get Started page, the Overview first-run nudge, and the Operator Chat pre-flight
 * so every surface tells the user the same thing. Honest by construction: on a
 * transport failure it reports `offline` rather than guessing.
 */

import { useEffect, useState } from "react";
import { api, ApiError } from "@/services/apiClient";

export interface SetupStatus {
  /** The request is still in flight. */
  loading: boolean;
  /** The operator gateway is unreachable (transport failure), not merely keyless. */
  offline: boolean;
  /** At least one provider has a key stored for the current account. */
  hasProvider: boolean;
  /** At least one provider is live (driving cognition on this instance). */
  liveProvider: boolean;
  /** How many providers have a key configured. */
  providerCount: number;
}

interface ProviderView {
  id: string;
  has_key?: boolean;
  live?: boolean;
}

const INITIAL: SetupStatus = {
  loading: true,
  offline: false,
  hasProvider: false,
  liveProvider: false,
  providerCount: 0,
};

/**
 * @param refreshKey change this value to re-fetch (e.g. after saving a key).
 */
export function useSetupStatus(refreshKey?: number): SetupStatus {
  const [status, setStatus] = useState<SetupStatus>(INITIAL);

  useEffect(() => {
    let cancelled = false;
    setStatus((s) => ({ ...s, loading: true }));
    api
      .get<{ providers?: ProviderView[] }>("/api/providers")
      .then((data) => {
        if (cancelled) return;
        const list = data.providers ?? [];
        const configured = list.filter((p) => p.has_key);
        setStatus({
          loading: false,
          offline: false,
          hasProvider: configured.length > 0,
          liveProvider: list.some((p) => p.live),
          providerCount: configured.length,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus({
          loading: false,
          offline: err instanceof ApiError && err.offline,
          hasProvider: false,
          liveProvider: false,
          providerCount: 0,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return status;
}
