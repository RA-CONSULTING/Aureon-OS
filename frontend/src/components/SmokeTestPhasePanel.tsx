/**
 * SMOKE TEST PHASE PANEL
 * 
 * Visual display of the Lighthouse-validated smoke test phases.
 * Shows each system family's startup status and ghost detection.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  smokeTestPhaseValidator, 
  SmokeTestState, 
  PhaseValidation,
  PhaseStatus 
} from '@/core/smokeTestPhaseValidator';
import { 
  Play, 
  Square, 
  RotateCcw, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Ghost,
  Loader2,
  Clock,
  Zap
} from 'lucide-react';

const getStatusIcon = (status: PhaseStatus) => {
  switch (status) {
    case 'PASSED':
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    case 'FAILED':
      return <XCircle className="h-4 w-4 text-destructive" />;
    case 'GHOST_DETECTED':
      return <Ghost className="h-4 w-4 text-primary" />;
    case 'VALIDATING':
      return <Loader2 className="h-4 w-4 text-warning animate-spin" />;
    case 'PENDING':
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
};

const getStatusBadge = (status: PhaseStatus) => {
  const variants: Record<PhaseStatus, string> = {
    'PASSED': 'bg-success/20 text-success border-success/30',
    'FAILED': 'bg-destructive/20 text-destructive border-destructive/30',
    'GHOST_DETECTED': 'bg-primary/20 text-primary border-primary/30',
    'VALIDATING': 'bg-warning/20 text-warning border-warning/30',
    'PENDING': 'bg-muted text-muted-foreground border-border',
  };
  
  return (
    <Badge variant="outline" className={`font-mono text-xs ${variants[status]}`}>
      {status.replace('_', ' ')}
    </Badge>
  );
};

const PhaseCard = ({ phase, isCurrent }: { phase: PhaseValidation; isCurrent: boolean }) => {
  const progress = (phase.validatedSystems.length / phase.requiredSystems.length) * 100;
  
  return (
    <div 
      className={`
        p-3 rounded-lg border transition-all duration-300
        ${isCurrent ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10' : 'border-border bg-card/50'}
        ${phase.status === 'PASSED' ? 'border-success/50' : ''}
        ${phase.status === 'GHOST_DETECTED' ? 'border-primary/50 animate-pulse' : ''}
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon(phase.status)}
          <span className="font-mono text-sm font-bold">
            PHASE {phase.phase}
          </span>
        </div>
        {getStatusBadge(phase.status)}
      </div>
      
      <div className="text-xs text-muted-foreground font-mono mb-2">
        {phase.name}
      </div>
      
      <Progress value={progress} className="h-1 mb-2" />
      
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          {phase.validatedSystems.length}/{phase.requiredSystems.length} systems
        </span>
        <span>
          L: {phase.lighthouseL.toFixed(3)} | Γ: {phase.coherence.toFixed(3)}
        </span>
      </div>
      
      {phase.ghostsDetected.length > 0 && (
        <div className="mt-2 p-2 rounded bg-primary/10 border border-primary/30">
          <div className="flex items-center gap-1 text-xs text-primary">
            <Ghost className="h-3 w-3" />
            <span>GHOSTS: {phase.ghostsDetected.join(', ')}</span>
          </div>
        </div>
      )}
      
      {phase.errorMessage && phase.status !== 'PASSED' && (
        <div className="mt-2 text-xs text-muted-foreground font-mono">
          {phase.errorMessage}
        </div>
      )}
    </div>
  );
};

export const SmokeTestPhasePanel = () => {
  const [state, setState] = useState<SmokeTestState | null>(null);

  useEffect(() => {
    const unsubscribe = smokeTestPhaseValidator.subscribe(setState);
    return unsubscribe;
  }, []);

  if (!state) {
    return (
      <Card className="bg-card/80 backdrop-blur border-border">
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const overallProgress = (state.currentPhase / state.totalPhases) * 100;
  const duration = state.endTime 
    ? ((state.endTime - state.startTime) / 1000).toFixed(1)
    : ((Date.now() - state.startTime) / 1000).toFixed(1);

  const getOverallStatusColor = () => {
    switch (state.overallStatus) {
      case 'PASSED': return 'text-success';
      case 'FAILED': return 'text-destructive';
      case 'GHOST_ALERT': return 'text-primary';
      case 'RUNNING': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <Card className="bg-card/80 backdrop-blur border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            LIGHTHOUSE SMOKE TEST
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge 
              variant="outline" 
              className={`font-mono ${getOverallStatusColor()}`}
            >
              {state.overallStatus}
            </Badge>
            <span className="text-xs text-muted-foreground font-mono">
              {duration}s
            </span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground font-mono">
            <span>Phase {state.currentPhase + 1} of {state.totalPhases}</span>
            <span>{Math.round(overallProgress)}% Complete</span>
          </div>
          <Progress value={overallProgress} className="h-2" />
        </div>

        {/* Controls */}
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={state.overallStatus === 'RUNNING' ? 'outline' : 'default'}
            onClick={() => smokeTestPhaseValidator.start()}
            disabled={state.overallStatus === 'RUNNING'}
            className="flex-1"
          >
            <Play className="h-4 w-4 mr-1" />
            Start
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => smokeTestPhaseValidator.stop()}
            disabled={state.overallStatus !== 'RUNNING'}
          >
            <Square className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => smokeTestPhaseValidator.reset()}
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => smokeTestPhaseValidator.forceAdvance()}
            disabled={state.overallStatus !== 'RUNNING'}
            className="text-warning"
          >
            <AlertTriangle className="h-4 w-4" />
          </Button>
        </div>

        {/* Lighthouse Validation Status */}
        <div className={`
          p-3 rounded-lg border text-center
          ${state.lighthouseValidated 
            ? 'bg-success/10 border-success/30' 
            : 'bg-muted/50 border-border'
          }
        `}>
          <div className="text-xs font-mono text-muted-foreground mb-1">
            LIGHTHOUSE PROTOCOL
          </div>
          <div className={`font-mono font-bold ${state.lighthouseValidated ? 'text-success' : 'text-muted-foreground'}`}>
            {state.lighthouseValidated ? '✓ VALIDATED' : 'AWAITING VALIDATION'}
          </div>
        </div>

        {/* Phase Grid */}
        <div className="grid grid-cols-2 gap-2">
          {state.phases.map((phase) => (
            <PhaseCard 
              key={phase.phase}
              phase={phase}
              isCurrent={phase.phase === state.currentPhase + 1}
            />
          ))}
        </div>

        {/* Ghost Alert */}
        {state.overallStatus === 'GHOST_ALERT' && (
          <div className="p-4 rounded-lg bg-primary/20 border border-primary/50 animate-pulse">
            <div className="flex items-center gap-2 text-primary font-mono">
              <Ghost className="h-5 w-5" />
              <span className="font-bold">SYSTEMIC GHOST PROBLEM DETECTED</span>
            </div>
            <p className="text-xs text-primary mt-2">
              Multiple systems are failing validation repeatedly. 
              Check for phantom registrations or stale connections.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
