import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { useBasicEcosystemMetrics, useHarmonicMetrics } from '@/hooks/useEcosystemData';

interface PhaseData {
  guardianPhase: number;
  anchorPhase: number;
  phaseDiff: number;
  coherence: number;
  synchrony: number;
}

export const AnalysisModePanel: React.FC<{ tool: string }> = ({ tool }) => {
  const [phaseData, setPhaseData] = useState<PhaseData[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [memoryTrace, setMemoryTrace] = useState<number[]>([]);

  // Use real ecosystem data
  const basicMetrics = useBasicEcosystemMetrics();
  const harmonicMetrics = useHarmonicMetrics();
  const liveCoherence = basicMetrics.coherence;
  const lambda = basicMetrics.frequency / 528;
  const resonance = harmonicMetrics.harmonicFidelity;
  const phaseAlignment = harmonicMetrics.probabilityFusion;
  const dimensionalCoherence = harmonicMetrics.coherence;

  const generatePhaseData = (): PhaseData[] => {
    return Array.from({ length: 50 }, (_, i) => {
      const t = i / 50;
      // Use live coherence to influence phase calculations
      const guardianPhase = Math.sin(t * 4 * Math.PI + lambda) * 180;
      const anchorPhase = Math.cos(t * 3 * Math.PI + phaseAlignment) * 180;
      const phaseDiff = Math.abs(guardianPhase - anchorPhase);
      // Blend live coherence with computed coherence
      const computedCoherence = Math.exp(-phaseDiff / 180) * 0.8;
      const finalCoherence = computedCoherence * 0.7 + liveCoherence * 0.3;
      const synchrony = finalCoherence > 0.6 ? 1 : 0;
      
      return { guardianPhase, anchorPhase, phaseDiff, coherence: finalCoherence, synchrony };
    });
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    await new Promise(resolve => setTimeout(resolve, 1200));
    
    const data = generatePhaseData();
    setPhaseData(data);
    
    // Generate memory trace based on real resonance
    const trace = Array.from({ length: 20 }, (_, i) => {
      const base = resonance * 0.6;
      const variation = dimensionalCoherence * 0.4;
      return Math.min(1, Math.max(0, base + variation * Math.sin(i * 0.5)));
    });
    setMemoryTrace(trace);
    
    setIsAnalyzing(false);
  };

  const renderPhaseDynamics = () => (
    <div className="space-y-4 p-4">
      <div className="flex justify-between items-center">
        <h4 className="font-semibold text-foreground">Phase Dynamics Interpreter</h4>
        <Button onClick={runAnalysis} disabled={isAnalyzing} size="sm">
          {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
        </Button>
      </div>
      
      {/* Live metrics display */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-muted/30 p-2 rounded">
          <span className="text-muted-foreground">Live Γ:</span> 
          <span className="font-mono ml-1">{liveCoherence.toFixed(3)}</span>
        </div>
        <div className="bg-muted/30 p-2 rounded">
          <span className="text-muted-foreground">Live Λ:</span> 
          <span className="font-mono ml-1">{lambda.toFixed(3)}</span>
        </div>
      </div>
      
      {phaseData.length > 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-primary/10 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {phaseData[phaseData.length - 1]?.guardianPhase.toFixed(1)}°
              </div>
              <div className="text-xs text-muted-foreground">Guardian Phase</div>
            </div>
            <div className="text-center p-3 bg-success/10 rounded-lg">
              <div className="text-2xl font-bold text-success">
                {phaseData[phaseData.length - 1]?.anchorPhase.toFixed(1)}°
              </div>
              <div className="text-xs text-muted-foreground">Anchor Phase</div>
            </div>
            <div className="text-center p-3 bg-primary/10 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {phaseData[phaseData.length - 1]?.coherence.toFixed(3)}
              </div>
              <div className="text-xs text-muted-foreground">Coherence</div>
            </div>
          </div>
          
          <div className="relative h-32 bg-background rounded-lg overflow-hidden border border-border">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 border-2 border-primary rounded-full relative">
                <div className="absolute top-0 left-1/2 w-0.5 h-12 bg-primary -translate-x-0.5" />
                <div className="absolute -top-1 left-1/2 w-2 h-2 bg-primary rounded-full -translate-x-1" />
              </div>
              
              <div className="w-16 h-16 border-2 border-success rounded-full relative ml-4">
                <div className="absolute top-0 left-1/2 w-0.5 h-8 bg-success -translate-x-0.5" />
                <div className="absolute -top-1 left-1/2 w-2 h-2 bg-success rounded-full -translate-x-1" />
              </div>
            </div>
            
            <div className="absolute bottom-2 left-2 text-xs text-muted-foreground">
              Guardian (Primary) • Anchor (Green)
            </div>
          </div>
          
          <div className="text-xs text-muted-foreground">
            Synchrony Events: {phaseData.filter(d => d.synchrony === 1).length}/50 • 
            Avg Coherence: {(phaseData.reduce((sum, d) => sum + d.coherence, 0) / phaseData.length).toFixed(3)}
          </div>
        </div>
      )}
    </div>
  );

  const renderMemoryTracer = () => (
    <div className="space-y-4 p-4">
      <h4 className="font-semibold text-foreground">Symbolic Memory Tracer</h4>
      
      {/* Live metrics */}
      <div className="text-xs text-muted-foreground">
        Live Resonance: {resonance.toFixed(3)} | Dimensional Coherence: {dimensionalCoherence.toFixed(3)}
      </div>
      
      {memoryTrace.length > 0 && (
        <div className="space-y-3">
          <div className="h-20 bg-muted/30 rounded-lg p-3">
            <div className="text-xs text-muted-foreground mb-2">Pattern Correlation Over Time</div>
            <div className="flex items-end gap-1 h-12">
              {memoryTrace.map((value, idx) => (
                <div
                  key={idx}
                  className="bg-primary rounded-sm flex-1 transition-all duration-300"
                  style={{ height: `${value * 100}%` }}
                />
              ))}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="p-3 bg-muted/30 rounded">
              <div className="font-medium text-foreground">Peak Correlation</div>
              <div className="text-lg font-mono text-primary">
                {Math.max(...memoryTrace).toFixed(3)}
              </div>
            </div>
            <div className="p-3 bg-muted/30 rounded">
              <div className="font-medium text-foreground">Memory Persistence</div>
              <div className="text-lg font-mono text-primary">
                {(memoryTrace.filter(v => v > 0.5).length / memoryTrace.length * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderStabilityAnalyst = () => (
    <div className="space-y-4 p-4">
      <h4 className="font-semibold text-foreground">Stability Analyst</h4>
      
      <div className="grid grid-cols-2 gap-4">
        <div className={`p-4 rounded-lg border ${liveCoherence > 0.5 ? 'bg-success/10 border-success/30' : 'bg-muted/30 border-border'}`}>
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-3 h-3 rounded-full ${liveCoherence > 0.5 ? 'bg-success' : 'bg-muted-foreground'}`} />
            <span className={`font-medium ${liveCoherence > 0.5 ? 'text-success' : 'text-muted-foreground'}`}>Bounded Regime</span>
          </div>
          <div className={`text-sm ${liveCoherence > 0.5 ? 'text-success/80' : 'text-muted-foreground'}`}>
            {liveCoherence > 0.5 
              ? 'System exhibits stable oscillations within expected parameters'
              : 'Waiting for stable coherence levels'}
          </div>
        </div>
        
        <div className={`p-4 rounded-lg border ${liveCoherence > 0.7 ? 'bg-primary/10 border-primary/30' : 'bg-warning/10 border-warning/30'}`}>
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-3 h-3 rounded-full animate-pulse ${liveCoherence > 0.7 ? 'bg-primary' : 'bg-warning'}`} />
            <span className={`font-medium ${liveCoherence > 0.7 ? 'text-primary' : 'text-warning'}`}>
              {liveCoherence > 0.7 ? 'Optimal Zone' : 'Edge Dynamics'}
            </span>
          </div>
          <div className={`text-sm ${liveCoherence > 0.7 ? 'text-primary/80' : 'text-warning/80'}`}>
            {liveCoherence > 0.7 
              ? 'Operating in optimal coherence zone'
              : 'Approaching phase transition threshold'}
          </div>
        </div>
      </div>
    </div>
  );

  switch (tool) {
    case 'phase':
      return <Card className="border-border/50">{renderPhaseDynamics()}</Card>;
    case 'memory':
      return <Card className="border-border/50">{renderMemoryTracer()}</Card>;
    case 'stability':
      return <Card className="border-border/50">{renderStabilityAnalyst()}</Card>;
    case 'temporal':
      return <Card className="border-border/50"><div className="p-8 text-center text-muted-foreground">Temporal Synthesizer Interface</div></Card>;
    default:
      return <Card className="border-border/50"><div className="p-8 text-center text-muted-foreground">Select an analysis tool</div></Card>;
  }
};
