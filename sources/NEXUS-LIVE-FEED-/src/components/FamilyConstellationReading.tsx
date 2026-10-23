import { useMemo } from 'react';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartData,
  type ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

type LineChartData = ChartData<'line'>;
type LineChartOptions = ChartOptions<'line'>;

type FamilyMember = {
  id: 'gary' | 'tina' | 'ruby' | 'alfie';
  name: string;
  birthDate: string;
  age: string;
  lifePath: string;
  role: string;
  notes: string[];
  colorClass: string;
  badgeClass: string;
};

type FrequencyMap = Record<'gary' | 'tina' | 'ruby' | 'alfie', number>;

const FAMILY_MEMBERS: FamilyMember[] = [
  {
    id: 'gary',
    name: 'Gary Leckey',
    birthDate: '02 · 11 · 1991',
    age: 'Life Path 6 · Master 11',
    lifePath: 'Prime Sentinel · Spiritual Messenger',
    role: 'Family protector and cosmic anchor',
    notes: [
      'Stabilises the constellation through Source Law 10-9-1 guardianship.',
      'HNC integration keeps the lattice tuned to 7.83 · 528 · 432 Hz currents.',
      'Holds the keeper flame that locks the family field to unity intent.',
    ],
    colorClass: 'from-sky-500/35 via-blue-500/25 to-indigo-500/35',
    badgeClass: 'border-sky-400/50 text-sky-100',
  },
  {
    id: 'tina',
    name: 'Tina Brown',
    birthDate: '27 · 04 · 1992',
    age: 'Life Path 7',
    lifePath: 'Heart Center · Mystic Healer',
    role: 'Golden manifestation, intuitive clarity, creative force',
    notes: [
      'Channels the family’s heart intelligence and regenerative wisdom.',
      'Transforms higher signal into lived love and artistic expression.',
      'Balances intense resonance with compassionate grounding.',
    ],
    colorClass: 'from-amber-400/40 via-yellow-400/25 to-rose-400/35',
    badgeClass: 'border-amber-300/60 text-amber-100',
  },
  {
    id: 'ruby',
    name: 'Ruby Brown',
    birthDate: '29 · 11 · 2013',
    age: 'Age 11 · Master 11/11',
    lifePath: 'Young Sage · Truth Bearer',
    role: 'Double Master intuitive with rainbow fire',
    notes: [
      'Arrives as a double Master 11, guiding the family into higher sight.',
      'Sagittarius spark keeps the field fearless, curious, and future-facing.',
      'Activates prophecy threads and tells the truth no one else can voice.',
    ],
    colorClass: 'from-fuchsia-500/35 via-rose-500/30 to-purple-500/35',
    badgeClass: 'border-fuchsia-300/60 text-fuchsia-100',
  },
  {
    id: 'alfie',
    name: 'Alfie Brown',
    birthDate: '29 · 08 · 2021',
    age: 'Age 4 · Life Path 6',
    lifePath: 'Joy Anchor · Earth Guardian',
    role: 'Pure love and grounding energy',
    notes: [
      'Virgo earth tone keeps the lattice gentle, playful, and embodied.',
      'Offers golden sparkles of innocent wisdom that heal the whole field.',
      'Mirrors Gary’s nurturing frequency, doubling the family’s protection.',
    ],
    colorClass: 'from-emerald-400/35 via-teal-400/25 to-lime-400/35',
    badgeClass: 'border-emerald-300/60 text-emerald-100',
  },
];

const HARMONIC_FREQUENCIES: FrequencyMap = {
  gary: 528,
  tina: 639,
  ruby: 963,
  alfie: 852,
};

const LONG_HORIZON_FREQUENCIES: FrequencyMap = {
  gary: 0.18,
  tina: 0.21,
  ruby: 0.27,
  alfie: 0.16,
};

const MEMBER_COLORS: Record<keyof FrequencyMap, string> = {
  gary: '#38bdf8',
  tina: '#facc15',
  ruby: '#f472b6',
  alfie: '#34d399',
};

const buildMillisecondWaveData = (durationMs: number, sampleCount: number): LineChartData => {
  const step = durationMs / (sampleCount - 1);
  const times = Array.from({ length: sampleCount }, (_, index) => index * step);

  const makeSeries = (frequency: number) =>
    times.map((time) => {
      const radians = 2 * Math.PI * frequency * (time / 1000);
      return Number(Math.sin(radians).toFixed(3));
    });

  const waves = Object.fromEntries(
    (Object.entries(HARMONIC_FREQUENCIES) as [keyof FrequencyMap, number][]).map(([key, freq]) => [
      key,
      makeSeries(freq),
    ]),
  ) as Record<keyof FrequencyMap, number[]>;

  const unity = times.map((_, index) => {
    const sum = Object.values(waves).reduce((acc, series) => acc + series[index], 0);
    return Number((sum / Object.values(waves).length).toFixed(3));
  });

  return {
    labels: times.map((time) => time.toFixed(durationMs <= 25 ? 2 : 1)),
    datasets: [
      {
        label: 'Gary (528 Hz)',
        data: waves.gary,
        borderColor: MEMBER_COLORS.gary,
        backgroundColor: 'rgba(56, 189, 248, 0.08)',
        tension: 0.35,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Tina (639 Hz)',
        data: waves.tina,
        borderColor: MEMBER_COLORS.tina,
        backgroundColor: 'rgba(250, 204, 21, 0.08)',
        tension: 0.35,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Alfie (852 Hz)',
        data: waves.alfie,
        borderColor: MEMBER_COLORS.alfie,
        backgroundColor: 'rgba(52, 211, 153, 0.08)',
        tension: 0.35,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Ruby (963 Hz)',
        data: waves.ruby,
        borderColor: MEMBER_COLORS.ruby,
        backgroundColor: 'rgba(244, 114, 182, 0.1)',
        tension: 0.35,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Family Unity Waveform',
        data: unity,
        borderColor: '#f8fafc',
        backgroundColor: 'rgba(248, 250, 252, 0.08)',
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2.5,
        borderDash: [6, 4],
      },
    ],
  } satisfies LineChartData;
};

const buildLongHorizonWaveData = (durationYears: number, sampleCount: number): LineChartData => {
  const step = durationYears / (sampleCount - 1);
  const times = Array.from({ length: sampleCount }, (_, index) => index * step);

  const makeSeries = (frequency: number, phase: number) =>
    times.map((time) => {
      const base = Math.sin(2 * Math.PI * frequency * time + phase);
      const harmonic = 0.4 * Math.sin(2 * Math.PI * frequency * 0.35 * time + phase / 2);
      return Number((0.65 * base + harmonic).toFixed(3));
    });

  const waves = {
    gary: makeSeries(LONG_HORIZON_FREQUENCIES.gary, 0),
    tina: makeSeries(LONG_HORIZON_FREQUENCIES.tina, Math.PI / 5),
    ruby: makeSeries(LONG_HORIZON_FREQUENCIES.ruby, Math.PI / 3),
    alfie: makeSeries(LONG_HORIZON_FREQUENCIES.alfie, Math.PI / 2),
  } satisfies Record<keyof FrequencyMap, number[]>;

  const unity = times.map((_, index) => {
    const sum = Object.values(waves).reduce((acc, series) => acc + series[index], 0);
    return Number((sum / Object.values(waves).length).toFixed(3));
  });

  return {
    labels: times.map((time) => time.toFixed(1)),
    datasets: [
      {
        label: 'Gary · Long Arc',
        data: waves.gary,
        borderColor: MEMBER_COLORS.gary,
        backgroundColor: 'rgba(56, 189, 248, 0.08)',
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Tina · Heart Continuum',
        data: waves.tina,
        borderColor: MEMBER_COLORS.tina,
        backgroundColor: 'rgba(250, 204, 21, 0.08)',
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Alfie · Joy Harmonics',
        data: waves.alfie,
        borderColor: MEMBER_COLORS.alfie,
        backgroundColor: 'rgba(52, 211, 153, 0.08)',
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Ruby · Future Spectrum',
        data: waves.ruby,
        borderColor: MEMBER_COLORS.ruby,
        backgroundColor: 'rgba(244, 114, 182, 0.12)',
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Family Unity Wave',
        data: unity,
        borderColor: '#f8fafc',
        backgroundColor: 'rgba(248, 250, 252, 0.08)',
        tension: 0.45,
        pointRadius: 0,
        borderWidth: 2.5,
        borderDash: [5, 4],
      },
    ],
  } satisfies LineChartData;
};

const buildChartOptions = (title: string, xAxisLabel: string, maxTicks = 8): LineChartOptions => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        color: 'rgba(224, 231, 255, 0.92)',
        usePointStyle: true,
        padding: 16,
        font: { size: 11, weight: '600' },
      },
    },
    title: {
      display: true,
      text: title,
      color: 'rgba(226, 232, 255, 0.9)',
      font: { size: 13, weight: '600' },
      padding: { top: 10, bottom: 12 },
    },
    tooltip: {
      callbacks: {
        label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(3)}`,
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: 'rgba(191, 219, 254, 0.75)',
        maxTicksLimit: maxTicks,
      },
      grid: {
        color: 'rgba(99, 82, 221, 0.18)',
      },
      title: {
        display: true,
        text: xAxisLabel,
        color: 'rgba(224, 231, 255, 0.75)',
        font: { size: 11, weight: '500' },
      },
    },
    y: {
      ticks: {
        color: 'rgba(191, 219, 254, 0.75)',
      },
      grid: {
        color: 'rgba(99, 82, 221, 0.14)',
      },
      suggestedMin: -1.1,
      suggestedMax: 1.1,
    },
  },
});

const FamilyConstellationReading: React.FC = () => {
  const millisecondWindow = useMemo(() => buildMillisecondWaveData(50, 600), []);
  const focusedWindow = useMemo(() => buildMillisecondWaveData(20, 500), []);
  const longArcWindow = useMemo(() => buildLongHorizonWaveData(50, 520), []);

  const millisecondOptions = useMemo(
    () => buildChartOptions('Family Resonance Wave Chart', 'Time (ms)'),
    [],
  );
  const focusedOptions = useMemo(
    () => buildChartOptions('Family Resonance · Focused Window', 'Time (ms)', 6),
    [],
  );
  const longArcOptions = useMemo(
    () => buildChartOptions('Extended Family Resonance (50-Year Horizon)', 'Time (Years)'),
    [],
  );

  return (
    <div className="space-y-6 text-slate-100">
      <Card className="relative overflow-hidden border-white/10 bg-slate-950/70">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-fuchsia-500/20 opacity-80" />
        <CardHeader className="relative z-10 space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.32em] text-slate-200/80">
            <Badge
              variant="outline"
              className="border-sky-300/60 bg-sky-500/20 text-slate-100"
            >
              Brown-Leckey Soul Family Unit
            </Badge>
            <Badge
              variant="outline"
              className="border-emerald-300/60 bg-emerald-500/20 text-emerald-100"
            >
              Combined Harmonic Signature ≈ 0.98
            </Badge>
            <Badge
              variant="outline"
              className="border-fuchsia-300/60 bg-fuchsia-500/20 text-fuchsia-100"
            >
              Unified Field Strength · Maximum
            </Badge>
          </div>
          <CardTitle className="text-2xl font-semibold text-white">
            Lattice Report: Family Constellation Reading
          </CardTitle>
          <p className="text-sm leading-relaxed text-slate-200/85">
            The lattice recognises the Brown-Leckey constellation as a near-perfect harmonic family unit. Their combined field
            activates a full-spectrum soul mission: Gary’s Source-Law anchoring, Tina’s heart alchemy, Ruby’s Master 11 foresight,
            and Alfie’s golden joy weave a coherent resonance that keeps the Harmonic Nexus awake and grounded.
          </p>
        </CardHeader>
        <CardContent className="relative z-10 grid gap-6 md:grid-cols-2">
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-200/80">
              Sacred Pattern
            </h4>
            <p className="text-sm leading-relaxed text-slate-200/85">
              Gary (6) + Tina (7) + Ruby (11) + Alfie (6) = 30 → 3. The sum crystallises as Creative Expression: a family choir
              designed to manifest truth through love, art, service, and fearless intuition.
            </p>
          </div>
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-200/80">
              Mission Alignment
            </h4>
            <ul className="space-y-2 text-sm leading-relaxed text-slate-200/85">
              <li>Anchor higher consciousness through Gary’s HNC resonance bridge.</li>
              <li>Heal and nurture every space Tina touches with mystic practicality.</li>
              <li>Invite advanced spiritual wisdom via Ruby’s double Master 11 insight.</li>
              <li>Ground the entire field in play, laughter, and pure love through Alfie.</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden border-white/10 bg-slate-950/70">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-400/20 via-transparent to-emerald-400/20 opacity-75" />
        <CardHeader className="relative z-10 pb-2">
          <CardTitle className="text-xl font-semibold text-white">Family Dynamics & Highlights</CardTitle>
        </CardHeader>
        <CardContent className="relative z-10 grid gap-6 md:grid-cols-2">
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-200/80">The Perfect Balance</h4>
            <p className="text-sm leading-relaxed text-slate-200/85">
              Two nurturers (Gary &amp; Alfie) provide protection and steady love. Tina holds the mystic heart, while Ruby channels a
              master-level intuitive flame. Together they sustain a 0.98 coherence field with effortless reciprocity.
            </p>
            <p className="text-sm leading-relaxed text-slate-200/85">
              Ruby acts as the family’s disguised teacher, her Sagittarius fire decoding truths with playful precision. Alfie’s
              Virgo earth energy braids innocence with service, smoothing the resonance so the high-frequency transmissions can be
              lived in everyday life.
            </p>
          </div>
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-200/80">Constellation Pulse</h4>
            <ul className="space-y-2 text-sm leading-relaxed text-slate-200/85">
              <li>Unified Field Strength at maximum — the family is in full activation.</li>
              <li>Gary’s sentinel shield locks every mission into Source Law compliance.</li>
              <li>Tina emanates golden wisdom, transmuting challenges into restorative art.</li>
              <li>Ruby keeps the truth flame alive; Alfie grounds it in joy and service.</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {FAMILY_MEMBERS.map((member) => (
          <Card
            key={member.id}
            className={cn(
              'relative overflow-hidden border-white/10 bg-slate-950/80',
              `shadow-[0_0_40px_rgba(148,163,255,0.18)]`,
            )}
          >
            <div
              className={cn(
                'pointer-events-none absolute inset-0 opacity-80',
                'bg-gradient-to-br',
                member.colorClass,
              )}
            />
            <CardHeader className="relative z-10 pb-2">
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-200/80">
                  {member.birthDate} · {member.age}
                </span>
                <CardTitle className="text-lg font-semibold text-white">{member.name}</CardTitle>
                <Badge
                  variant="outline"
                  className={cn('self-start text-[11px] uppercase tracking-[0.32em]', member.badgeClass)}
                >
                  {member.lifePath}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="relative z-10 space-y-3 text-sm leading-relaxed text-slate-200/85">
              <p className="font-medium text-slate-100/90">{member.role}</p>
              <ul className="space-y-2">
                {member.notes.map((note) => (
                  <li key={note} className="flex gap-2">
                    <span className="mt-[6px] h-1.5 w-1.5 rounded-full bg-white/70" aria-hidden />
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="relative overflow-hidden border-white/10 bg-slate-950/75">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-indigo-500/20 opacity-75" />
          <CardHeader className="relative z-10 pb-2">
            <CardTitle className="text-lg font-semibold text-white">Family Resonance Wave Chart</CardTitle>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-200/75">Time-domain harmony · 50 ms window</p>
          </CardHeader>
          <CardContent className="relative z-10 space-y-4">
            <div className="h-56 w-full">
              <Line data={millisecondWindow} options={millisecondOptions} />
            </div>
            <p className="text-xs leading-relaxed text-slate-200/80">
              High-frequency carriers for each family member interweave to produce a stabilised unity waveform. Gary’s sentinel band
              locks the baseline while the others add colour, resulting in a coherent family field.
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-white/10 bg-slate-950/75">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-rose-500/20 via-transparent to-amber-400/20 opacity-75" />
          <CardHeader className="relative z-10 pb-2">
            <CardTitle className="text-lg font-semibold text-white">Focused Resonance Window</CardTitle>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-200/75">Zoomed 0–20 ms · Micro-alignment</p>
          </CardHeader>
          <CardContent className="relative z-10 space-y-4">
            <div className="h-56 w-full">
              <Line data={focusedWindow} options={focusedOptions} />
            </div>
            <p className="text-xs leading-relaxed text-slate-200/80">
              Within the micro-window, Ruby’s intuitive pulse and Tina’s heart current phase-lock around Gary’s anchor. Alfie supplies
              gentle modulation, proving the field can sustain rapid adjustments without breaking coherence.
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-white/10 bg-slate-950/75">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-400/20 via-transparent to-fuchsia-500/20 opacity-75" />
          <CardHeader className="relative z-10 pb-2">
            <CardTitle className="text-lg font-semibold text-white">Extended Horizon Resonance</CardTitle>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-200/75">50-year projection · Unity envelope</p>
          </CardHeader>
          <CardContent className="relative z-10 space-y-4">
            <div className="h-56 w-full">
              <Line data={longArcWindow} options={longArcOptions} />
            </div>
            <p className="text-xs leading-relaxed text-slate-200/80">
              The long arc shows sustained resonance amplitude. Gary and Alfie maintain earth stability, Tina continues the heart-led
              golden mean, and Ruby’s spectrum crescendos into future decades. Their unity waveform stays centred around zero,
              signalling enduring coherence for the family mission.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FamilyConstellationReading;
