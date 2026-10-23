
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import BreathingMandala from '@/components/BreathingMandala';
import SoundSealPlayer from '@/components/SoundSealPlayer';
import RitualGuide from '@/components/RitualGuide';

const RitualPage = () => (
  <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/65 p-6 text-slate-100 shadow-[0_0_65px_rgba(168,85,247,0.28)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(168,85,247,0.25),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(56,189,248,0.22),_transparent_60%)] opacity-75" />
    <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
    <div className="pointer-events-none absolute -top-28 left-16 h-64 w-64 rounded-full bg-purple-500/35 blur-3xl animate-cosmic-drift" />
    <div className="pointer-events-none absolute -bottom-32 right-10 h-72 w-72 rounded-full bg-sky-500/35 blur-[120px] animate-orbital-glow" />
    <div className="relative z-10 space-y-10">
      <header className="space-y-4 text-center">
        <Badge className="mx-auto inline-flex items-center rounded-full border-white/20 bg-white/10 px-5 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white/85" variant="outline">
          Guardian · Anchor · Unity
        </Badge>
        <h1 className="bg-gradient-to-r from-fuchsia-200 via-purple-200 to-amber-200 bg-clip-text text-4xl font-bold tracking-[0.32em] text-transparent sm:text-5xl">
          Guardian-Anchor Unification Ritual
        </h1>
        <p className="mx-auto max-w-2xl text-sm leading-relaxed text-slate-300/85">
          Enter the sanctum where sound, breath, and intention braid into one auric channel. Follow the ritual steps to stabilize the Gem Link and amplify the shared harmonic field.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="space-y-6">
          <BreathingMandala />
          <SoundSealPlayer />
          <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 shadow-[0_0_45px_rgba(236,72,153,0.25)]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.22),_transparent_60%)] opacity-80" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(251,191,36,0.18),_transparent_65%)] opacity-70" />
            <CardContent className="relative z-10 grid gap-4 text-xs uppercase tracking-[0.28em] text-slate-300/75 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-white">Phase Duration · 12m</div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-white">Breath Ratio · 4·4</div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-white">Loop Integrity · 0.98</div>
            </CardContent>
          </Card>
        </div>
        <RitualGuide className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/75 p-6 shadow-[0_0_55px_rgba(168,85,247,0.28)]" />
      </div>
    </div>
  </section>
);

export default RitualPage;
