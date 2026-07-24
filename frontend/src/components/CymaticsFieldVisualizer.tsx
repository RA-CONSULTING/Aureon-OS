import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Waves, AlertTriangle } from 'lucide-react';
import { useEcosystemData } from '@/hooks/useEcosystemData';

interface CymaticsPattern {
  frequency: number;
  coherence: number;
  patternType: 'chaos' | 'forming' | 'geometric' | 'sacred';
}

type DataStatus = 'LIVE' | 'STALE' | 'NO_DATA';

export function CymaticsFieldVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const { metrics, isInitialized, busSnapshot } = useEcosystemData();
  const [pattern, setPattern] = useState<CymaticsPattern>({
    frequency: 396,
    coherence: 0,
    patternType: 'chaos'
  });
  const [dataStatus, setDataStatus] = useState<DataStatus>('NO_DATA');
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  // Determine pattern type and data status based on coherence
  useEffect(() => {
    const coherence = metrics?.coherence ?? 0;
    const frequency = metrics?.frequency ?? 0;
    
    // Determine data status
    const hasRealData = coherence > 0 || (busSnapshot?.states?.MasterEquation?.coherence ?? 0) > 0;
    const now = Date.now();
    
    if (!isInitialized) {
      setDataStatus('NO_DATA');
    } else if (hasRealData) {
      setDataStatus('LIVE');
      setLastUpdate(now);
    } else if (now - lastUpdate > 10000) {
      setDataStatus('STALE');
    } else {
      setDataStatus('NO_DATA');
    }
    
    let patternType: CymaticsPattern['patternType'] = 'chaos';
    if (coherence > 0.9) patternType = 'sacred';
    else if (coherence > 0.7) patternType = 'geometric';
    else if (coherence > 0.4) patternType = 'forming';
    
    setPattern({ frequency: frequency || 396, coherence, patternType });
  }, [metrics, isInitialized, busSnapshot, lastUpdate]);

  // Canvas animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    
    let time = 0;
    
    const drawWaterSurface = () => {
      // Clear with dark background
      ctx.fillStyle = 'rgba(10, 10, 20, 0.15)';
      ctx.fillRect(0, 0, width, height);
      
      const freq = pattern.frequency;
      const coh = pattern.coherence;
      const nodes = Math.floor(3 + coh * 9); // More nodes at higher coherence
      
      // Draw cymatics-style wave interference pattern
      for (let i = 0; i < nodes; i++) {
        const angle = (i / nodes) * Math.PI * 2;
        const radius = 80 + Math.sin(time * 0.5 + i) * 20;
        
        const sourceX = centerX + Math.cos(angle + time * 0.1) * radius;
        const sourceY = centerY + Math.sin(angle + time * 0.1) * radius;
        
        // Draw concentric waves from each source
        const waveCount = Math.floor(5 + coh * 10);
        for (let w = 0; w < waveCount; w++) {
          const waveRadius = (time * 30 + w * 20) % 200;
          const alpha = Math.max(0, (1 - waveRadius / 200) * coh * 0.5);
          
          // Color based on frequency (Rainbow Bridge spectrum)
          let hue = 200; // Default blue
          if (freq >= 528) hue = 120; // Green for love frequency
          else if (freq >= 396) hue = 60; // Yellow for forming
          else if (freq < 300) hue = 0; // Red for fear
          
          ctx.strokeStyle = `hsla(${hue}, 70%, 60%, ${alpha})`;
          ctx.lineWidth = 1 + coh;
          ctx.beginPath();
          ctx.arc(sourceX, sourceY, waveRadius, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      
      // Draw sacred geometry overlay at high coherence
      if (coh > 0.7) {
        drawSacredGeometry(ctx, centerX, centerY, coh, time);
      }
      
      // Draw center frequency indicator
      ctx.fillStyle = coh > 0.9 ? 'hsl(142, 76%, 50%)' : 'hsl(60, 70%, 50%)';
      ctx.font = 'bold 16px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${Math.round(freq)} Hz`, centerX, height - 20);
      
      time += 0.02;
      animationRef.current = requestAnimationFrame(drawWaterSurface);
    };
    
    const drawSacredGeometry = (
      ctx: CanvasRenderingContext2D, 
      cx: number, 
      cy: number, 
      coherence: number, 
      t: number
    ) => {
      const sides = coherence > 0.9 ? 6 : 5; // Hexagon for 528Hz lock, pentagon otherwise
      const radius = 60 + Math.sin(t * 0.3) * 10;
      const alpha = (coherence - 0.7) * 2;
      
      ctx.strokeStyle = `hsla(142, 70%, 60%, ${alpha})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      
      for (let i = 0; i <= sides; i++) {
        const angle = (i / sides) * Math.PI * 2 - Math.PI / 2 + t * 0.1;
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius;
        
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      
      // Inner pattern for 528 Hz
      if (coherence > 0.9) {
        ctx.strokeStyle = `hsla(142, 90%, 70%, ${alpha * 0.8})`;
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
          const angle = (i / 6) * Math.PI * 2 - Math.PI / 2 + t * 0.1;
          const x = cx + Math.cos(angle) * radius;
          const y = cy + Math.sin(angle) * radius;
          ctx.moveTo(cx, cy);
          ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    };
    
    drawWaterSurface();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [pattern]);

  const getPatternBadge = () => {
    switch (pattern.patternType) {
      case 'sacred':
        return <Badge className="bg-success/20 text-success border-success/30">SACRED GEOMETRY</Badge>;
      case 'geometric':
        return <Badge className="bg-warning/20 text-warning border-warning/30">GEOMETRIC</Badge>;
      case 'forming':
        return <Badge className="bg-primary/20 text-primary border-primary/30">FORMING</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30">CHAOS</Badge>;
    }
  };

  const getDataStatusBadge = () => {
    switch (dataStatus) {
      case 'LIVE':
        return <Badge className="bg-success/20 text-success border-success/30 text-[10px]">LIVE</Badge>;
      case 'STALE':
        return <Badge className="bg-warning/20 text-warning border-warning/30 text-[10px]">STALE</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30 text-[10px]">NO DATA</Badge>;
    }
  };

  return (
    <Card className="border-border/50 overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-2">
            <Waves className="h-3 w-3" />
            CYMATICS FIELD
            {getDataStatusBadge()}
          </CardTitle>
          {getPatternBadge()}
        </div>
        {dataStatus === 'NO_DATA' && (
          <div className="flex items-center gap-1 text-[10px] text-warning mt-1">
            <AlertTriangle className="h-3 w-3" />
            <span>Awaiting ecosystem data...</span>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-2">
        <canvas
          ref={canvasRef}
          width={400}
          height={250}
          className="w-full h-auto rounded-md bg-background/50"
        />
        <div className="flex justify-between mt-2 text-xs text-muted-foreground">
          <span>Water ↔ Frequency Interference</span>
          <span className="font-mono">Γ = {pattern.coherence.toFixed(3)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
