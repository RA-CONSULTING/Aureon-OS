import { useEffect, useMemo, useState } from "react";
import { resample } from "@/lib/akashic/aureon-akashic";
import type { AuthUser } from "@/contexts/AuthContext";
import {
  EMOTION_SPECTRUM_MAX,
  EMOTION_SPECTRUM_MIN,
  mapSchumannAmplitudeToEmotionFrequency,
} from "@/lib/emotionSpectrum";
import { MODE_MATRIX, type ModeMatrix } from "@/lib/modeMatrix";
import { NexusSystem } from "../nexus_system_simulator";

type Nullable<T> = T | null | undefined;
type NexusVisualization = ReturnType<NexusSystem["getVisualizationData"]>;

// Assuming the types are defined elsewhere and imported, but for simplicity, including them here.
export type MetricFormat = "ratio" | "percent" | "count";

export interface RealtimeMetric {
  id: string;
  label: string;
  value: number;
  unit?: string;
  change: number;
  format: MetricFormat;
  target?: number;
}

export interface RealtimeChartPoint {
  timestamp: number;
  value: number;
}

export interface RealtimeDataStream {
  id: string;
  name: string;
  rate: number;
  unit: string;
  state: "stable" | "degraded" | "updating";
}

export interface LiveSensoryStatus {
  chronicleRecorder: {
    status: "Recording" | "Idle";
    eventsPerMinute: number;
    storageUsedTb: number;
    integrityChecks: string;
    retentionHours: number;
  };
  celestialCartography: {
    trackingSatellites: number;
    harmonicSignatures: string;
    solarAlignment: string;
    lunarPhase: string;
  };
  dataStreams: RealtimeDataStream[];
}

export interface LiveProcessingStatus {
  qssrModule: {
    solarCoherenceIndex: number;
    planetaryResonance: string;
    cosmicWeather: string;
    analysisQueue: number;
  };
  stormTargeting: {
    status: string;
    activePatterns: number;
    neutralizationRate: number;
    harmonicIntegration: number;
  };
  aurisCognitiveSafeguard: {
    status: string;
    hazardDetections: number;
    dampeningFactor: number;
    authorizedTemporalId: string;
  };
  algorithms: string[];
}

export interface LiveOutputStatus {
  voicePipelines: {
    activeVoices: number;
    latencyMs: number;
    successfulTransmits: number;
  };
  commandQueue: {
    queued: number;
    executing: number;
    lastCommand: string;
  };
  compliance: {
    status: string;
    auditsPassed: number;
    escalationLevel: string;
  };
  transmissions: {
    id: string;
    channel: string;
    destination: string;
    status: "queued" | "transmitting" | "complete";
  }[];
}

export type BioSignalTone = "stable" | "watch" | "alert";

export interface BioSignalMetric {
  id: string;
  label: string;
  value: number;
  unit: string;
  tone: BioSignalTone;
  change: number;
  targetRange: [number, number];
}

export interface BioStreamStatus {
  id: string;
  label: string;
  value: number;
  unit: string;
  reading: string;
  hint: string;
  status: BioSignalTone;
  trend: number;
  targetRange: [number, number];
}

export interface BioProfileAnalytics {
  signature: string;
  profileId: string;
  displayName: string;
  origin: string;
  timelineTag: string;
  summary: string;
  metrics: BioSignalMetric[];
  streams: BioStreamStatus[];
}

export type QuantumHandshakeState = "idle" | "auto-dial" | "entangled";

export interface QuantumLinkStatus {
  handshakeState: QuantumHandshakeState;
  entangledSignature: string;
  entangledTemporalId: string;
  observerReturnChannel: string;
  observerAttunement: number;
  lastPulse: number;
}

const SCHUMANN_HARMONICS = [
  { key: "fundamental", frequencyHz: 7.83 },
  { key: "first_harmonic", frequencyHz: 14.07 },
  { key: "second_harmonic", frequencyHz: 20.25 },
  { key: "third_harmonic", frequencyHz: 26.41 },
  { key: "fourth_harmonic", frequencyHz: 32.45 },
  { key: "fifth_harmonic", frequencyHz: 38.45 },
  { key: "sixth_harmonic", frequencyHz: 44.45 },
] as const;

type SchumannHarmonicKey = typeof SCHUMANN_HARMONICS[number]["key"];

type SchumannAnomalyType =
  | "AMPLITUDE_SPIKE"
  | "WEAK_FUNDAMENTAL_FREQUENCY"
  | "FREQUENCY_SHIFT";

type SchumannAnomalySeverity = "low" | "medium" | "high";

export interface SchumannAnomaly {
  type: SchumannAnomalyType;
  severity: SchumannAnomalySeverity;
  value: number;
  explanation: string;
}

export interface SchumannSnapshotRecord {
  timestamp: string;
  coherence: number;
  normalizedPower: number;
  frequencyVariationHz: number;
  status: string;
  anomalies: SchumannAnomaly[];
  harmonicPowers: Record<SchumannHarmonicKey, number>;
  powerDistribution: number[];
}

export interface SchumannHarmonicTrend {
  averagePower: number;
  powerVariation: number;
}

export interface SchumannTrendAnalysis {
  averageCoherence: number;
  coherenceVariation: number;
  anomalyRate: number;
  harmonicTrends: Record<SchumannHarmonicKey, SchumannHarmonicTrend>;
}

export interface SchumannMonitoringSession {
  startTime: string;
  endTime: string;
  durationMinutes: number;
  totalSnapshots: number;
  trendAnalysis: SchumannTrendAnalysis;
  snapshots: SchumannSnapshotRecord[];
}

export interface SchumannCoherenceScorecard {
  dataComprehensiveness: number;
  metricDiversity: number;
  humanReadability: number;
  trendAnalysisDepth: number;
  anomalyTracking: number;
  combinedCoherence: number;
  status: string;
}

export interface SchumannPrimeSentinelWitness {
  name: string;
  title: string;
  institution: string;
  statement: string;
  timestamp: string;
}

export interface SchumannResonanceProtocol {
  monitoringSession: SchumannMonitoringSession;
  coherenceReport: SchumannCoherenceScorecard;
  witness: SchumannPrimeSentinelWitness;
}

export interface RealtimeChartCollection {
  magnetometer: RealtimeChartPoint[];
  schumann: RealtimeChartPoint[];
  coherence: RealtimeChartPoint[];
  planetaryResonance: RealtimeChartPoint[];
}

export interface RealtimeNexusData {
  timestamp: number;
  metrics: RealtimeMetric[];
  charts: RealtimeChartCollection;
  sensory: LiveSensoryStatus;
  processing: LiveProcessingStatus;
  output: LiveOutputStatus;
  bioProfile: BioProfileAnalytics;
  schumannProtocol: SchumannResonanceProtocol;
  quantumLink: QuantumLinkStatus;
  modeMatrix: ModeMatrix;
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const HISTORY_WINDOW_SECONDS = 10 * 60;
const HISTORY_WINDOW_MS = HISTORY_WINDOW_SECONDS * 1000;
const HISTORY_SEED_INTERVAL_MS = 500;
const HISTORY_SEED_POINTS = Math.round(HISTORY_WINDOW_MS / HISTORY_SEED_INTERVAL_MS);
const HISTORY_BUFFER_FACTOR = 1.15;
const RESAMPLE_STEP_SECONDS = 0.25;

const MAX_SCHUMANN_SNAPSHOTS = 96;

const EMOTIONAL_SCHUMANN_VARIANCE =
  (EMOTION_SPECTRUM_MAX - EMOTION_SPECTRUM_MIN) * 0.06;

const roundTo = (value: number, digits = 3) => Number(value.toFixed(digits));

const mean = (values: number[]) =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

const standardDeviation = (values: number[]) => {
  if (values.length <= 1) {
    return 0;
  }
  const average = mean(values);
  const variance =
    values.reduce((sum, value) => sum + (value - average) ** 2, 0) / (values.length - 1);
  return Math.sqrt(Math.max(variance, 0));
};

const statusFromCoherence = (coherence: number) => {
  if (coherence >= 0.8) {
    return "Normal planetary conditions";
  }
  if (coherence >= 0.6) {
    return "Harmonic field within nominal range";
  }
  if (coherence >= 0.4) {
    return "Geomagnetic turbulence rising";
  }
  return "Field stability compromised";
};

const shiftSeverity = (shift: number): SchumannAnomalySeverity => {
  if (shift > 0.2) {
    return "high";
  }
  if (shift > 0.14) {
    return "medium";
  }
  return "low";
};

const createSchumannSnapshot = (
  vizData: NexusVisualization,
  now: number,
  previous?: SchumannSnapshotRecord
): SchumannSnapshotRecord => {
  const amplitudeRaw = vizData?.frequencies?.schumann?.amplitude ?? 0;
  const amplitudeNormalized = clamp(Math.abs(amplitudeRaw) / 100, 0, 1);
  const sentinelCoherence = clamp((vizData?.sentinel?.coherence ?? 0) / 100, 0, 1);
  const coherence = clamp(sentinelCoherence * 0.65 + amplitudeNormalized * 0.35, 0, 1);

  const timeFactor = now / 1000;
  const harmonicEntries = SCHUMANN_HARMONICS.map(({ key }, index) => {
    const falloff = Math.exp(-index / 3.1);
    const modulation = Math.sin(timeFactor / (32 - index * 2) + index) * 0.05;
    const harmonized = clamp(
      amplitudeNormalized * falloff + sentinelCoherence * 0.1 + modulation,
      0,
      1
    );
    return [key, harmonized] as const;
  });

  const totalPower = harmonicEntries.reduce((sum, [, value]) => sum + value, 0) || 1;
  const harmonicPowers = Object.fromEntries(
    harmonicEntries.map(([key, value]) => [key, roundTo(value / totalPower)])
  ) as Record<SchumannHarmonicKey, number>;

  const previousFundamental = previous?.harmonicPowers?.fundamental;
  const fundamentalShift = previousFundamental != null
    ? Math.abs(harmonicPowers.fundamental - previousFundamental)
    : 0;
  const baseFrequency = SCHUMANN_HARMONICS[0].frequencyHz;
  const frequencyVariationHz = roundTo(fundamentalShift * baseFrequency, 3);

  const anomalies: SchumannAnomaly[] = [];
  if (amplitudeNormalized >= 0.85) {
    anomalies.push({
      type: "AMPLITUDE_SPIKE",
      severity: amplitudeNormalized > 0.93 ? "high" : "medium",
      value: roundTo(amplitudeNormalized * 3.5, 3),
      explanation: "Unusual frequency spike detected",
    });
  }
  if (coherence <= 0.4) {
    anomalies.push({
      type: "WEAK_FUNDAMENTAL_FREQUENCY",
      severity: coherence < 0.25 ? "high" : "medium",
      value: roundTo(coherence, 3),
      explanation: "Fundamental resonance bandwidth weakening",
    });
  }
  if (fundamentalShift > 0.1) {
    anomalies.push({
      type: "FREQUENCY_SHIFT",
      severity: shiftSeverity(fundamentalShift),
      value: roundTo(fundamentalShift * baseFrequency, 3),
      explanation: "Harmonic distribution pivot detected",
    });
  }

  const status = anomalies.length
    ? `${statusFromCoherence(coherence)} · ${anomalies[0].explanation}`
    : statusFromCoherence(coherence);

  const powerDistribution = SCHUMANN_HARMONICS.map(({ key }) => harmonicPowers[key]);

  return {
    timestamp: new Date(now).toISOString(),
    coherence: roundTo(coherence, 4),
    normalizedPower: roundTo(amplitudeNormalized, 4),
    frequencyVariationHz,
    status,
    anomalies,
    harmonicPowers,
    powerDistribution: powerDistribution.map((value) => roundTo(value, 4)),
  };
};

const computeSchumannTrend = (
  snapshots: SchumannSnapshotRecord[]
): SchumannTrendAnalysis => {
  if (!snapshots.length) {
    const emptyTrends = Object.fromEntries(
      SCHUMANN_HARMONICS.map(({ key }) => [key, { averagePower: 0, powerVariation: 0 }])
    ) as Record<SchumannHarmonicKey, SchumannHarmonicTrend>;
    return {
      averageCoherence: 0,
      coherenceVariation: 0,
      anomalyRate: 0,
      harmonicTrends: emptyTrends,
    };
  }

  const coherenceValues = snapshots.map((snapshot) => snapshot.coherence);
  const anomalyCount = snapshots.reduce(
    (sum, snapshot) => sum + (snapshot.anomalies.length > 0 ? 1 : 0),
    0
  );

  const harmonicTrends = Object.fromEntries(
    SCHUMANN_HARMONICS.map(({ key }) => {
      const values = snapshots.map((snapshot) => snapshot.harmonicPowers[key]);
      return [
        key,
        {
          averagePower: roundTo(mean(values), 4),
          powerVariation: roundTo(standardDeviation(values), 4),
        },
      ];
    })
  ) as Record<SchumannHarmonicKey, SchumannHarmonicTrend>;

  return {
    averageCoherence: roundTo(mean(coherenceValues), 4),
    coherenceVariation: roundTo(standardDeviation(coherenceValues), 4),
    anomalyRate: roundTo(anomalyCount / snapshots.length, 4),
    harmonicTrends,
  };
};

const computeSchumannCoherenceReport = (
  snapshots: SchumannSnapshotRecord[],
  trend: SchumannTrendAnalysis
): SchumannCoherenceScorecard => {
  const snapshotCount = snapshots.length;
  const engagedHarmonics = Object.values(trend.harmonicTrends).filter(
    (entry) => entry.averagePower > 0
  ).length;

  const dataComprehensiveness = roundTo(
    clamp(0.78 + Math.min(snapshotCount, 60) * 0.0035, 0, 0.99),
    3
  );
  const metricDiversity = roundTo(
    clamp(0.82 + (engagedHarmonics / SCHUMANN_HARMONICS.length) * 0.16, 0, 0.98),
    3
  );
  const humanReadability = roundTo(
    clamp(0.9 + Math.min(snapshotCount, 40) * 0.001 - trend.anomalyRate * 0.05, 0.82, 0.97),
    3
  );
  const trendAnalysisDepth = roundTo(
    clamp(
      0.84 + Math.min(snapshotCount, 50) * 0.0025 - trend.coherenceVariation * 0.15,
      0.8,
      0.97
    ),
    3
  );
  const anomalyTracking = roundTo(clamp(0.9 - trend.anomalyRate * 0.25, 0.7, 0.97), 3);

  const combinedCoherence = roundTo(
    Math.sqrt(
      (
        dataComprehensiveness ** 2 +
        metricDiversity ** 2 +
        humanReadability ** 2 +
        trendAnalysisDepth ** 2 +
        anomalyTracking ** 2
      ) / 5
    ),
    3
  );

  const status =
    combinedCoherence >= 0.9
      ? "HIGH-FIDELITY DATA CAPTURE"
      : combinedCoherence >= 0.78
        ? "CALIBRATION RECOMMENDED"
        : "REASSESS MONITORING GRID";

  return {
    dataComprehensiveness,
    metricDiversity,
    humanReadability,
    trendAnalysisDepth,
    anomalyTracking,
    combinedCoherence,
    status,
  };
};

const initializeSchumannProtocol = (
  vizData: NexusVisualization,
  now: number
): SchumannResonanceProtocol => {
  const snapshot = createSchumannSnapshot(vizData, now);
  const timestamp = new Date(now).toISOString();
  const trend = computeSchumannTrend([snapshot]);

  return {
    monitoringSession: {
      startTime: timestamp,
      endTime: timestamp,
      durationMinutes: 0,
      totalSnapshots: 1,
      trendAnalysis: trend,
      snapshots: [snapshot],
    },
    coherenceReport: computeSchumannCoherenceReport([snapshot], trend),
    witness: {
      name: "Gary Leckey (Gar-Aya Lek-Aey)",
      title: "Prime Sentinel",
      institution: "Aureon Institute",
      statement: "Schumann resonance data recording protocol initialized.",
      timestamp,
    },
  };
};

const updateSchumannProtocol = (
  previous: SchumannResonanceProtocol,
  vizData: NexusVisualization,
  now: number
): SchumannResonanceProtocol => {
  const lastSnapshot = previous.monitoringSession.snapshots.slice(-1)[0];
  const nextSnapshot = createSchumannSnapshot(vizData, now, lastSnapshot);
  const combinedSnapshots = [...previous.monitoringSession.snapshots, nextSnapshot];
  const trimmedSnapshots = combinedSnapshots.slice(-MAX_SCHUMANN_SNAPSHOTS);

  const startTime = trimmedSnapshots[0]?.timestamp ?? new Date(now).toISOString();
  const endTime = new Date(now).toISOString();
  const durationMinutes = roundTo(
    Math.max(0, new Date(endTime).getTime() - new Date(startTime).getTime()) / 60000,
    2
  );

  const trend = computeSchumannTrend(trimmedSnapshots);
  const coherenceReport = computeSchumannCoherenceReport(trimmedSnapshots, trend);

  return {
    monitoringSession: {
      startTime,
      endTime,
      durationMinutes,
      totalSnapshots: trimmedSnapshots.length,
      trendAnalysis: trend,
      snapshots: trimmedSnapshots,
    },
    coherenceReport,
    witness: {
      name: previous.witness.name,
      title: previous.witness.title,
      institution: previous.witness.institution,
      statement: `Protocol affirms ${trimmedSnapshots.length} harmonic captures; coherence ${(trend.averageCoherence * 100).toFixed(1)}% · status ${coherenceReport.status}.`,
      timestamp: endTime,
    },
  };
};

const SOLAR_ALIGNMENT_STATES = [
  { threshold: 0.75, label: "Optimal" },
  { threshold: 0.4, label: "Adjusting" },
  { threshold: -0.15, label: "Rebalancing" },
  { threshold: -Infinity, label: "Stormwatch" },
] as const;

const MS_IN_DAY = 24 * 60 * 60 * 1000;
const SYNODIC_MONTH = 29.53058867;

const dayOfYear = (date: Date) => {
  const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0));
  return Math.floor((date.getTime() - start.getTime()) / MS_IN_DAY);
};

const describeSolarAlignment = (date: Date) => {
  const day = dayOfYear(date);
  const annualWave = Math.sin((day / 365) * Math.PI * 2);
  const diurnalWave = Math.sin((date.getUTCHours() / 24) * Math.PI * 2) * 0.2;
  const composite = clamp(annualWave * 0.8 + diurnalWave, -1, 1);

  const state = SOLAR_ALIGNMENT_STATES.find(({ threshold }) => composite >= threshold);
  return state?.label ?? "Adjusting";
};

const describeLunarPhase = (date: Date) => {
  // Reference new moon: Jan 6, 2000 18:14 UTC (approx)
  const reference = Date.UTC(2000, 0, 6, 18, 14);
  const elapsedDays = (date.getTime() - reference) / MS_IN_DAY;
  const phase = ((elapsedDays % SYNODIC_MONTH) + SYNODIC_MONTH) % SYNODIC_MONTH;

  if (phase < 1) return "New Moon";
  if (phase < 6.3826469265) return "Waxing Crescent";
  if (phase < 8.3826469265) return "First Quarter";
  if (phase < 13.765293853) return "Waxing Gibbous";
  if (phase < 15.765293853) return "Full Moon";
  if (phase < 21.1479407795) return "Waning Gibbous";
  if (phase < 23.1479407795) return "Last Quarter";
  if (phase < 28.530587706) return "Waning Crescent";
  return "New Moon";
};

const createInitialSeries = (
  base: number,
  variance: number,
  min: number,
  max: number
): RealtimeChartPoint[] => {
  const now = Date.now();
  const totalPoints = Math.max(240, HISTORY_SEED_POINTS);

  return Array.from({ length: totalPoints }, (_, index) => {
    const progress = index / Math.max(totalPoints - 1, 1);
    const highFrequency = Math.sin(progress * Math.PI * 18) * variance * 0.35;
    const lowFrequency = Math.sin(progress * Math.PI * 4) * variance * 0.55;
    const drift = Math.cos(progress * Math.PI * 2) * variance * 0.1;
    const value = clamp(base + highFrequency + lowFrequency + drift, min, max);
    const timestamp = now - (totalPoints - index) * HISTORY_SEED_INTERVAL_MS;

    return {
      timestamp,
      value: Number(value.toFixed(3)),
    };
  });
};

const advanceSeries = (
  series: RealtimeChartPoint[],
  newValue: number
): RealtimeChartPoint[] => {
  const now = Date.now();
  const nextPoint: RealtimeChartPoint = {
    timestamp: now,
    value: Number(newValue.toFixed(3)),
  };

  const cutoff = now - HISTORY_WINDOW_MS * HISTORY_BUFFER_FACTOR;
  const trimmed = series.filter((point) => point.timestamp >= cutoff);

  return [...trimmed, nextPoint];
};


const STREAM_TUNINGS: Record<
  string,
  { variance: number; watch: number; alert: number }
> = {
  phenomena: { variance: 6, watch: 140, alert: 165 },
  temporal: { variance: 4, watch: 105, alert: 130 },
  geometry: { variance: 3, watch: 82, alert: 96 },
  celestial: { variance: 1.2, watch: 28, alert: 34 },
  geomagnetic: { variance: 2.5, watch: 56, alert: 70 },
};

const signatureForProfile = (profile: AuthUser | null): string => {
  if (!profile) return "anonymous";
  const name = profile.name.trim().toLowerCase();
  const origin = profile.placeOfBirth.trim().toLowerCase();
  const dob = profile.dateOfBirth || "";
  return `${name}|${dob}|${origin}`;
};

const hashString = (value: string): number => {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
};

const seededNumber = (seed: number, min: number, max: number, offset: number) => {
  const x = Math.abs(Math.sin(seed * 0.0001 + offset * 12.9898));
  return Number((min + (max - min) * x).toFixed(2));
};

const formatDate = (value: string | undefined) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
};

const toneForRange = (value: number, [low, high]: [number, number]): BioSignalTone => {
  const margin = (high - low) * 0.35 || 6;
  if (value >= low && value <= high) {
    return "stable";
  }
  if (value >= low - margin && value <= high + margin) {
    return "watch";
  }
  return "alert";
};

const createBioProfileAnalytics = (profile: AuthUser | null): BioProfileAnalytics => {
  const signature = signatureForProfile(profile);
  const hash = hashString(signature);
  const displayName = profile?.name?.trim() || "Unlinked Operative";
  const origin = profile?.placeOfBirth?.trim() || "Origin Unknown";
  const formattedDob = formatDate(profile?.dateOfBirth || "");
  const timelineTag = formattedDob ? `${formattedDob} · ${origin}` : origin;
  const summary = profile
    ? `Quantum bio-stream locked to ${displayName} across the ${origin} lattice.`
    : "Awaiting human-connection handshake to personalize analytics.";

  const cardiacBaseline = seededNumber(hash + 17, 58, 74, 1);
  const neuralBaseline = seededNumber(hash + 29, 80, 95, 2);
  const auraBaseline = seededNumber(hash + 43, 66, 90, 3);
  const respirationBaseline = seededNumber(hash + 11, 12, 17, 4);
  const hydrationBaseline = seededNumber(hash + 7, 58, 72, 5);
  const chronoBaseline = seededNumber(hash + 3, 84, 97, 6);

  const metrics: BioSignalMetric[] = [
    {
      id: "cardiac",
      label: "Cardiac Resonance",
      value: Number(cardiacBaseline.toFixed(1)),
      unit: "bpm",
      tone: toneForRange(cardiacBaseline, [59, 71]),
      change: 0,
      targetRange: [59, 71],
    },
    {
      id: "neural",
      label: "Neural Synchrony",
      value: Number(neuralBaseline.toFixed(1)),
      unit: "%",
      tone: toneForRange(neuralBaseline, [84, 93]),
      change: 0,
      targetRange: [84, 93],
    },
    {
      id: "aura",
      label: "Biofield Flux",
      value: Number(auraBaseline.toFixed(1)),
      unit: "%",
      tone: toneForRange(auraBaseline, [70, 88]),
      change: 0,
      targetRange: [70, 88],
    },
  ];

  const streams: BioStreamStatus[] = [
    {
      id: "respiration",
      label: "Respiration Wave",
      value: respirationBaseline,
      unit: "L/min",
      reading: `${respirationBaseline.toFixed(1)} L/min`,
      hint: "Diaphragmatic rhythm within harmonic tolerance.",
      status: toneForRange(respirationBaseline, [13, 16]),
      trend: 0,
      targetRange: [13, 16],
    },
    {
      id: "hydration",
      label: "Hydration Conductivity",
      value: hydrationBaseline,
      unit: "%",
      reading: `${hydrationBaseline.toFixed(1)}%`,
      hint: "Cellular lattice saturation level.",
      status: toneForRange(hydrationBaseline, [60, 70]),
      trend: 0,
      targetRange: [60, 70],
    },
    {
      id: "chrono",
      label: "Chrono-Stability",
      value: chronoBaseline,
      unit: "%",
      reading: `${chronoBaseline.toFixed(1)}%`,
      hint: "Temporal anchor resilience against drift.",
      status: toneForRange(chronoBaseline, [86, 94]),
      trend: 0,
      targetRange: [86, 94],
    },
  ];

  return {
    signature,
    profileId: signature.replace(/[^a-z0-9]+/g, "-") || "anonymous",
    displayName,
    origin,
    timelineTag,
    summary,
    metrics,
    streams,
  };
};

const updateBioProfile = (
  previous: BioProfileAnalytics,
  profile: AuthUser | null
): BioProfileAnalytics => {
  const signature = signatureForProfile(profile);
  if (signature !== previous.signature) {
    return createBioProfileAnalytics(profile);
  }

  const driftMetric = (metric: BioSignalMetric, variance: number) => {
    const nextValue = clamp(
      metric.value + (Math.random() - 0.5) * variance,
      metric.targetRange[0] - 12,
      metric.targetRange[1] + 12
    );
    const change = Number((nextValue - metric.value).toFixed(2));
    const tone = toneForRange(nextValue, metric.targetRange);
    return {
      ...metric,
      value: Number(nextValue.toFixed(1)),
      change,
      tone,
    };
  };

  const driftStream = (stream: BioStreamStatus, variance: number) => {
    const nextValue = clamp(
      stream.value + (Math.random() - 0.5) * variance,
      stream.targetRange[0] - variance,
      stream.targetRange[1] + variance
    );
    const tone = toneForRange(nextValue, stream.targetRange);
    const trend = Number((nextValue - stream.value).toFixed(2));
    return {
      ...stream,
      value: Number(nextValue.toFixed(2)),
      reading: `${nextValue.toFixed(1)} ${stream.unit}`,
      status: tone,
      trend,
    };
  };

  return {
    ...previous,
    metrics: previous.metrics.map((metric, index) =>
      driftMetric(metric, index === 0 ? 1.4 : index === 1 ? 2 : 2.5)
    ),
    streams: previous.streams.map((stream, index) =>
      driftStream(stream, index === 0 ? 0.6 : index === 1 ? 1 : 1.4)
    ),
  };
};

const temporalIdFromSignature = (signature: string) => {
  if (!signature || signature === "anonymous") {
    return "T-ANON";
  }
  const hash = hashString(signature);
  const suffix = hash.toString(16).toUpperCase().padStart(8, "0").slice(-8);
  return `T-${suffix}`;
};

const createQuantumLinkStatus = (profile: AuthUser | null): QuantumLinkStatus => {
  const signature = signatureForProfile(profile);
  const entangledTemporalId = temporalIdFromSignature(signature);
  const handshakeState: QuantumHandshakeState = profile ? "auto-dial" : "idle";
  const attunementBase = profile
    ? clamp(0.78 + Math.random() * 0.14, 0, 1)
    : clamp(0.32 + Math.random() * 0.12, 0, 1);

  const observerReturnChannel = profile
    ? `Observer echo pinned to ${profile.name?.trim() || "linked operative"}`
    : "Awaiting observer focus to seal the return path.";

  return {
    handshakeState,
    entangledSignature: signature,
    entangledTemporalId,
    observerReturnChannel,
    observerAttunement: Number(attunementBase.toFixed(3)),
    lastPulse: Date.now(),
  };
};

const updateQuantumLinkStatus = (
  previous: QuantumLinkStatus,
  profile: AuthUser | null
): QuantumLinkStatus => {
  const signature = signatureForProfile(profile);
  const entangledTemporalId = temporalIdFromSignature(signature);

  let handshakeState: QuantumHandshakeState = previous.handshakeState;
  if (!profile) {
    handshakeState = "idle";
  } else if (previous.handshakeState === "idle") {
    handshakeState = "auto-dial";
  } else {
    handshakeState = "entangled";
  }

  const targetAttunement = profile ? 0.9 : 0.4;
  const attunement = clamp(
    previous.observerAttunement + (targetAttunement - previous.observerAttunement) * 0.25 + (Math.random() - 0.5) * 0.05,
    0,
    1
  );

  const observerReturnChannel = profile
    ? `Return path locked to ${profile.name?.trim() || "linked operative"}`
    : "Observer return channel dormant.";

  return {
    handshakeState,
    entangledSignature: signature,
    entangledTemporalId,
    observerReturnChannel,
    observerAttunement: Number(attunement.toFixed(3)),
    lastPulse: Date.now(),
  };
};

const createInitialData = (nexus: NexusSystem, profile: AuthUser | null): RealtimeNexusData => {
    const now = Date.now();
    const vizData = nexus.getVisualizationData();
    const temporalId = signatureForProfile(profile).replace(/[^a-z0-9]+/g, "-");
    const schumannFrequency = mapSchumannAmplitudeToEmotionFrequency(
      vizData.frequencies.schumann.amplitude
    );

    return {
        timestamp: now,
        metrics: [
            {
              id: "coherence",
              label: "Solar Coherence Index (C)",
              value: vizData.sentinel.coherence / 100,
              unit: "",
              change: 0,
              format: "ratio",
            },
            {
              id: "resonance",
              label: "Planetary Resonance Harmony",
              value: vizData.stability.stable / 100,
              unit: "",
              change: 0,
              format: "ratio",
            },
            {
              id: "chronicle",
              label: "Chronicle Write Rate",
              value: 132,
              unit: "events/min",
              change: 0,
              format: "count",
              target: 180,
            },
            {
              id: "aureon",
              label: "Aureon Protocol Activity",
              value: 74,
              unit: "%",
              change: 0,
              format: "percent",
            },
          ],
          charts: {
            magnetometer: createInitialSeries(48, 6, 35, 65),
            schumann: createInitialSeries(
              schumannFrequency,
              EMOTIONAL_SCHUMANN_VARIANCE,
              EMOTION_SPECTRUM_MIN,
              EMOTION_SPECTRUM_MAX
            ),
            coherence: createInitialSeries(vizData.sentinel.coherence / 100, 0.05, 0.7, 1.02),
            planetaryResonance: createInitialSeries(vizData.stability.stable / 100, 0.08, 0.7, 1.05),
          },
          sensory: {
            chronicleRecorder: {
              status: "Recording",
              eventsPerMinute: 128,
              storageUsedTb: 2.4,
              integrityChecks: "Passing",
              retentionHours: 72,
            },
            celestialCartography: {
              trackingSatellites: 24,
              harmonicSignatures: "Stable",
              solarAlignment: "Optimal",
              lunarPhase: "Waxing Gibbous",
            },
            dataStreams: [
              {
                id: "phenomena",
                name: "Witnessed Phenomena Log",
                rate: 127,
                unit: "events/min",
                state: "stable",
              },
              {
                id: "temporal",
                name: "Temporal Stamp Verification",
                rate: 98,
                unit: "ops/min",
                state: "stable",
              },
              {
                id: "geometry",
                name: "Sacred Geometry Detection",
                rate: 76,
                unit: "patterns/min",
                state: "updating",
              },
              {
                id: "celestial",
                name: "Celestial Body Tracking",
                rate: 24,
                unit: "bodies",
                state: "stable",
              },
              {
                id: "geomagnetic",
                name: "Geomagnetic Field",
                rate: 48,
                unit: "nT",
                state: "stable",
              },
            ],
          },
          processing: {
            qssrModule: {
              solarCoherenceIndex: 0.89,
              planetaryResonance: "Harmonized",
              cosmicWeather: "Clear",
              analysisQueue: 42,
            },
            stormTargeting: {
              status: "Migrating to HNC",
              activePatterns: 3,
              neutralizationRate: 92,
              harmonicIntegration: 75,
            },
            aurisCognitiveSafeguard: {
              status: "Active",
              hazardDetections: 4,
              dampeningFactor: 0.5,
              authorizedTemporalId: temporalId,
            },
            algorithms: [
              "FFT Spectral Analysis",
              "MFCC Feature Extraction",
              "Cross-modal Correlation",
              "Event Detection ML",
            ],
          },
          output: {
            voicePipelines: {
              activeVoices: 3,
              latencyMs: 162,
              successfulTransmits: 47,
            },
            commandQueue: {
              queued: 5,
              executing: 2,
              lastCommand: "Stabilize QSSR Envelope",
            },
            compliance: {
              status: "Aligned",
              auditsPassed: 18,
              escalationLevel: "None",
            },
            transmissions: [
              {
                id: "uplink",
                channel: "Prime Uplink",
                destination: "Central Pillar",
                status: "transmitting",
              },
              {
                id: "field",
                channel: "Field Node Broadcast",
                destination: "All Active Nodes",
                status: "queued",
              },
              {
                id: "archive",
                channel: "Chronicle Archive Sync",
              destination: "Aureon Library",
              status: "complete",
            },
          ],
          },
          bioProfile: createBioProfileAnalytics(profile),
          schumannProtocol: initializeSchumannProtocol(vizData, now),
          quantumLink: createQuantumLinkStatus(profile),
          modeMatrix: MODE_MATRIX,
    };
};

const computeNextData = (
  prev: RealtimeNexusData,
  nexus: NexusSystem,
  liveData: { solarAlignment: string; lunarPhase: string },
  profile: AuthUser | null
): RealtimeNexusData => {
    nexus.egoDeathSim.step(0.01);
    const vizData = nexus.getVisualizationData();
  const toSample = (p: RealtimeChartPoint) => ({ t: p.timestamp / 1000, v: p.value });
  const fromSample = (s: { t: number; v: number }) => ({ timestamp: s.t * 1000, value: s.v });

  const now = Date.now();

  const timeWindow = HISTORY_WINDOW_MS;

  const truncateAndResample = (series: RealtimeChartPoint[]) => {
    const recentPoints = series.filter(p => now - p.timestamp < timeWindow);
    const samples = recentPoints.map(toSample);
    if (samples.length < 2) return recentPoints; // Not enough to resample
    return resample(samples, RESAMPLE_STEP_SECONDS).map(fromSample);
  }

  const newCharts: RealtimeChartCollection = {
    magnetometer: advanceSeries(prev.charts.magnetometer, vizData.energy.amplitude),
    schumann: advanceSeries(
      prev.charts.schumann,
      mapSchumannAmplitudeToEmotionFrequency(vizData.frequencies.schumann.amplitude)
    ),
    coherence: advanceSeries(prev.charts.coherence, vizData.sentinel.coherence / 100),
    planetaryResonance: advanceSeries(prev.charts.planetaryResonance, vizData.stability.stable / 100),
  };

  const resampledCharts: RealtimeChartCollection = {
    magnetometer: truncateAndResample(newCharts.magnetometer),
    schumann: truncateAndResample(newCharts.schumann),
    coherence: truncateAndResample(newCharts.coherence),
    planetaryResonance: truncateAndResample(newCharts.planetaryResonance),
  };

  const coherenceRatio = clamp(vizData.sentinel.coherence / 100, 0, 1);
  const resonanceRatio = clamp(vizData.stability.stable / 100, 0, 1);
  const updatedSchumannProtocol = updateSchumannProtocol(prev.schumannProtocol, vizData, now);

  const updatedStreams = prev.sensory.dataStreams.map((stream) => {
    const tuning = STREAM_TUNINGS[stream.id] ?? {
      variance: Math.max(1, stream.rate * 0.05),
      watch: Number.POSITIVE_INFINITY,
      alert: Number.POSITIVE_INFINITY,
    };
    const delta = (Math.random() - 0.5) * tuning.variance;
    const nextRate = clamp(stream.rate + delta, Math.max(0, stream.rate - tuning.variance * 4), stream.rate + tuning.variance * 4);
    let nextState: RealtimeDataStream["state"] = "stable";
    if (nextRate >= tuning.alert) {
      nextState = "degraded";
    } else if (nextRate >= tuning.watch) {
      nextState = "updating";
    }

    return {
      ...stream,
      rate: Number(nextRate.toFixed(1)),
      state: nextState,
    };
  });

  const updatedProcessing: LiveProcessingStatus = {
    qssrModule: {
      solarCoherenceIndex: Number(coherenceRatio.toFixed(3)),
      planetaryResonance: resonanceRatio > 0.85 ? "Harmonized" : resonanceRatio > 0.7 ? "Balancing" : "Investigating",
      cosmicWeather: resonanceRatio > 0.8 ? "Clear" : resonanceRatio > 0.65 ? "Variable" : "Turbulent",
      analysisQueue: clamp(
        Math.round(prev.processing.qssrModule.analysisQueue + (Math.random() - 0.5) * 6),
        18,
        96
      ),
    },
    stormTargeting: {
      status: coherenceRatio > 0.85 ? "Synchronized" : coherenceRatio > 0.72 ? "Migrating to HNC" : "Recalibrating",
      activePatterns: clamp(
        Math.round(
          prev.processing.stormTargeting.activePatterns + (Math.random() - 0.5) * 1.5
        ),
        1,
        6
      ),
      neutralizationRate: clamp(
        Math.round(70 + coherenceRatio * 28 + (Math.random() - 0.5) * 4),
        52,
        99
      ),
      harmonicIntegration: clamp(
        Math.round(60 + resonanceRatio * 35 + (Math.random() - 0.5) * 6),
        48,
        98
      ),
    },
    aurisCognitiveSafeguard: {
      status: prev.processing.aurisCognitiveSafeguard.status,
      hazardDetections: clamp(
        Math.round(prev.processing.aurisCognitiveSafeguard.hazardDetections + (Math.random() - 0.5) * 1.6),
        0,
        9
      ),
      dampeningFactor: Number(clamp(0.42 + (1 - coherenceRatio) * 0.4, 0.35, 0.88).toFixed(2)),
      authorizedTemporalId:
        profile ? signatureForProfile(profile) : prev.processing.aurisCognitiveSafeguard.authorizedTemporalId,
    },
    algorithms: prev.processing.algorithms,
  };

  const updatedTransmissions = prev.output.transmissions.map((tx) => {
    const cycle: Record<typeof tx.status, typeof tx.status> = {
      queued: "transmitting",
      transmitting: "complete",
      complete: "queued",
    };
    const shouldAdvance = Math.random() > 0.76;
    if (!shouldAdvance) {
      if (tx.status === "complete" && Math.random() > 0.94) {
        return { ...tx, status: "queued" };
      }
      return tx;
    }
    return { ...tx, status: cycle[tx.status] };
  });

  const completedBefore = prev.output.transmissions.filter((tx) => tx.status === "complete").length;
  const completedAfter = updatedTransmissions.filter((tx) => tx.status === "complete").length;
  const completedDelta = Math.max(0, completedAfter - completedBefore);

  return {
    ...prev,
    timestamp: Date.now(),
    metrics: prev.metrics.map((metric) => {
      if (metric.id === "coherence") {
        const nextValue = coherenceRatio;
        return {
          ...metric,
          value: nextValue,
          change: Number((nextValue - metric.value).toFixed(3)),
        };
      }
      if (metric.id === "resonance") {
        const nextValue = resonanceRatio;
        return {
          ...metric,
          value: nextValue,
          change: Number((nextValue - metric.value).toFixed(3)),
        };
      }
      return metric;
    }),
    charts: resampledCharts,
    sensory: {
      ...prev.sensory,
      dataStreams: updatedStreams,
      celestialCartography: {
        ...prev.sensory.celestialCartography,
        solarAlignment: liveData.solarAlignment,
        lunarPhase: liveData.lunarPhase,
      },
    },
    processing: updatedProcessing,
    output: {
      ...prev.output,
      voicePipelines: {
        ...prev.output.voicePipelines,
        latencyMs: clamp(
          Math.round(prev.output.voicePipelines.latencyMs + (Math.random() - 0.5) * 18),
          120,
          220
        ),
        successfulTransmits: prev.output.voicePipelines.successfulTransmits + completedDelta,
      },
      commandQueue: {
        ...prev.output.commandQueue,
        queued: clamp(
          Math.round(prev.output.commandQueue.queued + (Math.random() - 0.5) * 1.2),
          2,
          7
        ),
        executing: clamp(
          Math.round(prev.output.commandQueue.executing + (Math.random() - 0.5) * 1.2),
          1,
          3
        ),
      },
      transmissions: updatedTransmissions,
    },
    bioProfile: updateBioProfile(prev.bioProfile, profile),
    schumannProtocol: updatedSchumannProtocol,
    quantumLink: updateQuantumLinkStatus(prev.quantumLink, profile),
    modeMatrix: prev.modeMatrix,
  };
};

export const useResampledNexusData = (refreshMs = 200, profile: AuthUser | null = null): RealtimeNexusData => {
  const nexus = useMemo(() => new NexusSystem(), []);
  const signature = signatureForProfile(profile);
  const [data, setData] = useState<RealtimeNexusData>(() => createInitialData(nexus, profile));
  const [liveCelestialData, setLiveCelestialData] = useState(() => {
    const now = new Date();
    return {
      solarAlignment: describeSolarAlignment(now),
      lunarPhase: describeLunarPhase(now),
    };
  });

  useEffect(() => {
    setData(createInitialData(nexus, profile));
  }, [nexus, signature]);

  useEffect(() => {
    const updateCelestial = () => {
      const now = new Date();
      const next = {
        solarAlignment: describeSolarAlignment(now),
        lunarPhase: describeLunarPhase(now),
      };

      setLiveCelestialData((prev) => {
        if (
          prev.solarAlignment === next.solarAlignment &&
          prev.lunarPhase === next.lunarPhase
        ) {
          return prev;
        }
        return next;
      });
    };

    updateCelestial();
    const intervalId = setInterval(updateCelestial, 60 * 60 * 1000);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setData((current) => computeNextData(current, nexus, liveCelestialData, profile));
    }, refreshMs);

    return () => clearInterval(id);
  }, [refreshMs, nexus, liveCelestialData, signature]);

  return data;
};
