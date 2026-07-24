import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Play, Pause, Square, Camera } from 'lucide-react';

interface ValidationState {
  phase: 'idle' | 'warmup' | 'baseline' | 'intent' | 'washout' | 'nudge' | 'spheres';
  timeRemaining: number;
  totalTime: number;
  epoch: number;
  snapshots: number;
}

const PHASES = [
  { name: 'warmup', duration: 60, label: 'Warm-up' },
  { name: 'baseline', duration: 120, label: 'Baseline' },
  { name: 'intent', duration: 180, label: 'Intent (3x1min)' },
  { name: 'nudge', duration: 120, label: 'Schumann Nudge' },
  { name: 'spheres', duration: 60, label: 'Spheres Mix' }
];

export const LiveValidationProtocol: React.FC = () => {
  const [state, setState] = useState<ValidationState>({
    phase: 'idle',
    timeRemaining: 0,
    totalTime: 0,
    epoch: 0,
    snapshots: 0
  });

  const [isRunning, setIsRunning] = useState(false);
  const [metrics, setMetrics] = useState({
    coherence: 0.42,
    schumannLock: 0.38,
    tsvGain: 0.65,
    primeAlignment: 0.51,
    concordance: 0.44
  });

  useEffect(() => {
    if (!isRunning) return;
    
    const timer = setInterval(() => {
      setState(prev => {
        if (prev.timeRemaining <= 1) {
          // Move to next phase
          const currentIndex = PHASES.findIndex(p => p.name === prev.phase);
          if (currentIndex < PHASES.length - 1) {
            const nextPhase = PHASES[currentIndex + 1];
            return {
              ...prev,
              phase: nextPhase.name as any,
              timeRemaining: nextPhase.duration,
              totalTime: nextPhase.duration,
              epoch: prev.epoch + 1
            };
          } else {
            setIsRunning(false);
            return { ...prev, phase: 'idle', timeRemaining: 0 };
          }
        }
        return { ...prev, timeRemaining: prev.timeRemaining - 1 };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isRunning]);

  const startProtocol = () => {
    setState({
      phase: 'warmup',
      timeRemaining: 60,
      totalTime: 60,
      epoch: 1,
      snapshots: 0
    });
    setIsRunning(true);
  };

  const takeSnapshot = () => {
    setState(prev => ({ ...prev, snapshots: prev.snapshots + 1 }));
    // Log snapshot with current metrics
    console.log('Snapshot taken:', { phase: state.phase, metrics, timestamp: Date.now() });
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = state.totalTime > 0 ? ((state.totalTime - state.timeRemaining) / state.totalTime) * 100 : 0;
  const canSnapshot = metrics.coherence >= 0.65 && metrics.schumannLock >= 0.65;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Live Validation Protocol
            <Badge variant={isRunning ? "default" : "secondary"}>
              {state.phase.toUpperCase()}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Button onClick={startProtocol} disabled={isRunning}>
              <Play className="w-4 h-4 mr-2" />
              Start 10-Min Protocol
            </Button>
            <Button 
              onClick={takeSnapshot} 
              disabled={!isRunning || !canSnapshot}
              variant={canSnapshot ? "default" : "secondary"}
            >
              <Camera className="w-4 h-4 mr-2" />
              Snapshot ({state.snapshots})
            </Button>
          </div>

          {isRunning && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Phase: {PHASES.find(p => p.name === state.phase)?.label}</span>
                <span>{formatTime(state.timeRemaining)}</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div className="text-center">
              <div className="font-medium">Coherence</div>
              <div className={metrics.coherence >= 0.65 ? "text-success" : "text-gray-600"}>
                {metrics.coherence.toFixed(3)}
              </div>
            </div>
            <div className="text-center">
              <div className="font-medium">Lock</div>
              <div className={metrics.schumannLock >= 0.65 ? "text-success" : "text-gray-600"}>
                {metrics.schumannLock.toFixed(3)}
              </div>
            </div>
            <div className="text-center">
              <div className="font-medium">TSV Gain</div>
              <div className={metrics.tsvGain < 0.92 ? "text-success" : "text-destructive"}>
                {metrics.tsvGain.toFixed(3)}
              </div>
            </div>
            <div className="text-center">
              <div className="font-medium">Prime</div>
              <div className="text-gray-600">{metrics.primeAlignment.toFixed(3)}</div>
            </div>
            <div className="text-center">
              <div className="font-medium">10-9-1</div>
              <div className="text-gray-600">{metrics.concordance.toFixed(3)}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};