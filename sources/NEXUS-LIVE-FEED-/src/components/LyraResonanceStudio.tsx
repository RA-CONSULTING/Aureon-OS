import React from 'react';

const LyraResonanceStudio: React.FC = () => {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-slate-100 shadow-[0_0_45px_rgba(139,92,246,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.22),_transparent_60%)] opacity-80" />
      <div className="relative z-10 space-y-4">
        <h3 className="text-xl font-semibold uppercase tracking-[0.3em] text-white">Lyra Resonance Studio</h3>
        <p className="text-sm text-slate-300/80">
          Interactive control surface for harmonic layering, binaural sculpting, and Lyra wave articulation. Coming online in this build—placeholder controls stand in until the live studio is connected.
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          {["Harmonic Ladder", "Binaural Drift", "Celestial Chorus"].map((control) => (
            <div key={control} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-center">
              <span className="text-xs font-semibold uppercase tracking-[0.32em] text-white/85">{control}</span>
              <div className="mt-3 h-2 rounded-full bg-slate-800/70">
                <div className="h-2 rounded-full bg-gradient-to-r from-violet-400 via-sky-400 to-rose-400" style={{ width: '60%' }} />
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-slate-300/70">
                Awaiting live signal input. Configure modulation envelopes soon.
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default LyraResonanceStudio;
