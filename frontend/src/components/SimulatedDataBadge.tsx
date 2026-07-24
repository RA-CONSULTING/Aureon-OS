/**
 * SimulatedDataBadge — an honest marker for any surface whose numbers come from
 * a client-side simulation rather than a live backend feed.
 *
 * Some legacy panels animate their metrics with in-browser models (see
 * core/fullEcosystemConnector and friends). Until they are wired to real
 * producing data, they must SAY SO — this badge makes that explicit so a viewer
 * never mistakes a simulated readout for live telemetry.
 */
import { FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function SimulatedDataBadge({ className = "" }: { className?: string }) {
  return (
    <Badge
      variant="outline"
      className={`gap-1 border-warning/40 text-warning ${className}`}
      title="These values come from an in-browser simulation, not a live backend feed."
    >
      <FlaskConical className="h-3 w-3" aria-hidden />
      Simulated
    </Badge>
  );
}

export default SimulatedDataBadge;
