import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type ProcessingStatus = 'Nominal' | 'Balancing' | 'Calibrating';

type ProcessingLane = {
  id: string;
  name: string;
  load: number; // 0-1
  status: ProcessingStatus;
  note: string;
};

const statusBadgeVariant = (status: ProcessingStatus) => {
  switch (status) {
    case 'Nominal':
      return 'success' as const;
    case 'Balancing':
      return 'warning' as const;
    case 'Calibrating':
      return 'info' as const;
    default:
      return 'secondary' as const;
  }
};

type ProcessingCoreTabProps = {
  processing: ProcessingLane[];
};

const statusAccent: Record<ProcessingStatus, string> = {
  Nominal: 'from-emerald-500/45 via-teal-400/25 to-transparent',
  Balancing: 'from-sky-500/40 via-indigo-500/30 to-transparent',
  Calibrating: 'from-fuchsia-500/40 via-violet-500/30 to-transparent',
};

const ProcessingCoreTab = ({ processing }: ProcessingCoreTabProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(99,102,241,0.22)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_60%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Processing Lattice</CardTitle>
      <p className="mt-2 max-w-xl text-sm text-slate-300/85">
        Quantum harmonics, storm targeting, and ethical correlators co-steering the nexus. Load and stability update live.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 space-y-4">
      {processing.map((lane) => (
        <div key={lane.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
          <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
          <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-4">
            <div className={cn('pointer-events-none absolute inset-0 rounded-[calc(1rem-2px)] opacity-70 blur-2xl transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${statusAccent[lane.status]}`)} />
            <div className="relative z-10 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{lane.name}</div>
              <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant={statusBadgeVariant(lane.status)}>
                {lane.status}
              </Badge>
            </div>
            <div className="relative z-10 mt-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div className="text-3xl font-semibold text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.35)]">
                {Math.round(lane.load * 100)}%
              </div>
              <span className="text-xs uppercase tracking-[0.3em] text-slate-300/75">{lane.note}</span>
            </div>
            <div className="relative z-10 mt-4 h-2 rounded-full bg-slate-800/80">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-sky-400 via-blue-500 to-fuchsia-400 shadow-[0_0_20px_rgba(99,102,241,0.45)]"
                style={{ width: `${Math.round(lane.load * 100)}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

export default ProcessingCoreTab;
