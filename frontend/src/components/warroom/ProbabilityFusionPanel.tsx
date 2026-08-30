/**
 * Probability Fusion Panel for War Room
 * Displays HNC Probability Matrix fusion results
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Blend, Target, TrendingUp, TrendingDown, Minus, Zap } from 'lucide-react';
import { probabilityMatrix, type ProbabilityFusion } from '@/core/enhanced6DProbabilityMatrix';

export function ProbabilityFusionPanel() {
  const [fusion, setFusion] = useState<ProbabilityFusion | null>(null);
  
  useEffect(() => {
    // Get initial fusion
    setFusion(probabilityMatrix.getLastFusion());
    
    // Poll for updates
    const interval = setInterval(() => {
      const latest = probabilityMatrix.getLastFusion();
      if (latest) setFusion(latest);
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);
  
  if (!fusion) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="flex items-center justify-center h-32">
          <div className="text-muted-foreground animate-pulse">Awaiting Probability Fusion...</div>
        </CardContent>
      </Card>
    );
  }
  
  const ActionIcon = fusion.action.includes('BUY') ? TrendingUp : 
                     fusion.action.includes('SELL') ? TrendingDown : Minus;
  
  const actionColor = fusion.action.includes('BUY') ? 'text-success' :
                      fusion.action.includes('SELL') ? 'text-destructive' : 'text-muted-foreground';
  
  return (
    <Card className={`bg-card/50 backdrop-blur border-primary/20 transition-all duration-500 ${
      fusion.harmonicLock ? 'border-success/50 shadow-[0_0_20px_rgba(34,197,94,0.3)]' : ''
    }`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Blend className="w-5 h-5 text-primary" />
            Probability Fusion
          </CardTitle>
          {fusion.harmonicLock && (
            <Badge className="bg-success animate-pulse">
              <Zap className="w-3 h-3 mr-1" /> HARMONIC LOCK
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Input Probabilities */}
        <div className="space-y-2">
          <ProbabilityBar label="6D Harmonic" value={fusion.probability6D} weight={fusion.weight6D} color="bg-primary" />
          <ProbabilityBar label="HNC Matrix" value={fusion.probabilityHNC} weight={fusion.weightHNC} color="bg-primary" />
          <ProbabilityBar label="Lighthouse" value={fusion.probabilityLighthouse} weight={fusion.weightLighthouse} color="bg-warning" />
        </div>
        
        {/* Fused Probability Meter */}
        <div className="p-3 bg-background/30 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">Fused Probability</span>
            <span className="text-xs text-success">+{(fusion.resonanceBoost * 100).toFixed(0)}% boost</span>
          </div>
          
          <div className="relative h-5 bg-muted/30 rounded-full overflow-hidden mb-2">
            <div className="absolute inset-0 bg-gradient-to-r from-destructive via-warning to-success opacity-30" />
            <div 
              className="absolute top-0 bottom-0 w-1 bg-white shadow-lg transition-all duration-500"
              style={{ left: `${fusion.fusedProbability * 100}%` }}
            />
            <div 
              className="absolute top-0 bottom-0 flex items-center transition-all duration-500"
              style={{ left: `${fusion.fusedProbability * 100}%`, transform: 'translateX(-50%)' }}
            >
              <span className="text-xs font-bold bg-background/80 px-1 rounded">
                {(fusion.fusedProbability * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
        
        {/* Action & Confidence */}
        <div className="flex items-center justify-between p-2 bg-background/30 rounded-lg">
          <div className="flex items-center gap-2">
            <ActionIcon className={`w-5 h-5 ${actionColor}`} />
            <span className={`text-lg font-bold ${actionColor}`}>
              {fusion.action.replace('_', ' ')}
            </span>
          </div>
          <div className="text-right flex items-center gap-1">
            <Target className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-bold">{(fusion.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProbabilityBar({ label, value, weight, color }: { label: string; value: number; weight: number; color: string }) {
  const direction = value >= 0.5 ? 'BULL' : 'BEAR';
  const dirColor = value >= 0.5 ? 'text-success' : 'text-destructive';
  
  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <div className="flex items-center gap-2">
          <span className="text-xs">{label}</span>
          <span className="text-[10px] text-muted-foreground">({(weight * 100).toFixed(0)}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] ${dirColor}`}>{direction}</span>
          <span className="text-xs font-mono">{(value * 100).toFixed(0)}%</span>
        </div>
      </div>
      <Progress value={value * 100} className={`h-1.5 ${color}`} />
    </div>
  );
}
