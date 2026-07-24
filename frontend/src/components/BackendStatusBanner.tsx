/**
 * BackendStatusBanner — one honest, app-wide signal of whether the live backend
 * is reachable.
 *
 * Aureon's dashboards are wired to the operator's `/api/...` surface and degrade
 * to empty/last-known state when it's down (they never fabricate). This strip
 * makes that state explicit and consistent everywhere: when the operator gateway
 * is unreachable it tells the user plainly — and how to bring it up — instead of
 * leaving a silently empty dashboard. When the backend is live it renders nothing.
 */
import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";

import { useOperatorPulse } from "@/hooks/useOperatorPulse";

export function BackendStatusBanner() {
  const { offline, loading } = useOperatorPulse();
  const [dismissed, setDismissed] = useState(false);

  // Nothing to say while the first poll is in flight or when the backend is live.
  if (loading || !offline || dismissed) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-3 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive-foreground"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden />
      <div className="min-w-0 flex-1">
        <span className="font-medium text-destructive">Operator backend offline.</span>{" "}
        <span className="text-muted-foreground">
          Dashboards show last-known or empty data — nothing here is fabricated. Start the gateway
          with{" "}
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs text-foreground">
            python -m aureon.operator.operator_server
          </code>
          .
        </span>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss backend status notice"
        className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}

export default BackendStatusBanner;
