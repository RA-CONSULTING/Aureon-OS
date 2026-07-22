/**
 * RiskDisclaimer — a compact, always-visible financial-promotion disclaimer.
 *
 * Rendered on trading surfaces (and available elsewhere) so no performance-style data
 * is ever shown without the capital-at-risk / not-financial-advice framing. Links to
 * the full risk disclosure at /legal#risk.
 */

import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";

export function RiskDisclaimer({ className = "" }: { className?: string }) {
  return (
    <div
      role="note"
      className={`flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-[11px] leading-relaxed text-warning ${className}`}
    >
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        <strong>Not financial advice.</strong> Capital at risk — you may lose some or all of your
        funds. Past performance is not indicative of future results.{" "}
        <Link to="/legal#risk" className="underline hover:text-foreground">
          Full risk disclosure
        </Link>
        .
      </span>
    </div>
  );
}
