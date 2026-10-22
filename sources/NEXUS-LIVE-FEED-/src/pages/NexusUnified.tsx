import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

const NexusUnified = () => (
  <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/65 p-6 text-slate-100 shadow-[0_0_65px_rgba(148,163,184,0.28)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.25),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.2),_transparent_60%)] opacity-70" />
    <div className="relative z-10 space-y-8">
      <header className="space-y-4 text-center">
        <Badge className="mx-auto inline-flex items-center rounded-full border-white/20 bg-white/10 px-5 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white/85" variant="outline">
          Unified Console
        </Badge>
        <h1 className="bg-gradient-to-r from-sky-200 via-rose-200 to-amber-200 bg-clip-text text-4xl font-bold tracking-[0.32em] text-transparent sm:text-5xl">
          Harmonic Nexus · Unified View
        </h1>
        <p className="mx-auto max-w-3xl text-sm leading-relaxed text-slate-300/85">
          A condensed overview of every tab—sensory streams, processing corridors, visualization grids, recording vaults, governance pillars, and actuation suites—rendered in the new auroral aesthetic.
        </p>
      </header>

      <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_55px_rgba(148,163,184,0.28)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.2),_transparent_60%)] opacity-75" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.22),_transparent_65%)] opacity-70" />
        <CardContent className="relative z-10 grid gap-4 text-xs uppercase tracking-[0.3em] text-slate-200/80 sm:grid-cols-3">
          {[
            'Sensory Lattice',
            'Processing Core',
            'Visualization Deck',
            'Visual Relay',
            'Recording Vaults',
            'Chronicle Governance',
            'Output Command',
            'Actuation Command',
            'Meta Quest Portal',
          ].map((label) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-white">
              {label}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  </section>
);

export default NexusUnified;
