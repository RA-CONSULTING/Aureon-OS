import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { DimensionalDialler as Dialler, DimensionalDiallerState } from '@/core/dimensionalDialler';
import { Circle, Activity, Zap, Lock, Radio, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

interface DimensionalDiallerProps {
  harmonicCoherence: number;
  schumannFrequency: number;
  observerConsciousness: number;
}

export const DimensionalDialler = ({
  harmonicCoherence,
  schumannFrequency,
  observerConsciousness
}: DimensionalDiallerProps) => {
  const [dialler] = useState(() => new Dialler());
  const [state, setState] = useState<DimensionalDiallerState | null>(null);

  useEffect(() => {
    const update = () => {
      const timestamp = Date.now();
      const newState = dialler.dial(
        harmonicCoherence,
        schumannFrequency,
        observerConsciousness,
        timestamp
      );
      setState(newState);
    };

    update();
    const interval = setInterval(update, 50); // 20 Hz update rate
    return () => clearInterval(interval);
  }, [dialler, harmonicCoherence, schumannFrequency, observerConsciousness]);

  if (!state) return null;

  const { 
    stability, 
    primeLocks, 
    schumannLattice, 
    quantumEntanglements, 
    dialPosition, 
    activePrime, 
    temporalSync,
    driftDetection,
    correctionStatus
  } = state;

  const lockedPrimes = primeLocks.filter(p => p.locked);
  const coherentEntanglements = quantumEntanglements.filter(e => e.coherentState);

  // Drift status
  const isDrifting = driftDetection?.isDrifting || false;
  const driftUrgency = driftDetection?.urgency || 'low';
  const affectedSystems = driftDetection?.affectedSystems || [];

  // Correction status
  const isCorrecting = correctionStatus.isActive;
  const correctionPhase = correctionStatus.currentPhase;

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'text-destructive';
      case 'high': return 'text-warning';
      case 'medium': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  const handleManualCorrection = async () => {
    try {
      await dialler.manualCorrection();
    } catch (error) {
      console.error('Manual correction failed:', error);
    }
  };

  return (
    <Card className="border-primary/20 bg-background/95 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Circle className="h-5 w-5 text-primary animate-spin" style={{ animationDuration: '8s' }} />
            Dimensional Dialler
          </CardTitle>
          <div className="flex gap-2">
            {isDrifting && (
              <Badge variant="destructive" className={`gap-1 ${getUrgencyColor(driftUrgency)}`}>
                <AlertTriangle className="h-3 w-3" />
                Drift: {driftUrgency.toUpperCase()}
              </Badge>
            )}
            {isCorrecting && (
              <Badge variant="outline" className="gap-1 animate-pulse">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Correcting
              </Badge>
            )}
            <Badge variant={stability.overall > 0.8 ? "default" : "secondary"}>
              Stability: {(stability.overall * 100).toFixed(0)}%
            </Badge>
            <Badge variant="outline">
              Dial: {dialPosition.toFixed(0)}°
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Drift Detection Alert */}
        {isDrifting && (
          <div className={`p-3 rounded-lg border ${
            driftUrgency === 'critical' 
              ? 'bg-destructive/10 border-destructive/20' 
              : driftUrgency === 'high'
              ? 'bg-warning/10 border-warning/20'
              : 'bg-warning/10 border-warning/20'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`h-4 w-4 ${getUrgencyColor(driftUrgency)}`} />
                <span className={`text-sm font-medium ${getUrgencyColor(driftUrgency)}`}>
                  Dimensional Drift Detected
                </span>
              </div>
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleManualCorrection}
                disabled={isCorrecting}
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${isCorrecting ? 'animate-spin' : ''}`} />
                Manual Correction
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Affected systems: {affectedSystems.join(', ') || 'none'}
              {driftDetection && ` • Drift rate: ${(driftDetection.driftRate * 100).toFixed(2)}%/s`}
            </div>
            {isCorrecting && (
              <div className="mt-2 space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Phase: {correctionPhase}</span>
                  <span className="font-mono">{(correctionStatus.progress * 100).toFixed(0)}%</span>
                </div>
                <Progress value={correctionStatus.progress * 100} className="h-1" />
              </div>
            )}
          </div>
        )}

        {/* Successful Correction Alert */}
        {correctionStatus.lastCorrection && !isCorrecting && (
          <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-primary">
                Last Correction: {correctionStatus.lastCorrection.correctionType.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Stability improved from {(correctionStatus.lastCorrection.preCorrection.stability * 100).toFixed(0)}% 
              to {(correctionStatus.lastCorrection.postCorrection.stability * 100).toFixed(0)}% 
              in {correctionStatus.lastCorrection.duration}ms
            </div>
          </div>
        )}

        {/* Dimensional Dial Visualization */}
        <div className="relative w-full aspect-square max-w-xs mx-auto">
          <svg viewBox="0 0 200 200" className="w-full h-full">
            {/* Outer ring */}
            <circle
              cx="100"
              cy="100"
              r="90"
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
            
            {/* Prime number markers */}
            {primeLocks.slice(0, 12).map((lock, index) => {
              const angle = (index * 30 - 90) * Math.PI / 180;
              const x = 100 + 80 * Math.cos(angle);
              const y = 100 + 80 * Math.sin(angle);
              
              return (
                <g key={index}>
                  <circle
                    cx={x}
                    cy={y}
                    r="8"
                    fill={lock.locked ? 'hsl(var(--primary))' : 'hsl(var(--muted))'}
                    opacity={lock.coherence}
                  />
                  <text
                    x={x}
                    y={y + 4}
                    textAnchor="middle"
                    fill="hsl(var(--background))"
                    fontSize="10"
                    fontWeight="bold"
                  >
                    {lock.prime}
                  </text>
                </g>
              );
            })}

            {/* Quantum entanglement lines */}
            {quantumEntanglements.slice(0, 6).map((entanglement, index) => {
              if (entanglement.nodeA >= 12 || entanglement.nodeB >= 12) return null;
              
              const angleA = (entanglement.nodeA * 30 - 90) * Math.PI / 180;
              const angleB = (entanglement.nodeB * 30 - 90) * Math.PI / 180;
              const x1 = 100 + 80 * Math.cos(angleA);
              const y1 = 100 + 80 * Math.sin(angleA);
              const x2 = 100 + 80 * Math.cos(angleB);
              const y2 = 100 + 80 * Math.sin(angleB);
              
              return (
                <line
                  key={`ent-${index}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={entanglement.coherentState ? 'hsl(var(--primary))' : 'hsl(var(--muted))'}
                  strokeWidth={entanglement.coherentState ? "2" : "1"}
                  strokeDasharray={entanglement.coherentState ? "0" : "4 2"}
                  opacity={entanglement.entanglementStrength}
                />
              );
            })}

            {/* Dial pointer */}
            <line
              x1="100"
              y1="100"
              x2={100 + 70 * Math.cos((dialPosition - 90) * Math.PI / 180)}
              y2={100 + 70 * Math.sin((dialPosition - 90) * Math.PI / 180)}
              stroke="hsl(var(--primary))"
              strokeWidth="3"
              strokeLinecap="round"
            />
            
            {/* Center hub */}
            <circle
              cx="100"
              cy="100"
              r="10"
              fill="hsl(var(--primary))"
              opacity={stability.overall}
            />
          </svg>
        </div>

        {/* Stability Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Prime Alignment</span>
              <span className="font-mono">{(stability.primeAlignment * 100).toFixed(0)}%</span>
            </div>
            <Progress value={stability.primeAlignment * 100} className="h-2" />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Schumann Hold</span>
              <span className="font-mono">{(stability.schumannHold * 100).toFixed(0)}%</span>
            </div>
            <Progress value={stability.schumannHold * 100} className="h-2" />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Quantum Coherence</span>
              <span className="font-mono">{(stability.quantumCoherence * 100).toFixed(0)}%</span>
            </div>
            <Progress value={stability.quantumCoherence * 100} className="h-2" />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Dimensional Integrity</span>
              <span className="font-mono">{(stability.dimensionalIntegrity * 100).toFixed(0)}%</span>
            </div>
            <Progress value={stability.dimensionalIntegrity * 100} className="h-2" />
          </div>
        </div>

        {/* Prime Locks Status */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-muted-foreground">Prime Phase Locks</div>
            <Badge variant="outline" className="gap-1">
              <Lock className="h-3 w-3" />
              {lockedPrimes.length}/{primeLocks.length}
            </Badge>
          </div>
          <div className="grid grid-cols-10 gap-2">
            {primeLocks.map((lock, index) => (
              <div
                key={index}
                className={`p-2 rounded text-center text-xs font-mono transition-all ${
                  lock.locked
                    ? 'bg-primary text-primary-foreground shadow-lg'
                    : 'bg-muted text-muted-foreground'
                }`}
                style={{ opacity: 0.5 + lock.coherence * 0.5 }}
              >
                {lock.prime}
              </div>
            ))}
          </div>
        </div>

        {/* Schumann Lattice Status */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-muted-foreground">Schumann Lattice Harmonics</div>
            <Badge variant="outline" className="gap-1">
              <Radio className="h-3 w-3" />
              {schumannFrequency.toFixed(2)} Hz
            </Badge>
          </div>
          <div className="grid grid-cols-7 gap-2">
            {schumannLattice.map((node, index) => (
              <div
                key={index}
                className="space-y-1"
              >
                <div className="text-xs text-center text-muted-foreground">
                  {node.frequency.toFixed(1)}
                </div>
                <div className="h-16 bg-muted rounded-sm overflow-hidden">
                  <div
                    className="w-full bg-primary transition-all duration-300"
                    style={{
                      height: `${node.stability * 100}%`,
                      opacity: node.amplitude,
                      marginTop: 'auto'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quantum Entanglement Status */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-muted-foreground">Quantum Entanglement Pairs</div>
            <Badge variant={coherentEntanglements.length > 5 ? "default" : "secondary"} className="gap-1">
              <Zap className="h-3 w-3" />
              {coherentEntanglements.length} Coherent
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {quantumEntanglements.slice(0, 8).map((ent, index) => {
              const primeA = primeLocks[ent.nodeA]?.prime;
              const primeB = primeLocks[ent.nodeB]?.prime;
              const pingPongActive = Math.abs(Math.cos(ent.pingPongPhase)) > 0.5;
              
              return (
                <div
                  key={index}
                  className={`p-2 rounded-lg border transition-all ${
                    ent.coherentState
                      ? 'border-primary bg-primary/10'
                      : 'border-border bg-muted/50'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono">{primeA} ⇄ {primeB}</span>
                    {pingPongActive && (
                      <Activity className="h-3 w-3 text-primary animate-pulse" />
                    )}
                  </div>
                  <Progress
                    value={ent.entanglementStrength * 100}
                    className="h-1 mt-1"
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Status Summary */}
        <div className="pt-4 border-t border-border">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Active Prime</div>
              <div className="text-xl font-bold text-primary">{activePrime}</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Temporal Sync</div>
              <div className="text-xl font-bold text-primary">
                {(temporalSync * 100).toFixed(0)}%
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Dial Position</div>
              <div className="text-xl font-bold text-primary">{dialPosition.toFixed(0)}°</div>
            </div>
          </div>
        </div>

        {/* High Stability Alert */}
        {stability.overall > 0.9 && (
          <div className="p-3 rounded-lg bg-primary/10 border border-primary/20 animate-pulse">
            <div className="text-sm font-medium text-primary flex items-center gap-2">
              <Zap className="h-4 w-4" />
              🎯 DIMENSIONAL LOCK ACHIEVED - Prime Matrix Stable
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Quantum entanglement coherent • Schumann lattice holding • Temporal routing optimized
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
