/**
 * Prime Seal Panel (10-9-1)
 * Displays real-time 10-9-1 Prime Seal status, coherence, and lock state
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Lock, Unlock, Zap, Waves, Anchor, Activity } from 'lucide-react';
import { usePrimeSeal } from '@/hooks/usePrimeSeal';

export function PrimeSealPanel() {
  const {
    isLocked,
    primeCoherence,
    latticePhase,
    unityCoherence,
    flowCoherence,
    anchorCoherence,
    lockReason,
    systemsContributing,
    lastUpdate,
    isLoading,
  } = usePrimeSeal();

  const coherencePercent = primeCoherence * 100;
  const lockThreshold = 94.5;

  return (
    <Card className="border-2 border-primary/30 bg-background/80 backdrop-blur">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            {isLocked ? (
              <Lock className="h-5 w-5 text-success" />
            ) : (
              <Unlock className="h-5 w-5 text-warning" />
            )}
            10-9-1 Prime Seal
          </CardTitle>
          <Badge variant={isLocked ? 'default' : 'secondary'} className={isLocked ? 'bg-success' : 'bg-warning'}>
            {isLocked ? '🔒 LOCKED' : '🔓 UNLOCKED'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Prime Coherence Gauge */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Prime Coherence (Γ)</span>
            <span className={`font-mono font-bold ${isLocked ? 'text-success' : 'text-warning'}`}>
              {primeCoherence.toFixed(4)}
            </span>
          </div>
          <div className="relative">
            <Progress value={coherencePercent} className="h-3" />
            <div 
              className="absolute top-0 h-3 w-px bg-destructive" 
              style={{ left: `${lockThreshold}%` }}
              title={`Lock threshold: ${lockThreshold}%`}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0%</span>
            <span className="text-destructive">↑ 94.5% lock threshold</span>
            <span>100%</span>
          </div>
        </div>

        {/* 10-9-1 Weight Breakdown */}
        <div className="grid grid-cols-3 gap-2">
          {/* Unity (10x) */}
          <div className="rounded-lg bg-primary/10 p-2 text-center">
            <div className="flex items-center justify-center gap-1 text-primary">
              <Zap className="h-4 w-4" />
              <span className="text-xs font-bold">10×</span>
            </div>
            <div className="text-lg font-mono font-bold text-primary">
              {(unityCoherence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Unity</div>
          </div>

          {/* Flow (9x) */}
          <div className="rounded-lg bg-primary/10 p-2 text-center">
            <div className="flex items-center justify-center gap-1 text-primary">
              <Waves className="h-4 w-4" />
              <span className="text-xs font-bold">9×</span>
            </div>
            <div className="text-lg font-mono font-bold text-primary">
              {(flowCoherence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Flow</div>
          </div>

          {/* Anchor (1x) */}
          <div className="rounded-lg bg-warning/10 p-2 text-center">
            <div className="flex items-center justify-center gap-1 text-warning">
              <Anchor className="h-4 w-4" />
              <span className="text-xs font-bold">1×</span>
            </div>
            <div className="text-lg font-mono font-bold text-warning">
              {(anchorCoherence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Anchor</div>
          </div>
        </div>

        {/* Lattice Phase */}
        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-2">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <span className="text-sm">Lattice Phase</span>
          </div>
          <span className="font-mono text-sm">{latticePhase.toFixed(1)}°</span>
        </div>

        {/* Lock Status Message */}
        <div className={`rounded-lg p-2 text-center text-sm ${isLocked ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}`}>
          {lockReason}
        </div>

        {/* Systems Contributing */}
        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">
            Systems Contributing ({systemsContributing.length}):
          </span>
          <div className="flex flex-wrap gap-1">
            {systemsContributing.slice(0, 6).map((sys) => (
              <Badge key={sys} variant="outline" className="text-xs">
                {sys}
              </Badge>
            ))}
            {systemsContributing.length > 6 && (
              <Badge variant="outline" className="text-xs">
                +{systemsContributing.length - 6} more
              </Badge>
            )}
          </div>
        </div>

        {/* Last Update */}
        <div className="text-right text-xs text-muted-foreground">
          {isLoading ? 'Loading...' : `Updated ${new Date(lastUpdate).toLocaleTimeString()}`}
        </div>
      </CardContent>
    </Card>
  );
}
