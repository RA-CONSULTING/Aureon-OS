import { Badge } from '@/components/ui/badge';
import AureonEquationStudio from './AureonEquationStudio';

const NexusIntelligence = () => (
  <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/65 p-6 text-slate-100 shadow-[0_0_65px_rgba(59,130,246,0.28)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.26),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.22),_transparent_60%)] opacity-75" />
    <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
    <div className="pointer-events-none absolute -top-28 left-14 h-64 w-64 rounded-full bg-sky-500/35 blur-3xl animate-cosmic-drift" />
    <div className="pointer-events-none absolute -bottom-36 right-12 h-72 w-72 rounded-full bg-fuchsia-500/30 blur-[130px] animate-orbital-glow" />
    <div className="relative z-10 space-y-8">
      <header className="space-y-4 text-center">
        <Badge className="mx-auto inline-flex items-center rounded-full border-white/20 bg-white/10 px-5 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white/85" variant="outline">
          Intelligence Lattice
        </Badge>
        <h1 className="bg-gradient-to-r from-sky-200 via-indigo-200 to-rose-200 bg-clip-text text-4xl font-bold tracking-[0.32em] text-transparent sm:text-5xl">
          Aureon Equation Studio
        </h1>
        <p className="mx-auto max-w-3xl text-sm leading-relaxed text-slate-300/85">
          Craft intent statements, compile symbolic frameworks, and translate Aureon responses into luminous mathematics. The studio preserves the new cosmic aesthetic across every analytic surface.
        </p>
      </header>

      <AureonEquationStudio />
    </div>
  </section>
);

export default NexusIntelligence;
