import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

interface NanoParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  brightness: number;
  phase: number;
}

export const NanoParticleVisualizer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isActive, setIsActive] = useState(false);
  const [particleCount, setParticleCount] = useState([500]);
  const [fieldStrength, setFieldStrength] = useState([75]);
  const [coherenceLevel, setCoherenceLevel] = useState([60]);
  const [particles, setParticles] = useState<NanoParticle[]>([]);

  useEffect(() => {
    initializeParticles();
  }, [particleCount[0]]);

  useEffect(() => {
    if (isActive) {
      const interval = setInterval(updateVisualization, 50);
      return () => clearInterval(interval);
    }
  }, [isActive, fieldStrength[0], coherenceLevel[0]]);

  const initializeParticles = () => {
    const newParticles: NanoParticle[] = [];
    for (let i = 0; i < particleCount[0]; i++) {
      newParticles.push({
        x: Math.random() * 800,
        y: Math.random() * 600,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        size: Math.random() * 3 + 1,
        brightness: Math.random() * 0.8 + 0.2,
        phase: Math.random() * Math.PI * 2
      });
    }
    setParticles(newParticles);
  };

  const updateVisualization = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const time = Date.now() * 0.001;
    const field = fieldStrength[0] / 100;
    const coherence = coherenceLevel[0] / 100;

    setParticles(prevParticles => 
      prevParticles.map(particle => {
        // Update position
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Apply field effects
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const dx = centerX - particle.x;
        const dy = centerY - particle.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Harmonic field influence
        const fieldForce = field * 0.1 / (distance + 1);
        particle.vx += dx * fieldForce * 0.01;
        particle.vy += dy * fieldForce * 0.01;

        // Coherence creates synchronized movement
        particle.phase += 0.1 + coherence * 0.05;
        particle.vx += Math.sin(particle.phase) * coherence * 0.02;
        particle.vy += Math.cos(particle.phase) * coherence * 0.02;

        // Boundary wrapping
        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = canvas.height;
        if (particle.y > canvas.height) particle.y = 0;

        // Damping
        particle.vx *= 0.99;
        particle.vy *= 0.99;

        return particle;
      })
    );

    // Render particles
    particles.forEach(particle => {
      const alpha = particle.brightness * (0.3 + coherence * 0.7);
      const size = particle.size * (0.5 + field * 0.5);
      
      ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, size, 0, Math.PI * 2);
      ctx.fill();

      // Add glow effect for high coherence
      if (coherence > 0.5) {
        ctx.fillStyle = `rgba(100, 200, 255, ${alpha * 0.3})`;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, size * 2, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // Draw field lines
    if (field > 0.3) {
      const fieldCenterX = canvas.width / 2;
      const fieldCenterY = canvas.height / 2;
      ctx.strokeStyle = `rgba(0, 150, 255, ${field * 0.3})`;
      ctx.lineWidth = 1;
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + time * 0.5;
        const x1 = fieldCenterX + Math.cos(angle) * 50;
        const y1 = fieldCenterY + Math.sin(angle) * 50;
        const x2 = fieldCenterX + Math.cos(angle) * 200;
        const y2 = fieldCenterY + Math.sin(angle) * 200;
        
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🔬 Nano-Particle Field Visualizer
          {isActive && <span className="text-sm text-success animate-pulse">LIVE</span>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Particle Count: {particleCount[0]}</label>
            <Slider
              value={particleCount}
              onValueChange={setParticleCount}
              min={100}
              max={1000}
              step={50}
              className="w-full"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Field Strength: {fieldStrength[0]}%</label>
            <Slider
              value={fieldStrength}
              onValueChange={setFieldStrength}
              min={0}
              max={100}
              step={5}
              className="w-full"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Coherence: {coherenceLevel[0]}%</label>
            <Slider
              value={coherenceLevel}
              onValueChange={setCoherenceLevel}
              min={0}
              max={100}
              step={5}
              className="w-full"
            />
          </div>
        </div>
        
        <div className="flex justify-center">
          <Button 
            onClick={() => setIsActive(!isActive)}
            variant={isActive ? "destructive" : "default"}
          >
            {isActive ? "Stop Simulation" : "Start Simulation"}
          </Button>
        </div>

        <div className="border rounded-lg overflow-hidden bg-black">
          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            className="w-full h-auto"
            style={{ maxHeight: '600px' }}
          />
        </div>

        <div className="text-sm text-muted-foreground space-y-1">
          <p>• White particles represent nano-scale quantum dots</p>
          <p>• Blue field lines show harmonic resonance patterns</p>
          <p>• Higher coherence creates synchronized particle movement</p>
          <p>• Field strength affects particle attraction to center</p>
        </div>
      </CardContent>
    </Card>
  );
};