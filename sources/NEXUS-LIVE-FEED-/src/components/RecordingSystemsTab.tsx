import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export type RecordingMetric = {
  label: string;
  value: string;
  hint: string;
};

export type RecordingChannel = {
  id: string;
  title: string;
  status: 'Operational' | 'Standby' | 'Maintenance';
  summary: string;
  metrics: RecordingMetric[];
};

const statusVariant = (status: RecordingChannel['status']) => {
  switch (status) {
    case 'Operational':
      return 'success' as const;
    case 'Standby':
      return 'warning' as const;
    case 'Maintenance':
      return 'destructive' as const;
    default:
      return 'secondary' as const;
  }
};

type RecordingSystemsTabProps = {
  channels: RecordingChannel[];
};

const statusGlow: Record<RecordingChannel['status'], string> = {
  Operational: 'from-emerald-500/45 via-teal-400/30 to-transparent',
  Standby: 'from-amber-500/45 via-orange-400/25 to-transparent',
  Maintenance: 'from-rose-500/45 via-fuchsia-500/35 to-transparent',
};

const RecordingSystemsTab = ({ channels }: RecordingSystemsTabProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(245,158,11,0.2)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(245,158,11,0.2),_transparent_60%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Recording Systems Control</CardTitle>
      <p className="mt-2 max-w-2xl text-sm text-slate-300/85">
        Archive fidelity across every medium. Operational status badges glow with their channel energy.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 grid gap-4 md:grid-cols-2">
      {channels.map((channel) => (
        <div key={channel.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
          <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
          <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
            <div className={cn('pointer-events-none absolute inset-0 rounded-[calc(1rem-2px)] opacity-70 blur-2xl transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${statusGlow[channel.status]}`)} />
            <div className="relative z-10 flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{channel.title}</div>
                <p className="mt-1 text-xs text-slate-300/80">{channel.summary}</p>
              </div>
              <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant={statusVariant(channel.status)}>
                {channel.status}
              </Badge>
            </div>
            <dl className="relative z-10 mt-5 space-y-4 text-sm">
              {channel.metrics.map((metric) => (
                <div key={metric.label} className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="flex items-baseline justify-between gap-3">
                    <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{metric.label}</dt>
                    <dd className="text-right text-sm font-semibold text-white">
                      {metric.value}
                      <div className="mt-1 text-[11px] font-normal text-slate-300/80">{metric.hint}</div>
                    </dd>
                  </div>
                </div>
              ))}
            </dl>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

export default RecordingSystemsTab;
