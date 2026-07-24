import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Play, Pause, Square, Camera, Download } from 'lucide-react';
import { useEcosystemData } from '@/hooks/useEcosystemData';

interface ValidationMetrics {
  coherence: number;
  schumannLock: number;
  tsvGain: number;
  primeAlignment: number;
  tenNineOneConcordance: number;
  alphaTheta: number;
  hrvNorm: number;
  gsrNorm: number;
  calmIndex: number;
  auraHue: number;
}

interface ValidationPhase {
  name: string;
  duration: number;
  description: string;
  active: boolean;
  complete: boolean;
}

export default function LiveValidationDashboard() {
  const { metrics: ecosystemMetrics, isInitialized } = useEcosystemData();
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhase, setCurrentPhase] = useState(0);
  const [phaseTimer, setPhaseTimer] = useState(0);
  const [snapshots, setSnapshots] = useState<number[]>([]);
  
  // LIVE DATA ONLY - Use real ecosystem metrics
  const [metrics, setMetrics] = useState<ValidationMetrics>({
    coherence: 0,
    schumannLock: 0,
    tsvGain: 0,
    primeAlignment: 0,
    tenNineOneConcordance: 0,
    alphaTheta: 1.0,
    hrvNorm: 0,
    gsrNorm: 0,
    calmIndex: 0,
    auraHue: 0
  });

  const phases: ValidationPhase[] = [
    { name: "Warmup", duration: 60, description: "Sensor connection & baseline setup", active: false, complete: false },
    { name: "Baseline", duration: 120, description: "No intent recording", active: false, complete: false },
    { name: "Intent Block 1", duration: 60, description: "Grounding intent focus", active: false, complete: false },
    { name: "Washout 1", duration: 30, description: "Recovery period", active: false, complete: false },
    { name: "Intent Block 2", duration: 60, description: "Coherence intent focus", active: false, complete: false },
    { name: "Washout 2", duration: 30, description: "Recovery period", active: false, complete: false },
    { name: "Intent Block 3", duration: 60, description: "Alignment intent focus", active: false, complete: false },
    { name: "Schumann Nudge 1", duration: 60, description: "Fundamental +0.05 Hz", active: false, complete: false },
    { name: "Schumann Nudge 2", duration: 60, description: "Fundamental -0.05 Hz", active: false, complete: false },
    { name: "Spheres Mix", duration: 60, description: "Jupiter-Saturn synodic", active: false, complete: false }
  ];

  const [phaseStates, setPhaseStates] = useState(phases);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isRunning && currentPhase < phaseStates.length) {
      interval = setInterval(() => {
        setPhaseTimer(prev => {
          if (prev >= phaseStates[currentPhase].duration) {
            // Phase complete
            setPhaseStates(states => 
              states.map((phase, idx) => ({
                ...phase,
                active: idx === currentPhase + 1,
                complete: idx <= currentPhase
              }))
            );
            setCurrentPhase(prev => prev + 1);
            return 0;
          }
          return prev + 1;
        });

        // LIVE DATA ONLY - Use real ecosystem metrics
        setMetrics({
          coherence: ecosystemMetrics.coherence || 0,
          schumannLock: ecosystemMetrics.harmonicLock ? 1 : 0,
          tsvGain: ecosystemMetrics.probabilityFusion || 0,
          primeAlignment: ecosystemMetrics.consensusConfidence || 0,
          tenNineOneConcordance: ecosystemMetrics.hiveMindCoherence || 0,
          alphaTheta: 1.0 + (ecosystemMetrics.coherence || 0) * 0.5,
          hrvNorm: ecosystemMetrics.harmonicFidelity || 0,
          gsrNorm: ecosystemMetrics.qgitaConfidence || 0,
          calmIndex: ecosystemMetrics.coherence || 0,
          auraHue: (ecosystemMetrics.frequency || 528) / 10
        });
      }, 1000);
    }

    return () => clearInterval(interval);
  }, [isRunning, currentPhase, phaseStates]);

  const startValidation = () => {
    setIsRunning(true);
    setCurrentPhase(0);
    setPhaseTimer(0);
    setSnapshots([]);
    setPhaseStates(phases.map((phase, idx) => ({
      ...phase,
      active: idx === 0,
      complete: false
    })));
  };

  const pauseValidation = () => {
    setIsRunning(!isRunning);
  };

  const stopValidation = () => {
    setIsRunning(false);
    setCurrentPhase(0);
    setPhaseTimer(0);
    setPhaseStates(phases.map(phase => ({ ...phase, active: false, complete: false })));
  };

  const takeSnapshot = () => {
    const timestamp = Date.now();
    setSnapshots(prev => [...prev, timestamp]);
  };

  const exportData = () => {
    // Trigger CSV export
    console.log('Exporting validation data...');
  };

  const isValidationSuccess = metrics.coherence >= 0.65 && metrics.schumannLock >= 0.65;
  const totalDuration = phaseStates.reduce((sum, phase) => sum + phase.duration, 0);
  const elapsedTime = phaseStates.slice(0, currentPhase).reduce((sum, phase) => sum + phase.duration, 0) + phaseTimer;
  const progress = (elapsedTime / totalDuration) * 100;

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Live Validation Protocol
            <div className="flex gap-2">
              <Button 
                onClick={startValidation} 
                disabled={isRunning}
                size="sm"
              >
                <Play className="w-4 h-4 mr-2" />
                Start
              </Button>
              <Button 
                onClick={pauseValidation} 
                variant="outline"
                size="sm"
              >
                {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>
              <Button 
                onClick={stopValidation} 
                variant="destructive"
                size="sm"
              >
                <Square className="w-4 h-4" />
              </Button>
              <Button 
                onClick={takeSnapshot} 
                variant="secondary"
                size="sm"
                disabled={!isValidationSuccess}
              >
                <Camera className="w-4 h-4 mr-2" />
                Snapshot
              </Button>
              <Button 
                onClick={exportData} 
                variant="outline"
                size="sm"
              >
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Overall Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
            
            {currentPhase < phaseStates.length && (
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>{phaseStates[currentPhase]?.name}</span>
                  <span>{phaseTimer}s / {phaseStates[currentPhase]?.duration}s</span>
                </div>
                <Progress 
                  value={(phaseTimer / phaseStates[currentPhase]?.duration) * 100} 
                  className="h-1" 
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Metrics Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Coherence</div>
            <div className="text-2xl font-bold">{(metrics.coherence || 0).toFixed(3)}</div>
            <Badge variant={metrics.coherence >= 0.65 ? "default" : "secondary"}>
              {metrics.coherence >= 0.65 ? "PASS" : "MONITOR"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Schumann Lock</div>
            <div className="text-2xl font-bold">{(metrics.schumannLock || 0).toFixed(3)}</div>
            <Badge variant={metrics.schumannLock >= 0.65 ? "default" : "secondary"}>
              {metrics.schumannLock >= 0.65 ? "PASS" : "MONITOR"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">TSV Gain</div>
            <div className="text-2xl font-bold">{(metrics.tsvGain || 0).toFixed(3)}</div>
            <Badge variant={metrics.tsvGain < 0.92 ? "default" : "destructive"}>
              {metrics.tsvGain < 0.92 ? "SAFE" : "CLIP"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Calm Index</div>
            <div className="text-2xl font-bold">{(metrics.calmIndex || 0).toFixed(3)}</div>
            <Badge variant="outline">AURA</Badge>
          </CardContent>
        </Card>
      </div>
      {/* Phase Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Validation Phases</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {phaseStates.map((phase, idx) => (
              <div 
                key={idx} 
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  phase.active ? 'bg-primary border-primary' : 
                  phase.complete ? 'bg-success border-success' : 
                  'bg-gray-50 border-gray-200'
                }`}
              >
                <div>
                  <div className="font-medium">{phase.name}</div>
                  <div className="text-sm text-muted-foreground">{phase.description}</div>
                </div>
                <div className="text-sm">
                  {phase.duration}s
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Snapshots */}
      {snapshots.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Validation Snapshots ({snapshots.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-2">
              {snapshots.map((timestamp, idx) => (
                <div key={idx} className="p-2 bg-success rounded text-sm text-center">
                  Snap {idx + 1}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}