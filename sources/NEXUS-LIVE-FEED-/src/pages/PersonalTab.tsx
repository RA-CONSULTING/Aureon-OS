import { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';

const metrics = [
  { id: 'hrv', label: 'Heart Rate Variability', value: '74 ms', status: 'Aligned', detail: 'Breath cadence synchronized with Nexus rhythm.' },
  { id: 'frequency', label: 'Core Frequency', value: '432 Hz', status: 'Attuned', detail: 'Personal resonance anchored to Golden Mean.' },
  { id: 'coherence', label: 'Coherence Index', value: '0.88', status: 'Radiant', detail: 'Consistent unity field engagement across sessions.' },
  { id: 'vagus', label: 'Vagus Flow', value: 'Harmonic 3', status: 'Flowing', detail: 'Parasympathetic response optimized through daily ritual.' },
] as const;

const checkIns = [
  { id: 'dawn', title: 'Dawn Alignment', note: 'Gratitude + sun salutation recorded.', tone: 'Sky Ember' },
  { id: 'midday', title: 'Midday Resonance', note: 'Shared meditation with global cohort.', tone: 'Emerald Pulse' },
  { id: 'evening', title: 'Evening Reflection', note: 'Journaled insights from guardian dreamwork.', tone: 'Violet Echo' },
] as const;

const tools = [
  {
    id: 'meditation',
    title: 'Meditation Mode',
    description: 'Immersive guided sequences tuned to your resonance signature.',
    cta: 'Enter Meditation Mode',
  },
  {
    id: 'frequency-generator',
    title: 'Frequency Generator',
    description: 'Compose harmonic blends, generate binaural alignments, and broadcast healing waves.',
    cta: 'Launch Generator',
  },
  {
    id: 'sacred-geometry',
    title: 'Sacred Geometry Viewer',
    description: 'Explore living mandalas, rotate merkaba forms, and anchor new templates.',
    cta: 'Open Viewer',
  },
  {
    id: 'journal',
    title: 'Resonance Journal',
    description: 'Capture visions, synchronicities, and coherence milestones.',
    cta: 'Write Entry',
  },
] as const;

const interactions = [
  {
    title: 'Tap Stat Card',
    description: 'Expands into detail graphs, breathing prescriptions, and ritual tools tuned to that metric.',
  },
  {
    title: 'Tap Tool',
    description: 'Launches immersive interfaces—meditation studio, frequency console, journal editor.',
  },
  {
    title: 'Tap Edit Profile',
    description: 'Opens resonance profile editor with name, birth alignments, guardianship commitments.',
  },
] as const;

const resonanceProfile = [
  { label: 'Resonance Name', value: 'Auric Pathfinder' },
  { label: 'Birth Alignment', value: 'Scorpio Sun · Leo Moon · Aquarius Rising' },
  { label: 'Guardian Seat', value: 'North Atlantic Choir' },
  { label: 'Mission Cycle', value: 'Cycle 07 · Day 144' },
] as const;

const PersonalTab = () => {
  const { user } = useAuth();
  const greeting = useMemo(() => {
    if (!user) return 'Welcome Guardian';
    return `Welcome ${user.name}`;
  }, [user]);

  return (
    <div className="space-y-12">
      <section className="grid gap-6 lg:grid-cols-[1.4fr,0.8fr]">
        <Card className="border-white/10 bg-[rgba(12,20,44,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-emerald-500/20 text-emerald-100">Personal Dashboard</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">{greeting}</CardTitle>
            <p className="text-sm text-[#c8d4ff]/80">
              Maintain your resonance field. Review metrics, unlock tools, and honor daily coherence commitments.
            </p>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {metrics.map((metric) => (
              <div key={metric.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">
                  <span>{metric.label}</span>
                  <span className="text-emerald-200">{metric.status}</span>
                </div>
                <div className="mt-3 text-3xl font-semibold text-white">{metric.value}</div>
                <p className="mt-3 text-xs text-[#c8d4ff]/80">{metric.detail}</p>
                <Button className="mt-4 w-full rounded-full bg-sky-500/80 text-[0.65rem] uppercase tracking-[0.35em] text-white hover:bg-sky-400/90">
                  Tap Stat Card
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(12,20,44,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-purple-500/20 text-purple-100">Resonance Profile</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Identity Signature</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#c8d4ff]/80">
            {resonanceProfile.map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 p-3">
                <span className="text-[0.6rem] uppercase tracking-[0.35em] text-[#d0dcff]/70">{row.label}</span>
                <span className="text-right text-sm text-white">{row.value}</span>
              </div>
            ))}
            <Button className="mt-2 w-full rounded-full bg-emerald-500/80 text-xs uppercase tracking-[0.4em] text-white hover:bg-emerald-400/90">
              Tap Edit Profile
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {tools.map((tool) => (
          <Card key={tool.id} className="border-white/10 bg-[rgba(8,18,38,0.76)] backdrop-blur">
            <CardHeader>
              <Badge className="w-max bg-sky-500/20 text-sky-100">Tool</Badge>
              <CardTitle className="text-sm uppercase tracking-[0.3em]">{tool.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-[#c8d4ff]/80">
              <p>{tool.description}</p>
              <Button className="w-full rounded-full bg-purple-500/80 text-[0.65rem] uppercase tracking-[0.35em] text-white hover:bg-purple-400/90">
                {tool.cta}
              </Button>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr,0.7fr]">
        <Card className="border-white/10 bg-[rgba(8,18,38,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-amber-500/20 text-amber-100">Daily Check-Ins</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Ritual Log</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {checkIns.map((entry) => (
              <div key={entry.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">
                  <span>{entry.title}</span>
                  <span className="text-emerald-200">{entry.tone}</span>
                </div>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{entry.note}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(8,18,38,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">Every Tap</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Interaction Flow</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {interactions.map((interaction) => (
              <div key={interaction.title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-xs uppercase tracking-[0.4em] text-[#d0dcff]/85">{interaction.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{interaction.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default PersonalTab;
