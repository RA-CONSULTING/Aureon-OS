/**
 * useIdentity — which plane is this session on?
 *
 * The backend enforces a hard boundary: an operator sees the whole instance, a signed-in end user
 * sees only their own account plane (their keys, their reasoning, their billing) plus the read-only
 * showcase views. See `docs/architecture/MULTI_TENANT_AUTH.md`.
 *
 * Without this hook the console renders the operator's navigation to everyone and a signed-in user
 * discovers the boundary by collecting 403s. `GET /api/me` is the one identity call a tenant may
 * make — it reports the caller's own identity and deliberately nothing about the instance.
 *
 * Degrades quietly: if the endpoint is unreachable (older backend, gateway down) the hook reports
 * `unknown` and callers should fall back to showing everything, exactly as before this existed.
 */

import { useEffect, useState } from "react";
import { ApiError, api } from "@/services/apiClient";

export type IdentityKind = "open" | "admin" | "tenant" | "unknown";

export interface Identity {
  kind: IdentityKind;
  isAdmin: boolean;
  /** A short hash of the account id — never the raw JWT subject. */
  tenantLabel: string | null;
  plane: "instance" | "account" | "unknown";
  tenancyEnabled: boolean;
  authRequired: boolean;
  /** Route patterns this caller may reach; null for an operator (everything). */
  allowedRoutes: string[] | null;
}

interface MeResponse {
  kind?: string;
  is_admin?: boolean;
  tenant_label?: string | null;
  plane?: string;
  tenancy_enabled?: boolean;
  auth_required?: boolean;
  allowed_routes?: string[] | null;
}

const UNKNOWN: Identity = {
  kind: "unknown",
  // Permissive when we genuinely do not know: the backend is the enforcer, so a wrong guess here
  // hides features from an operator rather than exposing anything to a tenant.
  isAdmin: true,
  tenantLabel: null,
  plane: "unknown",
  tenancyEnabled: false,
  authRequired: false,
  allowedRoutes: null,
};

export function useIdentity(): { identity: Identity; loading: boolean; offline: boolean } {
  const [identity, setIdentity] = useState<Identity>(UNKNOWN);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api.get<MeResponse>("/api/me");
        if (cancelled) return;
        const kind = (["open", "admin", "tenant"].includes(String(me.kind))
          ? (me.kind as IdentityKind)
          : "unknown");
        setIdentity({
          kind,
          isAdmin: me.is_admin !== false,
          tenantLabel: me.tenant_label ?? null,
          plane: me.plane === "account" ? "account" : me.plane === "instance" ? "instance" : "unknown",
          tenancyEnabled: Boolean(me.tenancy_enabled),
          authRequired: Boolean(me.auth_required),
          allowedRoutes: Array.isArray(me.allowed_routes) ? me.allowed_routes : null,
        });
      } catch (err) {
        if (cancelled) return;
        setOffline(err instanceof ApiError ? err.offline : true);
        setIdentity(UNKNOWN);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { identity, loading, offline };
}
