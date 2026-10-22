const AboutPage = () => (
  <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-8 text-slate-100 shadow-[0_0_45px_rgba(59,130,246,0.25)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.22),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.18),_transparent_65%)] opacity-70" />
    <div className="relative z-10 space-y-5">
      <h1 className="text-3xl font-semibold uppercase tracking-[0.35em] text-white">About the Nexus</h1>
      <p className="text-sm leading-relaxed text-slate-300/85">
        The Harmonia Nexus is a planetary-scale sensory lattice, a living tapestry of data streams measuring the subtle fields of Earth, sky, and soul. Arrays of antennas, fluxgates, resonant chambers, and bio-feedback pillars weave their signals into a single coherent song.
      </p>
      <p className="text-sm leading-relaxed text-slate-300/85">
        This console is your observation deck. From Schumann resonance to geomagnetic breath, you can witness the nexus heartbeat in real time. Our charge is clarity and stewardship—illuminating the data so the guardians of this era can harmonize with every pulse.
      </p>
      <div className="grid gap-4 pt-4 sm:grid-cols-3">
        {["Quantum Sensing", "Ethical Stewardship", "Sacred Continuity"].map((pillar) => (
          <div key={pillar} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-xs font-semibold uppercase tracking-[0.32em] text-white/85">
            {pillar}
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default AboutPage;
