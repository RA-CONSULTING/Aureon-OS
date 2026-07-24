import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { fmt } from '@/utils/number';
import { useHarmonicMetrics } from '@/hooks/useEcosystemData';

interface HarmonicLayer {
  frequency: number;
  amplitude: number;
  phase: number;
  color: string;
}

export const HarmonicFieldVisualizer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  
  const {
    coherence,
    frequency,
    waveState,
    harmonicLock,
    prismLevel,
    probabilityFusion,
    isInitialized,
  } = useHarmonicMetrics();

  // Derive harmonics from real ecosystem data
  const harmonics: HarmonicLayer[] = [
    { frequency: 7.83, amplitude: coherence, phase: 0, color: '#8B5CF6' },
    { frequency: 14.3, amplitude: coherence * 0.8, phase: 0.5, color: '#3B82F6' },
    { frequency: 20.8, amplitude: coherence * 0.6, phase: 1.0, color: '#10B981' },
    { frequency: 27.3, amplitude: coherence * 0.4, phase: 1.5, color: '#F59E0B' },
    { frequency: 33.8, amplitude: coherence * 0.2, phase: 2.0, color: '#EF4444' },
  ];

  // Derive field metrics from ecosystem
  const fieldMetrics = {
    coherence,
    phaseAlignment: probabilityFusion || (coherence * 0.9 + 0.05),
    resonanceStrength: harmonicLock ? 0.95 : (coherence * 0.85 + 0.1),
    unityFactor: (prismLevel / 5) * 0.9 + 0.1,
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = 800;
    canvas.height = 400;

    const drawHarmonicField = (time: number) => {
      ctx.fillStyle = 'hsl(0 0% 5%)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw harmonic layers
      harmonics.forEach((harmonic, index) => {
        ctx.strokeStyle = harmonic.color;
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();

        for (let x = 0; x < canvas.width; x++) {
          const t = x / 100;
          const y = canvas.height / 2 + 
            harmonic.amplitude * 50 * Math.sin(
              2 * Math.PI * harmonic.frequency * t / 100 + 
              harmonic.phase + 
              time * 0.001
            ) * (1 + index * 0.1);
          
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });

      // Draw composite waveform (love-locked = green, otherwise white)
      ctx.strokeStyle = harmonicLock ? '#10B981' : '#FFF';
      ctx.lineWidth = 3;
      ctx.globalAlpha = 1;
      ctx.beginPath();

      for (let x = 0; x < canvas.width; x++) {
        const t = x / 100;
        let composite = 0;
        
        harmonics.forEach(harmonic => {
          composite += harmonic.amplitude * Math.sin(
            2 * Math.PI * harmonic.frequency * t / 100 + 
            harmonic.phase + 
            time * 0.001
          );
        });
        
        const y = canvas.height / 2 + composite * 20;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    const animate = (time: number) => {
      drawHarmonicField(time);
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [harmonics, harmonicLock]);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-muted-foreground">Initializing harmonic field...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gradient-to-r from-primary to-primary text-white">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <span className="text-2xl">🌊</span>
              <span>Harmonic Field Visualizer</span>
            </span>
            <Badge variant={harmonicLock ? "default" : "secondary"} className={harmonicLock ? "bg-success" : ""}>
              {harmonicLock ? "🔒 528 Hz LOCKED" : `${waveState}`}
            </Badge>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Field Visualization */}
      <Card>
        <CardContent className="p-6">
          <canvas
            ref={canvasRef}
            className="w-full border rounded-lg bg-background"
            style={{ maxWidth: '100%', height: 'auto' }}
          />
        </CardContent>
      </Card>

      {/* Metrics Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-primary to-primary text-white">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{fmt(fieldMetrics.coherence * 100, 1)}%</div>
            <div className="text-sm opacity-80">Field Coherence</div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-primary to-primary text-white">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{fmt(fieldMetrics.phaseAlignment * 100, 1)}%</div>
            <div className="text-sm opacity-80">Phase Alignment</div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-success to-success text-white">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{fmt(fieldMetrics.resonanceStrength * 100, 1)}%</div>
            <div className="text-sm opacity-80">Resonance Strength</div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-warning to-warning text-white">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{fmt(fieldMetrics.unityFactor * 100, 1)}%</div>
            <div className="text-sm opacity-80">Unity Factor</div>
          </CardContent>
        </Card>
      </div>

      {/* Harmonic Layers */}
      <Card>
        <CardHeader>
          <CardTitle>🎵 Harmonic Layers (Prism Level {prismLevel})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {harmonics.map((harmonic, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: harmonic.color }}
                  />
                  <span className="font-medium">Harmonic {index + 1}</span>
                </div>
                <div className="flex items-center space-x-4 text-sm">
                  <Badge variant="outline">{fmt(harmonic.frequency, 2)} Hz</Badge>
                  <Badge variant="outline">Amp: {fmt(harmonic.amplitude, 2)}</Badge>
                  <Badge variant="outline">Phase: {fmt(harmonic.phase, 2)}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
