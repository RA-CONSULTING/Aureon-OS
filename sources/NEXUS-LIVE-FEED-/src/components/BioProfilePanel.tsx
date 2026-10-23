import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BioProfileAnalytics, BioSignalTone } from "@/hooks/useResampledNexusData";
import { cn } from "@/lib/utils";

interface BioProfilePanelProps {
  profile: BioProfileAnalytics;
}

const toneBadgeStyles: Record<BioSignalTone, string> = {
  stable: "border-emerald-400/50 bg-emerald-500/15 text-emerald-100",
  watch: "border-amber-300/50 bg-amber-500/15 text-amber-100",
  alert: "border-rose-400/50 bg-rose-500/20 text-rose-100",
};

const toneShadow: Record<BioSignalTone, string> = {
  stable: "shadow-[0_0_25px_rgba(16,185,129,0.45)]",
  watch: "shadow-[0_0_25px_rgba(251,191,36,0.35)]",
  alert: "shadow-[0_0_25px_rgba(244,63,94,0.35)]",
};

const trendGlyph = (value: number): string => {
  if (value > 0.05) return "▲";
  if (value < -0.05) return "▼";
  return "―";
};

const BioProfilePanel = ({ profile }: BioProfilePanelProps) => {
  return (
    <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_40px_rgba(14,165,233,0.35)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.18),_transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.18),_transparent_60%)] opacity-80" />
      <CardHeader className="relative z-10 pb-4">
        <CardTitle className="text-xl font-semibold tracking-[0.3em] text-white">Personal Quantum Bio-Profile</CardTitle>
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.35em] text-slate-300/80">
          <span className="rounded-full border border-cyan-400/40 bg-cyan-500/20 px-3 py-1 text-cyan-100 shadow-[0_0_18px_rgba(56,189,248,0.45)]">
            {profile.displayName}
          </span>
          <span className="rounded-full border border-slate-600/40 bg-slate-700/30 px-3 py-1 text-slate-200/85">
            {profile.timelineTag}
          </span>
        </div>
        <p className="mt-4 text-sm leading-relaxed text-slate-300/85">{profile.summary}</p>
      </CardHeader>
      <CardContent className="relative z-10 grid gap-6 lg:grid-cols-[1.2fr_1fr] xl:grid-cols-[1.4fr_1.2fr_1fr]">
        <div className="flex flex-col gap-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-[1px]">
            <div className="rounded-[calc(1.5rem-2px)] bg-slate-950/80 p-6">
              <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-200">Vital Metrics</h3>
              <ul className="mt-4 space-y-4">
                {profile.metrics.map((metric) => (
                  <li
                    key={metric.id}
                    className="group relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 p-4"
                  >
                    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.2),_transparent_60%)] opacity-0 transition duration-500 group-hover:opacity-100" />
                    <div className="relative z-10 flex items-center justify-between">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.4em] text-slate-400">{metric.label}</p>
                        <p className="mt-2 text-2xl font-semibold text-white">
                          {metric.value}
                          <span className="ml-1 text-sm text-slate-300/80">{metric.unit}</span>
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className={cn(
                          "rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]",
                          toneBadgeStyles[metric.tone],
                          toneShadow[metric.tone]
                        )}
                      >
                        {metric.tone === "stable" ? "Stable" : metric.tone === "watch" ? "Watch" : "Alert"}
                      </Badge>
                    </div>
                    <div className="relative z-10 mt-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.35em] text-slate-400">
                      <span>Δ {metric.change > 0 ? "+" : ""}{metric.change.toFixed(2)}</span>
                      <span className="text-slate-500">|</span>
                      <span>
                        Target {metric.targetRange[0]}–{metric.targetRange[1]} {metric.unit}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-[1px]">
            <div className="rounded-[calc(1.5rem-2px)] bg-slate-950/80 p-6">
              <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-200">Stream Alignment</h3>
              <ul className="mt-4 space-y-4">
                {profile.streams.map((stream) => {
                  const trend = trendGlyph(stream.trend);
                  return (
                    <li
                      key={stream.id}
                      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 p-4"
                    >
                      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.18),_transparent_65%)] opacity-0 transition duration-500 group-hover:opacity-100" />
                      <div className="relative z-10 flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.4em] text-slate-400">{stream.label}</p>
                          <p className="mt-2 text-lg font-semibold text-white">
                            {stream.reading}
                            <span className="ml-2 text-xs font-medium text-slate-300/80">Δ {stream.trend > 0 ? "+" : ""}{stream.trend.toFixed(2)} {stream.unit}</span>
                          </p>
                          <p className="mt-2 text-[11px] text-slate-400/80">{stream.hint}</p>
                        </div>
                        <Badge
                          variant="outline"
                          className={cn(
                            "flex items-center gap-1 rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]",
                            toneBadgeStyles[stream.status],
                            toneShadow[stream.status]
                          )}
                        >
                          <span>{trend}</span>
                          <span>{stream.status === "stable" ? "Balanced" : stream.status === "watch" ? "Watch" : "Critical"}</span>
                        </Badge>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default BioProfilePanel;
