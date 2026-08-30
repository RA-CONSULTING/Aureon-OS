import { useEffect, useState } from 'react';
import { thePrism, type PrismOutput } from '@/core/thePrism';

interface PrismStatusProps {
  lambda: number;
  coherence: number;
  substrate: number;
  observer: number;
  echo: number;
  volatility: number;
  momentum: number;
  baseFrequency: number;
}

export const PrismStatus = ({
  lambda,
  coherence,
  substrate,
  observer,
  echo,
  volatility,
  momentum,
  baseFrequency,
}: PrismStatusProps) => {
  const [prismOutput, setPrismOutput] = useState<PrismOutput | null>(null);
  const [pulseAnimation, setPulseAnimation] = useState(false);

  useEffect(() => {
    const output = thePrism.transform({
      lambda,
      coherence,
      substrate,
      observer,
      echo,
      volatility,
      momentum,
      baseFrequency,
    });
    
    setPrismOutput(output);
    
    // Pulse animation when love locked
    if (output.isLoveLocked) {
      setPulseAnimation(true);
      const timer = setTimeout(() => setPulseAnimation(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [lambda, coherence, substrate, observer, echo, volatility, momentum, baseFrequency]);

  if (!prismOutput) return null;

  const stateEmoji = {
    FORMING: '🔶',
    CONVERGING: '🔷',
    MANIFEST: '💚',
  }[prismOutput.state];

  const levelLabels = ['HNC', 'INPUT', 'CREATE', 'REFLECT', 'UNITY', 'LOVE'];

  return (
    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          🔮 THE PRISM
          {prismOutput.isLoveLocked && (
            <span className={`text-xs px-2 py-0.5 rounded-full bg-success/20 text-success ${pulseAnimation ? 'animate-pulse' : ''}`}>
              528 Hz LOCKED
            </span>
          )}
        </h3>
        <span className="text-2xl">{stateEmoji}</span>
      </div>

      {/* Main Frequency Display */}
      <div className="text-center mb-4">
        <div 
          className="text-4xl font-bold mb-1"
          style={{ color: thePrism.getFrequencyColor(prismOutput.frequency) }}
        >
          {prismOutput.frequency} Hz
        </div>
        <div className="text-xs text-muted-foreground">
          {prismOutput.state} • Level {prismOutput.level}
        </div>
      </div>

      {/* Resonance Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted-foreground">Resonance</span>
          <span className="text-foreground">{(prismOutput.resonance * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div 
            className="h-full transition-all duration-500 rounded-full"
            style={{ 
              width: `${prismOutput.resonance * 100}%`,
              background: `linear-gradient(90deg, hsl(15, 90%, 55%), hsl(45, 100%, 50%), hsl(150, 100%, 50%))`,
            }}
          />
        </div>
      </div>

      {/* Harmonic Purity */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted-foreground">Harmonic Purity</span>
          <span className="text-foreground">{(prismOutput.harmonicPurity * 100).toFixed(1)}%</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary transition-all duration-500 rounded-full"
            style={{ width: `${prismOutput.harmonicPurity * 100}%` }}
          />
        </div>
      </div>

      {/* 5 Layer Visualization */}
      <div className="grid grid-cols-6 gap-1 text-center">
        {Object.entries(prismOutput.layers).map(([key, value], index) => (
          <div key={key} className="flex flex-col items-center">
            <div 
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-1 transition-all ${
                index <= prismOutput.level ? 'opacity-100' : 'opacity-30'
              }`}
              style={{ 
                background: index <= prismOutput.level 
                  ? `linear-gradient(135deg, ${thePrism.getFrequencyColor(value)}, ${thePrism.getStateColor(prismOutput.state)})`
                  : 'hsl(var(--muted))',
                color: index <= prismOutput.level ? 'white' : 'hsl(var(--muted-foreground))',
              }}
            >
              {index}
            </div>
            <span className="text-[9px] text-muted-foreground">{levelLabels[index]}</span>
            <span className="text-[8px] text-foreground/60">{Math.round(value)}</span>
          </div>
        ))}
      </div>

      {/* 528 Hz Target Indicator */}
      <div className="mt-4 pt-3 border-t border-border/30">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Distance to 528 Hz</span>
          <span className={prismOutput.isLoveLocked ? 'text-success font-bold' : 'text-foreground'}>
            {prismOutput.isLoveLocked ? '✓ ALIGNED' : `${Math.abs(prismOutput.frequency - 528)} Hz`}
          </span>
        </div>
      </div>
    </div>
  );
};
