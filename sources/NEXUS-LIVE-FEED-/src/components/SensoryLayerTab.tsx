import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { SensorState } from '@/data/streamMetadata';

type SensorStream = {
  id: string;
  name: string;
  location: string;
  intensity: number; // percentage 0-100
  state: SensorState;
  note: string;
};

const statusBadgeVariant = (state: SensorState) => {
  switch (state) {
    case 'Stable':
      return 'success' as const;
    case 'Watch':
      return 'warning' as const;
    case 'Anomaly':
      return 'destructive' as const;
    default:
      return 'secondary' as const;
  }
};

type SensoryLayerTabProps = {
  sensors: SensorStream[];
};

const accentByState: Record<SensorState, string> = {
  Stable: 'from-emerald-500/50 via-teal-400/30 to-transparent',
  Watch: 'from-amber-500/45 via-orange-400/25 to-transparent',
  Anomaly: 'from-rose-500/50 via-fuchsia-500/35 to-transparent',
};

const SensoryLayerTab = ({ sensors }: SensoryLayerTabProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(16,185,129,0.22)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.18),_transparent_60%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Sensory Array</CardTitle>
      <p className="mt-2 max-w-xl text-sm text-slate-300/85">
        Live resonance from each nexus station. Amplitude, coherence, and location context shimmer in real time.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 space-y-4">
      {sensors.map((stream) => (
        <div key={stream.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
          <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
          <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-4">
            <div className={cn('pointer-events-none absolute inset-0 rounded-[calc(1rem-2px)] opacity-70 blur-2xl transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${accentByState[stream.state]}`)} />
            <div className="relative z-10 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{stream.name}</div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/80">{stream.location}</div>
              </div>
              <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant={statusBadgeVariant(stream.state)}>
                {stream.state}
              </Badge>
            </div>
            <div className="relative z-10 mt-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div className="text-3xl font-semibold text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.35)]">
                {stream.intensity.toFixed(1)}%
              </div>
              <span className="text-xs uppercase tracking-[0.3em] text-slate-300/75">{stream.note}</span>
            </div>
            <div className="relative z-10 mt-4 h-2 rounded-full bg-slate-800/80">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-fuchsia-400 shadow-[0_0_20px_rgba(56,189,248,0.45)]"
                style={{ width: `${Math.round(stream.intensity)}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

export default SensoryLayerTab;
