import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export type VisualizationMetric = {
  label: string;
  value: string;
  hint: string;
  tone?: 'stable' | 'watch' | 'alert';
  progress?: number;
};

export type VisualizationModule = {
  id: string;
  title: string;
  summary: string;
  status?: string;
  metrics: VisualizationMetric[];
};

const badgeVariant = (tone?: 'stable' | 'watch' | 'alert') => {
  if (!tone) return 'secondary' as const;
  if (tone === 'stable') return 'success' as const;
  if (tone === 'watch') return 'warning' as const;
  return 'destructive' as const;
};

type LiveVisualizationTabProps = {
  modules: VisualizationModule[];
};

const gradientByTone: Record<'stable' | 'watch' | 'alert', string> = {
  stable: 'from-emerald-500/45 via-teal-400/25 to-transparent',
  watch: 'from-amber-500/45 via-orange-400/25 to-transparent',
  alert: 'from-rose-500/45 via-fuchsia-500/35 to-transparent',
};

const severityRank: Record<'stable' | 'watch' | 'alert', number> = {
  stable: 0,
  watch: 1,
  alert: 2,
};

const metricLabel = (tone: 'stable' | 'watch' | 'alert') =>
  tone === 'stable' ? 'Stable' : tone === 'watch' ? 'Watch' : 'Alert';

const progressGradient = (tone?: 'stable' | 'watch' | 'alert') =>
  tone ? gradientByTone[tone] : 'from-sky-500/45 via-blue-500/30 to-transparent';

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const LiveVisualizationTab = ({ modules }: LiveVisualizationTabProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(236,72,153,0.22)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.2),_transparent_60%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Live Visualization Center</CardTitle>
      <p className="mt-2 text-sm text-slate-300/85">
        Every module paints the nexus from a different prism. Select metrics pulse alongside their health glyphs.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 grid gap-4 lg:grid-cols-3">
      {modules.map((module) => {
        const dominantTone = module.metrics.reduce<'stable' | 'watch' | 'alert' | null>((current, metric) => {
          if (!metric.tone) return current;
          if (!current) return metric.tone;
          return severityRank[metric.tone] > severityRank[current] ? metric.tone : current;
        }, null);

        return (
          <div
            key={module.id}
            className="group relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]"
          >
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
            {dominantTone ? (
              <div
                className={cn(
                  'pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition duration-500 group-hover:opacity-90',
                  'bg-gradient-to-br',
                  gradientByTone[dominantTone]
                )}
              />
            ) : null}
            <div className="relative z-10 flex flex-col gap-5 rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{module.title}</div>
                  <p className="mt-1 text-xs text-slate-300/80">{module.summary}</p>
                </div>
                {module.status ? (
                  <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant="outline">
                    {module.status}
                  </Badge>
                ) : null}
              </div>
              <dl className="space-y-4 text-sm">
                {module.metrics.map((metric) => {
                  const progress =
                    typeof metric.progress === 'number' && Number.isFinite(metric.progress)
                      ? clamp(metric.progress, 0, 1)
                      : null;

                  return (
                    <div key={`${module.id}-${metric.label}`} className="space-y-2">
                      <div className="flex items-baseline justify-between gap-3">
                        <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{metric.label}</dt>
                        <dd className="text-right text-sm font-semibold text-white">
                          <div className="flex items-center justify-end gap-2">
                            <span>{metric.value}</span>
                            {metric.tone ? (
                              <Badge
                                className="px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.3em]"
                                variant={badgeVariant(metric.tone)}
                              >
                                {metricLabel(metric.tone)}
                              </Badge>
                            ) : null}
                          </div>
                        </dd>
                      </div>
                      <p className="text-[11px] font-normal text-slate-300/80">{metric.hint}</p>
                      {progress !== null ? (
                        <div className="relative h-1.5 overflow-hidden rounded-full bg-slate-800/80">
                          <div
                            className={cn(
                              'absolute inset-y-0 left-0 h-full rounded-full bg-gradient-to-r shadow-[0_0_18px_rgba(56,189,248,0.35)]',
                              progressGradient(metric.tone)
                            )}
                            style={{ width: `${Math.round(progress * 100)}%` }}
                          />
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </dl>
            </div>
          </div>
        );
      })}
    </CardContent>
  </Card>
);

export default LiveVisualizationTab;
