import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EnrichedLiveDataSource } from "@/lib/liveDataSources";
import { cn } from "@/lib/utils";

interface DataSourceRegistryProps {
  sources: EnrichedLiveDataSource[];
  version?: string;
}

const typeBadgeStyles: Record<string, string> = {
  zip: "border-cyan-400/60 bg-cyan-500/20 text-cyan-50 shadow-[0_0_20px_rgba(34,211,238,0.35)]",
  html: "border-amber-300/60 bg-amber-400/20 text-amber-50 shadow-[0_0_20px_rgba(245,158,11,0.35)]",
  csv: "border-emerald-300/60 bg-emerald-500/20 text-emerald-100 shadow-[0_0_20px_rgba(16,185,129,0.35)]",
  default: "border-slate-400/50 bg-slate-700/30 text-slate-100/90",
};

const formatUpdateRate = (rate: string | null): string => {
  if (!rate) {
    return "On demand";
  }

  const match = rate.match(/^(\d+)([smhd])$/i);
  if (!match) {
    return rate;
  }

  const [, rawValue, unit] = match;
  const value = Number.parseInt(rawValue, 10);
  const unitLabelMap: Record<string, string> = {
    s: "second",
    m: "minute",
    h: "hour",
    d: "day",
  };
  const label = unitLabelMap[unit.toLowerCase()] ?? unit;
  const plural = value === 1 ? label : `${label}s`;
  return `Every ${value} ${plural}`;
};

const DataSourceRegistry = ({ sources, version }: DataSourceRegistryProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_50px_rgba(56,189,248,0.28)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.2),_transparent_60%)]" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.18),_transparent_65%)] opacity-80" />
    <CardHeader className="relative z-10 flex flex-col gap-3 pb-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <CardTitle className="text-xl font-semibold tracking-[0.3em] text-white">Ingestion Data Sources</CardTitle>
        <p className="mt-2 max-w-2xl text-sm text-slate-300/85">
          Registry of live feeds powering the sensory layer. Update cadences and schemas stay visible for rapid verification.
        </p>
      </div>
      {version ? (
        <Badge className="self-start rounded-full border-white/20 bg-slate-800/60 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-200">
          Config v{version}
        </Badge>
      ) : null}
    </CardHeader>
    <CardContent className="relative z-10 space-y-4">
      {sources.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 text-center text-sm text-slate-300/85">
          No data sources registered.
        </div>
      ) : null}
      {sources.map((source) => {
        const typeStyle = typeBadgeStyles[source.type] ?? typeBadgeStyles.default;
        const updateRate = formatUpdateRate(source.updateRate);
        return (
          <div key={source.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
            <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/85 p-4">
              <div className="pointer-events-none absolute inset-0 rounded-[calc(1rem-2px)] bg-gradient-to-br from-sky-500/25 via-transparent to-fuchsia-500/20 opacity-0 blur-2xl transition duration-500 group-hover:opacity-100" />
              <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-200">{source.label}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.3em] text-slate-400/80">ID · {source.id}</p>
                  <p className="mt-3 font-mono text-[13px] text-slate-300/80 break-all">{source.path}</p>
                </div>
                <Badge className={cn("rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em]", typeStyle)}>
                  {source.type.toUpperCase()}
                </Badge>
              </div>
              <div className="relative z-10 mt-4 flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.32em] text-slate-300/80">
                <Badge variant="outline" className="rounded-full border-white/20 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.32em] text-slate-200">
                  {updateRate}
                </Badge>
                {source.schema ? (
                  <Badge variant="outline" className="rounded-full border-white/20 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.32em] text-slate-200">
                    Schema · {source.schema}
                  </Badge>
                ) : null}
              </div>
            </div>
          </div>
        );
      })}
    </CardContent>
  </Card>
);

export default DataSourceRegistry;
