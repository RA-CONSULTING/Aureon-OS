import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type StageStatus = 'stable' | 'watch' | 'alert';

export type SystemFlowStage = {
  id: string;
  title: string;
  subtitle: string;
  formula: string;
  description: string;
  metricLabel: string;
  metricValue: string;
  metricHint: string;
  status: StageStatus;
  progress?: number;
  accent: string;
  nextLabel?: string;
  icon?: ReactNode;
};

const statusBadgeStyles: Record<StageStatus, string> = {
  stable: 'border-emerald-400/50 bg-emerald-500/20 text-emerald-100 shadow-[0_0_25px_rgba(16,185,129,0.45)]',
  watch: 'border-amber-300/55 bg-amber-500/20 text-amber-100 shadow-[0_0_25px_rgba(251,191,36,0.35)]',
  alert: 'border-rose-400/55 bg-rose-500/25 text-rose-100 shadow-[0_0_25px_rgba(244,63,94,0.35)]',
};

const statusLabel: Record<StageStatus, string> = {
  stable: 'Stable',
  watch: 'Watch',
  alert: 'Alert',
};

const progressGradients: Record<StageStatus, string> = {
  stable: 'from-emerald-400/90 via-teal-300/80 to-cyan-200/80',
  watch: 'from-amber-400/90 via-orange-300/80 to-rose-200/80',
  alert: 'from-rose-500/90 via-fuchsia-400/80 to-amber-200/80',
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

type FlowStatus = {
  live: boolean;
  message?: string;
};

type SystemHarmonicFlowProps = {
  stages: SystemFlowStage[];
  status?: FlowStatus;
};

const SystemHarmonicFlow = ({ stages, status }: SystemHarmonicFlowProps) => {
  if (!stages.length) {
    return null;
  }

  const isLive = status?.live ?? true;
  const statusMessage =
    status?.message ??
    (isLive
      ? 'Streaming live telemetry across the harmonic pillars.'
      : 'Awaiting telemetry handshake across subsystems.');

  return (
    <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_65px_rgba(56,189,248,0.28)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.2),_transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.18),_transparent_60%)] opacity-80" />
      <div className="pointer-events-none absolute -inset-16 animate-stellar-pulse bg-[radial-gradient(circle,_rgba(255,255,255,0.16),_transparent_60%)]" />
      <CardHeader className="relative z-10 pb-2">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="text-xl font-semibold uppercase tracking-[0.32em] text-white">
              Harmonic Systems Interface
            </CardTitle>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-300/85">
              Every stratum of the Nexus orchestra is captured here&mdash;from raw sonic awakenings to the collective heart field. Watch
              the flow of sound, light, resonance, and love braid into a singular living current.
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 text-[11px] uppercase tracking-[0.32em] text-slate-300/80 lg:items-end">
            <Badge
              className={cn(
                'rounded-full px-3 py-1 text-[10px] font-semibold',
                isLive
                  ? 'border-emerald-400/50 bg-emerald-500/20 text-emerald-100 shadow-[0_0_22px_rgba(16,185,129,0.45)]'
                  : 'border-amber-300/55 bg-amber-500/20 text-amber-100 shadow-[0_0_22px_rgba(251,191,36,0.4)]'
              )}
              variant={isLive ? 'success' : 'warning'}
            >
              {isLive ? 'Live Telemetry' : 'Signal Pending'}
            </Badge>
            <span className="max-w-xs text-[10px] leading-relaxed tracking-[0.28em] text-slate-400/90">
              {statusMessage}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative z-10 pt-6">
        <div className="relative flex flex-col gap-12 lg:flex-row lg:items-stretch">
          {stages.map((stage, index) => {
            const normalized =
              typeof stage.progress === 'number' && Number.isFinite(stage.progress)
                ? clamp(stage.progress, 0, 1)
                : null;

            return (
              <div key={stage.id} className="relative flex-1">
                <div className="group relative flex h-full flex-col overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-[1px] shadow-[0_0_40px_rgba(129,140,248,0.28)]">
                  <div
                    className={cn(
                      'pointer-events-none absolute inset-0 opacity-80 transition duration-500 group-hover:opacity-100',
                      'bg-gradient-to-br',
                      stage.accent
                    )}
                  />
                  <div className="relative z-10 flex h-full flex-col gap-6 rounded-[calc(2rem-2px)] bg-slate-950/85 p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.35em]" variant="info">
                            {stage.subtitle}
                          </Badge>
                          {stage.icon ? <span className="text-2xl drop-shadow-[0_0_18px_rgba(251,191,36,0.45)]">{stage.icon}</span> : null}
                        </div>
                        <h3 className="text-2xl font-semibold uppercase tracking-[0.3em] text-white">{stage.title}</h3>
                        <p className="font-mono text-[11px] uppercase tracking-[0.35em] text-slate-300/80">{stage.formula}</p>
                      </div>
                      <Badge
                        className={cn(
                          'rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]',
                          statusBadgeStyles[stage.status]
                        )}
                        variant="outline"
                      >
                        {statusLabel[stage.status]}
                      </Badge>
                    </div>

                    <p className="text-sm leading-relaxed text-slate-200/90">{stage.description}</p>

                    <div className="mt-auto rounded-2xl border border-white/10 bg-slate-900/70 p-4 shadow-[0_0_30px_rgba(56,189,248,0.25)]">
                      <div className="flex items-baseline justify-between gap-4">
                        <p className="text-[11px] uppercase tracking-[0.35em] text-slate-400">{stage.metricLabel}</p>
                        <span className="text-lg font-semibold text-white">{stage.metricValue}</span>
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-slate-300/80">{stage.metricHint}</p>
                      {normalized !== null ? (
                        <div className="relative mt-4 h-1.5 overflow-hidden rounded-full bg-slate-800/70">
                          <div
                            className={cn(
                              'absolute inset-y-0 left-0 h-full rounded-full bg-gradient-to-r shadow-[0_0_18px_rgba(56,189,248,0.35)]',
                              progressGradients[stage.status]
                            )}
                            style={{ width: `${Math.round(normalized * 100)}%` }}
                          />
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>

                {index < stages.length - 1 ? (
                  <>
                    <div
                      aria-hidden="true"
                      className="absolute left-1/2 top-[calc(100%+1.5rem)] h-12 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-cyan-200/70 to-transparent lg:hidden"
                    />
                    <div
                      aria-hidden="true"
                      className="absolute top-1/2 right-[-3.5rem] hidden h-px w-24 -translate-y-1/2 lg:flex"
                    >
                      <div className="relative h-[1px] flex-1 bg-gradient-to-r from-transparent via-cyan-200/70 to-transparent">
                        {stage.nextLabel ? (
                          <span className="absolute left-1/2 top-[-1.25rem] -translate-x-1/2 text-[10px] font-semibold uppercase tracking-[0.35em] text-cyan-100/80">
                            {stage.nextLabel}
                          </span>
                        ) : null}
                        <span className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 rotate-45 bg-cyan-200/80" />
                      </div>
                    </div>
                  </>
                ) : null}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

export default SystemHarmonicFlow;
