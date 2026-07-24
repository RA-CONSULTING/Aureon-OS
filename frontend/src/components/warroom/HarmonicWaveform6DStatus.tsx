import React from 'react';
import { Card } from '@/components/ui/card';
import { Activity, Waves, Clock, Link2, TrendingUp, Radio } from 'lucide-react';
import type { HarmonicWaveform6D, WaveState } from '@/core/sixDimensionalHarmonicEngine';

interface HarmonicWaveform6DStatusProps {
  waveform: HarmonicWaveform6D | null;
}

const dimensionIcons = {
  d1_price: Activity,
  d2_volume: Waves,
  d3_time: Clock,
  d4_correlation: Link2,
  d5_momentum: TrendingUp,
  d6_frequency: Radio,
};

const dimensionLabels = {
  d1_price: 'Price Wave',
  d2_volume: 'Volume Pulse',
  d3_time: 'Temporal Phase',
  d4_correlation: 'Correlation',
  d5_momentum: 'Momentum',
  d6_frequency: 'Frequency',
};

const waveStateColors: Record<WaveState, string> = {
  CRYSTALLINE: 'text-success bg-success/20',
  RESONANT: 'text-primary bg-primary/20',
  TURBULENT: 'text-warning bg-warning/20',
  CHAOTIC: 'text-destructive bg-destructive/20',
};

export function HarmonicWaveform6DStatus({ waveform }: HarmonicWaveform6DStatusProps) {
  if (!waveform) {
    return (
      <Card className="p-4 bg-card/50 border-border/50">
        <div className="text-muted-foreground text-sm">Awaiting 6D waveform data...</div>
      </Card>
    );
  }

  const dimensions = [
    { key: 'd1_price', dim: waveform.d1_price },
    { key: 'd2_volume', dim: waveform.d2_volume },
    { key: 'd3_time', dim: waveform.d3_time },
    { key: 'd4_correlation', dim: waveform.d4_correlation },
    { key: 'd5_momentum', dim: waveform.d5_momentum },
    { key: 'd6_frequency', dim: waveform.d6_frequency },
  ];

  return (
    <Card className="p-4 bg-card/50 border-border/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">6D Harmonic Waveform</h3>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${waveStateColors[waveform.waveState]}`}>
            {waveform.waveState}
          </span>
          {waveform.harmonicLock && (
            <span className="px-2 py-0.5 rounded text-xs font-medium text-success bg-success/20 animate-pulse">
              528 Hz LOCK
            </span>
          )}
        </div>
      </div>

      {/* 6 Dimensions Grid */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {dimensions.map(({ key, dim }) => {
          const Icon = dimensionIcons[key as keyof typeof dimensionIcons];
          const label = dimensionLabels[key as keyof typeof dimensionLabels];
          const phasePercent = ((dim.phase + Math.PI) / (2 * Math.PI)) * 100;
          
          return (
            <div key={key} className="p-2 rounded bg-background/50 border border-border/30">
              <div className="flex items-center gap-1 mb-1">
                <Icon className="w-3 h-3 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">{label}</span>
              </div>
              <div className="text-xs font-mono text-foreground">
                A: {dim.amplitude.toFixed(3)}
              </div>
              <div className="text-[10px] text-muted-foreground font-mono">
                φ: {(dim.phase * 180 / Math.PI).toFixed(1)}°
              </div>
              {/* Phase bar */}
              <div className="h-1 bg-muted/30 rounded-full mt-1 overflow-hidden">
                <div 
                  className="h-full bg-primary/60 transition-all duration-300"
                  style={{ width: `${phasePercent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Derived Metrics */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <MetricBox label="Coherence" value={waveform.dimensionalCoherence} />
        <MetricBox label="Phase Align" value={waveform.phaseAlignment} />
        <MetricBox label="Energy" value={waveform.energyDensity} />
        <MetricBox label="Resonance" value={waveform.resonanceScore} />
      </div>

      {/* Probability & Action */}
      <div className="flex items-center justify-between pt-2 border-t border-border/30">
        <div>
          <span className="text-[10px] text-muted-foreground">Probability Field</span>
          <div className="text-lg font-mono font-bold text-foreground">
            {(waveform.probabilityField * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-muted-foreground">Market Phase</span>
          <div className="text-xs font-medium text-foreground">{waveform.marketPhase}</div>
        </div>
        <div className={`px-3 py-1.5 rounded font-medium text-sm ${getActionColor(waveform.action)}`}>
          {waveform.action.replace('_', ' ')}
        </div>
      </div>
    </Card>
  );
}

function MetricBox({ label, value }: { label: string; value: number }) {
  const color = value > 0.7 ? 'text-success' : value > 0.5 ? 'text-primary' : 'text-warning';
  
  return (
    <div className="text-center p-1.5 rounded bg-background/30">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className={`text-sm font-mono font-bold ${color}`}>
        {(value * 100).toFixed(0)}%
      </div>
    </div>
  );
}

function getActionColor(action: string): string {
  if (action.includes('BUY')) return 'bg-success/20 text-success';
  if (action.includes('SELL')) return 'bg-destructive/20 text-destructive';
  return 'bg-muted/50 text-muted-foreground';
}
