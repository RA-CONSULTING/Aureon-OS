import { useMemo } from 'react';

import LiveStreamShowcase, { type LiveStreamDatum, type LiveStreamState } from '@/components/LiveStreamShowcase';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useLiveNexusData } from '@/contexts/LiveNexusDataContext';
import { SENSOR_STATE_NOTES, STREAM_METADATA, type SensorState } from '@/data/streamMetadata';
import type {
  RealtimeChartPoint,
  RealtimeMetric,
  SchumannAnomaly,
} from '@/hooks/useResampledNexusData';

const onboardingSteps = [
  { id: '01', title: 'Welcome to Nexus', status: 'Complete', detail: 'Signal attunement + mission brief.' },
  { id: '02', title: 'Field Calibration', status: 'Complete', detail: 'Bio-scan + coherence anchor set.' },
  { id: '03', title: 'Sensor Sync', status: 'Complete', detail: 'Link planetary nodes + resonance ID.' },
  { id: '04', title: 'Map Orientation', status: 'Complete', detail: 'Ley-line grid + coherence zones preview.' },
  { id: '05', title: 'Personal Profile', status: 'Complete', detail: 'HRV baseline, resonance signature, guardianship oath.' },
  { id: '06', title: 'Gesture Primer', status: 'Complete', detail: 'Tap, swipe, pinch, rotate, shake walkthrough.' },
  { id: '07', title: 'Live Launch', status: 'In Progress', detail: 'Final harmonic countdown + dashboard unlock.' },
] as const;

const quickActions = [
  { label: 'Stabilize Field', description: 'Launch harmonic rebalance macro.' },
  { label: 'Open Sacred Channel', description: 'Initiate real-time guardian bridge.' },
  { label: 'Mirror to Command', description: 'Share current scene to Nexus council.' },
] as const;

const dashboardInteractions = [
  {
    id: 'coherence-meter',
    title: 'Tap Coherence Meter',
    outcome: 'Expands into full-spectrum graph with coherence wave history + predictive arc.',
  },
  {
    id: 'quick-stat-card',
    title: 'Tap Quick Stat Card',
    outcome: 'Opens detail analytics, trend explanations, and recommended ritual responses.',
  },
  {
    id: 'live-feed-card',
    title: 'Tap Live Feed Card',
    outcome: 'Streams sensor transcript, field logs, and direct chat with ground stewards.',
  },
  {
    id: 'fab',
    title: 'Tap Floating Action Button',
    outcome: 'Summons quick actions: Stabilize, Signal Boost, Deploy Meditation Mode.',
  },
  {
    id: 'profile-avatar',
    title: 'Tap Profile Avatar',
    outcome: 'Transitions into personal dashboard for resonance maintenance.',
  },
  {
    id: 'notifications',
    title: 'Tap Notifications',
    outcome: 'Surfaces anomaly queue, coherence milestones, and sacred site invitations.',
  },
] as const;

const gestureControls = [
  { gesture: 'Tap', description: 'Select metrics, open detail cards, confirm rituals.' },
  { gesture: 'Swipe', description: 'Navigate screens, dismiss overlays, scroll live feed.' },
  { gesture: 'Pinch', description: 'Zoom on maps, expand coherence bands, scale sacred geometry.' },
  { gesture: 'Rotate', description: 'Shift 3D globe perspective and align ley-line overlays.' },
  { gesture: 'Shake', description: 'Trigger rapid anomaly acknowledgment + send reassurance ping.' },
] as const;

const processTree = [
  {
    label: 'App Launch',
    children: [
      {
        label: 'First-Time User',
        children: [
          { label: 'Onboarding (7 screens)', children: [{ label: 'Live Dashboard' }] },
        ],
      },
      { label: 'Returning User', children: [{ label: 'Live Dashboard (default)' }] },
    ],
  },
] as const;

const METRIC_TONES: Record<string, { label: string; className: string }> = {
  coherence: { label: 'Emerald Flux', className: 'bg-emerald-500/20 text-emerald-100' },
  resonance: { label: 'Skywave Mesh', className: 'bg-sky-500/20 text-sky-100' },
  chronicle: { label: 'Amber Relay', className: 'bg-amber-500/20 text-amber-100' },
  aureon: { label: 'Violet Pulse', className: 'bg-fuchsia-500/20 text-fuchsia-100' },
};

const DEFAULT_METRIC_TONE = { label: 'Live Telemetry', className: 'bg-white/10 text-white/70' };

const metricDeltaClass = (metric: RealtimeMetric) => {
  const change = metric.change ?? 0;
  if (change > 0) {
    return 'text-emerald-200';
  }
  if (change < 0) {
    return 'text-amber-200';
  }
  return 'text-[#c8d4ff]/70';
};

const formatMetricValue = (metric: RealtimeMetric) => {
  if (metric.format === 'ratio') {
    return `${(metric.value * 100).toFixed(1)}%`;
  }
  if (metric.format === 'percent') {
    return `${metric.value.toFixed(0)}%`;
  }
  const suffix = metric.unit ? ` ${metric.unit}` : '';
  return `${metric.value.toFixed(0)}${suffix}`;
};

const formatMetricDelta = (metric: RealtimeMetric) => {
  const change = metric.change ?? 0;
  const sign = change > 0 ? '+' : change < 0 ? '−' : '±';
  const magnitude = Math.abs(change);
  if (metric.format === 'ratio') {
    return `${sign}${(magnitude * 100).toFixed(2)}%`;
  }
  if (metric.format === 'percent') {
    return `${sign}${magnitude.toFixed(1)}%`;
  }
  const suffix = metric.unit ? ` ${metric.unit}` : '';
  return `${sign}${magnitude.toFixed(0)}${suffix}`;
};

const metricTrendLabel = (metric: RealtimeMetric) => {
  const change = metric.change ?? 0;
  const threshold = metric.format === 'ratio' ? 0.0005 : metric.format === 'percent' ? 0.05 : 0.5;
  if (change > threshold) {
    return 'Rising';
  }
  if (change < -threshold) {
    return 'Falling';
  }
  return 'Steady';
};

type VisualizationChartKey = 'coherence' | 'planetaryResonance' | 'magnetometer' | 'schumann';

type SparklineShape = { line: string; area: string; min: number; max: number } | null;

const buildSparkline = (points: RealtimeChartPoint[], sampleSize = 28): SparklineShape => {
  if (!points || points.length < 2) {
    return null;
  }
  const sample = points.slice(-sampleSize);
  if (sample.length < 2) {
    return null;
  }

  const min = Math.min(...sample.map((point) => point.value));
  const max = Math.max(...sample.map((point) => point.value));
  const range = max - min || 1;
  const step = 100 / (sample.length - 1);

  const coordinates = sample.map((point, index) => {
    const x = Number((index * step).toFixed(2));
    const y = Number((28 - ((point.value - min) / range) * 24).toFixed(2));
    return { x, y };
  });

  const line = coordinates.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
  const area = `M 0 28 ${coordinates.map((point) => `L ${point.x} ${point.y}`).join(' ')} L 100 28 Z`;

  return { line, area, min, max };
};

const formatChartValueForKey = (key: VisualizationChartKey, value: number | null) => {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  switch (key) {
    case 'coherence':
    case 'planetaryResonance':
      return `${(value * 100).toFixed(1)}%`;
    case 'schumann':
      return `${value.toFixed(2)} Hz`;
    case 'magnetometer':
      return `${value.toFixed(1)} nT`;
    default:
      return value.toFixed(2);
  }
};

const formatChartDeltaForKey = (key: VisualizationChartKey, delta: number | null) => {
  if (delta == null || Number.isNaN(delta)) {
    return '±0';
  }
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : '±';
  const magnitude = Math.abs(delta);
  switch (key) {
    case 'coherence':
    case 'planetaryResonance':
      return `${sign}${(magnitude * 100).toFixed(2)}%`;
    case 'schumann':
      return `${sign}${magnitude.toFixed(2)} Hz`;
    case 'magnetometer':
      return `${sign}${magnitude.toFixed(1)} nT`;
    default:
      return `${sign}${magnitude.toFixed(2)}`;
  }
};

const formatPulseTime = (baseTimestamp: number, offsetIndex = 0) => {
  const date = new Date(baseTimestamp - offsetIndex * 5500);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const formatRelativeTime = (timestamp: number) => {
  const deltaSeconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (deltaSeconds < 5) {
    return 'moments ago';
  }
  if (deltaSeconds < 60) {
    return `${deltaSeconds}s ago`;
  }
  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `${deltaMinutes}m ago`;
  }
  const deltaHours = Math.floor(deltaMinutes / 60);
  return `${deltaHours}h ago`;
};

const anomalyTone = (severity: SchumannAnomaly['severity']) => {
  if (severity === 'high') {
    return 'Crimson Trace';
  }
  if (severity === 'medium') {
    return 'Amber Pulse';
  }
  return 'Violet Whisper';
};

const stateFromRealtime: Record<'stable' | 'updating' | 'degraded', LiveStreamState> = {
  stable: 'Stable',
  updating: 'Watch',
  degraded: 'Anomaly',
};

type VisualizationDefinition = {
  id: string;
  title: string;
  detail: string;
  chartKey?: VisualizationChartKey;
  accent: string;
};

type VisualizationCard = VisualizationDefinition & {
  valueLabel: string;
  deltaLabel: string;
  deltaPositive: boolean;
  sparkline: SparklineShape;
  range?: string | null;
};

const VISUALIZATION_DEFINITIONS: VisualizationDefinition[] = [
  {
    id: 'coherence-wave',
    title: 'Line Graphs',
    detail: 'Coherence waveform updating every 250 ms through the Sentinel channel.',
    chartKey: 'coherence',
    accent: 'from-sky-500/20 via-cyan-500/10 to-transparent',
  },
  {
    id: 'resonance-heat',
    title: 'Heat Maps',
    detail: 'Planetary resonance coverage derived from QSSR harmonics.',
    chartKey: 'planetaryResonance',
    accent: 'from-amber-500/20 via-rose-500/10 to-transparent',
  },
  {
    id: 'gauges',
    title: 'Gauges',
    detail: 'Magnetometer amplitudes feeding the adaptive gauge clusters.',
    chartKey: 'magnetometer',
    accent: 'from-emerald-500/20 via-sky-500/10 to-transparent',
  },
  {
    id: 'spectrograms',
    title: 'Spectrograms',
    detail: 'Schumann harmonic bands rendered for audio + electromagnetic sensors.',
    chartKey: 'schumann',
    accent: 'from-fuchsia-500/20 via-purple-500/10 to-transparent',
  },
  {
    id: 'globe',
    title: '3D Globe',
    detail: 'Sensor occupancy projected onto the orbital globe mesh.',
    accent: 'from-indigo-500/20 via-blue-500/10 to-transparent',
  },
];

const LiveTab = () => {
  const {
    metrics,
    charts,
    sensory,
    output,
    schumannProtocol,
    quantumLink,
    timestamp,
  } = useLiveNexusData();

  const coherenceMetric = metrics.find((metric) => metric.id === 'coherence');
  const coherenceValue = coherenceMetric?.value ?? 0;
  const gaugeStyle = useMemo(() => {
    const ratio = Math.max(0, Math.min(1, coherenceValue));
    const angle = ratio * 360;
    return {
      background: `conic-gradient(#22d3ee ${angle}deg, rgba(14,23,55,0.45) ${angle}deg)`
    };
  }, [coherenceValue]);
  const coherencePercent = Math.round(coherenceValue * 100);
  const coherenceDeltaLabel = coherenceMetric ? formatMetricDelta(coherenceMetric) : '±0';
  const coherenceTrend = coherenceMetric ? metricTrendLabel(coherenceMetric) : 'Stable';
  const coherenceDeltaTone = coherenceMetric ? metricDeltaClass(coherenceMetric) : 'text-[#c8d4ff]/70';
  const coherenceDotTone = coherenceMetric && coherenceMetric.change < 0 ? 'bg-amber-300' : 'bg-emerald-400';
  const lastPulseTime = formatPulseTime(timestamp);

  const quickMetricCards = useMemo(
    () =>
      metrics.slice(0, 4).map((metric) => {
        const accent = METRIC_TONES[metric.id] ?? DEFAULT_METRIC_TONE;
        return {
          metric,
          accent,
          value: formatMetricValue(metric),
          delta: formatMetricDelta(metric),
          deltaClass: metricDeltaClass(metric),
          trend: metricTrendLabel(metric),
        };
      }),
    [metrics]
  );

  const transmissions = useMemo(
    () => {
      const records = output?.transmissions ?? [];
      const statusLabel: Record<'queued' | 'transmitting' | 'complete', string> = {
        queued: 'Queued',
        transmitting: 'Transmitting',
        complete: 'Complete',
      };
      const statusTone: Record<'queued' | 'transmitting' | 'complete', string> = {
        queued: 'text-amber-300',
        transmitting: 'text-sky-300',
        complete: 'text-emerald-300',
      };
      const statusDetail: Record<'queued' | 'transmitting' | 'complete', string> = {
        queued: 'Awaiting harmonic release window.',
        transmitting: 'Channel open and streaming telemetry.',
        complete: 'Archive sealed and mirrored.',
      };

      return records.slice(0, 4).map((tx, index) => ({
        id: tx.id,
        title: tx.channel,
        destination: tx.destination,
        status: statusLabel[tx.status],
        tone: statusTone[tx.status],
        detail: statusDetail[tx.status],
        pulse: formatPulseTime(timestamp, index),
      }));
    },
    [output?.transmissions, timestamp]
  );

  const liveStreams = useMemo<LiveStreamDatum[]>(() => {
    const streams = sensory?.dataStreams ?? [];
    return streams.map((stream) => {
      const state = stateFromRealtime[stream.state];
      const meta = STREAM_METADATA[stream.id] ?? { location: 'Unknown Node', capacity: 100 };
      const capacity = meta.capacity || 100;
      const intensity = Math.max(0, Math.min(100, (stream.rate / capacity) * 100));
      return {
        id: stream.id,
        name: stream.name,
        location: meta.location,
        intensity: Number(intensity.toFixed(1)),
        state,
        note: SENSOR_STATE_NOTES[state as SensorState],
        rate: Number(stream.rate.toFixed(1)),
        unit: stream.unit,
        capacity,
      };
    });
  }, [sensory?.dataStreams]);

  const visualizationCards = useMemo<VisualizationCard[]>(() => {
    return VISUALIZATION_DEFINITIONS.map((definition) => {
      if (definition.chartKey) {
        const points = charts[definition.chartKey] ?? [];
        const sparkline = buildSparkline(points);
        const latest = points.length ? points[points.length - 1].value : null;
        const previous = points.length > 1 ? points[points.length - 2].value : null;
        const delta = latest != null && previous != null ? latest - previous : null;
        const range = sparkline
          ? `${formatChartValueForKey(definition.chartKey, sparkline.min)} → ${formatChartValueForKey(definition.chartKey, sparkline.max)}`
          : null;

        return {
          ...definition,
          valueLabel: formatChartValueForKey(definition.chartKey, latest),
          deltaLabel: formatChartDeltaForKey(definition.chartKey, delta),
          deltaPositive: (delta ?? 0) >= 0,
          sparkline,
          range,
        };
      }

      const streams = sensory?.dataStreams ?? [];
      if (!streams.length) {
        return {
          ...definition,
          valueLabel: 'Awaiting mesh',
          deltaLabel: '—',
          deltaPositive: true,
          sparkline: null,
          range: null,
        };
      }

      const totalCapacity = streams.reduce(
        (sum, stream) => sum + (STREAM_METADATA[stream.id]?.capacity ?? 0),
        0
      );
      const totalRate = streams.reduce((sum, stream) => sum + stream.rate, 0);
      const occupancy = totalCapacity > 0 ? totalRate / totalCapacity : 0;
      const active = streams.filter((stream) => stream.state !== 'degraded').length;
      const anomalies = streams.length - active;
      const range = totalCapacity
        ? `${Math.round(totalRate)} / ${totalCapacity} throughput`
        : `${Math.round(totalRate)} total throughput`;

      return {
        ...definition,
        valueLabel: `${Math.round(occupancy * 100)}% engaged`,
        deltaLabel: `${active} live · ${anomalies} anomaly`,
        deltaPositive: anomalies === 0,
        sparkline: null,
        range,
      };
    });
  }, [charts, sensory?.dataStreams]);

  const notifications = useMemo(() => {
    const items: Array<{ id: string; badge: string; tone: string; message: string; time: string }> = [];
    const snapshots = schumannProtocol.monitoringSession.snapshots;
    const latestSnapshot = snapshots.at(-1);

    if (latestSnapshot) {
      const snapshotTime = new Date(latestSnapshot.timestamp).getTime();
      items.push({
        id: 'schumann-status',
        badge: 'Schumann',
        tone: 'Azure Bloom',
        message: latestSnapshot.status,
        time: formatRelativeTime(snapshotTime),
      });

      latestSnapshot.anomalies.slice(0, 2).forEach((anomaly, index) => {
        items.push({
          id: `anomaly-${anomaly.type}-${index}`,
          badge: anomaly.type.replace(/_/g, ' '),
          tone: anomalyTone(anomaly.severity),
          message: anomaly.explanation,
          time: formatRelativeTime(snapshotTime - (index + 1) * 8000),
        });
      });
    }

    items.push({
      id: 'command-queue',
      badge: 'Command Queue',
      tone: 'Golden Dawn',
      message: `${output.commandQueue.executing} executing · ${output.commandQueue.queued} queued · Last: ${output.commandQueue.lastCommand}`,
      time: formatRelativeTime(timestamp - 4000),
    });

    const handshakeLabel = quantumLink.handshakeState.replace(/-/g, ' ');
    const handshakeTitle = handshakeLabel.charAt(0).toUpperCase() + handshakeLabel.slice(1);

    items.push({
      id: 'quantum-link',
      badge: 'Quantum Link',
      tone: 'Emerald Rise',
      message:
        quantumLink.handshakeState === 'entangled'
          ? `Entangled with ${quantumLink.entangledSignature}`
          : `Handshake ${handshakeTitle}`,
      time: formatRelativeTime(quantumLink.lastPulse),
    });

    return items.slice(0, 4);
  }, [schumannProtocol, output.commandQueue, quantumLink, timestamp]);

  const updatedAt = useMemo(() => new Date(timestamp), [timestamp]);

  return (
    <div className="space-y-12">
      <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="border-white/10 bg-white/5 bg-[rgba(12,18,45,0.7)] shadow-[0_0_35px_rgba(45,190,255,0.18)] backdrop-blur">
          <CardHeader className="space-y-2">
            <Badge className="w-max bg-sky-500/20 text-sky-200">Onboarding Flow</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">First-Time Resonance Journey</CardTitle>
            <p className="text-sm text-[#c8d4ff]/80">
              Seven guided screens align new guardians with the Harmonic Nexus. Each stage locks before the next to guarantee full
              system attunement.
            </p>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {onboardingSteps.map((step) => (
              <div
                key={step.id}
                className="flex flex-col justify-between rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/50 to-slate-900/20 p-4"
              >
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.45em]">
                  <span className="text-white/70">{step.id}</span>
                  <span className={step.status === 'In Progress' ? 'text-amber-300' : 'text-emerald-300'}>{step.status}</span>
                </div>
                <h3 className="mt-4 text-sm font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{step.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(12,18,45,0.7)] shadow-[0_0_30px_rgba(251,191,36,0.25)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-emerald-500/20 text-emerald-100">Coherence Meter</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Live Coherence</CardTitle>
            <p className="text-xs uppercase tracking-[0.3em] text-[#c8d4ff]/60">Pulse {lastPulseTime}</p>
          </CardHeader>
          <CardContent>
            <div className="mx-auto flex w-full max-w-[220px] flex-col items-center gap-4">
              <div className="relative flex h-48 w-48 items-center justify-center rounded-full" style={gaugeStyle}>
                <div className="absolute inset-3 rounded-full bg-slate-950/80 backdrop-blur" />
                <div className="relative flex flex-col items-center justify-center">
                  <span className="text-4xl font-semibold text-white">{coherencePercent}%</span>
                  <span className="text-xs uppercase tracking-[0.3em] text-sky-200">Global</span>
                </div>
              </div>
              <p className="text-center text-xs text-[#c8d4ff]/75">
                Sentinel telemetry updates the coherence gauge every 250 ms, projecting the global resonance field in real time.
              </p>
              <div className={`flex items-center gap-2 text-xs ${coherenceDeltaTone}`}>
                <span className={`h-2 w-2 rounded-full ${coherenceDotTone}`} /> Δ {coherenceDeltaLabel} · {coherenceTrend}
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {quickMetricCards.map(({ metric, accent, value, delta, deltaClass, trend }) => (
          <Card key={metric.id} className="border-white/10 bg-[rgba(8,18,38,0.75)] backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-xs uppercase tracking-[0.4em] text-[#c8d4ff]/80">{metric.label}</CardTitle>
              <Badge className={`bg-white/10 text-[0.6rem] uppercase tracking-[0.3em] text-white/80 ${accent.className}`}>
                {accent.label}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-3xl font-semibold text-white">{value}</p>
              <p className={`text-xs uppercase tracking-[0.3em] ${deltaClass}`}>
                Δ {delta} · {trend}
              </p>
            </CardContent>
          </Card>
        ))}

        <Card className="border-white/10 bg-[rgba(8,18,38,0.75)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-fuchsia-500/20 text-fuchsia-100">Live Feed</Badge>
            <CardTitle className="text-xs uppercase tracking-[0.4em] text-[#c8d4ff]/80">Real-Time Planetary Feed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {transmissions.map((entry) => (
              <div key={entry.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-[#c8d4ff]/70">
                  <span>{entry.pulse}</span>
                  <span className={entry.tone}>{entry.status}</span>
                </div>
                <h3 className="mt-2 text-sm font-semibold text-white">{entry.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">Routing to {entry.destination}</p>
                <p className="mt-2 text-[0.6rem] uppercase tracking-[0.3em] text-[#c8d4ff]/60">{entry.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6">
        <LiveStreamShowcase streams={liveStreams} updatedAt={updatedAt} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr,1fr]">
        <Card className="border-white/10 bg-[rgba(7,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-indigo-500/20 text-indigo-100">Process Tree</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Operational Flow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-[#d0dcff]/85">
              <ul className="space-y-4">
                {processTree.map((node) => (
                  <li key={node.label}>
                    <div className="font-semibold text-white">{node.label}</div>
                    <ul className="mt-2 space-y-3 border-l border-white/10 pl-4">
                      {node.children?.map((child) => (
                        <li key={child.label}>
                          <div className="font-medium text-sky-200">{child.label}</div>
                          {child.children && (
                            <ul className="mt-2 space-y-2 border-l border-white/10 pl-4">
                              {child.children.map((grand) => (
                                <li key={grand.label} className="text-xs text-[#c8d4ff]/80">
                                  {grand.label}
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(7,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-amber-500/20 text-amber-100">Quick Actions</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Floating Action Menu</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {quickActions.map((action) => (
              <div key={action.label} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-[0.4em] text-[#c8d4ff]/70">{action.label}</div>
                <p className="mt-2 text-xs text-[#d0dcff]/80">{action.description}</p>
              </div>
            ))}
            <Button className="w-full rounded-full bg-sky-500/80 text-xs uppercase tracking-[0.4em] text-white hover:bg-sky-400/90">
              Tap FAB
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-white/10 bg-[rgba(6,14,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-emerald-500/20 text-emerald-100">Live Dashboard Actions</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Every Tap</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {dashboardInteractions.map((interaction) => (
              <div key={interaction.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-xs uppercase tracking-[0.4em] text-sky-200">{interaction.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{interaction.outcome}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(6,14,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-rose-500/20 text-rose-100">Notifications</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Live Alerts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {notifications.map((note) => (
              <div key={note.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-[0.35em]">
                  <span className="text-white/80">{note.badge}</span>
                  <span className="text-[#c8d4ff]/60">{note.time}</span>
                </div>
                <div className="mt-2 text-[0.6rem] uppercase tracking-[0.4em] text-sky-200">{note.tone}</div>
                <p className="mt-2 text-xs text-[#d0dcff]/85">{note.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-white/10 bg-[rgba(6,14,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">Data Visualizations</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Visual Arsenal</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {visualizationCards.map((viz) => {
              const gradientId = `viz-spark-${viz.id}`;
              const areaId = `${gradientId}-fill`;

              return (
                <div key={viz.id} className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${viz.accent} opacity-70`} />
                  <div className="relative z-10 space-y-3">
                    <h3 className="text-sm font-semibold text-white">{viz.title}</h3>
                    <div className="flex items-baseline justify-between">
                      <span className="text-xl font-semibold text-white">{viz.valueLabel}</span>
                      <span
                        className={`text-xs uppercase tracking-[0.3em] ${viz.deltaPositive ? 'text-emerald-200' : 'text-amber-200'}`}
                      >
                        {viz.deltaLabel}
                      </span>
                    </div>
                    {viz.sparkline ? (
                      <svg viewBox="0 0 100 28" className="h-16 w-full" preserveAspectRatio="none">
                        <defs>
                          <linearGradient id={gradientId} x1="0" x2="1" y1="0" y2="0">
                            <stop offset="0%" stopColor="rgba(56,189,248,0.65)" />
                            <stop offset="100%" stopColor="rgba(236,72,153,0.65)" />
                          </linearGradient>
                          <linearGradient id={areaId} x1="0" x2="1" y1="0" y2="0">
                            <stop offset="0%" stopColor="rgba(56,189,248,0.25)" />
                            <stop offset="100%" stopColor="rgba(236,72,153,0.08)" />
                          </linearGradient>
                        </defs>
                        <path d={viz.sparkline.area} fill={`url(#${areaId})`} stroke="none" />
                        <path d={viz.sparkline.line} stroke={`url(#${gradientId})`} strokeWidth="1.6" fill="none" />
                      </svg>
                    ) : (
                      <div className="mt-4 h-16 rounded-xl border border-white/10 bg-white/5 p-4 text-xs text-[#c8d4ff]/70">
                        {viz.range ?? 'Awaiting sensor mesh'}
                      </div>
                    )}
                    <p className="text-[0.65rem] leading-relaxed text-[#c8d4ff]/80">
                      {viz.detail}
                      {viz.range ? ` Range ${viz.range}.` : ''}
                    </p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(6,14,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-purple-500/20 text-purple-100">Gesture Controls</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Embodied Commands</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {gestureControls.map((gesture) => (
              <div key={gesture.gesture} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-[0.4em] text-white/75">{gesture.gesture}</div>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{gesture.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default LiveTab;

