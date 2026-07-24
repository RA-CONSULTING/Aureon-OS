import React, { useState, useEffect, useRef } from 'react';
// import { motion } from 'framer-motion';
import { Card } from './ui/card';
import { Button } from './ui/button';

export const VisualizationPanel: React.FC<{ tool: string }> = ({ tool }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [snapshot, setSnapshot] = useState<'early' | 'mid' | 'late' | null>(null);

  // Generate synthetic field visualization
  const generateFieldViz = (timepoint: 'early' | 'mid' | 'late') => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Create gradient based on timepoint
    const gradient = ctx.createRadialGradient(
      canvas.width / 2, canvas.height / 2, 0,
      canvas.width / 2, canvas.height / 2, Math.min(canvas.width, canvas.height) / 2
    );
    
    switch (timepoint) {
      case 'early':
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)'); // blue
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.1)');
        break;
      case 'mid':
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.8)'); // green
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.1)');
        break;
      case 'late':
        gradient.addColorStop(0, 'rgba(139, 92, 246, 0.8)'); // purple
        gradient.addColorStop(1, 'rgba(139, 92, 246, 0.1)');
        break;
    }

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Add field lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    
    const time = Date.now() * 0.001;
    for (let i = 0; i < 20; i++) {
      ctx.beginPath();
      const phase = (i / 20) * Math.PI * 2 + time;
      const radius = 50 + i * 10;
      
      for (let angle = 0; angle < Math.PI * 2; angle += 0.1) {
        const x = canvas.width / 2 + Math.cos(angle + phase) * radius;
        const y = canvas.height / 2 + Math.sin(angle + phase) * radius * 0.6;
        
        if (angle === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    }
  };

  const loadSnapshot = async (timepoint: 'early' | 'mid' | 'late') => {
    setIsLoading(true);
    setSnapshot(timepoint);
    
    await new Promise(resolve => setTimeout(resolve, 800)); // Simulate loading
    generateFieldViz(timepoint);
    setIsLoading(false);
  };

  useEffect(() => {
    if (tool.startsWith('lev_')) {
      const timepoint = tool.split('_')[1] as 'early' | 'mid' | 'late';
      loadSnapshot(timepoint);
    }
  }, [tool]);

  const renderLEVSnapshot = () => {
    const timepoint = tool.split('_')[1] as 'early' | 'mid' | 'late';
    const timeLabels = { early: 't=050', mid: 't=500', late: 't=950' };
    
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h4 className="font-semibold text-slate-700">
            LEV Field Snapshot ({timeLabels[timepoint]})
          </h4>
          <Button onClick={() => loadSnapshot(timepoint)} disabled={isLoading} size="sm">
            {isLoading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
        
        <div className="relative bg-slate-900 rounded-lg overflow-hidden">
          <canvas
            ref={canvasRef}
            width={400}
            height={300}
            className="w-full h-auto"
          />
          
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50">
              <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="text-center p-2 bg-slate-50 rounded">
            <div className="font-semibold text-primary">φ Phase</div>
            <div className="text-slate-600">
              {timepoint === 'early' ? '0.234' : timepoint === 'mid' ? '0.567' : '0.891'}
            </div>
          </div>
          <div className="text-center p-2 bg-slate-50 rounded">
            <div className="font-semibold text-success">κ Coherence</div>
            <div className="text-slate-600">
              {timepoint === 'early' ? '0.123' : timepoint === 'mid' ? '0.456' : '0.789'}
            </div>
          </div>
          <div className="text-center p-2 bg-slate-50 rounded">
            <div className="font-semibold text-primary">ψ Amplitude</div>
            <div className="text-slate-600">
              {timepoint === 'early' ? '0.345' : timepoint === 'mid' ? '0.678' : '0.234'}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const render3DField = () => (
    <div className="space-y-4">
      <h4 className="font-semibold text-slate-700">3D Field Viewer (ψ/κ)</h4>
      <div className="bg-slate-900 rounded-lg p-8 text-center text-white">
        <div className="text-6xl mb-4">🌐</div>
        <div className="text-lg">3D Field Visualization</div>
        <div className="text-sm text-slate-400 mt-2">
          Interactive Three.js renderer would appear here
        </div>
      </div>
    </div>
  );

  switch (tool) {
    case 'lev_early':
    case 'lev_mid':
    case 'lev_late':
      return <Card>{renderLEVSnapshot()}</Card>;
    case 'field3d':
      return <Card>{render3DField()}</Card>;
    case 'overlay':
      return <Card><div className="p-8 text-center text-slate-500">LEV Layer Overlay Tool</div></Card>;
    case 'plotly':
      return <Card><div className="p-8 text-center text-slate-500">Plotly Chart Panel</div></Card>;
    default:
      return <Card><div className="p-8 text-center text-slate-500">Select a visualization tool</div></Card>;
  }
};