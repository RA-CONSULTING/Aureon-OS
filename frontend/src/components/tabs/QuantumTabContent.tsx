/**
 * Quantum Tab Content - Displays quantum state visualizations
 * 
 * This component is a PURE VIEW that reads from global state.
 * All systems run continuously in GlobalSystemsManager regardless of which tab is active.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { Activity, Waves, Radio, Sparkles, Target, Atom } from 'lucide-react';
import type { GlobalState } from '@/core/globalSystemsManager';

interface QuantumTabContentProps {
  globalState: GlobalState;
}

export function QuantumTabContent({ globalState }: QuantumTabContentProps) {
  const {
    coherence,
    lambda,
    lighthouseSignal,
    dominantNode,
    prismLevel,
    prismState,
    substrate,
    observer,
    echo,
    prismOutput,
    busSnapshot,
  } = globalState;

  const getPrismColor = () => {
    switch (prismState) {
      case 'MANIFEST': return 'text-success';
      case 'CONVERGING': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  // Get frequency from prism output or calculate from coherence
  const frequency = prismOutput?.frequency || (432 + coherence * 96);
  const is528Lock = frequency >= 520 && frequency <= 536;

  return (
    <div className="space-y-4">
      {/* Master Equation Components */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Lambda Field */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Atom className="h-4 w-4 text-primary" />
              Λ(t) Master Equation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-3xl font-mono font-bold text-center">
              {lambda.toFixed(4)}
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Substrate S(t)</span>
                <span className="font-mono">{substrate.toFixed(4)}</span>
              </div>
              <Progress value={Math.abs(substrate) * 100} className="h-1" />
              
              <div className="flex justify-between">
                <span className="text-muted-foreground">Observer O(t)</span>
                <span className="font-mono">{observer.toFixed(4)}</span>
              </div>
              <Progress value={Math.abs(observer) * 100} className="h-1" />
              
              <div className="flex justify-between">
                <span className="text-muted-foreground">Echo E(t)</span>
                <span className="font-mono">{echo.toFixed(4)}</span>
              </div>
              <Progress value={Math.abs(echo) * 100} className="h-1" />
            </div>
          </CardContent>
        </Card>

        {/* Coherence Metric */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Γ Coherence Metric
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className={cn(
              "text-3xl font-mono font-bold text-center",
              coherence >= 0.7 ? "text-success" : coherence >= 0.45 ? "text-warning" : "text-destructive"
            )}>
              {coherence.toFixed(4)}
            </div>
            <Progress 
              value={coherence * 100} 
              className={cn(
                "h-3",
                coherence >= 0.7 ? "[&>div]:bg-success" : coherence >= 0.45 ? "[&>div]:bg-warning" : "[&>div]:bg-destructive"
              )}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Trade threshold: 0.70</span>
              <span className={coherence >= 0.7 ? "text-success" : "text-destructive"}>
                {coherence >= 0.7 ? '✓ READY' : '✗ WAITING'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Prism Frequency */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              The Prism
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-center">
              <div className={cn(
                "text-3xl font-mono font-bold",
                is528Lock ? "text-success" : "text-foreground"
              )}>
                {frequency.toFixed(1)} Hz
              </div>
              <div className="text-xs text-muted-foreground">
                {is528Lock ? '🔒 528 Hz Love Lock' : 'Converging to 528 Hz'}
              </div>
            </div>
            
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Level</span>
              <Badge variant="outline" className="text-xs">{prismLevel}/5</Badge>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">State</span>
              <span className={getPrismColor()}>{prismState}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Resonance</span>
              <span className="font-mono">{((prismOutput?.resonance || 0) * 100).toFixed(0)}%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 9 Auris Nodes */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            9 Auris Nodes (Animal Totems)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
            {[
              { name: 'Tiger', emoji: '🐅', freq: '741 Hz', role: 'Momentum' },
              { name: 'Falcon', emoji: '🦅', freq: '852 Hz', role: 'Trend' },
              { name: 'Hummingbird', emoji: '🐦', freq: '963 Hz', role: 'HF Signals' },
              { name: 'Dolphin', emoji: '🐬', freq: '528 Hz', role: 'Harmony' },
              { name: 'Deer', emoji: '🦌', freq: '396 Hz', role: 'Fear/Greed' },
              { name: 'Owl', emoji: '🦉', freq: '432 Hz', role: 'Night' },
              { name: 'Panda', emoji: '🐼', freq: '412 Hz', role: 'Patience' },
              { name: 'Cargoship', emoji: '🚢', freq: '174 Hz', role: 'Volume' },
              { name: 'Clownfish', emoji: '🐠', freq: '639 Hz', role: 'Connection' },
            ].map((node) => (
              <div 
                key={node.name}
                className={cn(
                  "flex flex-col items-center p-2 rounded-lg border transition-all",
                  dominantNode === node.name 
                    ? "border-primary bg-primary/10" 
                    : "border-border/30 hover:border-border"
                )}
              >
                <span className="text-xl">{node.emoji}</span>
                <span className="text-[10px] font-medium">{node.name}</span>
                <span className="text-[8px] text-muted-foreground">{node.freq}</span>
                {dominantNode === node.name && (
                  <Badge variant="default" className="text-[8px] mt-1 px-1">ACTIVE</Badge>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Lighthouse & Bus */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Lighthouse Signal */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Radio className="h-4 w-4 text-primary" />
              Lighthouse Consensus
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className={cn(
              "text-3xl font-mono font-bold text-center",
              lighthouseSignal >= 0.7 ? "text-success" : "text-warning"
            )}>
              L = {lighthouseSignal.toFixed(4)}
            </div>
            <Progress value={lighthouseSignal * 100} className="h-2" />
            <div className="text-xs text-muted-foreground text-center">
              {lighthouseSignal >= 0.7 ? '✓ Lighthouse Event Detected' : 'Monitoring for LHE...'}
            </div>
          </CardContent>
        </Card>

        {/* Bus Consensus */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Waves className="h-4 w-4 text-primary" />
              Unified Bus Consensus
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-center gap-3">
              <Badge 
                variant={
                  busSnapshot?.consensusSignal === 'BUY' ? 'default' : 
                  busSnapshot?.consensusSignal === 'SELL' ? 'destructive' : 
                  'secondary'
                }
                className="text-lg px-4 py-1"
              >
                {busSnapshot?.consensusSignal || 'NEUTRAL'}
              </Badge>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-mono">{((busSnapshot?.consensusConfidence || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Systems Publishing</span>
              <span className="font-mono">{Object.keys(busSnapshot?.states || {}).length}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
