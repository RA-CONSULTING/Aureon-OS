
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const RitualGuide = ({ className }: { className?: string }) => (
  <Card
    className={className}
  >
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(168,85,247,0.22),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.22),_transparent_65%)] opacity-70" />
    <CardHeader className="relative z-10 space-y-2 pb-4">
      <CardTitle className="text-2xl font-semibold uppercase tracking-[0.28em] text-white">
        Gem Link Unification Guide
      </CardTitle>
      <p className="text-sm leading-relaxed text-slate-300/80">
        Navigate each movement in concert—prepare the chamber, synchronize the breath, invoke the vow, circulate the light, and seal the field with gratitude.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 space-y-6 text-sm text-slate-200/85">
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-fuchsia-200">Preparation</h4>
        <p>
          Sit facing one another if possible. Begin the <span className="font-semibold text-white">Sound Seal</span>, allowing the resonance to cleanse and attune the shared field.
        </p>
      </div>
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-fuchsia-200">Phase 1 · Breath Synchronization</h4>
        <p>
          Gaze softly into the <span className="font-semibold text-white">Breathing Mandala</span>. Follow its expansion on each inhale and its convergence on each exhale. Sense both heartbeats drifting toward the Schumann rhythm (7.83 Hz).
        </p>
      </div>
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-fuchsia-200">Phase 2 · Symbolic Command</h4>
        <p>
          When the rhythm unifies, speak the command together:
        </p>
        <p className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center text-sm italic text-white/90">
          “Gem link in unity—Guardian and Anchor, coherence sustained.”
        </p>
      </div>
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-fuchsia-200">Phase 3 · Harmonic Loop</h4>
        <p>
          Close the eyes and visualize the golden strand flowing clockwise between you. Send protective fire outward on the exhale and receive the anchor&rsquo;s stabilizing current on the inhale.
        </p>
      </div>
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-fuchsia-200">Phase 4 · Gratitude Seal</h4>
        <p>
          Release the visualization and hold shared gratitude—for each other, for the mission, for the cosmic lattice that holds you. Let the feeling seal the loop.
        </p>
      </div>
    </CardContent>
  </Card>
);

export default RitualGuide;
