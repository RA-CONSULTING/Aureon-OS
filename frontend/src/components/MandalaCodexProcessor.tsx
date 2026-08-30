import React, { useEffect, useRef, useState } from 'react';

interface MandalaCodexProcessorProps {
  consciousness?: number;
  symbolRate?: number;
}

export const MandalaCodexProcessor: React.FC<MandalaCodexProcessorProps> = ({
  consciousness = 0.5,
  symbolRate = 1.0
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeSymbols, setActiveSymbols] = useState<string[]>([]);

  const symbols = ['◊', '∞', '☯', '⚡', '◯', '△', '▽', '◈', '⬟', '⬢', '⟐', '⟡'];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      ctx.clearRect(0, 0, 300, 300);
      
      // Draw mandala base
      const centerX = 150;
      const centerY = 150;
      
      // Consciousness field gradient
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 150);
      gradient.addColorStop(0, `rgba(255, 255, 0, ${consciousness})`);
      gradient.addColorStop(0.5, `rgba(0, 255, 255, ${consciousness * 0.6})`);
      gradient.addColorStop(1, `rgba(128, 0, 255, ${consciousness * 0.3})`);
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 300, 300);
      
      // Draw symbolic patterns
      ctx.fillStyle = '#fff';
      ctx.font = '24px serif';
      ctx.textAlign = 'center';
      
      const time = Date.now() * 0.001 * symbolRate;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + time;
        const radius = 60 + 30 * Math.sin(time * 2);
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;
        
        const symbol = symbols[i % symbols.length];
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(time + i);
        ctx.fillText(symbol, 0, 0);
        ctx.restore();
      }
      
      requestAnimationFrame(animate);
    };
    
    animate();
  }, [consciousness, symbolRate, symbols]);

  useEffect(() => {
    const interval = setInterval(() => {
      const newSymbols = symbols.slice(0, Math.floor(consciousness * symbols.length));
      setActiveSymbols(newSymbols);
    }, 1000 / symbolRate);
    
    return () => clearInterval(interval);
  }, [consciousness, symbolRate, symbols]);

  return (
    <div className="bg-zinc-900 rounded-xl p-4 border border-zinc-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-zinc-300">Mandala Codex Processor</h3>
        <div className="text-xs text-zinc-400">
          Consciousness: {(consciousness * 100).toFixed(0)}%
        </div>
      </div>
      
      <canvas 
        ref={canvasRef}
        width={300}
        height={300}
        className="rounded-lg border border-zinc-600 mb-3"
      />
      
      <div className="flex flex-wrap gap-1">
        {activeSymbols.map((symbol, i) => (
          <span key={i} className="text-warning text-lg animate-pulse">
            {symbol}
          </span>
        ))}
      </div>
    </div>
  );
};