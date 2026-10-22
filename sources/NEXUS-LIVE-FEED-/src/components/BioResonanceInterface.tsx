import React, { useState, useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';

interface BioResonanceMetrics {
  heartRate?: number;
  oxygenSaturation?: number;
  bloodPressure?: string;
  respirationRate?: number;
  bodyTemperature?: number;
  brainwaveState?: string;
  ecg?: number[];
  auricFieldStrength?: number;
}

interface BioResonanceData {
  species: string;
  resonanceFactor: number;
  location: string;
  metrics?: BioResonanceMetrics;
  updatedAt?: string;
}

type HarmonizationResult =
  | {
      status: 'success';
      message: string;
    }
  | {
      status: 'error';
      message: string;
    };


const BioResonanceInterface: React.FC = () => {
  const [bioResonanceData, setBioResonanceData] = useState<BioResonanceData[]>([]);
  const [harmonizationResult, setHarmonizationResult] = useState<HarmonizationResult | null>(null);
  const [isHarmonizing, setIsHarmonizing] = useState(false);


  useEffect(() => {
    const eventSource = new EventSource('/bio-resonance-stream');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setBioResonanceData(Array.isArray(data.bioResonance) ? data.bioResonance : []);
    };
    return () => {
      eventSource.close();
    };
  }, []);

  const latestEnrichedEntry = useMemo(() => {
    if (!bioResonanceData.length) return null;
    return bioResonanceData.find((entry) => entry.metrics) ?? null;
  }, [bioResonanceData]);

  const latestMetrics = latestEnrichedEntry?.metrics ?? null;
  const lastUpdated = latestEnrichedEntry?.updatedAt ?? null;

  const ecgSignal = useMemo(() => {
    if (!latestMetrics?.ecg?.length) return [];
    return latestMetrics.ecg.slice(-42);
  }, [latestMetrics]);

  const handleHarmonize = async () => {
    setIsHarmonizing(true);
    try {
      const response = await fetch('/harmonize-bio-resonance');
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result?.error || 'Failed to harmonize bio-resonance');
      }

      setHarmonizationResult({ status: 'success', message: result?.message || 'Resonance harmonized successfully.' });
    } catch (error) {
      console.error('Error during bio-resonance harmonization:', error);
      setHarmonizationResult({
        status: 'error',
        message: 'Failed to harmonize bio-resonance. Please attempt the ritual again.',
      });
    } finally {
      setIsHarmonizing(false);
    }
  };

  const resonanceTone = (value: number) => {
    if (value < 0.5) return 'from-rose-500/50 via-amber-500/25 to-transparent';
    if (value < 0.8) return 'from-amber-500/45 via-yellow-400/30 to-transparent';
    return 'from-emerald-500/45 via-teal-400/30 to-transparent';
  };

  const renderSnapshot = () => {
    if (!latestEnrichedEntry || !latestMetrics) return null;

    return (
      <article className="group relative overflow-hidden rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-[1px]">
        <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-emerald-400/20 via-teal-400/20 to-transparent opacity-70" />
        <div className="relative rounded-[calc(1rem-2px)] bg-slate-950/80 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-emerald-200/80">Live Bio Signature</p>
              <p className="mt-2 text-lg font-semibold uppercase tracking-[0.22em] text-white">
                {latestEnrichedEntry.species}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-emerald-200/80">Location</p>
              <p className="mt-2 text-sm uppercase tracking-[0.24em] text-emerald-100">
                {latestEnrichedEntry.location}
              </p>
            </div>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Heart Rate</p>
              <p className="mt-2 text-2xl font-semibold tracking-[0.16em] text-white">
                {latestMetrics.heartRate ? `${latestMetrics.heartRate} bpm` : '—'}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Oxygen</p>
              <p className="mt-2 text-2xl font-semibold tracking-[0.16em] text-white">
                {latestMetrics.oxygenSaturation ? `${latestMetrics.oxygenSaturation}%` : '—'}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Auric Field</p>
              <p className="mt-2 text-2xl font-semibold tracking-[0.16em] text-white">
                {latestMetrics.auricFieldStrength
                  ? `${Math.round(latestMetrics.auricFieldStrength)}%`
                  : '—'}
              </p>
            </div>
          </div>
          {lastUpdated && (
            <p className="mt-6 text-[10px] uppercase tracking-[0.28em] text-emerald-200/70">
              Last sync {new Date(lastUpdated).toLocaleTimeString()}
            </p>
          )}
        </div>
      </article>
    );
  };

  const renderVitals = () => {
    if (!latestMetrics) {
      return (
        <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-xs text-slate-300/70">
          No biometric stream detected. Awaiting connection to ECG and vital monitors.
        </p>
      );
    }

    const vitalCards = [
      {
        label: 'Heart Rate',
        value: latestMetrics.heartRate ? `${latestMetrics.heartRate} bpm` : '—',
      },
      {
        label: 'Oxygen Saturation',
        value: latestMetrics.oxygenSaturation ? `${latestMetrics.oxygenSaturation}%` : '—',
      },
      {
        label: 'Blood Pressure',
        value: latestMetrics.bloodPressure ?? '—',
      },
      {
        label: 'Respiration Rate',
        value: latestMetrics.respirationRate ? `${latestMetrics.respirationRate} rpm` : '—',
      },
      {
        label: 'Temperature',
        value: latestMetrics.bodyTemperature ? `${latestMetrics.bodyTemperature.toFixed(1)} °C` : '—',
      },
      {
        label: 'Auric Field',
        value: latestMetrics.auricFieldStrength ? `${Math.round(latestMetrics.auricFieldStrength)}%` : '—',
      },
      {
        label: 'Brainwave State',
        value: latestMetrics.brainwaveState ?? '—',
      },
    ];

    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {vitalCards.map((card) => (
            <article
              key={card.label}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]"
            >
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-emerald-500/10 via-teal-400/5 to-transparent opacity-60 group-hover:opacity-80" />
              <div className="relative rounded-[calc(1rem-2px)] bg-slate-950/85 p-5">
                <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-slate-400">{card.label}</p>
                <p className="mt-4 text-2xl font-semibold tracking-[0.08em] text-white">{card.value}</p>
              </div>
            </article>
          ))}
        </div>
        {lastUpdated && (
          <p className="text-[10px] uppercase tracking-[0.28em] text-slate-300/70">
            Live vitals refreshed {new Date(lastUpdated).toLocaleTimeString()}
          </p>
        )}
      </div>
    );
  };

  const renderResonance = () => {
    if (!bioResonanceData.length) {
      return (
        <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-xs text-slate-300/70">
          Awaiting resonance stream synchronization. Connect to a guardian relay to receive active signatures.
        </p>
      );
    }

    return (
      <div className="space-y-4">
        {bioResonanceData.map((entry) => (
          <article
            key={`${entry.species}-${entry.location}-${entry.updatedAt ?? 'pending'}`}
            className="group relative overflow-hidden rounded-2xl border border-emerald-400/20 bg-slate-950/60 p-[1px]"
          >
            <div
              className={cn(
                'pointer-events-none absolute inset-0 bg-gradient-to-r opacity-70 transition-opacity group-hover:opacity-90',
                resonanceTone(entry.resonanceFactor)
              )}
            />
            <div className="relative rounded-[calc(1rem-2px)] bg-slate-950/85 p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-emerald-200/80">Species</p>
                  <p className="mt-1 text-base font-semibold uppercase tracking-[0.24em] text-white">{entry.species}</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.32em] text-emerald-200/80">Resonance</p>
                  <p className="mt-1 text-lg font-semibold tracking-[0.2em] text-emerald-100">
                    {entry.resonanceFactor.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Location</p>
                  <p className="mt-2 text-sm uppercase tracking-[0.2em] text-white">{entry.location}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Last Update</p>
                  <p className="mt-2 text-sm uppercase tracking-[0.2em] text-emerald-100/90">
                    {entry.updatedAt ? new Date(entry.updatedAt).toLocaleTimeString() : 'Pending'}
                  </p>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    );
  };

  const renderDiagnostics = () => {
    if (!latestMetrics) {
      return (
        <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-xs text-slate-300/70">
          Diagnostics console dormant. Sync to a nexus node to visualize ECG traces.
        </p>
      );
    }

    return (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)]">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h5 className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-300/70">ECG Signal</h5>
          <div className="mt-6 h-40 overflow-hidden rounded-xl bg-slate-950/70 p-4">
            {ecgSignal.length ? (
              <svg viewBox={`0 0 ${ecgSignal.length * 4} 160`} className="h-full w-full" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="rgb(74,222,128)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  points={ecgSignal
                    .map((value, index) => {
                      const x = index * 4;
                      const y = 80 - value * 60;
                      return `${x},${Math.min(155, Math.max(5, y))}`;
                    })
                    .join(' ')}
                />
              </svg>
            ) : (
              <div className="flex h-full items-center justify-center text-xs uppercase tracking-[0.24em] text-slate-500">
                ECG data stream pending
              </div>
            )}
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <h5 className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-300/70">Telemetry Summary</h5>
            <dl className="mt-4 space-y-3 text-[11px] uppercase tracking-[0.26em] text-slate-300/80">
              <div className="flex items-center justify-between">
                <dt>Heart Rhythm</dt>
                <dd>{latestMetrics.heartRate ? `${latestMetrics.heartRate} bpm` : 'Stable'}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Oxygen Saturation</dt>
                <dd>{latestMetrics.oxygenSaturation ? `${latestMetrics.oxygenSaturation}%` : 'Balanced'}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Respiration</dt>
                <dd>{latestMetrics.respirationRate ? `${latestMetrics.respirationRate} rpm` : 'Aligned'}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Thermal Regulation</dt>
                <dd>
                  {latestMetrics.bodyTemperature
                    ? `${latestMetrics.bodyTemperature.toFixed(1)} °C`
                    : 'Baseline'}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Brainwave State</dt>
                <dd>{latestMetrics.brainwaveState ?? 'Coherent'}</dd>
              </div>
            </dl>
            {lastUpdated && (
              <p className="mt-4 text-[10px] uppercase tracking-[0.28em] text-slate-400/70">
                Sync checkpoint {new Date(lastUpdated).toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <h5 className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-300/70">Alerts</h5>
            <p className="mt-4 text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {latestMetrics.heartRate && latestMetrics.heartRate > 120
                ? 'Elevated heart rate detected — recommend calming protocol.'
                : 'All biometric channels stable. Guardian clearance maintained.'}
            </p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-slate-100 shadow-[0_0_45px_rgba(20,184,166,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(20,184,166,0.18),_transparent_60%)] opacity-80" />
      <header className="relative z-10 flex flex-col gap-4 pb-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-xl font-semibold uppercase tracking-[0.3em] text-white">Bio-Resonance Interface</h3>
          <p className="mt-1 text-sm text-slate-300/80">
            Monitoring the living resonance of allied species and sanctuaries. Harmonize to cascade restorative frequencies.
          </p>
        </div>
        <button
          onClick={handleHarmonize}
          disabled={isHarmonizing}
          className={cn(
            'relative overflow-hidden rounded-2xl border border-emerald-400/50 bg-emerald-500/20 px-5 py-2 text-xs font-semibold uppercase tracking-[0.32em] text-emerald-100 shadow-[0_0_25px_rgba(16,185,129,0.35)] transition hover:border-emerald-300/70 hover:bg-emerald-500/30',
            isHarmonizing && 'cursor-not-allowed opacity-70'
          )}
        >
          {isHarmonizing ? 'Harmonizing…' : 'Harmonize Bio-Resonance'}
        </button>
      </header>

      <div className="relative z-10 space-y-6">
        {harmonizationResult && (
          <div
            className={cn(
              'rounded-2xl border px-4 py-3 text-xs uppercase tracking-[0.26em]',
              harmonizationResult.status === 'success'
                ? 'border-emerald-400/50 bg-emerald-500/10 text-emerald-100'
                : 'border-rose-500/50 bg-rose-500/10 text-rose-100'
            )}
          >
            {harmonizationResult.message}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="space-y-6">
            {renderSnapshot()}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Vital Metrics</h4>
              <div className="mt-4">{renderVitals()}</div>
            </div>
          </div>
          <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Resonance Stream</h4>
              <div className="mt-4">{renderResonance()}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h4 className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-300/70">Diagnostics</h4>
              <div className="mt-4">{renderDiagnostics()}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default BioResonanceInterface;
