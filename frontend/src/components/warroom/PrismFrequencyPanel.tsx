/**
 * Prism Frequency Panel for War Room
 * Displays The Prism frequency transformation status
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Sparkles, Zap, Heart } from 'lucide-react';
import { useGlobalState } from '@/hooks/useGlobalState';
import { thePrism, type PrismOutput } from '@/core/thePrism';

export function PrismFrequencyPanel() {
  const globalState = useGlobalState();
  const [prismOutput, setPrismOutput] = useState<PrismOutput | null>(globalState.prismOutput);
  
  useEffect(() => {
    // Compute prism output from global state
    if (globalState.coherence > 0 || globalState.lambda !== 0) {
      const output = thePrism.transform({
        lambda: globalState.lambda,
        coherence: globalState.coherence,
        substrate: globalState.substrate,
        observer: globalState.observer,
        echo: globalState.echo,
        volatility: globalState.marketData.volatility,
        momentum: globalState.marketData.momentum,
        baseFrequency: 432,
      });
      setPrismOutput(output);
    }
  }, [globalState]);
  
  if (!prismOutput) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="flex items-center justify-center h-32">
          <div className="text-muted-foreground animate-pulse">Awaiting Prism...</div>
        </CardContent>
      </Card>
    );
  }
  
  const stateEmoji = {
    FORMING: '',
    CONVERGING: '',
    MANIFEST: '',
  }[prismOutput.state] || '';
  
  const levelLabels = ['HNC', 'IN', 'CREATE', 'REFLECT', 'UNITY', 'LOVE'];
  
  return (
    <Card className={`bg-card/50 backdrop-blur border-primary/20 transition-all duration-500 ${
      prismOutput.isLoveLocked ? 'border-success/50 shadow-[0_0_20px_rgba(34,197,94,0.3)]' : ''
    }`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="w-5 h-5 text-primary" />
            The Prism
          </CardTitle>
          {prismOutput.isLoveLocked && (
            <Badge className="bg-success animate-pulse">
              <Heart className="w-3 h-3 mr-1" /> 528Hz LOCKED
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Frequency Display */}
        <div className="text-center p-3 bg-background/30 rounded-lg">
          <div 
            className="text-4xl font-bold mb-1"
            style={{ color: thePrism.getFrequencyColor(prismOutput.frequency) }}
          >
            {prismOutput.frequency} Hz
          </div>
          <div className="text-xs text-muted-foreground flex items-center justify-center gap-2">
            <span>{stateEmoji}</span>
            <span>{prismOutput.state}</span>
            <span>•</span>
            <span>Level {prismOutput.level}/5</span>
          </div>
        </div>
        
        {/* Resonance & Purity */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Resonance</span>
              <span>{(prismOutput.resonance * 100).toFixed(0)}%</span>
            </div>
            <Progress value={prismOutput.resonance * 100} className="h-2" />
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Purity</span>
              <span>{(prismOutput.harmonicPurity * 100).toFixed(0)}%</span>
            </div>
            <Progress value={prismOutput.harmonicPurity * 100} className="h-2" />
          </div>
        </div>
        
        {/* 5-Layer Visualization */}
        <div className="grid grid-cols-6 gap-1">
          {Object.entries(prismOutput.layers).map(([key, value], index) => (
            <div key={key} className="flex flex-col items-center">
              <div 
                className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
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
              <span className="text-[8px] text-muted-foreground mt-0.5">{levelLabels[index]}</span>
            </div>
          ))}
        </div>
        
        {/* 528 Hz Distance */}
        <div className="flex items-center justify-between text-xs p-2 bg-background/30 rounded-lg">
          <span className="text-muted-foreground">Distance to 528 Hz</span>
          <span className={prismOutput.isLoveLocked ? 'text-success font-bold' : ''}>
            {prismOutput.isLoveLocked ? '✓ ALIGNED' : `${Math.abs(prismOutput.frequency - 528)} Hz`}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
