import { useEffect, useMemo, useState } from 'react';
import { useId } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useLiveNexusData } from '@/contexts/LiveNexusDataContext';
import type {
  BioSignalMetric,
  BioSignalTone,
  BioStreamStatus,
  RealtimeChartCollection,
  RealtimeChartPoint,
} from '@/hooks/useResampledNexusData';
import { cn } from '@/lib/utils';
import { earthToneGroups, realtimeSpectrumOrder } from '@/theme/palette';

type HistoryPoint = {
  timestamp: number;
  value: number;
};

type SignalDescriptor = {
  id: string;
  label: string;
  unit: string;
  value: number;
  tone: BioSignalTone;
  targetRange: [number, number];
  hint?: string;
  reading?: string;
};

type ChartConfig = {
  key: keyof RealtimeChartCollection;
  label: string;
  description: string;
  unit?: string;
  background: string;
  accent: string;
  colors: [string, string, string];
  valueTransform?: (value: number) => number;
  valueFormatter?: (value: number, unit?: string) => string;
};

const HISTORY_WINDOW_MS = 5 * 60 * 1000;
const MAX_HISTORY_POINTS = 360;

const toneLabels: Record<BioSignalTone, string> = {
  stable: 'Stable',
  watch: 'Watch',
  alert: 'Alert',
};

const toneBadgeStyles: Record<BioSignalTone, string> = {
  stable: 'border-emerald-400/60 bg-emerald-400/10 text-emerald-200',
  watch: 'border-amber-400/60 bg-amber-400/10 text-amber-200',
  alert: 'border-rose-500/60 bg-rose-500/10 text-rose-200',
};

const sectionBadgeStyles: Record<'info' | BioSignalTone, string> = {
  info: 'border-cyan-300/50 bg-cyan-400/10 text-cyan-100',
  stable: toneBadgeStyles.stable,
  watch: toneBadgeStyles.watch,
  alert: toneBadgeStyles.alert,
};

const signalThemes: Record<
  string,
  { background: string; accent: string; colors: [string, string, string] }
> = {
  cardiac: {
    background: 'from-[#7C3AED]/25 via-[#5B8DFF]/15 to-transparent',
    accent: 'text-[#B7A5FF]',
    colors: earthToneGroups.vitality,
  },
  neural: {
    background: 'from-[#5A4BFF]/25 via-[#6D4BFF]/15 to-transparent',
    accent: 'text-[#DADFFF]',
    colors: earthToneGroups.dusk,
  },
  aura: {
    background: 'from-[#3FA3FF]/25 via-[#4FB6FF]/15 to-transparent',
    accent: 'text-[#9AD7FF]',
    colors: earthToneGroups.horizon,
  },
  respiration: {
    background: 'from-[#4FB6FF]/25 via-[#57E3FF]/15 to-transparent',
    accent: 'text-[#B8F0FF]',
    colors: earthToneGroups.resonance,
  },
  hydration: {
    background: 'from-[#9F5FFF]/25 via-[#B7A5FF]/15 to-transparent',
    accent: 'text-[#DADFFF]',
    colors: earthToneGroups.flow,
  },
  chrono: {
    background: 'from-[#5B8DFF]/25 via-[#7C3AED]/15 to-transparent',
    accent: 'text-[#E0EDFF]',
    colors: earthToneGroups.ember,
  },
};

const defaultTheme = {
  background: 'from-[#5A4BFF]/20 via-[#6D4BFF]/12 to-transparent',
  accent: 'text-[#A7B5FF]',
  colors: earthToneGroups.dusk,
};

const planetaryCharts: ChartConfig[] = [
  {
    key: 'magnetometer',
    label: 'Magnetometer Field Strength',
    description: 'Flux density captured along the anchor-node lattice.',
    unit: 'µT',
    background: 'from-[#6D4BFF]/22 via-[#7C3AED]/12 to-transparent',
    accent: 'text-[#B7A5FF]',
    colors: realtimeSpectrumOrder[0],
  },
  {
    key: 'schumann',
    label: 'Schumann Resonance Envelope',
    description: 'Planetary heartbeat coupling amplitude across harmonics.',
    unit: 'Hz',
    background: 'from-[#3FA3FF]/22 via-[#4FB6FF]/12 to-transparent',
    accent: 'text-[#9AD7FF]',
    colors: realtimeSpectrumOrder[1],
    valueTransform: (value) => value,
  },
  {
    key: 'coherence',
    label: 'Unified Coherence Index',
    description: 'Composite field coherence derived from neural, cardiac, and Schumann alignment.',
    unit: '%',
    background: 'from-[#5B8DFF]/25 via-[#9F5FFF]/12 to-transparent',
    accent: 'text-[#DADFFF]',
    colors: realtimeSpectrumOrder[2],
    valueTransform: (value) => value * 100,
    valueFormatter: (value, unit) => `${value.toFixed(1)}${unit ? ` ${unit}` : ''}`,
  },
  {
    key: 'planetaryResonance',
    label: 'Planetary Resonance Harmony',
    description: 'Stability ratio across the planetary resonance vectors.',
    unit: '%',
    background: 'from-[#5A4BFF]/25 via-[#6D4BFF]/12 to-transparent',
    accent: 'text-[#A7B5FF]',
    colors: realtimeSpectrumOrder[3],
    valueTransform: (value) => value * 100,
    valueFormatter: (value, unit) => `${value.toFixed(1)}${unit ? ` ${unit}` : ''}`,
  },
];

const aggregateTone = (signals: SignalDescriptor[]): BioSignalTone => {
  if (signals.some((signal) => signal.tone === 'alert')) {
    return 'alert';
  }
  if (signals.some((signal) => signal.tone === 'watch')) {
    return 'watch';
  }
  return 'stable';
};

const relativeTime = (timestamp?: number | null) => {
  if (!timestamp) {
    return '—';
  }

  const deltaMs = Date.now() - timestamp;
  if (deltaMs < 1000) {
    return 'just now';
  }

  const totalSeconds = Math.max(0, Math.round(deltaMs / 1000));
  if (totalSeconds < 60) {
    return `${totalSeconds}s ago`;
  }

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${seconds}s ago`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m ago`;
};

const formatValue = (value: number, unit?: string) => {
  const magnitude = Math.abs(value);
  const digits = magnitude >= 100 ? 0 : magnitude >= 10 ? 1 : 2;
  const formatted = Number.isFinite(value) ? value.toFixed(digits) : '—';
  return `${formatted}${unit ? ` ${unit}` : ''}`;
};

const formatChange = (change: number | null | undefined, unit?: string) => {
  if (change === null || change === undefined || Number.isNaN(change)) {
    return '—';
  }

  if (Math.abs(change) < 0.001) {
    return '0';
  }

  const sign = change >= 0 ? '▲' : '▼';
  const magnitude = Math.abs(change);
  const digits = magnitude >= 100 ? 0 : magnitude >= 10 ? 1 : 2;
  return `${sign} ${magnitude.toFixed(digits)}${unit ? ` ${unit}` : ''}`;
};

const computeStats = (points: HistoryPoint[]) => {
  if (!points.length) {
    return { min: 0, max: 0, average: 0 };
  }

  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;

  return { min, max, average };
};

const computeDelta = (points: HistoryPoint[]) => {
  if (points.length < 2) {
    return null;
  }

  const latest = points[points.length - 1];
  const previous = points[points.length - 2];
  return latest.value - previous.value;
};

const MiniChart = ({
  points,
  colors,
  height = 120,
  showPoints = true,
  strokeWidth = 1.6,
}: {
  points: HistoryPoint[];
  colors: [string, string, string];
  height?: number;
  showPoints?: boolean;
  strokeWidth?: number;
}) => {
  const gradientId = useId();

  if (!points.length) {
    return (
      <div className="flex h-[120px] items-center justify-center rounded-2xl border border-white/10 bg-slate-950/60 text-sm text-slate-400">
        Awaiting telemetry…
      </div>
    );
  }

  const trimmed = points.slice(-MAX_HISTORY_POINTS);
  const values = trimmed.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const normalized = trimmed.map((point, index) => {
    const x = trimmed.length > 1 ? (index / (trimmed.length - 1)) * 100 : 100;
    const y = trimmed.length > 1 ? 100 - ((point.value - min) / range) * 100 : 50;
    return { x, y };
  });

  const polyline = normalized.map(({ x, y }) => `${x},${y}`).join(' ');
  const areaPath =
    normalized.length > 1
      ? [
          `M ${normalized[0].x},${normalized[0].y}`,
          ...normalized.slice(1).map(({ x, y }) => `L ${x},${y}`),
          `L ${normalized[normalized.length - 1].x},100`,
          `L ${normalized[0].x},100`,
          'Z',
        ].join(' ')
      : null;

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="w-full overflow-visible"
      style={{ height }}
    >
      <defs>
        <linearGradient id={`${gradientId}-stroke`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={colors[0]} />
          <stop offset="50%" stopColor={colors[1]} />
          <stop offset="100%" stopColor={colors[2]} />
        </linearGradient>
        <linearGradient id={`${gradientId}-fill`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={colors[0]} stopOpacity={0.3} />
          <stop offset="100%" stopColor={colors[2]} stopOpacity={0.04} />
        </linearGradient>
      </defs>
      {areaPath ? (
        <path d={areaPath} fill={`url(#${gradientId}-fill)`} stroke="none" opacity={0.85} />
      ) : null}
      {polyline ? (
        <polyline
          points={polyline}
          fill="none"
          stroke={`url(#${gradientId}-stroke)`}
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ) : null}
      {showPoints && normalized.length <= 120
        ? normalized.map(({ x, y }, index) => (
            <circle
              // eslint-disable-next-line react/no-array-index-key
              key={index}
              cx={x}
              cy={y}
              r={1.6}
              fill={colors[0]}
              stroke={colors[2]}
              strokeWidth={0.5}
            />
          ))
        : null}
    </svg>
  );
};

const Section = ({
  title,
  description,
  badge,
  badgeTone = 'info',
  children,
}: {
  title: string;
  description?: string;
  badge?: string;
  badgeTone?: 'info' | BioSignalTone;
  children: React.ReactNode;
}) => (
  <Card className="group relative overflow-hidden border-[rgba(99,82,221,0.22)] bg-[#0b1230]/75 text-[#E8F1FF] shadow-[0_0_45px_rgba(120,76,255,0.26)]">
    <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/15 via-transparent to-fuchsia-500/15 opacity-60 transition duration-700 group-hover:opacity-80" />
    <div className="relative z-10">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <CardTitle className="text-xl font-semibold text-white">{title}</CardTitle>
            {description ? (
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300/85">{description}</p>
            ) : null}
          </div>
          {badge ? (
            <Badge
              variant="outline"
              className={cn(
                'rounded-full px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.35em]',
                sectionBadgeStyles[badgeTone]
              )}
            >
              {badge}
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </div>
  </Card>
);

const BioSignalCard = ({ signal, history }: { signal: SignalDescriptor; history: HistoryPoint[] }) => {
  const theme = signalThemes[signal.id] ?? defaultTheme;
  const delta = computeDelta(history);
  const stats = computeStats(history);
  const lastTimestamp = history.at(-1)?.timestamp ?? null;

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-5 shadow-[0_0_30px_rgba(14,165,233,0.25)] backdrop-blur',
        `bg-gradient-to-br ${theme.background}`
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.12),_transparent_60%)]" />
      <div className="relative z-10 flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h4 className={cn('text-sm font-semibold uppercase tracking-[0.24em]', theme.accent)}>
              {signal.label}
            </h4>
            {signal.reading ? (
              <p className="mt-1 text-xs text-slate-200/80">{signal.reading}</p>
            ) : null}
            {signal.hint ? (
              <p className="mt-1 text-xs leading-relaxed text-slate-300/75">{signal.hint}</p>
            ) : null}
          </div>
          <Badge
            variant="outline"
            className={cn('rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em]', toneBadgeStyles[signal.tone])}
          >
            {toneLabels[signal.tone]}
          </Badge>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="text-3xl font-semibold text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.35)]">
            {formatValue(signal.value, signal.unit)}
          </div>
          <div className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-200/80">
            {formatChange(delta, signal.unit)}
          </div>
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] uppercase tracking-[0.2em] text-slate-200/70">
          <span>
            Target {signal.targetRange[0]}–{signal.targetRange[1]} {signal.unit}
          </span>
          <span>
            Min {formatValue(stats.min, signal.unit)} · Max {formatValue(stats.max, signal.unit)}
          </span>
          <span>Updated {relativeTime(lastTimestamp)}</span>
        </div>

        <MiniChart points={history} colors={theme.colors} />
      </div>
    </div>
  );
};

const TelemetryPanel = ({ config, points }: { config: ChartConfig; points: RealtimeChartPoint[] }) => {
  const transform = config.valueTransform ?? ((value: number) => value);
  const transformedPoints: HistoryPoint[] = points
    .slice(-MAX_HISTORY_POINTS)
    .map((point) => ({ timestamp: point.timestamp, value: transform(point.value) }));

  const stats = computeStats(transformedPoints);
  const delta = computeDelta(transformedPoints);
  const latest = transformedPoints.at(-1);
  const formatter = config.valueFormatter ?? formatValue;

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-6 shadow-[0_0_35px_rgba(96,165,250,0.25)] backdrop-blur',
        `bg-gradient-to-br ${config.background}`
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.12),_transparent_60%)]" />
      <div className="relative z-10 flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h4 className={cn('text-sm font-semibold uppercase tracking-[0.24em]', config.accent)}>{config.label}</h4>
            <p className="mt-1 text-xs leading-relaxed text-slate-300/80">{config.description}</p>
          </div>
          <div className="text-right text-xs uppercase tracking-[0.24em] text-slate-300/70">
            <div>{latest ? formatter(latest.value, config.unit) : '—'}</div>
            <div className="mt-1 text-[10px] font-semibold">{formatChange(delta, config.unit)}</div>
            <div className="mt-1 text-[10px]">{relativeTime(latest?.timestamp)}</div>
          </div>
        </div>

        <MiniChart
          points={transformedPoints}
          colors={config.colors}
          height={180}
          showPoints={transformedPoints.length <= 200}
          strokeWidth={1.9}
        />

        <div className="grid gap-4 sm:grid-cols-3 text-[11px] uppercase tracking-[0.2em] text-slate-200/70">
          <div>
            <p className="text-slate-300/60">Min</p>
            <p className="mt-1 text-sm font-semibold text-white">{formatter(stats.min, config.unit)}</p>
          </div>
          <div>
            <p className="text-slate-300/60">Max</p>
            <p className="mt-1 text-sm font-semibold text-white">{formatter(stats.max, config.unit)}</p>
          </div>
          <div>
            <p className="text-slate-300/60">Average</p>
            <p className="mt-1 text-sm font-semibold text-white">{formatter(stats.average, config.unit)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const TemporalBiofieldScanTab: React.FC = () => {
  const { bioProfile, charts, quantumLink, schumannProtocol } = useLiveNexusData();
  const [history, setHistory] = useState<Record<string, HistoryPoint[]>>({});

  useEffect(() => {
    const now = Date.now();
    setHistory((previous) => {
      const next = { ...previous };

      const pushValue = (id: string, value: number) => {
        const existing = next[id] ?? [];
        const updated = [...existing, { timestamp: now, value }].filter(
          (point) => now - point.timestamp <= HISTORY_WINDOW_MS
        );
        next[id] = updated;
      };

      bioProfile.metrics.forEach((metric) => pushValue(metric.id, metric.value));
      bioProfile.streams.forEach((stream) => pushValue(stream.id, stream.value));

      return next;
    });
  }, [bioProfile.metrics, bioProfile.streams]);

  const metricSignals: SignalDescriptor[] = useMemo(
    () =>
      bioProfile.metrics.map((metric: BioSignalMetric) => ({
        id: metric.id,
        label: metric.label,
        unit: metric.unit,
        value: metric.value,
        tone: metric.tone,
        targetRange: metric.targetRange,
        hint: `Δ ${formatChange(metric.change, metric.unit)} · Adaptive window engaged`,
      })),
    [bioProfile.metrics]
  );

  const streamSignals: SignalDescriptor[] = useMemo(
    () =>
      bioProfile.streams.map((stream: BioStreamStatus) => ({
        id: stream.id,
        label: stream.label,
        unit: stream.unit,
        value: stream.value,
        tone: stream.status,
        targetRange: stream.targetRange,
        hint: stream.hint,
        reading: stream.reading,
      })),
    [bioProfile.streams]
  );

  const handshakeBadge = useMemo(() => {
    switch (quantumLink.handshakeState) {
      case 'entangled':
        return { label: 'Quantum Entangled', tone: 'stable' as const };
      case 'auto-dial':
        return { label: 'Auto-Dial Linking', tone: 'watch' as const };
      default:
        return { label: 'Link Idle', tone: 'watch' as const };
    }
  }, [quantumLink.handshakeState]);

  const planetaryTone = useMemo(() => {
    const latest = charts.coherence.at(-1)?.value ?? 0;
    if (latest >= 0.75) {
      return 'stable' as BioSignalTone;
    }
    if (latest >= 0.55) {
      return 'watch' as BioSignalTone;
    }
    return 'alert' as BioSignalTone;
  }, [charts.coherence]);

  const schumannSnapshots = schumannProtocol.monitoringSession.snapshots;
  const schumannHistory: HistoryPoint[] = useMemo(
    () =>
      schumannSnapshots.slice(-MAX_HISTORY_POINTS).map((snapshot) => ({
        timestamp: new Date(snapshot.timestamp).getTime(),
        value: snapshot.coherence * 100,
      })),
    [schumannSnapshots]
  );

  const schumannStats = useMemo(() => computeStats(schumannHistory), [schumannHistory]);

  return (
    <div className="space-y-8">
      <Section
        title="Temporal Anchor Signature"
        description="Live biometric imprint synchronized with the Prime Sentinel anchor stream."
        badge={handshakeBadge.label}
        badgeTone={handshakeBadge.tone}
      >
        <div className="grid gap-6 lg:grid-cols-[1.35fr,1fr]">
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-[0.4em] text-slate-300/70">Linked Operative</p>
              <h3 className="mt-2 text-2xl font-semibold text-white drop-shadow-[0_0_35px_rgba(255,255,255,0.35)]">
                {bioProfile.displayName}
              </h3>
              <p className="mt-1 text-sm text-slate-300/80">{bioProfile.timelineTag}</p>
            </div>
            <p className="text-sm leading-relaxed text-slate-200/85">{bioProfile.summary}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-[rgba(99,82,221,0.24)] bg-[#0b1230]/65 p-4">
                <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/60">Entangled Signature</p>
                <p className="mt-2 text-sm font-semibold text-white">{quantumLink.entangledSignature}</p>
                <p className="mt-1 text-xs text-slate-300/70">Temporal ID: {quantumLink.entangledTemporalId}</p>
              </div>
              <div className="rounded-xl border border-[rgba(99,82,221,0.24)] bg-[#0b1230]/65 p-4">
                <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/60">Observer Return Channel</p>
                <p className="mt-2 text-sm font-semibold text-white leading-relaxed">
                  {quantumLink.observerReturnChannel}
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-[rgba(99,82,221,0.24)] bg-[#0b1230]/65 p-4 text-center">
              <p className="text-[11px] uppercase tracking-[0.3em] text-slate-300/60">Observer Attunement</p>
              <p className="mt-3 text-3xl font-semibold text-white">{(quantumLink.observerAttunement * 100).toFixed(1)}%</p>
              <p className="mt-2 text-xs text-slate-300/70">Harmonic alignment with operative field</p>
            </div>
            <div className="rounded-xl border border-[rgba(99,82,221,0.24)] bg-[#0b1230]/65 p-4 text-center">
              <p className="text-[11px] uppercase tracking-[0.3em] text-slate-300/60">Last Quantum Pulse</p>
              <p className="mt-3 text-2xl font-semibold text-white">{relativeTime(quantumLink.lastPulse)}</p>
              <p className="mt-2 text-xs text-slate-300/70">Pulse stream time-synced to current window</p>
            </div>
          </div>
        </div>
      </Section>

      <Section
        title="Electrical & Neural Coherence"
        description="Neural, cardiac, and auric electrical metrics captured as live harmonics."
        badge={toneLabels[aggregateTone(metricSignals)]}
        badgeTone={aggregateTone(metricSignals)}
      >
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {metricSignals.map((signal) => (
            <BioSignalCard key={signal.id} signal={signal} history={history[signal.id] ?? []} />
          ))}
        </div>
      </Section>

      <Section
        title="Vital Stream Regulation"
        description="Breath, hydration, and chrono-stability telemetry anchoring the operator body."
        badge={toneLabels[aggregateTone(streamSignals)]}
        badgeTone={aggregateTone(streamSignals)}
      >
        <div className="grid gap-5 md:grid-cols-3">
          {streamSignals.map((signal) => (
            <BioSignalCard key={signal.id} signal={signal} history={history[signal.id] ?? []} />
          ))}
        </div>
      </Section>

      <Section
        title="Planetary & Quantum Coupling"
        description="Real-time resonance charts for the planetary heartbeat and coherence envelope."
        badge={toneLabels[planetaryTone]}
        badgeTone={planetaryTone}
      >
        <div className="grid gap-6 xl:grid-cols-2">
          {planetaryCharts.map((config) => (
            <TelemetryPanel key={config.key} config={config} points={charts[config.key] ?? []} />
          ))}
        </div>
      </Section>

      <Section
        title="Schumann Session Snapshot"
        description="Temporal coherence history from the active Schumann monitoring session."
        badge="Session Monitor"
      >
        <div className="grid gap-6 lg:grid-cols-[1.6fr,1fr]">
          <div className="rounded-2xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-6 shadow-[0_0_35px_rgba(59,130,246,0.25)] backdrop-blur">
            <h4 className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">
              Coherence Timeline
            </h4>
            <p className="mt-1 text-xs leading-relaxed text-slate-300/80">
              Session window {schumannProtocol.monitoringSession.startTime} →{' '}
              {schumannProtocol.monitoringSession.endTime}
            </p>
            <div className="mt-4">
              <MiniChart points={schumannHistory} colors={['#38bdf8', '#22d3ee', '#a855f7']} height={180} />
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-5">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/60">Session Duration</p>
              <p className="mt-2 text-2xl font-semibold text-white">
                {schumannProtocol.monitoringSession.durationMinutes} minutes
              </p>
              <p className="mt-1 text-xs text-slate-300/70">
                Snapshots captured: {schumannProtocol.monitoringSession.totalSnapshots}
              </p>
            </div>
            <div className="rounded-xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-5">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/60">Coherence Metrics</p>
              <ul className="mt-2 space-y-2 text-sm text-slate-200/80">
                <li>Average: {schumannStats.average.toFixed(1)}%</li>
                <li>Min: {schumannStats.min.toFixed(1)}% · Max: {schumannStats.max.toFixed(1)}%</li>
                <li>Anomaly rate: {(schumannProtocol.monitoringSession.trendAnalysis.anomalyRate * 100).toFixed(1)}%</li>
              </ul>
            </div>
            <div className="rounded-xl border border-[rgba(99,82,221,0.28)] bg-[#0c1533]/70 p-5">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/60">Witness Statement</p>
              <p className="mt-2 text-sm font-semibold text-white">{schumannProtocol.witness.name}</p>
              <p className="text-xs text-slate-300/70">{schumannProtocol.witness.title}</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-300/75">{schumannProtocol.witness.statement}</p>
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
};

export default TemporalBiofieldScanTab;

