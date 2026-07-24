import React from 'react';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Blend, Target, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { ProbabilityFusion } from '@/core/enhanced6DProbabilityMatrix';

interface ProbabilityMatrixDisplayProps {
  fusion: ProbabilityFusion | null;
}

export function ProbabilityMatrixDisplay({ fusion }: ProbabilityMatrixDisplayProps) {
  if (!fusion) {
    return (
      <Card className="p-4 bg-card/50 border-border/50">
        <div className="text-muted-foreground text-sm">Awaiting probability fusion...</div>
      </Card>
    );
  }

  const ActionIcon = fusion.action.includes('BUY') ? TrendingUp : 
                     fusion.action.includes('SELL') ? TrendingDown : Minus;
  
  const actionColor = fusion.action.includes('BUY') ? 'text-success' :
                      fusion.action.includes('SELL') ? 'text-destructive' : 'text-muted-foreground';

  return (
    <Card className="p-4 bg-card/50 border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <Blend className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Probability Matrix Fusion</h3>
      </div>

      {/* Input Probabilities */}
      <div className="space-y-3 mb-4">
        <ProbabilityBar 
          label="6D Harmonic" 
          value={fusion.probability6D} 
          weight={fusion.weight6D}
          color="bg-primary"
        />
        <ProbabilityBar 
          label="HNC" 
          value={fusion.probabilityHNC} 
          weight={fusion.weightHNC}
          color="bg-primary"
        />
        <ProbabilityBar 
          label="Lighthouse" 
          value={fusion.probabilityLighthouse} 
          weight={fusion.weightLighthouse}
          color="bg-warning"
        />
      </div>

      {/* Fusion Result */}
      <div className="border-t border-border/30 pt-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">Fused Probability</span>
          <span className="text-xs text-muted-foreground">
            Resonance Boost: +{(fusion.resonanceBoost * 100).toFixed(1)}%
          </span>
        </div>
        
        <div className="relative h-6 bg-muted/30 rounded-full overflow-hidden mb-3">
          {/* Gradient bar */}
          <div className="absolute inset-0 bg-gradient-to-r from-destructive via-warning to-success opacity-30" />
          {/* Indicator */}
          <div 
            className="absolute top-0 bottom-0 w-1 bg-white shadow-lg transition-all duration-500"
            style={{ left: `${fusion.fusedProbability * 100}%` }}
          />
          {/* Value label */}
          <div 
            className="absolute top-0 bottom-0 flex items-center transition-all duration-500"
            style={{ left: `${fusion.fusedProbability * 100}%`, transform: 'translateX(-50%)' }}
          >
            <span className="text-xs font-mono font-bold text-foreground bg-background/80 px-1 rounded">
              {(fusion.fusedProbability * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Action & Confidence */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ActionIcon className={`w-5 h-5 ${actionColor}`} />
            <span className={`text-lg font-bold ${actionColor}`}>
              {fusion.action.replace('_', ' ')}
            </span>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-muted-foreground">Confidence</div>
            <div className="flex items-center gap-1">
              <Target className="w-3 h-3 text-muted-foreground" />
              <span className="text-sm font-mono font-bold text-foreground">
                {(fusion.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>

        {/* Harmonic Lock Indicator */}
        {fusion.harmonicLock && (
          <div className="mt-2 flex items-center justify-center gap-2 py-1.5 rounded bg-success/10 border border-success/30">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
            <span className="text-xs font-medium text-success">HARMONIC LOCK ACTIVE</span>
          </div>
        )}
      </div>
    </Card>
  );
}

function ProbabilityBar({ 
  label, 
  value, 
  weight, 
  color 
}: { 
  label: string; 
  value: number; 
  weight: number; 
  color: string;
}) {
  const direction = value >= 0.5 ? 'BULL' : 'BEAR';
  const directionColor = value >= 0.5 ? 'text-success' : 'text-destructive';
  
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-foreground">{label}</span>
          <span className="text-[10px] text-muted-foreground">
            ({(weight * 100).toFixed(0)}% weight)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] ${directionColor}`}>{direction}</span>
          <span className="text-xs font-mono text-foreground">
            {(value * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-500`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );
}
