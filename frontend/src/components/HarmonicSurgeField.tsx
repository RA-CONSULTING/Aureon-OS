import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SurgePoint {
  x: number;
  y: number;
  z: number;
  intensity: number;
  phase: number;
}

export const HarmonicSurgeField: React.FC = () => {
  const [surgeData, setSurgeData] = useState<SurgePoint[]>([]);
  const [timestamp, setTimestamp] = useState(0);

  useEffect(() => {
    const generateSurgeField = () => {
      const points: SurgePoint[] = [];
      const time = Date.now() * 0.001;
      
      for (let i = 0; i < 500; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.random() * Math.PI;
        const r = Math.random() * 2 - 1;
        
        const x = r * Math.sin(phi) * Math.cos(theta);
        const y = r * Math.sin(phi) * Math.sin(theta);
        const z = r * Math.cos(phi);
        
        const intensity = Math.abs(Math.sin(time + x * 2) * Math.cos(time + y * 2) * Math.sin(time + z * 2));
        const phase = Math.atan2(y, x) + time * 0.5;
        
        points.push({ x, y, z, intensity, phase });
      }
      
      setSurgeData(points);
      setTimestamp(time);
    };

    generateSurgeField();
    const interval = setInterval(generateSurgeField, 100);
    return () => clearInterval(interval);
  }, []);

  const getPointColor = (point: SurgePoint) => {
    const hue = (point.phase * 180 / Math.PI) % 360;
    const saturation = Math.min(100, point.intensity * 100);
    const lightness = 40 + point.intensity * 40;
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-warning">6D Harmonic Surge Field</CardTitle>
        <div className="text-xs text-gray-400 font-mono">
          Timestamp: {timestamp.toFixed(3)}s | Points: {surgeData.length}
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative w-full h-96 bg-black rounded-lg overflow-hidden">
          <svg width="100%" height="100%" viewBox="-200 -200 400 400">
            {surgeData.map((point, i) => {
              const screenX = point.x * 150 + point.z * 50;
              const screenY = point.y * 150 + point.z * 30;
              const size = 2 + point.intensity * 4;
              
              return (
                <circle
                  key={i}
                  cx={screenX}
                  cy={screenY}
                  r={size}
                  fill={getPointColor(point)}
                  opacity={0.7 + point.intensity * 0.3}
                />
              );
            })}
          </svg>
          
          <div className="absolute top-2 left-2 text-xs text-warning">
            <div>Surge Phase Projection (X)</div>
            <div>Curvature + Feedback (Y)</div>
            <div>Memory Loop + Frequency Drift (Z)</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};