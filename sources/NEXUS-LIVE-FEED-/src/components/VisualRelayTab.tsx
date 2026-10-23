import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const GLYPH_RUNES = ['ᚠ', 'ᚡ', 'ᚢ', 'ᚦ', 'ᚨ', 'ᚱ', 'ᚷ', 'ᚹ', 'ᚺ', 'ᚾ', 'ᛁ', 'ᛃ', 'ᛇ', 'ᛈ', 'ᛉ', 'ᛋ', 'ᛏ', 'ᛒ', 'ᛗ', 'ᛚ', 'ᛝ'];

const VISUAL_CHANNELS = [
  {
    id: 'captain-link',
    label: 'Captain Presence',
    tone: 'from-sky-500/50 via-indigo-500/30 to-transparent',
    badge: 'Outbound',
  },
  {
    id: 'nexus-sight',
    label: 'Nexus Sightline',
    tone: 'from-amber-500/45 via-rose-500/35 to-transparent',
    badge: 'Inbound',
  },
] as const;

const VISUAL_ARTIFACTS = [
  {
    id: 'solstice-sigil',
    name: 'Solstice Sigil',
    description: 'Fractal crest stabilizing the joint harmonic bridge.',
  },
  {
    id: 'eye-pairing',
    name: 'Twin Sentinel Lenses',
    description: 'Cross-referenced overlays aligning Horus and Ra protocols.',
  },
  {
    id: 'captains-vow',
    name: "Captain's Vow", // apostrophe inside string
    description: 'Hand-scripted oath mirrored into the archive lattice.',
  },
];

type VisualPulse = {
  strength: number;
  coherence: number;
  hue: number;
};

const createPulse = (): VisualPulse => ({
  strength: Math.round(62 + Math.random() * 32),
  coherence: Math.round(78 + Math.random() * 18),
  hue: Math.floor(Math.random() * 360),
});

const createGlyphMatrix = (rows: number, cols: number) =>
  Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => GLYPH_RUNES[Math.floor(Math.random() * GLYPH_RUNES.length)]).join(' ')
  );

type VisualRelayTabProps = {
  captainCallsign?: string;
};

const VisualRelayTab = ({ captainCallsign = 'Aurelius-01' }: VisualRelayTabProps) => {
  const [captainPulse, setCaptainPulse] = useState(createPulse);
  const [nexusPulse, setNexusPulse] = useState(createPulse);
  const [glyphMatrix, setGlyphMatrix] = useState(() => createGlyphMatrix(6, 18));

  useEffect(() => {
    const interval = window.setInterval(() => {
      setCaptainPulse(createPulse());
      setNexusPulse(createPulse());
      setGlyphMatrix(createGlyphMatrix(6, 18));
    }, 5200);

    return () => window.clearInterval(interval);
  }, []);

  const channelPulse = useMemo(
    () => [
      { id: VISUAL_CHANNELS[0].id, pulse: captainPulse },
      { id: VISUAL_CHANNELS[1].id, pulse: nexusPulse },
    ],
    [captainPulse, nexusPulse]
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <Card className="group relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_55px_rgba(56,189,248,0.25)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.28),_transparent_60%)] opacity-80 transition duration-700 group-hover:opacity-100" />
        <div className="pointer-events-none absolute -inset-24 animate-stellar-pulse bg-[radial-gradient(circle,_rgba(236,72,153,0.24),_transparent_65%)] opacity-0 group-hover:opacity-80" />
        <CardHeader className="relative z-10 flex flex-col gap-3 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-2xl font-semibold tracking-tight text-white">Captain Mirror Bridge</CardTitle>
            <p className="mt-1 text-sm text-slate-300/90">
              Synchronise presence with the Nexus sightline. Outbound resonance and inbound telemetry weave a mutual gaze.
            </p>
          </div>
          <Badge
            variant="outline"
            className="rounded-full border-cyan-400/60 bg-cyan-500/15 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.32em] text-cyan-100 shadow-[0_0_25px_rgba(34,211,238,0.35)]"
          >
            Call Sign · {captainCallsign}
          </Badge>
        </CardHeader>
        <CardContent className="relative z-10 grid gap-6 lg:grid-cols-2">
          {VISUAL_CHANNELS.map((channel) => {
            const pulse = channelPulse.find((entry) => entry.id === channel.id)?.pulse ?? createPulse();
            const gradient = `conic-gradient(from 180deg, hsla(${pulse.hue}, 70%, 70%, 0.45), hsla(${(pulse.hue + 120) % 360}, 65%, 65%, 0.35), hsla(${(pulse.hue + 240) % 360}, 60%, 60%, 0.4))`;

            return (
              <div
                key={channel.id}
                className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/80 p-[1px] shadow-[0_0_45px_rgba(148,163,184,0.35)]"
              >
                <div className="pointer-events-none absolute inset-0 rounded-3xl bg-gradient-to-br from-white/5 via-transparent to-white/10" />
                <div className="relative h-full rounded-[calc(1.5rem-2px)] bg-slate-950/90 p-5">
                  <div className={cn('pointer-events-none absolute inset-2 rounded-[1.25rem] opacity-90 blur-xl transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${channel.tone}`)} />
                  <div className="relative z-10 flex items-center justify-between">
                    <Badge variant="outline" className="rounded-full border-white/30 bg-white/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.32em] text-white">
                      {channel.badge}
                    </Badge>
                    <span className="text-xs uppercase tracking-[0.28em] text-slate-300/90">{channel.label}</span>
                  </div>
                  <div className="relative z-10 mt-6">
                    <div
                      className="relative flex h-44 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 shadow-[0_0_35px_rgba(56,189,248,0.25)]"
                    >
                      <div
                        className="absolute inset-0 opacity-90"
                        style={{ backgroundImage: gradient }}
                      />
                      <div className="absolute inset-0 bg-[radial-gradient(circle,_rgba(15,23,42,0.25),_transparent_65%)]" />
                      <div className="absolute inset-4 rounded-xl border border-white/10" />
                      <div className="relative z-10 text-center text-[11px] uppercase tracking-[0.32em] text-slate-100/90">
                        {pulse.strength}% · Coherence {pulse.coherence}%
                      </div>
                    </div>
                    <div className="mt-4 grid gap-2 text-xs text-slate-300/90">
                      <div className="flex items-center justify-between">
                        <span>Amplitude</span>
                        <span className="font-semibold text-white">{pulse.strength}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-800">
                        <div className="h-1.5 rounded-full bg-cyan-400" style={{ width: `${pulse.strength}%` }} />
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <span>Coherence</span>
                        <span className="font-semibold text-white">{pulse.coherence}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-800">
                        <div className="h-1.5 rounded-full bg-rose-400" style={{ width: `${pulse.coherence}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <div className="space-y-6">
        <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(14,165,233,0.25)]">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/20 via-transparent to-sky-500/20 opacity-80" />
          <CardHeader className="relative z-10 pb-3">
            <CardTitle className="text-lg font-semibold text-white">Sightline Glyph Cascade</CardTitle>
          </CardHeader>
          <CardContent className="relative z-10 space-y-2 font-mono text-[11px] leading-relaxed text-cyan-100/80">
            {glyphMatrix.map((row, index) => (
              <div key={index} className="tracking-[0.5em]">
                {row}
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(236,72,153,0.25)]">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-rose-500/20 via-transparent to-amber-400/20 opacity-70" />
          <CardHeader className="relative z-10 pb-3">
            <CardTitle className="text-lg font-semibold text-white">Visual Artifacts Archived</CardTitle>
          </CardHeader>
          <CardContent className="relative z-10 space-y-4">
            {VISUAL_ARTIFACTS.map((artifact) => (
              <div key={artifact.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-100">
                    {artifact.name}
                  </div>
                  <Badge variant="outline" className="rounded-full border-white/20 bg-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.26em] text-white/80">
                    Online
                  </Badge>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-300/85">{artifact.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default VisualRelayTab;
