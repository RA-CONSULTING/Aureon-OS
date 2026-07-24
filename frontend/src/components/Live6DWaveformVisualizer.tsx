import React, { useRef, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ecosystemConnector } from '@/core/ecosystemConnector';
import { Activity, Waves, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Point6D {
  x: number; y: number; z: number;
  w: number; v: number; u: number;
  intensity: number;
  phase: number;
}

export function Live6DWaveformVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const [waveform, setWaveform] = useState(ecosystemConnector.getWaveform6D());
  const [fieldPoints, setFieldPoints] = useState<Point6D[]>([]);
  const timeRef = useRef(0);

  // Subscribe to ecosystem updates
  useEffect(() => {
    const unsubscribe = ecosystemConnector.subscribe((state) => {
      setWaveform(state.waveform6D);
    });
    return () => unsubscribe();
  }, []);

  // Generate 6D field points from waveform dimensions
  useEffect(() => {
    if (!waveform) return;

    const points: Point6D[] = [];
    const numPoints = 150;

    for (let i = 0; i < numPoints; i++) {
      const t = (i / numPoints) * Math.PI * 4;
      
      // Use actual dimension data
      const d1 = waveform.d1_price || { amplitude: 0.5, phase: 0 };
      const d2 = waveform.d2_volume || { amplitude: 0.5, phase: 0 };
      const d3 = waveform.d3_time || { amplitude: 0.5, phase: 0 };
      const d4 = waveform.d4_correlation || { amplitude: 0.5, phase: 0 };
      const d5 = waveform.d5_momentum || { amplitude: 0.5, phase: 0 };
      const d6 = waveform.d6_frequency || { amplitude: 0.5, phase: 0 };

      points.push({
        x: Math.sin(t + d1.phase) * d1.amplitude,
        y: Math.cos(t + d2.phase) * d2.amplitude,
        z: Math.sin(t * 0.5 + d3.phase) * d3.amplitude,
        w: Math.cos(t * 0.7 + d4.phase) * d4.amplitude,
        v: Math.sin(t * 0.3 + d5.phase) * d5.amplitude,
        u: Math.cos(t * 0.9 + d6.phase) * d6.amplitude,
        intensity: waveform.dimensionalCoherence || 0.5,
        phase: (waveform.phaseAlignment || 0) * Math.PI * 2,
      });
    }

    setFieldPoints(points);
  }, [waveform]);

  // Canvas animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const render = () => {
      timeRef.current += 0.02;
      const time = timeRef.current;
      
      const width = canvas.width;
      const height = canvas.height;

      // Clear with slight trail effect
      ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
      ctx.fillRect(0, 0, width, height);

      // Get current coherence for intensity
      const coherence = waveform?.dimensionalCoherence || 0.5;
      const isLocked = waveform?.waveState === 'RESONANT' || (waveform?.resonanceScore || 0) > 0.8;

      // Draw 6D field
      fieldPoints.forEach((point, i) => {
        const t = time + i * 0.1;
        
        // Animate position based on time
        const animX = point.x * Math.cos(t * 0.5) - point.z * Math.sin(t * 0.5);
        const animY = point.y * Math.cos(t * 0.3) + point.w * Math.sin(t * 0.3);
        const animZ = point.z * Math.cos(t * 0.5) + point.x * Math.sin(t * 0.5);
        
        // Project to 2D - primary view (XYZ)
        const scale1 = 120;
        const x1 = width * 0.25 + animX * scale1 + animZ * scale1 * 0.3;
        const y1 = height * 0.35 + animY * scale1 - animZ * scale1 * 0.2;

        // Secondary view (WVU)
        const animW = point.w * Math.cos(t * 0.4) - point.u * Math.sin(t * 0.4);
        const animV = point.v * Math.cos(t * 0.6);
        const animU = point.u * Math.cos(t * 0.4) + point.w * Math.sin(t * 0.4);
        
        const x2 = width * 0.75 + animW * scale1 + animU * scale1 * 0.3;
        const y2 = height * 0.35 + animV * scale1 - animU * scale1 * 0.2;

        // Mixed dimension view
        const x3 = width * 0.5 + (animX + animW) * 0.5 * scale1 * 0.7;
        const y3 = height * 0.8 + (animY + animV) * 0.5 * scale1 * 0.5;

        const intensity = point.intensity * (0.5 + Math.sin(t) * 0.3);
        
        // Color based on 528Hz lock and coherence
        let hue: number;
        if (isLocked) {
          hue = 120; // Green for 528Hz lock
        } else {
          hue = (point.phase * 180 / Math.PI + time * 50) % 360;
        }
        
        const saturation = 70 + coherence * 20;
        const lightness = 40 + intensity * 40;

        // Draw primary projection
        ctx.fillStyle = `hsla(${hue}, ${saturation}%, ${lightness}%, ${intensity * 0.9})`;
        ctx.beginPath();
        ctx.arc(x1, y1, 2 + intensity * 4, 0, Math.PI * 2);
        ctx.fill();

        // Draw secondary projection
        ctx.fillStyle = `hsla(${(hue + 120) % 360}, ${saturation - 10}%, ${lightness + 10}%, ${intensity * 0.7})`;
        ctx.beginPath();
        ctx.arc(x2, y2, 1.5 + intensity * 3, 0, Math.PI * 2);
        ctx.fill();

        // Draw mixed projection
        ctx.fillStyle = `hsla(${(hue + 240) % 360}, ${saturation - 20}%, ${lightness + 20}%, ${intensity * 0.5})`;
        ctx.beginPath();
        ctx.arc(x3, y3, 1 + intensity * 2, 0, Math.PI * 2);
        ctx.fill();

        // Connect high-intensity points
        if (intensity > 0.6 && i > 0) {
          const prev = fieldPoints[i - 1];
          const prevX = width * 0.25 + prev.x * Math.cos(t - 0.1) * scale1;
          const prevY = height * 0.35 + prev.y * Math.cos(t * 0.3 - 0.1) * scale1;
          
          ctx.strokeStyle = `hsla(${hue}, 80%, 60%, ${intensity * 0.3})`;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(prevX, prevY);
          ctx.lineTo(x1, y1);
          ctx.stroke();
        }
      });

      // Draw resonance rings when locked
      if (isLocked) {
        const ringIntensity = 0.3 + Math.sin(time * 2) * 0.2;
        ctx.strokeStyle = `hsla(120, 80%, 50%, ${ringIntensity})`;
        ctx.lineWidth = 2;
        
        [0.25, 0.75, 0.5].forEach((xPos, idx) => {
          const yPos = idx === 2 ? 0.8 : 0.35;
          ctx.beginPath();
          ctx.arc(width * xPos, height * yPos, 60 + Math.sin(time + idx) * 10, 0, Math.PI * 2);
          ctx.stroke();
        });
      }

      // Labels
      ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.font = '10px monospace';
      ctx.fillText('D1-D3 (Price/Vol/Time)', 10, height * 0.35 - 70);
      ctx.fillText('D4-D6 (Corr/Mom/Freq)', width * 0.75 - 60, height * 0.35 - 70);
      ctx.fillText('FUSED', width * 0.5 - 20, height * 0.8 + 50);

      animationRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [fieldPoints, waveform]);

  const getWaveStateColor = () => {
    switch (waveform?.waveState) {
      case 'CRYSTALLINE': return 'text-primary';
      case 'RESONANT': return 'text-success';
      case 'TURBULENT': return 'text-warning';
      case 'CHAOTIC': return 'text-destructive';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Waves className="h-4 w-4 text-primary" />
            6D HARMONIC FIELD
          </CardTitle>
          <div className="flex items-center gap-2">
            {waveform?.harmonicLock && (
              <Badge variant="default" className="text-[10px] bg-success/20 text-success border-success/50">
                <Zap className="h-3 w-3 mr-1" />
                528 Hz LOCK
              </Badge>
            )}
            <Badge variant="outline" className={cn("text-[10px]", getWaveStateColor())}>
              {waveform?.waveState || 'INITIALIZING'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <canvas
          ref={canvasRef}
          width={500}
          height={300}
          className="w-full h-[300px] bg-black/90"
          style={{ imageRendering: 'auto' }}
        />
        
        {/* Metrics overlay */}
        <div className="grid grid-cols-4 gap-2 p-3 bg-muted/20 border-t border-border/30">
          <MetricBox 
            label="Coherence" 
            value={waveform?.dimensionalCoherence || 0} 
            icon={<Activity className="h-3 w-3" />}
          />
          <MetricBox 
            label="Phase Align" 
            value={waveform?.phaseAlignment || 0}
          />
          <MetricBox 
            label="Resonance" 
            value={waveform?.resonanceScore || 0}
          />
          <MetricBox 
            label="Energy" 
            value={waveform?.energyDensity || 0}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function MetricBox({ 
  label, 
  value, 
  icon 
}: { 
  label: string; 
  value: number; 
  icon?: React.ReactNode 
}) {
  const percentage = (value * 100).toFixed(1);
  const color = value > 0.8 ? 'text-success' : value > 0.5 ? 'text-warning' : 'text-muted-foreground';
  
  return (
    <div className="text-center">
      <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground mb-1">
        {icon}
        {label}
      </div>
      <div className={cn("text-sm font-mono font-bold", color)}>
        {percentage}%
      </div>
    </div>
  );
}
