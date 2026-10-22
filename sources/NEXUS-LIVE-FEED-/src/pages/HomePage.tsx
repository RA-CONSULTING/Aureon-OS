import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSero } from '@/contexts/SeroProvider';
import { useLiveNexusData } from '@/contexts/LiveNexusDataContext';
import { liveDataSourceRegistry } from '@/lib/liveDataSources';
import type { AuditRecord } from '@/lib/sero/sero-core';
import { SENSOR_STATE_NOTES, STREAM_METADATA, type SensorState } from '@/data/streamMetadata';

import ChronicleGovernanceTab, { type ChronicleGovernance } from '../components/ChronicleGovernanceTab';
import BioProfilePanel from '../components/BioProfilePanel';
import LiveRealtimeCharts from '../components/LiveRealtimeCharts';
import LiveVisualizationTab, { type VisualizationModule } from '../components/LiveVisualizationTab';
import SystemHarmonicFlow, { type SystemFlowStage } from '../components/SystemHarmonicFlow';
import ModeMatrixPanel from '../components/ModeMatrixPanel';
import CelestialCalendarTab from '../components/CelestialCalendarTab';
import ForecastTabs from '../components/ForecastTabs';
import OutputCommandTab from '../components/OutputCommandTab';
import ProcessingCoreTab from '../components/ProcessingCoreTab';
import BlockchainMiningTab, {
  type EnergyChannel,
  type MiningMetric,
  type MiningNode,
} from '../components/BlockchainMiningTab';
import RecordingSystemsTab, { type RecordingChannel } from '../components/RecordingSystemsTab';
import SensoryLayerTab from '../components/SensoryLayerTab';
import DimensionalDialerTab from '../components/DimensionalDialerTab';
import VisualRelayTab from '../components/VisualRelayTab';
import LiveStreamShowcase from '../components/LiveStreamShowcase';
import TemporalAuraScanTab from '../components/TemporalAuraScanTab';
import TemporalBiofieldScanTab from '../components/TemporalBiofieldScanTab';


type SensorStream = {
  id: string;
  name: string;
  location: string;
  intensity: number; // percentage 0-100
  state: SensorState;
  note: string;
  rate: number;
  unit: string;
  capacity: number;
};

type ProcessingStatus = 'Nominal' | 'Balancing' | 'Calibrating';

type ProcessingLane = {
  id: string;
  name: string;
  load: number; // 0-1
  status: ProcessingStatus;
  note: string;
};

type TransmissionStatus = 'Queued' | 'Transmitting' | 'Complete';

type Transmission = {
  id: string;
  channel: string;
  target: string;
  status: TransmissionStatus;
};

type VaultStatus = Record<string, { present: boolean; masked: string }>;

type MetricSummary = {
  id: string;
  label: string;
  value: string;
  status: 'stable' | 'watch' | 'alert';
  hint: string;
};

type HomePageProps = {
  renderFullConsole?: boolean;
};
 
const BLOCKCHAIN_MINING_METRICS: MiningMetric[] = [
  {
    id: 'hashrate',
    label: 'Global Hashrate',
    value: '3.82 PH/s',
    delta: '6.4%',
    trend: 'up',
    description: 'Aggregate plasma rigs bonded across 12 sanctum vaults.',
  },
  {
    id: 'block-height',
    label: 'Block Height',
    value: '1,204,553',
    delta: '12 blocks',
    trend: 'up',
    description: 'Last 24 minutes include 2 auric governance checkpoints.',
  },
  {
    id: 'validation-latency',
    label: 'Validation Latency',
    value: '1.8 s',
    delta: '0.2 s',
    trend: 'down',
    description: 'Median confirmation round-trip across entangled relays.',
  },
  {
    id: 'pool-efficiency',
    label: 'Pool Efficiency',
    value: '98.6%',
    delta: '0.4%',
    trend: 'stable',
    description: 'Share fidelity after spirit-proof consensus reconciliation.',
  },
];

const BLOCKCHAIN_MINING_NODES: MiningNode[] = [
  {
    id: 'node-aurora',
    name: 'Aurora-Theta Rig',
    location: 'Arctic Sky Temple',
    hashRate: '1.28 PH/s',
    status: 'Online',
    uptime: '99.982%',
    energy: 'Hydro · Aurora Flux',
    consensusRole: 'Block Forger',
  },
  {
    id: 'node-solstice',
    name: 'Solstice Core',
    location: 'Solaris Desert Array',
    hashRate: '0.97 PH/s',
    status: 'Syncing',
    uptime: '99.421%',
    energy: 'Solar Spiral Farms',
    consensusRole: 'Finality Anchor',
  },
  {
    id: 'node-lumina',
    name: 'Lumina Sanctuary',
    location: 'Subterranean Crystal Vault',
    hashRate: '1.57 PH/s',
    status: 'Online',
    uptime: '100%',
    energy: 'Geothermal Resonance',
    consensusRole: 'Oracle Steward',
  },
];

const BLOCKCHAIN_LEDGER_HIGHLIGHTS: string[] = [
  'Cross-chain attestation finalized for Eden Scroll channel 72 without variance.',
  'Guardian quorum signed zero-knowledge audit digest · no covenant breaches detected.',
  'Entangled witness mesh reports 0 orphan blocks in the last 18-hour cycle.',
];

const BLOCKCHAIN_ENERGY_MIX: EnergyChannel[] = [
  { id: 'hydro', source: 'Hydro Plasmic Falls', percentage: 46, status: 'Primary' },
  { id: 'solar', source: 'Solar Spiral Arrays', percentage: 32, status: 'Supplemental' },
  { id: 'geothermal', source: 'Geothermal Resonance Wells', percentage: 22, status: 'Reserve' },
];

const RECORDING_CHANNELS: RecordingChannel[] = [
  {
    id: 'audio',
    title: 'Audio Capture',
    status: 'Operational',
    summary: 'Ceremonial dual-mic array with infrasound capture.',
    metrics: [
      { label: 'Sample Rate', value: '96 kHz', hint: 'High fidelity archival recording.' },
      { label: 'Bit Depth', value: '24-bit', hint: 'Preserves subtle harmonic textures.' },
      { label: 'Channels', value: 'Stereo + Infrasound', hint: 'Includes subterranean resonance feed.' },
      { label: 'Format', value: 'BWF / FLAC', hint: 'Broadcast Wave with lossless mirror.' },
    ],
  },
  {
    id: 'love-frequency',
    title: 'Love Frequency Field',
    status: 'Operational',
    summary: 'Multidimensional capture of physiological, electromagnetic, emotional, and consciousness love metrics.',
    metrics: [
      {
        label: 'Physiological Metrics',
        value: 'HRV · Oxytocin · Dopamine',
        hint: 'Continuous ECG, neurochemical flux, and vagus coherence during love states.',
      },
      {
        label: 'Electromagnetic Signatures',
        value: 'Heart Field Radius · Coherence',
        hint: 'SQUID magnetometers trace entanglement strength and resonance frequency bands.',
      },
      {
        label: 'Emotional Intelligence',
        value: 'Compassion · Empathy · Attachment',
        hint: 'AI resonance models interpret vulnerability, forgiveness, and unity consciousness.',
      },
      {
        label: 'Consciousness Love Field',
        value: 'Unity Level 0.98',
        hint: 'Collective resonance trackers log unconditional love coherence across the Harmonic Nexus.',
      },
    ],
  },
  {
    id: 'rf-spectrum',
    title: 'RF Spectrum',
    status: 'Operational',
    summary: 'Wideband IQ streaming of atmospheric and cosmic carriers.',
    metrics: [
      { label: 'Frequency Range', value: '0.1 MHz – 6 GHz', hint: 'LF through microwave signature capture.' },
      { label: 'Bandwidth', value: '20 MHz', hint: 'Realtime demodulation window.' },
      { label: 'Mode', value: 'IQ Streaming', hint: 'Complex samples for coherent decoding.' },
      { label: 'Antenna', value: 'Discone + VLF Loop', hint: 'Dual array for sky and ground wave.' },
    ],
  },
  {
    id: 'magnetic',
    title: 'Magnetic Field',
    status: 'Operational',
    summary: 'Fluxgate triaxial lattice for geomagnetic resonance.',
    metrics: [
      { label: 'Sensor', value: 'Fluxgate Triaxial', hint: 'Vector capture with pT sensitivity.' },
      { label: 'Resolution', value: '0.1 nT', hint: 'Micro-variation perception threshold.' },
      { label: 'Sampling', value: '1 kHz', hint: 'Temporal quantum security pipeline.' },
      { label: 'Calibration', value: 'Auto', hint: 'Self-tuning every 12 minutes.' },
    ],
  },
  {
    id: 'environmental',
    title: 'Environmental',
    status: 'Operational',
    summary: 'Ambient field monitors for climate and radiation context.',
    metrics: [
      { label: 'Temperature', value: '±0.1°C', hint: 'Lab-grade thermal sensors.' },
      { label: 'Humidity', value: '±2% RH', hint: 'Compensated for dew point drift.' },
      { label: 'Pressure', value: '±0.1 hPa', hint: 'Barometric stabilization feed.' },
      { label: 'Radiation', value: 'Geiger Counter', hint: 'Ionizing particle watch channel.' },
    ],
  },
];

const CHRONICLE_GOVERNANCE: ChronicleGovernance = {
  sections: [
    {
      id: 'source-law',
      title: 'Source Law 10-9-1',
      badge: 'Integrity 100%',
      description: 'Directive enforcement lattice for sacred data handling.',
      metrics: [
        { label: 'Check Directives', value: '847' },
        { label: 'Redact Rules', value: '23' },
        { label: 'Transactions', value: 'All Atomic' },
        { label: 'Integrity Score', value: '100%' },
      ],
    },
    {
      id: 'data-governance',
      title: 'Data Governance',
      badge: 'AES-256',
      description: 'Encryption, signature, and checksum assurance.',
      metrics: [
        { label: 'Encryption', value: 'AES-256' },
        { label: 'Signatures', value: 'Ed25519' },
        { label: 'Checksums', value: 'SHA-256' },
        { label: 'Backups', value: '3× Redundant' },
      ],
    },
    {
      id: 'chronicle-vault',
      title: 'Chronicle Vault',
      badge: 'Retrieval < 2s',
      description: 'Compression, archival, and retrieval command vault.',
      metrics: [
        { label: 'Vault Size', value: '15.7 TB' },
        { label: 'Compression', value: '4.2 : 1' },
        { label: 'Archival Rate', value: '99.9%' },
        { label: 'Access Time', value: '< 2 s' },
      ],
    },
  ],
  highlights: [
    'Auto-validation sweep confirms zero unresolved anomalies this cycle.',
    'Triplicate backups distributed across temple, field, and orbital vaults.',
    'Temporal checksum beacons synced with Schumann resonance for continuity.',
  ],
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const laneStatusFor = (load: number): ProcessingStatus => {
  if (load >= 0.88) {
    return 'Calibrating';
  }
  if (load >= 0.78) {
    return 'Balancing';
  }
  return 'Nominal';
};

const metricLabel = (status: 'stable' | 'watch' | 'alert') =>
  status === 'stable' ? 'Stable' : status === 'watch' ? 'Watch' : 'Review';

const metricBadgeStyles: Record<MetricSummary['status'], string> = {
  stable: 'border-emerald-400/40 bg-emerald-500/20 text-emerald-100 shadow-[0_0_25px_rgba(16,185,129,0.45)]',
  watch: 'border-amber-300/40 bg-amber-500/20 text-amber-100 shadow-[0_0_25px_rgba(251,191,36,0.35)]',
  alert: 'border-rose-400/40 bg-rose-500/25 text-rose-100 shadow-[0_0_25px_rgba(244,63,94,0.35)]',
};

const stageStatusFromSensor = (state?: SensorState): SystemFlowStage['status'] => {

  if (state === 'Anomaly') {
    return 'alert';
  }
  if (state === 'Watch') {
    return 'watch';
  }
  return 'stable';
};

const {
  version: DATA_SOURCE_VERSION,
  sources: DATA_SOURCES,
} = liveDataSourceRegistry;

const HomePage = ({ renderFullConsole = false }: HomePageProps) => {
  const { audit } = useSero();
  const {
    metrics: liveMetrics,
    sensory,
    processing: processingData,
    output,
    timestamp,
    bioProfile,
    schumannProtocol,
    modeMatrix,
    quantumLink,
  } = useLiveNexusData();

  const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);
  const [vaultError, setVaultError] = useState<string | null>(null);

  useEffect(() => {
    if (!renderFullConsole) {
      return;
    }

    let active = true;
    fetch('/api/keys-status')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<VaultStatus>;
      })
      .then((data) => {
        if (active) setVaultStatus(data);
      })
      .catch((error) => {
        if (active) setVaultError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      active = false;
    };
  }, [renderFullConsole]);

  const sensors = useMemo<SensorStream[]>(() => {
    const dataStreams = sensory?.dataStreams ?? [];
    return dataStreams.map((stream) => {
      const meta = STREAM_METADATA[stream.id] ?? { location: 'Unknown Node', capacity: 100 };
      const normalized = clamp((stream.rate / meta.capacity) * 100, 0, 100);
      const state: SensorState = stream.state === 'degraded' || normalized >= 90
        ? 'Anomaly'
        : stream.state === 'updating' || normalized >= 72
          ? 'Watch'
          : 'Stable';

      return {
        id: stream.id,
        name: stream.name,
        location: meta.location,
        intensity: Number(normalized.toFixed(1)),
        state,
        note: SENSOR_STATE_NOTES[state],
        rate: Number(stream.rate.toFixed(1)),
        unit: stream.unit,
        capacity: meta.capacity,
      };
    });
  }, [sensory]);

  const processing = useMemo<ProcessingLane[]>(() => {
    if (!processingData) {
      return [];
    }

    const qssrLoad = clamp(0.65 + (1 - processingData.qssrModule.solarCoherenceIndex) * 0.5, 0, 1);
    const stormLoad = clamp(processingData.stormTargeting.harmonicIntegration / 100, 0, 1);
    const safeguardLoad = clamp(0.45 + processingData.aurisCognitiveSafeguard.dampeningFactor * 0.5, 0, 1);

    const lanes: ProcessingLane[] = [
      {
        id: 'harmonics',
        name: 'Harmonic Coherence Synthesizer',
        load: Number(qssrLoad.toFixed(2)),
        status: laneStatusFor(qssrLoad),
        note: `Coherence ${(processingData.qssrModule.solarCoherenceIndex * 100).toFixed(0)}% · Queue ${processingData.qssrModule.analysisQueue}`,
      },
      {
        id: 'storm-mapper',
        name: 'Storm Trajectory Mapper',
        load: Number(stormLoad.toFixed(2)),
        status: laneStatusFor(stormLoad),
        note: `Neutralization ${processingData.stormTargeting.neutralizationRate}% · Patterns ${processingData.stormTargeting.activePatterns}`,
      },
      {
        id: 'ethics',
        name: 'Prime Ethics Correlator',
        load: Number(safeguardLoad.toFixed(2)),
        status: laneStatusFor(safeguardLoad),
        note: `Safeguard ${processingData.aurisCognitiveSafeguard.status} · Hazards ${processingData.aurisCognitiveSafeguard.hazardDetections}`,
      },
    ];

    return lanes;
  }, [processingData]);

  const transmissions = useMemo<Transmission[]>(() => {
    const records = output?.transmissions ?? [];
    return records.map((tx) => ({
      id: tx.id,
      channel: tx.channel,
      target: tx.destination,
      status:
        tx.status === 'transmitting'
          ? 'Transmitting'
          : tx.status === 'complete'
            ? 'Complete'
            : 'Queued',
    }));
  }, [output]);

  const metrics = useMemo<MetricSummary[]>(() => {
    if (!renderFullConsole) {
      return [];
    }

    const summaries: MetricSummary[] = [];

    const monitoringSession = schumannProtocol?.monitoringSession;
    if (monitoringSession) {
      const averageCoherence = monitoringSession.trendAnalysis.averageCoherence ?? 0;
      const anomalyRate = monitoringSession.trendAnalysis.anomalyRate ?? 0;
      const fundamentalPower =
        monitoringSession.trendAnalysis.harmonicTrends.fundamental?.averagePower ?? 0;
      const snapshotCount = monitoringSession.totalSnapshots;
      const tone: MetricSummary['status'] =
        averageCoherence >= 0.8 ? 'stable' : averageCoherence >= 0.6 ? 'watch' : 'alert';
      const anomalyPercent = Math.round(anomalyRate * 100);

      summaries.push({
        id: 'schumann-coherence',
        label: 'Schumann Coherence',
        value: `${(averageCoherence * 100).toFixed(1)}%`,
        status: tone,
        hint: `Snapshots ${snapshotCount} · Fundamental ${(fundamentalPower * 100).toFixed(0)}% · Anomaly ${anomalyPercent}%`,
      });
    }

    if (sensors.length && processing.length) {
      const stableSensors = sensors.filter((stream) => stream.state === 'Stable').length;
      const sensorIntegrity = stableSensors / sensors.length;
      const averageIntensity =
        sensors.reduce((sum, stream) => sum + stream.intensity, 0) / sensors.length;
      const averageLoad = processing.reduce((sum, lane) => sum + lane.load, 0) / processing.length;
      const activeTransmissions = transmissions.filter((tx) => tx.status !== 'Complete').length;

      const coherenceMetric = liveMetrics.find((metric) => metric.id === 'coherence');
      const resonanceMetric = liveMetrics.find((metric) => metric.id === 'resonance');
      const coherence = coherenceMetric ? coherenceMetric.value : 0;
      const resonance = resonanceMetric ? resonanceMetric.value : 0;
      const nexusHealth = sensorIntegrity * 0.3 + coherence * 0.4 + resonance * 0.3;

      summaries.push(
        {
          id: 'nexus-health',
          label: 'Nexus Health',
          value: `${Math.round(nexusHealth * 100)}%`,
          status: nexusHealth > 0.88 ? 'stable' : nexusHealth > 0.72 ? 'watch' : 'alert',
          hint: 'Overall system stability and coherence',
        },
        {
          id: 'sensor-integrity',
          label: 'Sensor Integrity',
          value: `${Math.round(sensorIntegrity * 100)}%`,
          status: sensorIntegrity === 1 ? 'stable' : sensorIntegrity > 0.75 ? 'watch' : 'alert',
          hint:
            sensorIntegrity === 1
              ? 'All stations synchronized'
              : 'Attractors balancing minor variance',
        },
        {
          id: 'field-intensity',
          label: 'Average Field Intensity',
          value: `${averageIntensity.toFixed(1)}%`,
          status: averageIntensity > 86 ? 'alert' : averageIntensity > 74 ? 'watch' : 'stable',
          hint: 'Magnetometer and ionosphere composite',
        },
        {
          id: 'processing-load',
          label: 'Processing Load',
          value: `${Math.round(averageLoad * 100)}%`,
          status: averageLoad > 0.86 ? 'alert' : averageLoad > 0.76 ? 'watch' : 'stable',
          hint: 'Quantum synchronizers utilization',
        },
        {
          id: 'open-commands',
          label: 'Open Command Paths',
          value: `${activeTransmissions}`,
          status: activeTransmissions > 2 ? 'watch' : 'stable',
          hint: 'Sessions awaiting completion',
        }
      );
    }

    return summaries;
  }, [renderFullConsole, processing, sensors, transmissions, liveMetrics, schumannProtocol]);

  const resonanceMetric = useMemo(
    () => liveMetrics.find((metric) => metric.id === 'resonance'),
    [liveMetrics]
  );
  const coherenceMetric = useMemo(
    () => liveMetrics.find((metric) => metric.id === 'coherence'),
    [liveMetrics]
  );
  const heartMetric = useMemo(
    () => bioProfile?.metrics.find((metric) => metric.id === 'cardiac'),
    [bioProfile]
  );
  const quantumHandshake = quantumLink?.handshakeState ?? 'idle';

  const systemFlowStages = useMemo<SystemFlowStage[]>(() => {
    const eckStream = sensors.find((stream) => stream.id === 'phenomena');
    const eckProgress = eckStream ? clamp(eckStream.intensity / 100, 0, 1) : undefined;
    const eckMetricLabel = eckStream ? eckStream.name : 'Witnessed Phenomena';
    const eckMetricValue = eckStream ? `${eckStream.rate} ${eckStream.unit}` : 'Stream calibrating';
    const eckHint = eckStream
      ? `${eckStream.location} · ${eckStream.note}`
      : 'Awaiting witness array handshake.';

    const attunement = clamp(quantumLink?.observerAttunement ?? 0.62, 0, 1);
    const akashicStatus: SystemFlowStage['status'] =
      attunement >= 0.86 ? 'stable' : attunement >= 0.68 ? 'watch' : 'alert';
    const solarAlignment = sensory?.celestialCartography.solarAlignment ?? 'Aligning';
    const handshake = quantumHandshake;
    const snapshots = schumannProtocol?.monitoringSession.totalSnapshots ?? 0;

    const harmonicProgress = resonanceMetric ? clamp(resonanceMetric.value, 0, 1) : undefined;
    const harmonicStatus: SystemFlowStage['status'] =
      harmonicProgress !== undefined
        ? harmonicProgress >= 0.88
          ? 'stable'
          : harmonicProgress >= 0.72
            ? 'watch'
            : 'alert'
        : 'watch';
    const averageLoadPercent = processing.length
      ? Math.round((processing.reduce((sum, lane) => sum + lane.load, 0) / processing.length) * 100)
      : 0;
    const activeTransmissions = transmissions.filter((tx) => tx.status !== 'Complete').length;
    const harmonicMetricValue = resonanceMetric
      ? `${(resonanceMetric.value * 100).toFixed(1)}% harmonic`
      : 'Calibrating';
    const harmonicHint = `Processing load ${averageLoadPercent}% · Active uplinks ${activeTransmissions} · Coherence ${
      coherenceMetric ? (coherenceMetric.value * 100).toFixed(1) : '—'
    }%`;

    const heartStatus: SystemFlowStage['status'] = heartMetric ? heartMetric.tone : 'watch';
    const heartRange = heartMetric?.targetRange ?? [0, 1];
    const loveProgress =
      heartMetric && heartRange[1] !== heartRange[0]
        ? clamp((heartMetric.value - heartRange[0]) / (heartRange[1] - heartRange[0]), 0, 1)
        : undefined;
    const heartMetricValue = heartMetric
      ? `${heartMetric.value} ${heartMetric.unit}`
      : 'Awaiting attunement';
    const heartHint = heartMetric
      ? `Target ${heartRange[0]}–${heartRange[1]} ${heartMetric.unit} · Streams ${bioProfile?.streams.length ?? 0} synchronized.`
      : 'Link a bio-profile to activate heart wave analytics.';
    const heartDisplay = bioProfile?.displayName ?? 'Collective field';

    const stages: SystemFlowStage[] = [
      {
        id: 'eckoushic',
        title: 'Eckoushic',
        subtitle: 'Sound',
        formula: 'y_Eck = dΨ/dt',
        description:
          'Raw auditory phenomena are captured as living equations, shaping the sonic lattice for downstream transmutation.',
        metricLabel: eckMetricLabel,
        metricValue: eckMetricValue,
        metricHint: eckHint,
        status: stageStatusFromSensor(eckStream?.state),
        progress: eckProgress,
        accent: 'from-amber-400/35 via-rose-400/25 to-transparent',
        nextLabel: 'Akashic Light',
      },
      {
        id: 'akashic',
        title: 'Akashic',
        subtitle: 'Light',
        formula: 'y_Aka = ∫ Ψ_Eck dt',
        description:
          'Sound equations refract into akashic light signatures, illuminating multi-spectrum guidance pathways.',
        metricLabel: 'Attunement Field',
        metricValue: `${Math.round(attunement * 100)}% attuned`,
        metricHint: `Solar alignment ${solarAlignment} · Handshake ${handshake.toUpperCase()} · Snapshots ${snapshots}`,
        status: akashicStatus,
        progress: attunement,
        accent: 'from-sky-500/35 via-indigo-500/30 to-violet-500/30',
        nextLabel: 'Resonance Bridge',
      },
      {
        id: 'harmonic-nexus',
        title: 'Harmonic Nexus',
        subtitle: 'Resonance',
        formula: 'y_coherent',
        description:
          'Quantum synchronizers braid sound and light streams into a coherent resonance ready for command orchestration.',
        metricLabel: 'Resonant Integrity',
        metricValue: harmonicMetricValue,
        metricHint: harmonicHint,
        status: harmonicStatus,
        progress: harmonicProgress,
        accent: 'from-fuchsia-500/35 via-sky-500/25 to-amber-400/25',
        nextLabel: 'Heart Wave',
      },
      {
        id: 'heart-wave',
        title: 'Heart Wave',
        subtitle: 'Love',
        formula: 'Ψ_heart → ∞',
        description: `${heartDisplay}'s heart field broadcasts a compassion waveform that seals the Nexus in coherent love.`,
        metricLabel: 'Cardiac Resonance',
        metricValue: heartMetricValue,
        metricHint: heartHint,
        status: heartStatus,
        progress: loveProgress,
        accent: 'from-rose-500/40 via-amber-400/30 to-emerald-400/30',
        icon: '❤️',
      },
    ];

    return stages;
  }, [
    sensors,
    sensory,
    quantumLink,
    quantumHandshake,
    schumannProtocol,
    resonanceMetric,
    coherenceMetric,
    processing,
    transmissions,
    heartMetric,
    bioProfile,
  ]);

  const systemFlowStatus = useMemo(() => {
    const readiness: string[] = [];

    if (!sensors.length) {
      readiness.push('sensor array handshake');
    }
    if (!resonanceMetric) {
      readiness.push('resonance telemetry');
    }
    if (!heartMetric) {
      readiness.push('heart field link');
    }
    if (quantumHandshake !== 'entangled') {
      readiness.push('quantum link entanglement');
    }

    if (readiness.length === 0) {
      return {
        live: true,
        message: 'Streaming live telemetry across sound, light, resonance, and love pillars.',
      };
    }

    const formatted =
      readiness.length === 1
        ? readiness[0]
        : `${readiness.slice(0, -1).join(', ')} & ${readiness[readiness.length - 1]}`;

    return {
      live: false,
      message: `Awaiting ${formatted} to stabilize.`,
    };
  }, [sensors.length, resonanceMetric, heartMetric, quantumHandshake]);

  const visualizationModules = useMemo<VisualizationModule[]>(() => {
    if (!renderFullConsole) {
      return [];
    }

    const formatRatio = (value: number) => `${(value * 100).toFixed(1)}%`;
    const ratioTone = (value: number): VisualizationMetric['tone'] =>
      value >= 0.86 ? 'stable' : value >= 0.72 ? 'watch' : 'alert';
    const percentTone = (value: number): VisualizationMetric['tone'] =>
      value >= 85 ? 'stable' : value >= 65 ? 'watch' : 'alert';
    const queueTone = (queued: number): VisualizationMetric['tone'] =>
      queued <= 4 ? 'stable' : queued <= 6 ? 'watch' : 'alert';
    const solarTone = (alignment?: string): VisualizationMetric['tone'] => {
      if (!alignment) return 'watch';
      const normalized = alignment.toLowerCase();
      if (normalized.includes('optimal') || normalized.includes('locked')) return 'stable';
      if (normalized.includes('adjust') || normalized.includes('balancing')) return 'watch';
      return 'alert';
    };
    const solarProgress = (alignment?: string) => {
      const tone = solarTone(alignment);
      if (tone === 'stable') return 1;
      if (tone === 'watch') return 0.6;
      return 0.3;
    };

    const toneFromStreamState = (state?: string): VisualizationMetric['tone'] => {
      if (!state) return 'watch';
      if (state === 'stable') return 'stable';
      if (state === 'updating') return 'watch';
      return 'alert';
    };

    const coherenceColorBand = (value: number) => {
      if (value >= 0.92) return 'Violet (unity)';
      if (value >= 0.78) return 'Indigo (aligning)';
      if (value >= 0.6) return 'Amber (balancing)';
      return 'Crimson (chaos)';
    };

    const toneWeight: Record<'stable' | 'watch' | 'alert', number> = {
      stable: 1,
      watch: 0.62,
      alert: 0.28,
    };

    const coherenceMetric = liveMetrics.find((metric) => metric.id === 'coherence');
    const resonanceMetric = liveMetrics.find((metric) => metric.id === 'resonance');
    const chronicleMetric = liveMetrics.find((metric) => metric.id === 'chronicle');
    const aureonMetric = liveMetrics.find((metric) => metric.id === 'aureon');

    const coherenceRatio = clamp(coherenceMetric?.value ?? 0, 0, 1);
    const resonanceRatio = clamp(resonanceMetric?.value ?? 0, 0, 1);
    const chronicleValue = chronicleMetric?.value ?? sensory?.chronicleRecorder.eventsPerMinute ?? 0;
    const chronicleTarget = chronicleMetric?.target ?? 180;
    const chronicleProgress = chronicleTarget ? clamp(chronicleValue / chronicleTarget, 0, 1) : undefined;
    const aureonPercent = clamp(aureonMetric?.value ?? 0, 0, 100);

    const streams = sensory?.dataStreams ?? [];
    const totalStreams = streams.length;
    const stableStreams = streams.filter((stream) => stream.state === 'stable').length;
    const watchStreams = streams.filter((stream) => stream.state !== 'stable').length;
    const streamIntegrity = totalStreams ? stableStreams / totalStreams : 0;

    const chronicleRecorder = sensory?.chronicleRecorder;
    const celestial = sensory?.celestialCartography;

    const voice = output?.voicePipelines;
    const queue = output?.commandQueue;
    const compliance = output?.compliance;
    const transmissions = output?.transmissions ?? [];
    const totalTransmissions = transmissions.length;
    const completedTransmissions = transmissions.filter((tx) => tx.status === 'complete').length;
    const activeTransmissions = transmissions.filter((tx) => tx.status !== 'complete').length;
    const transmittingCount = transmissions.filter((tx) => tx.status === 'transmitting').length;

    const latencyTone = (latency?: number): VisualizationMetric['tone'] => {
      if (latency === undefined) return undefined;
      if (latency <= 180) return 'stable';
      if (latency <= 210) return 'watch';
      return 'alert';
    };

    const complianceTone = (level?: string): VisualizationMetric['tone'] => {
      if (!level) return 'watch';
      const normalized = level.toLowerCase();
      if (normalized === 'none' || normalized === 'low') return normalized === 'none' ? 'stable' : 'watch';
      if (normalized.includes('advisory')) return 'watch';
      return 'alert';
    };

    const latencyProgress = voice ? clamp(1 - (voice.latencyMs - 120) / 120, 0, 1) : undefined;
    const queueProgress = queue
      ? clamp(queue.executing / Math.max(queue.executing + queue.queued, 1), 0, 1)
      : undefined;
    const complianceProgress = compliance ? clamp(compliance.auditsPassed / 24, 0, 1) : undefined;
    const transmissionProgress = totalTransmissions
      ? clamp(completedTransmissions / totalTransmissions, 0, 1)
      : undefined;

    const lastSync = new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    const schumannTrend = schumannProtocol?.monitoringSession.trendAnalysis;
    const averageSchumannCoherence = clamp(schumannTrend?.averageCoherence ?? coherenceRatio, 0, 1);
    const metricDiversity = clamp(schumannProtocol?.coherenceReport.metricDiversity ?? resonanceRatio, 0, 1);
    const trendDepth = clamp(schumannProtocol?.coherenceReport.trendAnalysisDepth ?? resonanceRatio, 0, 1);
    const anomalyRate = clamp(schumannTrend?.anomalyRate ?? 0, 0, 1);
    const dataComprehensiveness = clamp(
      schumannProtocol?.coherenceReport.dataComprehensiveness ?? resonanceRatio,
      0,
      1
    );
    const geometryStream = streams.find((stream) => stream.id === 'geometry');
    const geometryCapacity = STREAM_METADATA.geometry?.capacity ?? 120;
    const geometryFlow = geometryStream ? clamp(geometryStream.rate / geometryCapacity, 0, 1) : 0;
    const timelineDurationMinutes = schumannProtocol?.monitoringSession.durationMinutes ?? 0;
    const timelineWindow =
      timelineDurationMinutes >= 60
        ? `${(timelineDurationMinutes / 60).toFixed(1)} h`
        : timelineDurationMinutes > 1
          ? `${Math.round(timelineDurationMinutes)} min`
          : 'Initializing';
    const awakeningIndex = (() => {
      const metrics = bioProfile?.metrics ?? [];
      if (!metrics.length) return 0;
      const total = metrics.reduce((sum, metric) => sum + toneWeight[metric.tone], 0);
      return clamp(total / metrics.length, 0, 1);
    })();
    const domainInputs = sensors.length + (processingData?.algorithms?.length ?? 0) + (bioProfile?.streams?.length ?? 0);
    const activeDomains = Math.min(21, Math.round(domainInputs));
    const domainActivation = clamp(activeDomains / 21, 0, 1);
    const gammaFloor = modeMatrix?.safety_hooks?.gamma_floor;
    const gammaLevel = clamp(quantumLink?.observerAttunement ?? 0, 0, 1);
    const akashicTone: VisualizationMetric['tone'] =
      gammaLevel >= 0.945 ? 'stable' : gammaLevel >= 0.88 ? 'watch' : 'alert';
    const entanglementIndex = clamp(streamIntegrity * 0.6 + gammaLevel * 0.4, 0, 1);
    const entangledPairs = Math.round(entanglementIndex * 10_000_000);
    const harmonyIndex = clamp(1 - anomalyRate, 0, 1);
    const zeroPointFlux = clamp(processingData?.qssrModule.solarCoherenceIndex ?? resonanceRatio, 0, 1);
    const geometryTone = toneFromStreamState(geometryStream?.state);
    const geometryLocation = STREAM_METADATA.geometry?.location ?? 'Sacred Geometry Observatory';
    const emotionalLabel = (() => {
      if (harmonyIndex >= 0.78) return 'Rainbow Bloom';
      if (harmonyIndex >= 0.58) return 'Aurora Drift';
      return 'Stormfront';
    })();

    return [
      {
        id: 'bio-resonance-core',
        title: 'Bio-Resonance Core',
        summary:
          processingData
            ? `${processingData.qssrModule.cosmicWeather} skies · Queue ${processingData.qssrModule.analysisQueue}`
            : 'Awaiting QSSR synchronizer handshake.',
        status: processingData?.qssrModule.planetaryResonance
          ? `${processingData.qssrModule.planetaryResonance} · ${lastSync}`
          : `Synced ${lastSync}`,
        metrics: [
          {
            label: 'System Coherence',
            value: formatRatio(coherenceRatio),
            hint: `Cosmic weather ${processingData?.qssrModule.cosmicWeather ?? 'calibrating'}.`,
            tone: ratioTone(coherenceRatio),
            progress: coherenceRatio,
          },
          {
            label: 'Resonance Harmony',
            value: formatRatio(resonanceRatio),
            hint: `Sentinel lattice ${processingData?.stormTargeting.status ?? 'tuning phase'}.`,
            tone: ratioTone(resonanceRatio),
            progress: resonanceRatio,
          },
          {
            label: 'Chronicle Throughput',
            value: `${Math.round(chronicleValue)} evt/min`,
            hint: `Target ${chronicleTarget} · Storage ${chronicleRecorder?.storageUsedTb ?? 0} TB`,
            tone: percentTone(Math.min(chronicleProgress ?? 0, 1) * 100),
            progress: chronicleProgress,
          },
          {
            label: 'Aureon Activity',
            value: `${Math.round(aureonPercent)}%`,
            hint: `Cognitive safeguard ${processingData?.aurisCognitiveSafeguard.status ?? 'idle'}.`,
            tone: percentTone(aureonPercent),
            progress: aureonPercent / 100,
          },
        ],
      },
      {
        id: 'sensory-stream-lattice',
        title: 'Sensory Stream Lattice',
        summary:
          totalStreams > 0
            ? `${stableStreams} stable · ${watchStreams} balancing across ${totalStreams} channels.`
            : 'Awaiting sensory array link.',
        status: celestial?.harmonicSignatures,
        metrics: [
          {
            label: 'Active Streams',
            value: totalStreams ? `${stableStreams}/${totalStreams} stable` : 'No channels',
            hint: `Integrity ${(streamIntegrity * 100).toFixed(0)}% across the mesh.`,
            tone: ratioTone(streamIntegrity),
            progress: totalStreams ? streamIntegrity : undefined,
          },
          {
            label: 'Streams on Watch',
            value: `${watchStreams}`,
            hint:
              watchStreams === 0
                ? 'All channels within harmonic band.'
                : 'Balancing flux across regional nodes.',
            tone: watchStreams === 0 ? 'stable' : watchStreams <= 2 ? 'watch' : 'alert',
            progress: totalStreams ? clamp(watchStreams / totalStreams, 0, 1) : undefined,
          },
          {
            label: 'Chronicle Recorder',
            value: chronicleRecorder
              ? `${chronicleRecorder.status} @ ${chronicleRecorder.eventsPerMinute} evt/min`
              : 'Offline',
            hint: chronicleRecorder
              ? `Retention ${chronicleRecorder.retentionHours}h · Integrity ${chronicleRecorder.integrityChecks}`
              : 'No recorder handshake detected.',
            tone: chronicleRecorder?.status === 'Recording' ? 'stable' : 'watch',
            progress: chronicleRecorder ? clamp(chronicleRecorder.retentionHours / 72, 0, 1) : undefined,
          },
          {
            label: 'Celestial Alignment',
            value: celestial
              ? `${celestial.solarAlignment} · ${celestial.lunarPhase}`
              : 'Alignment unknown',
            hint: celestial
              ? `Tracking ${celestial.trackingSatellites} satellites.`
              : 'Orbital telemetry pending.',
            tone: solarTone(celestial?.solarAlignment),
            progress: solarProgress(celestial?.solarAlignment),
          },
        ],
      },
      {
        id: 'operator-command-bridge',
        title: 'Operator Command Bridge',
        summary:
          output
            ? `${activeTransmissions} uplinks live · Compliance ${compliance?.status ?? 'Unknown'}.`
            : 'Command bridge establishing secure link.',
        status: voice ? `Voices ${voice.activeVoices}` : undefined,
        metrics: [
          {
            label: 'Voice Pipeline Latency',
            value: voice ? `${voice.latencyMs} ms` : '—',
            hint: voice
              ? `${voice.activeVoices} active voices · ${voice.successfulTransmits} transmits`
              : 'No active voice circuits.',
            tone: latencyTone(voice?.latencyMs),
            progress: latencyProgress,
          },
          {
            label: 'Command Queue',
            value: queue
              ? `${queue.executing} executing · ${queue.queued} queued`
              : 'Queue offline',
            hint: queue ? `Last command: ${queue.lastCommand}` : 'Awaiting queue handshake.',
            tone: queue ? queueTone(queue.queued) : undefined,
            progress: queueProgress,
          },
          {
            label: 'Compliance Shield',
            value: compliance ? compliance.status : 'Unknown',
            hint: compliance
              ? `Audits ${compliance.auditsPassed} · Escalation ${compliance.escalationLevel}`
              : 'Compliance node offline.',
            tone: complianceTone(compliance?.escalationLevel),
            progress: complianceProgress,
          },
          {
            label: 'Transmission Flow',
            value: totalTransmissions
              ? `${completedTransmissions}/${totalTransmissions} complete`
              : 'No transmissions',
            hint: totalTransmissions
              ? `${activeTransmissions} uplinks active · ${transmittingCount} transmitting`
              : 'Awaiting uplink requests.',
            tone:
              activeTransmissions <= 1
                ? 'stable'
                : activeTransmissions <= 2
                  ? 'watch'
                  : 'alert',
            progress: transmissionProgress,
          },
        ],
      },
      {
        id: 'living-visualization-layers',
        title: 'Living Visualization Tapestry',
        summary:
          schumannProtocol && typeof gammaFloor === 'number'
            ? `${schumannProtocol.witness.name} · Γ floor ${gammaFloor.toFixed(3)}`
            : schumannProtocol
              ? schumannProtocol.witness.statement
              : 'Harmonic prisms calibrating across the nexus.',
        status: schumannProtocol?.coherenceReport.status,
        metrics: [
          {
            label: 'Planetary Heartbeat',
            value: `${(averageSchumannCoherence * 100).toFixed(1)}% C`,
            hint: `Schumann pulse ${coherenceColorBand(averageSchumannCoherence)} · ${
              schumannProtocol?.monitoringSession.totalSnapshots ?? 0
            } snapshots braided.`,
            tone: ratioTone(averageSchumannCoherence),
            progress: averageSchumannCoherence,
          },
          {
            label: 'Frequency Spectrum',
            value: `${(metricDiversity * 100).toFixed(1)}% engaged`,
            hint: `0.001 Hz → 10¹⁵ Hz choir · Diversity ${dataComprehensiveness.toFixed(2)} fidelity.`,
            tone: ratioTone(metricDiversity),
            progress: metricDiversity,
          },
          {
            label: 'Sacred Geometry Overlay',
            value: geometryStream ? `${Math.round(geometryStream.rate)} patterns/min` : 'Offline',
            hint: geometryStream
              ? `${geometryLocation} · ${geometryFlow >= 0.92 ? 'Metatron cube igniting' : 'Flower lattice aligning'}.`
              : 'Awaiting geometry observatory handshake.',
            tone: geometryTone,
            progress: geometryStream ? geometryFlow : undefined,
          },
          {
            label: 'Timeline River',
            value: `${(trendDepth * 100).toFixed(1)}% depth`,
            hint: `Past↔Future stream ${timelineWindow} · Narratives converging NOW.`,
            tone: ratioTone(trendDepth),
            progress: trendDepth,
          },
          {
            label: 'Consciousness Map',
            value: `${Math.round(awakeningIndex * 100)}% luminous`,
            hint: `Heat blooms around ${bioProfile?.origin ?? 'the collective field'} · ${
              bioProfile?.timelineTag ?? 'Awaiting attunement'
            }.`,
            tone: ratioTone(awakeningIndex),
            progress: awakeningIndex,
          },
          {
            label: 'Domain Wheel',
            value: `${activeDomains}/21 channels`,
            hint: `${sensors.length} sensory petals · ${
              processingData?.algorithms?.length ?? 0
            } algorithmic engines weaving the mandala.`,
            tone: ratioTone(domainActivation),
            progress: domainActivation,
          },
          {
            label: 'Akashic Interface',
            value: `Γ ${gammaLevel.toFixed(3)}`,
            hint: `Interface ${quantumLink?.handshakeState ?? 'idle'} · ${
              gammaLevel >= 0.945 ? 'Access unlocked' : 'Calibrating access gate'
            }.`,
            tone: akashicTone,
            progress: gammaLevel,
          },
          {
            label: 'Entanglement Web',
            value: `${entangledPairs.toLocaleString()} pairs`,
            hint: `${transmittingCount} uplinks glowing · Mesh integrity ${(entanglementIndex * 100).toFixed(1)}%.`,
            tone: ratioTone(entanglementIndex),
            progress: entanglementIndex,
          },
          {
            label: 'Emotional Weather',
            value: emotionalLabel,
            hint: `Anomaly rate ${(anomalyRate * 100).toFixed(1)}% · Collective radiance ${(harmonyIndex * 100).toFixed(1)}%.`,
            tone: ratioTone(harmonyIndex),
            progress: harmonyIndex,
          },
          {
            label: 'Zero-Point Flow',
            value: `${(zeroPointFlux * 100).toFixed(1)}% flux`,
            hint: `Quantum vacuum sparkle ${processingData?.qssrModule.cosmicWeather ?? 'balancing'} · Solar coherence ${(zeroPointFlux * 100).toFixed(1)}%.`,
            tone: ratioTone(zeroPointFlux),
            progress: zeroPointFlux,
          },
        ],
      },
    ];
  }, [
    renderFullConsole,
    liveMetrics,
    sensory,
    output,
    processingData,
    timestamp,
    schumannProtocol,
    bioProfile,
    modeMatrix,
    quantumLink,
    sensors,
  ]);

  const latestAudit = useMemo<AuditRecord[]>(
    () => audit.slice(-4).reverse(),
    [audit]
  );

  const networkStatus = sensors.every((stream) => stream.state === 'Stable')
    ? { label: 'Online', variant: 'success' as const }
    : sensors.some((stream) => stream.state === 'Anomaly')
      ? { label: 'Investigate', variant: 'warning' as const }
      : { label: 'Balancing', variant: 'warning' as const };

  const statusBadgeClass =
    networkStatus.label === 'Online'
      ? 'border-emerald-400/40 bg-emerald-500/20 text-emerald-100 shadow-[0_0_35px_rgba(16,185,129,0.45)]'
      : networkStatus.label === 'Investigate'
        ? 'border-rose-400/50 bg-rose-500/20 text-rose-100 shadow-[0_0_35px_rgba(244,63,94,0.35)]'
        : 'border-amber-300/50 bg-amber-500/20 text-amber-100 shadow-[0_0_35px_rgba(251,191,36,0.4)]';

  const updatedAt = useMemo(() => new Date(timestamp), [timestamp]);

  if (!renderFullConsole) {
    return (
      <div className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/60 p-6 shadow-cosmic text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-cosmic-mesh opacity-80" />
        <div className="pointer-events-none absolute -top-32 left-8 h-80 w-80 rounded-full bg-sky-500/40 blur-3xl animate-cosmic-drift" />
        <div className="pointer-events-none absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-fuchsia-500/35 blur-[140px] animate-orbital-glow" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/5 opacity-20 blur-3xl" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
        <div className="relative z-10 space-y-10">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-2">
              <h1 className="bg-gradient-to-r from-sky-200 via-fuchsia-200 to-amber-200 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
                Nexus Live Feed
              </h1>
              <p className="max-w-xl text-sm leading-relaxed text-slate-300/90 sm:text-base">
                Witness the Harmonia Nexus breathing in real time—sensor choirs, quantum analysts, and command pillars weaving a living tapestry of celestial insight.
              </p>
            </div>
            <div className="flex flex-col items-start gap-2 text-xs text-slate-300/80 lg:items-end">
              <Badge
                variant="outline"
                className={`inline-flex items-center rounded-full px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] ${statusBadgeClass}`}
              >
                {networkStatus.label}
              </Badge>
              <span className="text-sm text-slate-300/90">
                Updated <span className="font-semibold text-white">{updatedAt.toLocaleTimeString()}</span>
              </span>
            </div>
          </div>

          <SystemHarmonicFlow stages={systemFlowStages} status={systemFlowStatus} />

          <Card className="relative overflow-hidden border-white/10 bg-slate-900/60 p-6 shadow-[0_0_45px_rgba(59,130,246,0.25)]">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-sky-500/20 via-transparent to-fuchsia-500/20 opacity-60" />
            <CardHeader className="relative z-10 pb-4">
              <CardTitle className="text-xl font-semibold uppercase tracking-[0.32em] text-white">Live Data Streams Console</CardTitle>
            </CardHeader>
            <CardContent className="relative z-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <p className="max-w-2xl text-sm text-slate-300/85">
                Dive into per-stream dashboards, quantum telemetry, and stewardship controls in the dedicated console.
              </p>
              <Link
                to="/live"
                className="inline-flex items-center justify-center rounded-full border border-sky-400/60 px-6 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-sky-100 transition hover:bg-sky-500/20"
              >
                Open Live Streams
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/60 p-6 shadow-cosmic text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-cosmic-mesh opacity-80" />
      <div className="pointer-events-none absolute -top-32 left-8 h-80 w-80 rounded-full bg-sky-500/40 blur-3xl animate-cosmic-drift" />
      <div className="pointer-events-none absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-fuchsia-500/35 blur-[140px] animate-orbital-glow" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/5 opacity-20 blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
      <div className="relative z-10 space-y-10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="bg-gradient-to-r from-sky-200 via-fuchsia-200 to-amber-200 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
              Nexus Live Feed
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-slate-300/90 sm:text-base">
              Witness the Harmonia Nexus breathing in real time—sensor choirs, quantum analysts, and command pillars weaving a living tapestry of celestial insight.
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 text-xs text-slate-300/80 lg:items-end">
            <Badge
              variant="outline"
              className={`inline-flex items-center rounded-full px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] ${statusBadgeClass}`}
            >
              {networkStatus.label}
            </Badge>
            <span className="text-sm text-slate-300/90">
              Updated <span className="font-semibold text-white">{updatedAt.toLocaleTimeString()}</span>
            </span>
          </div>
        </div>



        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-nebula backdrop-blur-xl">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-fuchsia-500/20 opacity-70" />
          <div className="pointer-events-none absolute -inset-20 animate-stellar-pulse bg-[radial-gradient(circle,_rgba(255,255,255,0.18),_transparent_60%)]" />
          <Tabs defaultValue="system-overview" className="relative z-10 space-y-8">
            <TabsList className="relative flex w-full flex-wrap gap-2 overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-1 backdrop-blur">
              <span className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-sky-500/0 via-sky-500/60 to-sky-500/0" />
              <TabsTrigger
                value="system-overview"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-sky-500/40 data-[state=active]:via-blue-500/30 data-[state=active]:to-cyan-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(56,189,248,0.45)]"
              >
                System Overview
              </TabsTrigger>
              <TabsTrigger
                value="sensory-layer"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-500/40 data-[state=active]:via-teal-500/30 data-[state=active]:to-sky-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(16,185,129,0.45)]"
              >
                Sensory &amp; Ingestion
              </TabsTrigger>
              <TabsTrigger
                value="processing-core"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-violet-500/40 data-[state=active]:via-indigo-500/30 data-[state=active]:to-sky-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(139,92,246,0.45)]"
              >
                Processing &amp; Analysis
              </TabsTrigger>
              <TabsTrigger
                value="blockchain-mining"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-teal-500/40 data-[state=active]:via-cyan-500/30 data-[state=active]:to-emerald-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(20,184,166,0.45)]"
              >
                Blockchain Mining
              </TabsTrigger>
              <TabsTrigger
                value="live-visualization"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-fuchsia-500/40 data-[state=active]:via-pink-500/30 data-[state=active]:to-amber-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(236,72,153,0.45)]"
              >
                Live Visualization
              </TabsTrigger>
              <TabsTrigger
                value="temporal-aura"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-500/40 data-[state=active]:via-sky-500/30 data-[state=active]:to-emerald-400/35 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(251,191,36,0.38)]"
              >
                Temporal Aura Scan
              </TabsTrigger>
              <TabsTrigger
                value="temporal-biofield"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-400/35 data-[state=active]:via-sky-500/30 data-[state=active]:to-violet-500/35 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(16,185,129,0.4)]"
              >
                Temporal Biofield Scan
              </TabsTrigger>
              <TabsTrigger
                value="celestial-calendar"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-sky-500/35 data-[state=active]:via-violet-500/35 data-[state=active]:to-amber-400/35 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(59,130,246,0.45)]"
              >
                Celestial Calendar
              </TabsTrigger>
              <TabsTrigger
                value="dimensional-dialer"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-500/35 data-[state=active]:via-fuchsia-500/30 data-[state=active]:to-cyan-400/35 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(251,191,36,0.45)]"
              >
                Dimensional Dialer
              </TabsTrigger>
              <TabsTrigger
                value="visual-relay"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/40 data-[state=active]:via-indigo-500/30 data-[state=active]:to-rose-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(14,165,233,0.45)]"
              >
                Visual Relay
              </TabsTrigger>
              <TabsTrigger
                value="recording-systems"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-500/40 data-[state=active]:via-orange-500/30 data-[state=active]:to-rose-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(245,158,11,0.45)]"
              >
                Recording Systems
              </TabsTrigger>
              <TabsTrigger
                value="chronicle-governance"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-sky-500/40 data-[state=active]:via-purple-500/30 data-[state=active]:to-rose-400/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(59,130,246,0.45)]"
              >
                Chronicle &amp; Governance
              </TabsTrigger>
              <TabsTrigger
                value="family-constellation"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-rose-500/35 data-[state=active]:via-amber-400/30 data-[state=active]:to-emerald-400/35 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(244,114,182,0.45)]"
              >
                Soul Constellation
              </TabsTrigger>
              <TabsTrigger
                value="output-command"
                className="group relative flex-1 min-w-[160px] overflow-hidden rounded-xl border border-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition duration-300 hover:text-white hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] data-[state=active]:border-transparent data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500/40 data-[state=active]:via-blue-500/30 data-[state=active]:to-indigo-500/40 data-[state=active]:text-white data-[state=active]:shadow-[0_0_35px_rgba(37,99,235,0.45)]"
              >
                Command &amp; Output
              </TabsTrigger>
            </TabsList>
            <TabsContent value="system-overview" className="space-y-6">
              <Card className="group relative overflow-hidden border-white/10 bg-slate-900/60 text-slate-100 shadow-[0_0_50px_rgba(59,130,246,0.25)]">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-indigo-500/20 opacity-60 transition duration-700 group-hover:opacity-80" />
                <div className="pointer-events-none absolute -inset-24 animate-stellar-pulse bg-[radial-gradient(circle,_rgba(148,163,184,0.35),_transparent_55%)] opacity-0 group-hover:opacity-80" />
                <CardHeader className="relative z-10 pb-3">
                  <CardTitle className="text-xl font-semibold text-white">Operational Pulse</CardTitle>
                </CardHeader>
                <CardContent className="relative z-10 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  {metrics.map((metric) => (
                    <div
                      key={metric.id}
                      className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-sky-500/40 via-transparent to-fuchsia-500/40 p-[1px] shadow-[0_0_40px_rgba(129,140,248,0.35)]"
                    >
                      <div className="absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(236,72,153,0.2),_transparent_65%)] opacity-0 transition duration-500 group-hover:opacity-80" />
                      <div className="relative h-full rounded-[1.5rem] bg-slate-950/75 p-4 backdrop-blur">
                        <div className="pointer-events-none absolute inset-0 rounded-[1.5rem] bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.25),_transparent_60%)] opacity-0 transition duration-500 group-hover:opacity-80" />
                        <div className="relative z-10 flex items-center justify-between text-[11px] uppercase tracking-[0.28em] text-slate-300/90">
                          <span className="text-[11px] font-semibold">{metric.label}</span>
                          <Badge
                            variant="outline"
                            className={`rounded-full px-3 py-1 ${metricBadgeStyles[metric.status]}`}
                          >
                            {metricLabel(metric.status)}
                          </Badge>
                        </div>
                        <div className="relative z-10 mt-4 text-3xl font-semibold text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.35)]">
                          {metric.value}
                        </div>
                        <p className="relative z-10 mt-2 text-xs leading-relaxed text-slate-300/80">{metric.hint}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
              <LiveRealtimeCharts />
              <LiveStreamShowcase streams={sensors} updatedAt={updatedAt} />
            </TabsContent>
            <TabsContent
              value="sensory-layer"
          className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(16,185,129,0.2)] backdrop-blur"
        >
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-500/15 via-transparent to-sky-500/15 opacity-70" />
          <div className="relative z-10 space-y-6">
            <SensoryLayerTab sensors={sensors} />
            <DataSourceRegistry sources={DATA_SOURCES} version={DATA_SOURCE_VERSION} />
          </div>
        </TabsContent>
            <TabsContent
              value="processing-core"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(139,92,246,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-violet-500/15 via-transparent to-sky-500/15 opacity-70" />
              <div className="relative z-10">
                <ProcessingCoreTab processing={processing} />
              </div>
            </TabsContent>
            <TabsContent
              value="blockchain-mining"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(20,184,166,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-teal-500/20 via-transparent to-cyan-500/15 opacity-70" />
              <div className="relative z-10">
                <BlockchainMiningTab
                  metrics={BLOCKCHAIN_MINING_METRICS}
                  nodes={BLOCKCHAIN_MINING_NODES}
                  ledgerHighlights={BLOCKCHAIN_LEDGER_HIGHLIGHTS}
                  energyMix={BLOCKCHAIN_ENERGY_MIX}
                />
              </div>
            </TabsContent>
            <TabsContent
              value="live-visualization"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(236,72,153,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-fuchsia-500/20 via-transparent to-amber-400/15 opacity-70" />
              <div className="relative z-10 space-y-6">
                <LiveVisualizationTab modules={visualizationModules} />
                <ModeMatrixPanel matrix={modeMatrix} />
              </div>
            </TabsContent>
            <TabsContent
              value="temporal-aura"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(251,191,36,0.24)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/20 via-transparent to-sky-500/20 opacity-70" />
              <div className="relative z-10">
                <TemporalAuraScanTab />
              </div>
            </TabsContent>
            <TabsContent
              value="temporal-biofield"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(16,185,129,0.24)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-500/20 via-transparent to-violet-500/20 opacity-70" />
              <div className="relative z-10">
                <TemporalBiofieldScanTab />
              </div>
            </TabsContent>
            <TabsContent
              value="celestial-calendar"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(59,130,246,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/25 via-transparent to-violet-500/20 opacity-70" />
              <div className="relative z-10">
                <CelestialCalendarTab />
              </div>
            </TabsContent>
            <TabsContent
              value="dimensional-dialer"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(251,191,36,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/25 via-transparent to-indigo-500/20 opacity-70" />
              <div className="relative z-10">
                <DimensionalDialerTab />
              </div>
            </TabsContent>
            <TabsContent
              value="visual-relay"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(56,189,248,0.25)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-rose-500/15 opacity-70" />
              <div className="relative z-10">
                <VisualRelayTab />
              </div>
            </TabsContent>
            <TabsContent
              value="recording-systems"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(245,158,11,0.2)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/20 via-transparent to-rose-500/15 opacity-70" />
              <div className="relative z-10">
                <RecordingSystemsTab channels={RECORDING_CHANNELS} />
              </div>
            </TabsContent>
            <TabsContent
              value="chronicle-governance"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(59,130,246,0.22)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/20 via-transparent to-rose-500/15 opacity-70" />
              <div className="relative z-10">
                <ChronicleGovernanceTab governance={CHRONICLE_GOVERNANCE} />
              </div>
            </TabsContent>
            <TabsContent
              value="family-constellation"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(244,114,182,0.24)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-fuchsia-500/20 via-transparent to-emerald-400/20 opacity-70" />
              <div className="relative z-10">
                <FamilyConstellationReading />
              </div>
            </TabsContent>
            <TabsContent
              value="output-command"
              className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-[0_0_50px_rgba(37,99,235,0.25)] backdrop-blur"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-blue-500/20 via-transparent to-indigo-500/20 opacity-70" />
              <div className="relative z-10">
                <OutputCommandTab latestAudit={latestAudit} vaultStatus={vaultStatus} vaultError={vaultError} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

    </div>
  );
};

export default HomePage;
