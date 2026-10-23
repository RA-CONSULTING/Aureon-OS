import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import MandalaOverlay from './MandalaOverlay';

type ChronicleMetric = {
  label: string;
  value: string;
  hint: string;
  tone: 'stable' | 'watch' | 'alert';
};

type ChronicleRecord = {
  id: string;
  title: string;
  badge: string;
  description: string;
  accent: string;
  metrics: ChronicleMetric[];
};

const CHRONICLES: ChronicleRecord[] = [
  {
    id: 'terrestrial',
    title: 'Terrestrial Chronicle',
    badge: 'Earth Grid',
    description: 'Geomantic pulse and acoustic watchers harmonized across planetary ley-lines.',
    accent: 'from-emerald-500/25 via-teal-500/20 to-sky-400/25',
    metrics: [
      { label: 'Geomantic Flux', value: '0.92', hint: 'Normalized coherence index', tone: 'stable' },
      { label: 'Acoustic Horizon', value: '37 dB', hint: 'Subsonic sentinel average', tone: 'watch' },
      { label: 'Seismic Drift', value: '±0.4 µGal', hint: 'Gravitational deviation', tone: 'stable' },
    ],
  },
  {
    id: 'heliospheric',
    title: 'Heliospheric Chronicle',
    badge: 'Solar Breath',
    description: 'Solar wind, magnetopause harmonics, and auroral charge interplay visualized.',
    accent: 'from-sky-500/25 via-indigo-500/25 to-fuchsia-400/25',
    metrics: [
      { label: 'Solar Wind', value: '412 km/s', hint: 'ACE + DSCOVR composite', tone: 'stable' },
      { label: 'Auroral Power', value: '82 GW', hint: 'Integrated hemisphere flow', tone: 'watch' },
      { label: 'K-Index', value: '3', hint: 'Geomagnetic storm potential', tone: 'stable' },
    ],
  },
  {
    id: 'bio-resonant',
    title: 'Bio-Resonant Chronicle',
    badge: 'Sentience Choir',
    description: 'Biofeedback pillars, heart-coherence clusters, and neural entrainment loops.',
    accent: 'from-rose-500/25 via-amber-400/25 to-purple-500/25',
    metrics: [
      { label: 'Coherence', value: '94%', hint: 'Collective HRV alignment', tone: 'stable' },
      { label: 'Theta Bloom', value: '18%', hint: 'Neural entrainment depth', tone: 'watch' },
      { label: 'Vitality Lift', value: '+12%', hint: 'Somatic vitality delta', tone: 'stable' },
    ],
  },
];

const toneBadgeClass: Record<ChronicleMetric['tone'], string> = {
  stable: 'border-emerald-400/40 bg-emerald-500/20 text-emerald-100 shadow-[0_0_25px_rgba(16,185,129,0.4)]',
  watch: 'border-amber-300/40 bg-amber-500/20 text-amber-100 shadow-[0_0_25px_rgba(251,191,36,0.35)]',
  alert: 'border-rose-400/40 bg-rose-500/25 text-rose-100 shadow-[0_0_25px_rgba(244,63,94,0.35)]',
};

const Chronicles = () => (
  <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/65 p-6 text-slate-100 shadow-[0_0_65px_rgba(59,130,246,0.28)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.25),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.22),_transparent_60%)] opacity-75" />
    <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
    <div className="pointer-events-none absolute -top-36 left-10 h-72 w-72 rounded-full bg-sky-500/35 blur-3xl animate-cosmic-drift" />
    <div className="pointer-events-none absolute -bottom-40 right-8 h-80 w-80 rounded-full bg-fuchsia-500/30 blur-[140px] animate-orbital-glow" />
    <div className="relative z-10 space-y-10">
      <header className="space-y-4 text-center">
        <Badge className="mx-auto inline-flex items-center rounded-full border-white/20 bg-white/10 px-5 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white/85" variant="outline">
          Sensory Chronicles
        </Badge>
        <h1 className="bg-gradient-to-r from-sky-200 via-emerald-200 to-amber-200 bg-clip-text text-4xl font-bold tracking-[0.32em] text-transparent sm:text-5xl">
          Harmonic Chronicle Vault
        </h1>
        <p className="mx-auto max-w-3xl text-sm leading-relaxed text-slate-300/85">
          Survey each sensory pillar of the nexus—earthbound flux, heliospheric breath, and bio-resonant choirs rendered within luminous stratums.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {CHRONICLES.map((chronicle) => (
          <Card key={chronicle.id} className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_55px_rgba(56,189,248,0.25)]">
            <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${chronicle.accent} opacity-80`} />
            <MandalaOverlay className="opacity-25" />
            <CardHeader className="relative z-10 space-y-3 pb-4">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-lg font-semibold uppercase tracking-[0.26em] text-white">
                  {chronicle.title}
                </CardTitle>
                <Badge className="rounded-full border-white/15 bg-white/10 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-white/85" variant="outline">
                  {chronicle.badge}
                </Badge>
              </div>
              <p className="text-xs text-slate-200/80">{chronicle.description}</p>
            </CardHeader>
            <CardContent className="relative z-10 space-y-4">
              {chronicle.metrics.map((metric) => (
                <div key={metric.label} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="pointer-events-none absolute inset-0 opacity-0 transition duration-500 group-hover:opacity-100" style={{ backgroundImage: 'linear-gradient(135deg, rgba(56,189,248,0.18), rgba(236,72,153,0.18))' }} />
                  <div className="relative z-10 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.28em] text-slate-300/80">
                    <span>{metric.label}</span>
                    <Badge className={`rounded-full px-3 py-1 ${toneBadgeClass[metric.tone]}`} variant="outline">
                      {metric.tone === 'stable' ? 'Stable' : metric.tone === 'watch' ? 'Watch' : 'Alert'}
                    </Badge>
                  </div>
                  <div className="relative z-10 mt-3 flex items-baseline justify-between text-white">
                    <span className="text-2xl font-semibold drop-shadow-[0_0_30px_rgba(255,255,255,0.35)]">{metric.value}</span>
                    <span className="text-xs uppercase tracking-[0.28em] text-slate-200/85">{metric.hint}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  </section>
);

export default Chronicles;
