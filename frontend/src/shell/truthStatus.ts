/**
 * The provenance legend — single source of truth for how a value's origin is
 * shown across every shell surface.
 *
 * These hues are deliberate and load-bearing for the "no fabricated values"
 * contract: a viewer can tell live data from derived, cached, absent, or a test
 * fixture at a glance. They are intentionally kept as a distinct five-way palette
 * (not folded into the success/warning/destructive status triad) so the four
 * "real-ish" states stay separable. Every page imports from here — the map lived
 * copy-pasted in nine pages before this was extracted.
 */

export type TruthStatus = "live" | "real_derived" | "cached_real" | "no_data" | "test_fixture";

/** Badge classes per provenance state (tinted surface + readable text + hairline border). */
export const TRUTH_STATUS_STYLE: Record<TruthStatus, string> = {
  live: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
  real_derived: "bg-sky-500/15 text-sky-600 border-sky-500/30",
  cached_real: "bg-amber-500/15 text-amber-600 border-amber-500/30",
  no_data: "bg-muted text-muted-foreground border-border",
  test_fixture: "bg-purple-500/15 text-purple-600 border-purple-500/30",
};

/** Safety-posture legend for gated capabilities (read-only → reversible → records-gated). */
export const SAFETY_POSTURE_STYLE: Record<string, string> = {
  read_only_assess: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
  records_only_gated: "bg-amber-500/15 text-amber-600 border-amber-500/30",
  reversible_ascent_gated: "bg-sky-500/15 text-sky-600 border-sky-500/30",
};

/** Provenance badge classes, defaulting to the honest no_data styling for unknown states. */
export const truthStatusStyle = (status: TruthStatus | string): string =>
  TRUTH_STATUS_STYLE[status as TruthStatus] ?? TRUTH_STATUS_STYLE.no_data;

/** Safety-posture badge classes, defaulting to neutral for unknown postures. */
export const safetyPostureStyle = (posture: string): string =>
  SAFETY_POSTURE_STYLE[posture] ?? "bg-muted text-muted-foreground border-border";
