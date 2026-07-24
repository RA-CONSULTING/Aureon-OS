import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface QuantumParticle {
  id: string;
  energy: number;
  phase: number;
  spin: string;
  x: number;
  y: number;
  z: number;
}

interface MatrixDimension {
  name: string;
  value: number;
  stability: number;
}

export function QuantumField3DProjection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [timestamp, setTimestamp] = useState(new Date());
  const [fieldStability, setFieldStability] = useState(93.8);
  const [entanglement, setEntanglement] = useState(true);
  const [coherence, setCoherence] = useState(0.847);
  const [superposition, setSuperposition] = useState(0.923);
  
  const [dimensions] = useState<MatrixDimension[]>([
    { name: 'X-Dimension', value: 0.854, stability: 92 },
    { name: 'Y-Dimension', value: 0.843, stability: 85 },
    { name: 'Z-Dimension', value: 0.757, stability: 95 },
    { name: 'T-Dimension', value: 0.641, stability: 80 }
  ]);

  const [particles] = useState<QuantumParticle[]>([
    { id: 'Q1', energy: 1.35, phase: 94, spin: '↑+', x: 0.2, y: 0.3, z: 0.4 },
    { id: 'Q2', energy: 1.24, phase: 188, spin: '↑-', x: -0.3, y: 0.1, z: -0.2 },
    { id: 'Q3', energy: 1.30, phase: 320, spin: '↑+', x: 0.1, y: -0.4, z: 0.3 },
    { id: 'Q4', energy: 1.15, phase: 45, spin: '↑-', x: -0.2, y: 0.2, z: -0.1 }
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimestamp(new Date());
      setFieldStability(93.8 + Math.sin(Date.now() / 1000) * 2.5);
      setCoherence(0.847 + Math.cos(Date.now() / 1500) * 0.1);
      setSuperposition(0.923 + Math.sin(Date.now() / 2000) * 0.05);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw3DProjection = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const scale = 80;
      
      // Draw 3D axes
      ctx.strokeStyle = '#444';
      ctx.lineWidth = 1;
      
      // X-axis (red)
      ctx.strokeStyle = '#ff4444';
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(centerX + scale, centerY - scale * 0.3);
      ctx.stroke();
      
      // Y-axis (green)
      ctx.strokeStyle = '#44ff44';
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(centerX - scale * 0.5, centerY - scale * 0.5);
      ctx.stroke();
      
      // Z-axis (blue)
      ctx.strokeStyle = '#4444ff';
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(centerX, centerY - scale);
      ctx.stroke();

      // Draw quantum particles
      particles.forEach((particle, index) => {
        const projectedX = centerX + particle.x * scale - particle.y * scale * 0.5;
        const projectedY = centerY - particle.z * scale - particle.x * scale * 0.3;
        
        // Particle glow effect
        const gradient = ctx.createRadialGradient(projectedX, projectedY, 0, projectedX, projectedY, 15);
        gradient.addColorStop(0, `hsl(${particle.phase}, 80%, 60%)`);
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(projectedX, projectedY, 15, 0, Math.PI * 2);
        ctx.fill();
        
        // Particle core
        ctx.fillStyle = `hsl(${particle.phase}, 90%, 70%)`;
        ctx.beginPath();
        ctx.arc(projectedX, projectedY, 4, 0, Math.PI * 2);
        ctx.fill();
        
        // Particle label
        ctx.fillStyle = '#fff';
        ctx.font = '10px monospace';
        ctx.fillText(particle.id, projectedX + 8, projectedY - 8);
      });

      // Draw entanglement connections
      if (entanglement) {
        ctx.strokeStyle = '#ff00ff';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            const p1 = particles[i];
            const p2 = particles[j];
            
            const x1 = centerX + p1.x * scale - p1.y * scale * 0.5;
            const y1 = centerY - p1.z * scale - p1.x * scale * 0.3;
            const x2 = centerX + p2.x * scale - p2.y * scale * 0.5;
            const y2 = centerY - p2.z * scale - p2.x * scale * 0.3;
            
            ctx.globalAlpha = 0.3;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
        }
        ctx.setLineDash([]);
      }
    };

    draw3DProjection();
  }, [particles, entanglement, timestamp]);

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl">⚛️ Quantum Field Matrix Analytics</CardTitle>
          <Badge variant="secondary" className="text-xs">
            {timestamp.toLocaleTimeString()}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 3D Projection Canvas */}
        <div className="flex justify-center">
          <canvas
            ref={canvasRef}
            width={300}
            height={250}
            className="border rounded-lg bg-black"
          />
        </div>
        
        {/* Real-time Stats */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="text-center">
            <div className="font-semibold text-primary">Entangled</div>
            <div className={entanglement ? "text-success" : "text-destructive"}>
              {entanglement ? "ACTIVE" : "INACTIVE"}
            </div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-primary">Coherence</div>
            <div className="text-white">{coherence.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-warning">Superposition</div>
            <div className="text-white">{superposition.toFixed(3)}</div>
          </div>
        </div>

        {/* Field Stability */}
        <div className="text-center">
          <div className="font-semibold text-lg">Field Stability</div>
          <div className="text-2xl text-success">{fieldStability.toFixed(1)}%</div>
        </div>

        {/* Matrix Dimensions */}
        <div className="space-y-2">
          <h3 className="font-semibold text-center">Matrix Dimensions</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {dimensions.map((dim, index) => (
              <div key={index} className="bg-gray-800 p-2 rounded">
                <div className="font-semibold text-primary">{dim.name}</div>
                <div className="text-white">{dim.value.toFixed(3)}</div>
                <div className="text-gray-400">Stability: {dim.stability}%</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quantum Particles */}
        <div className="space-y-2">
          <h3 className="font-semibold text-center">Quantum Particles</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {particles.map((particle, index) => (
              <div key={index} className="bg-gray-800 p-2 rounded">
                <div className="font-semibold text-primary">
                  {particle.id} ({particle.spin})
                </div>
                <div className="text-white">{particle.energy.toFixed(2)} eV</div>
                <div className="text-gray-400">Phase: {particle.phase}°</div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}