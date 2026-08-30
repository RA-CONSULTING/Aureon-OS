/**
 * LiveVitals — a compact, always-visible strip of REAL operator numbers.
 *
 * Reads /api/pulse (via useOperatorPulse) and shows a few genuine vitals in the
 * shell top bar: configured providers, switchboard enabled/total, and the
 * organism's connectome coverage. Renders nothing when the backend is offline or
 * the fields are absent — so it only ever shows live, backend-sourced values,
 * never a placeholder.
 */
import { useOperatorPulse } from "@/hooks/useOperatorPulse";

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums text-foreground">{value}</span>
    </span>
  );
}

export function LiveVitals() {
  const { pulse, offline, loading } = useOperatorPulse();
  if (loading || offline || !pulse) return null;

  const providers = Array.isArray(pulse.providers) ? pulse.providers.length : null;
  const sb = pulse.switchboard;
  const enabled = typeof sb?.enabled === "number" ? sb.enabled : null;
  const total = typeof sb?.total === "number" ? sb.total : null;
  const coverage = pulse.organism?.connectome?.coverage_pct;

  const items: Array<{ label: string; value: string }> = [];
  if (providers != null) items.push({ label: "providers", value: String(providers) });
  if (enabled != null && total != null) items.push({ label: "switchboard", value: `${enabled}/${total}` });
  if (typeof coverage === "number") items.push({ label: "coverage", value: `${coverage.toFixed(1)}%` });

  if (items.length === 0) return null;

  return (
    <div
      className="hidden items-center gap-3 text-xs lg:flex"
      title="Live operator vitals (GET /api/pulse)"
      aria-label="live operator vitals"
    >
      {items.map((it, i) => (
        <span key={it.label} className="flex items-center gap-3">
          {i > 0 && <span className="text-border">·</span>}
          <Pill label={it.label} value={it.value} />
        </span>
      ))}
    </div>
  );
}

export default LiveVitals;
