// 5-Mode Schumann Spectrogram visualization
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Activity, Radio, Waves } from 'lucide-react';
import type { SchumannFeatures } from '@/lib/earth-data-loader';

interface Props {
  currentSchumann: SchumannFeatures | null;
  coherenceIndex: number;
}

export function SchumannSpectrogramPanel({ currentSchumann, coherenceIndex }: Props) {
  if (!currentSchumann) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-muted-foreground animate-pulse">Loading Schumann data...</div>
        </CardContent>
      </Card>
    );
  }
  
  const modes = [
    { freq: 7.83, label: 'Mode 1', amplitude: currentSchumann.A7_83, envelope: currentSchumann.envelope_7_83, color: 'bg-destructive', key: 'C' },
    { freq: 14.3, label: 'Mode 2', amplitude: currentSchumann.A14_3, envelope: currentSchumann.envelope_14_3, color: 'bg-warning', key: 'G' },
    { freq: 20.8, label: 'Mode 3', amplitude: currentSchumann.A20_8, envelope: currentSchumann.envelope_20_8, color: 'bg-warning', key: 'D' },
    { freq: 27.3, label: 'Mode 4', amplitude: currentSchumann.A27_3, envelope: currentSchumann.envelope_27_3, color: 'bg-success', key: 'A' },
    { freq: 33.8, label: 'Mode 5', amplitude: currentSchumann.A33_8, envelope: currentSchumann.envelope_33_8, color: 'bg-primary', key: 'E' }
  ];
  
  const maxAmplitude = Math.max(...modes.map(m => m.amplitude));
  
  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Waves className="w-5 h-5 text-primary" />
            Schumann Spectrogram
          </CardTitle>
          <Badge variant={coherenceIndex > 0.75 ? "default" : "secondary"}>
            Coherence: {(coherenceIndex * 100).toFixed(1)}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Spectrogram bars */}
        <div className="flex items-end justify-between h-32 gap-2 p-4 bg-background/50 rounded-lg border border-border/50">
          {modes.map((mode) => {
            const heightPercent = maxAmplitude > 0 ? (mode.amplitude / maxAmplitude) * 100 : 0;
            return (
              <div key={mode.freq} className="flex flex-col items-center flex-1">
                <div 
                  className={`w-full ${mode.color} rounded-t transition-all duration-300`}
                  style={{ 
                    height: `${heightPercent}%`,
                    boxShadow: `0 0 10px ${mode.color.replace('bg-', 'var(--').replace('-500', '-500)')}`
                  }}
                />
                <div className="mt-2 text-center">
                  <div className="text-xs font-bold text-foreground">{mode.freq} Hz</div>
                  <div className="text-xs text-muted-foreground">{mode.key}</div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Mode details */}
        <div className="grid grid-cols-5 gap-2">
          {modes.map((mode) => (
            <div key={mode.freq} className="p-2 bg-background/30 rounded border border-border/30 text-center">
              <div className="text-xs text-muted-foreground">{mode.label}</div>
              <div className="text-sm font-bold">{mode.amplitude.toFixed(3)}</div>
              <div className="text-xs text-muted-foreground">A: {mode.envelope.toFixed(3)}</div>
            </div>
          ))}
        </div>
        
        {/* Timestamp */}
        <div className="text-xs text-muted-foreground text-center">
          {currentSchumann.timestamp_utc}
        </div>
      </CardContent>
    </Card>
  );
}
