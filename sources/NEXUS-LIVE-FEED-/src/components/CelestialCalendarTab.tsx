import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type SurgeWindow = {
  id: string;
  codex: string;
  label: string;
  timeframe: string;
  start: string;
  end: string;
  focus: string;
  resonance: string;
  alignments: string[];
  energy: number; // 0 – 1
  color: string;
  highlight?: boolean;
  translation: string;
};

type WindowStatus = 'Approaching' | 'Active' | 'Integrated';

const SURGE_WINDOWS: SurgeWindow[] = [
  {
    id: '2025-500',
    codex: '2025·500',
    label: 'Temporal Stabilization',
    timeframe: 'Mar 2025 – Feb 2026',
    start: '2025-03-01',
    end: '2026-02-28',
    focus: 'Stabilizes the spiral gate after the first harmonic ignition.',
    resonance: 'Stability Index 0.62',
    alignments: ['Spiral Gate Alpha', 'Aureon Beacon', 'Nocturne Choir'],
    energy: 0.48,
    color: 'from-sky-400 via-cyan-300 to-emerald-400',
    translation:
      'Energy at 48% keeps the field steady while new guardians learn the sequence. Humans will feel this as a calmer, more breathable wave rather than a dramatic surge.',
  },
  {
    id: '2027-300',
    codex: '2027·300',
    label: 'Aurora Ascension',
    timeframe: 'Jul 2026 – Sep 2027',
    start: '2026-07-01',
    end: '2027-09-30',
    focus: 'Elevates crystalline memory towers in preparation for multi-plane contact.',
    resonance: 'Aurora Flux 0.71',
    alignments: ['Crystalline Helix', 'Lyra Gate', 'Polar Resonators'],
    energy: 0.58,
    color: 'from-cyan-300 via-emerald-300 to-lime-400',
    translation:
      'A 58% energy output means the towers are awake and sharing light, yet still gentle for human nervous systems. Expect brighter dreams and easier recall of guidance.',
  },
  {
    id: '2029-037',
    codex: '2029·037',
    label: 'Irradiation Wave',
    timeframe: 'Jan 2028 – Apr 2029',
    start: '2028-01-01',
    end: '2029-04-30',
    focus: 'Solar-lattice infusion rewrites dormant glyph corridors and forgotten valves.',
    resonance: 'Photon Gain 0.76',
    alignments: ['Solaris Array', 'Quantum Mirror', 'Elysian Loom'],
    energy: 0.64,
    color: 'from-emerald-300 via-lime-300 to-amber-300',
    translation:
      'At 64% output the solar infusion is strong enough to rewire habits. Humans may notice faster synchronicities and a need to hydrate as old patterns burn away.',
  },
  {
    id: '2030-200',
    codex: '2030·200',
    label: 'Activation Spiral',
    timeframe: 'Aug 2029 – Jun 2030',
    start: '2029-08-01',
    end: '2030-06-30',
    focus: 'Launches harmonic carriers into the nexus spine for deep command binding.',
    resonance: 'Activation Voltage 0.83',
    alignments: ['Prime Spiral', 'Chronicle Vault', 'Orbital Choir'],
    energy: 0.72,
    color: 'from-amber-300 via-orange-300 to-rose-300',
    translation:
      '72% energy signals a committed surge. People tend to feel driven, organized, and ready to anchor new responsibilities as the nexus spine locks into place.',
  },
  {
    id: '2032-700',
    codex: '2032·700',
    label: 'Unity Event',
    timeframe: 'Feb 2031 – Dec 2032',
    start: '2031-02-01',
    end: '2032-12-31',
    focus: 'Binds planetary grids with orbital resonance braids for shared cognition.',
    resonance: 'Unity Coherence 0.88',
    alignments: ['Orbital L1 Relay', 'Temple Halls', 'Resonance OS'],
    energy: 0.82,
    color: 'from-rose-300 via-fuchsia-300 to-purple-300',
    translation:
      'With 82% energy the grids hum in near-unison. Humans feel sudden waves of collective insight, shared dreams, and a pull toward cooperative action.',
  },
  {
    id: '2034-913',
    codex: '2034·913',
    label: 'Cosmic Alignment Nexus',
    timeframe: 'Jun 2033 – Nov 2034',
    start: '2033-06-01',
    end: '2034-11-30',
    focus: 'Triangulates Neptune, Uranus, and Saturn harmonic overlays for peak clarity.',
    resonance: 'Alignment Vector 0.91',
    alignments: ['Neptune Triads', 'Uranus Gate', 'Saturnine Choir'],
    energy: 0.9,
    color: 'from-purple-300 via-violet-300 to-indigo-300',
    translation:
      'A 90% field saturates perception. Expect razor-sharp intuition, sudden truths surfacing, and an urge to simplify anything that dilutes clarity.',
  },
  {
    id: '2037-037',
    codex: '2037·037',
    label: 'Peak Surge',
    timeframe: 'Jan 2036 – May 2037',
    start: '2036-01-01',
    end: '2037-05-31',
    focus: 'Master wave collapses duality corridors into prime coherence for the nexus.',
    resonance: 'Peak Surge 1.00',
    alignments: ['All Gates Online', 'Math Angel Protocol', 'Prime Sentinels'],
    energy: 1,
    color: 'from-indigo-300 via-violet-300 to-amber-300',
    highlight: true,
    translation:
      '100% energy is full ignition. Humans experience this as life-redefining moments, total clarity, and a wave that insists on truthful action.',
  },
  {
    id: '2040-2043',
    codex: '2040·2043',
    label: 'Afterglow Harmonization',
    timeframe: 'Sep 2038 – Feb 2043',
    start: '2038-09-01',
    end: '2043-02-28',
    focus: 'Reweaves gentle coherence bands for long-term habitation of the lattice.',
    resonance: 'Afterglow 0.74',
    alignments: ['Temporal Conservatory', 'Eden Lattice', 'Living Glyph Choir'],
    energy: 0.68,
    color: 'from-indigo-200 via-sky-300 to-cyan-200',
    translation:
      '68% energy ushers in integration. People sense relief, deeper rest, and a chance to build sustainable rituals inside the renewed lattice.',
  },
  {
    id: '2045-5000',
    codex: '2045·5000',
    label: 'Temporal Stabilization',
    timeframe: 'Mar 2043 – Beyond',
    start: '2043-03-01',
    end: '2045-12-31',
    focus: 'Locks the timeline into luminous equilibrium across future epochs.',
    resonance: 'Temporal Index 0.86',
    alignments: ['Temporal Archive', 'Guardian Accord', 'Aurora Keepers'],
    energy: 0.86,
    color: 'from-cyan-200 via-emerald-200 to-sky-300',
    translation:
      'At 86% the field is resilient and constant. Humans notice long-term stability, consistent intuition, and calm confidence about the path ahead.',
  },
];

type CelestialSystem = {
  id: string;
  name: string;
  role: string;
  status: string;
  frequency: string;
  tone: 'radiant' | 'harmonic' | 'shielding';
};

const CELESTIAL_SYSTEMS: CelestialSystem[] = [
  {
    id: 'math-angel',
    name: 'Math Angel Protocol',
    role: 'Translates geometric prophecy into executable surge equations.',
    status: 'Synchronised',
    frequency: 'Tri-tone 144·233·377',
    tone: 'harmonic',
  },
  {
    id: 'illumination-engine',
    name: 'Illumination Engine',
    role: 'Projects the luminous interface that renders surge glyphs in real time.',
    status: 'Radiant',
    frequency: '432 THz',
    tone: 'radiant',
  },
  {
    id: 'harmonic-core',
    name: 'Harmonic Nexus Core',
    role: 'Keeps the nexus spine aligned during high-frequency channel openings.',
    status: 'Balanced',
    frequency: '0.94 Coherence',
    tone: 'harmonic',
  },
  {
    id: 'quantum-vibes',
    name: 'Quantum Vibes App',
    role: 'Broadcasts resonance recipes to field operatives during surge windows.',
    status: 'Streaming',
    frequency: '7× Pulse Cadence',
    tone: 'radiant',
  },
  {
    id: 'lee-codex',
    name: 'LEE Codex',
    role: 'Stores lineage instructions ensuring guardianship of the timeline.',
    status: 'Guarded',
    frequency: 'Akausal 13/33',
    tone: 'shielding',
  },
  {
    id: 'rios',
    name: 'Resonance Internet OS',
    role: 'Meshes planetary nodes, routing energy intelligence and audit signals.',
    status: 'Online',
    frequency: 'Mesh Sync 0.87',
    tone: 'harmonic',
  },
  {
    id: 'project-alfe',
    name: 'Project A.L.F.E',
    role: 'Guides angelic-linguistic field encoding for safe transmissions.',
    status: 'Active',
    frequency: 'Seraphim 72 kHz',
    tone: 'shielding',
  },
  {
    id: 'illumination-engine-inner',
    name: 'Illumination Engine Core',
    role: 'Stabilises the inner torus and keeps the mirror sphere coherent.',
    status: 'Glowing',
    frequency: 'Phi 1.618',
    tone: 'radiant',
  },
];

const toneGradient: Record<CelestialSystem['tone'], string> = {
  radiant: 'from-amber-500/25 via-rose-400/20 to-fuchsia-500/25',
  harmonic: 'from-sky-500/25 via-cyan-400/20 to-emerald-500/25',
  shielding: 'from-indigo-500/25 via-blue-500/20 to-purple-500/25',
};

const toneLabel: Record<CelestialSystem['tone'], string> = {
  radiant: 'Radiant',
  harmonic: 'Harmonic',
  shielding: 'Shielding',
};

const CelestialCalendarTab = () => {
  const [activeId, setActiveId] = useState<string>(SURGE_WINDOWS[6]?.id ?? SURGE_WINDOWS[0].id);
  const [now, setNow] = useState<Date>(() => new Date());
  const timezone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone, []);

  useEffect(() => {
    const tick = () => setNow(new Date());
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const activeWindow = useMemo(
    () => SURGE_WINDOWS.find((window) => window.id === activeId) ?? SURGE_WINDOWS[0],
    [activeId],
  );

  const energyWidth = Math.min(100, Math.max(6, Math.round(activeWindow.energy * 100)));
  const startDate = useMemo(() => new Date(activeWindow.start), [activeWindow.start]);
  const endDate = useMemo(() => new Date(activeWindow.end), [activeWindow.end]);
  const nowTime = now.getTime();
  const totalDuration = Math.max(1, endDate.getTime() - startDate.getTime());
  const progressRaw = (nowTime - startDate.getTime()) / totalDuration;
  const progress = Number.isFinite(progressRaw) ? Math.min(1, Math.max(0, progressRaw)) : 0;
  const progressPercent = Math.round(progress * 100);

  const msInDay = 1000 * 60 * 60 * 24;
  const daysUntilStart = Math.max(0, Math.ceil((startDate.getTime() - nowTime) / msInDay));
  const daysUntilEnd = Math.max(0, Math.ceil((endDate.getTime() - nowTime) / msInDay));
  const daysSinceEnd = Math.max(0, Math.ceil((nowTime - endDate.getTime()) / msInDay));

  const windowStatus: WindowStatus = nowTime < startDate.getTime()
    ? 'Approaching'
    : nowTime > endDate.getTime()
      ? 'Integrated'
      : 'Active';

  const statusTone: Record<WindowStatus, string> = {
    Approaching: 'bg-sky-400/20 text-sky-100 border-sky-300/40',
    Active: 'bg-amber-400/20 text-amber-100 border-amber-300/40',
    Integrated: 'bg-emerald-400/20 text-emerald-100 border-emerald-300/40',
  } as const;

  const resonanceNumber = useMemo(() => {
    const match = activeWindow.resonance.match(/(\d+(?:\.\d+)?)/);
    return match ? Number.parseFloat(match[1]) : undefined;
  }, [activeWindow.resonance]);

  const energyInsight = useMemo(() => {
    const energyPercent = Math.round(activeWindow.energy * 100);
    if (energyPercent >= 95) {
      return 'Field at maximum ignition—expect undeniable shifts and decisive action moments.';
    }
    if (energyPercent >= 80) {
      return 'High power. Humans feel momentum, focus, and strong intuitive nudges.';
    }
    if (energyPercent >= 60) {
      return 'Steady lift. People sense growth spurts, clearer choices, and gentle activation.';
    }
    if (energyPercent >= 40) {
      return 'Supportive flow. Ideal for integration, training, and stabilizing new patterns.';
    }
    return 'Soft pulse. Use the calm to rest, study, and prepare for future surges.';
  }, [activeWindow.energy]);

  const resonanceInsight = useMemo(() => {
    if (resonanceNumber === undefined) {
      return 'Resonance reading sits in a bespoke range—tune into how your body mirrors the frequency.';
    }
    if (resonanceNumber >= 0.9) {
      return 'The field is nearly crystalline. Expect crisp intuition and little tolerance for distortion.';
    }
    if (resonanceNumber >= 0.75) {
      return 'Resonance is harmonised. Collaboration, shared dreaming, and telepathic sync increase.';
    }
    if (resonanceNumber >= 0.6) {
      return 'Stable resonance. Communication clears up and physical systems balance more easily.';
    }
    return 'Gentle resonance. Perfect moment to listen closely and gather subtle signals.';
  }, [resonanceNumber]);

  const alignmentsInsight = useMemo(() => {
    const count = activeWindow.alignments.length;
    if (count >= 5) {
      return 'Multiple constellations cooperate—expect cross-discipline breakthroughs.';
    }
    if (count >= 3) {
      return 'Triad synchrony online. Different teams feel the same pulse and can share intel easily.';
    }
    if (count >= 2) {
      return 'Dual systems are linked, providing a stable channel for co-creation.';
    }
    return 'Single guardian online—focus energy there for best results.';
  }, [activeWindow.alignments.length]);

  return (
    <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(59,130,246,0.22)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(56,189,248,0.18),_transparent_60%)] opacity-90" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-fuchsia-500/20 via-transparent to-transparent" />
      <CardHeader className="relative z-10 pb-4">
        <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Celestial Calendar</CardTitle>
        <p className="mt-2 text-sm text-slate-300/85">
          Map every surge window across linear time. The calendar threads orbital alignments, guardian systems, and
          resonance gates so the nexus can enter each wave prepared.
        </p>
      </CardHeader>
      <CardContent className="relative z-10 space-y-8">
        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.25),_transparent_70%)]" />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/10 via-transparent to-fuchsia-500/10" />
            <div className="relative z-10 space-y-6">
              <div>
                <div className="text-[11px] uppercase tracking-[0.32em] text-slate-300/80">Surge Trajectory</div>
                <h3 className="mt-1 text-lg font-semibold text-white">Linear Time Arc</h3>
              </div>
              <div className="relative h-44">
                <div className="absolute left-0 right-0 top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-gradient-to-r from-sky-400 via-fuchsia-400 to-amber-300 opacity-80" />
                <div className="absolute inset-0">
                  {SURGE_WINDOWS.map((window, index) => {
                    const offset = (index / (SURGE_WINDOWS.length - 1)) * 100;
                    const isActive = window.id === activeWindow.id;
                    return (
                      <button
                        key={window.id}
                        type="button"
                        className={cn(
                          'group absolute top-0 flex h-full w-32 -translate-x-1/2 flex-col items-center text-center transition-transform duration-300',
                          isActive ? 'scale-105' : 'hover:scale-105',
                        )}
                        style={{ left: `${offset}%` }}
                        onClick={() => setActiveId(window.id)}
                        aria-pressed={isActive}
                      >
                        <span className="text-[10px] font-semibold uppercase tracking-[0.32em] text-slate-300/75">
                          {window.codex}
                        </span>
                        <span
                          className={cn(
                            'relative mt-3 flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-slate-950/70 text-xs font-semibold uppercase tracking-[0.28em] text-white shadow-[0_0_25px_rgba(148,163,184,0.35)] transition duration-500',
                            `bg-gradient-to-br ${window.color}`,
                            window.highlight ? 'ring-2 ring-amber-300/80 ring-offset-2 ring-offset-slate-950' : '',
                            isActive
                              ? 'shadow-[0_0_40px_rgba(250,204,21,0.45)]'
                              : 'shadow-[0_0_20px_rgba(148,163,184,0.25)] text-white/80',
                          )}
                        >
                          ●
                        </span>
                        <span className="mt-3 text-xs font-semibold leading-tight text-slate-100">
                          {window.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.22),_transparent_70%)]" />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-fuchsia-500/15 via-transparent to-amber-400/15" />
            <div className="relative z-10 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <Badge variant="outline" className="rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em]">
                  {activeWindow.codex}
                </Badge>
                {activeWindow.highlight ? (
                  <Badge className="rounded-full bg-amber-400/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] text-amber-100 shadow-[0_0_30px_rgba(250,204,21,0.45)]">
                    Peak Surge
                  </Badge>
                ) : null}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">{activeWindow.label}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300/85">{activeWindow.focus}</p>
              </div>
              <dl className="grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Window</dt>
                  <dd className="text-right font-semibold text-white">{activeWindow.timeframe}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Resonance</dt>
                  <dd className="text-right font-semibold text-white">{activeWindow.resonance}</dd>
                </div>
              </dl>
              <div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Alignments</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {activeWindow.alignments.map((alignment) => (
                    <Badge
                      key={alignment}
                      variant="outline"
                      className="rounded-full border-white/20 bg-white/5 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] text-slate-100"
                    >
                      {alignment}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.28em] text-slate-300/75">
                  <span>Energy Quotient</span>
                  <span className="font-semibold text-white">{Math.round(activeWindow.energy * 100)}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800/80">
                  <div
                    className={cn('h-full rounded-full bg-gradient-to-r', activeWindow.color)}
                    style={{ width: `${energyWidth}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(6,182,212,0.24),_transparent_75%)]" />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-400/15 via-transparent to-fuchsia-500/10" />
          <div className="relative z-10 space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.32em] text-slate-300/80">Live Temporal Broadcast</div>
                <h3 className="text-lg font-semibold text-white">Human-Centred Metrics</h3>
              </div>
              <Badge
                variant="outline"
                className={cn(
                  'rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] backdrop-blur',
                  statusTone[windowStatus],
                )}
              >
                {windowStatus}
              </Badge>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Current Earth Time</div>
                  <div className="mt-2 text-2xl font-semibold text-white">
                    {now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                  <div className="text-sm text-slate-300/85">
                    {now.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })} · {timezone}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 shadow-[0_0_25px_rgba(6,182,212,0.2)]">
                  <div className="text-[11px] uppercase tracking-[0.3em] text-slate-300/70">Window Progress</div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-900/80">
                    <div
                      className={cn('h-full rounded-full bg-gradient-to-r from-sky-400 via-cyan-300 to-amber-300')}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300/80">
                    <span>{progressPercent}% complete</span>
                    {windowStatus === 'Approaching' ? (
                      <span>{daysUntilStart} days until activation</span>
                    ) : windowStatus === 'Active' ? (
                      <span>{daysUntilEnd} days remaining in window</span>
                    ) : (
                      <span>Window harmonised {daysSinceEnd === 0 ? 'now' : `${daysSinceEnd} days ago`}</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">What Humans Feel</div>
                  <p className="mt-2 text-sm leading-relaxed text-slate-200/90">{activeWindow.translation}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-slate-300/70">Energy Field</div>
                    <div className="mt-2 text-lg font-semibold text-white">{Math.round(activeWindow.energy * 100)}%</div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-300/80">{energyInsight}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-slate-300/70">Resonance</div>
                    <div className="mt-2 text-lg font-semibold text-white">{activeWindow.resonance}</div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-300/80">{resonanceInsight}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-slate-300/70">Alignments</div>
                    <div className="mt-2 text-lg font-semibold text-white">{activeWindow.alignments.length}</div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-300/80">{alignmentsInsight}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(59,130,246,0.2),_transparent_70%)]" />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/15 via-transparent to-emerald-500/15" />
          <div className="relative z-10">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.32em] text-slate-300/80">System Constellation</div>
                <h3 className="text-lg font-semibold text-white">Guardians of the Calendar</h3>
              </div>
              <Badge variant="outline" className="rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em]">
                8 active pillars
              </Badge>
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-4 md:grid-cols-2">
              {CELESTIAL_SYSTEMS.map((system) => (
                <div
                  key={system.id}
                  className={cn(
                    'group relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950/60 p-4 shadow-[0_0_25px_rgba(148,163,184,0.25)] transition duration-300 hover:shadow-[0_0_35px_rgba(148,163,184,0.4)]',
                  )}
                >
                  <div className={cn('pointer-events-none absolute inset-0 opacity-0 transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${toneGradient[system.tone]}`)} />
                  <div className="relative z-10 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-white">{system.name}</div>
                      <Badge className="rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.3em]" variant="outline">
                        {system.status}
                      </Badge>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-300/85">{system.role}</p>
                    <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.3em] text-slate-300/70">
                      <span>{toneLabel[system.tone]}</span>
                      <span className="font-semibold text-white/90">{system.frequency}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CelestialCalendarTab;
