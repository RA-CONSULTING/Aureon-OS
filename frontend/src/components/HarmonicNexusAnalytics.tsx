import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { useHarmonicMetrics } from '@/hooks/useEcosystemData';

export const HarmonicNexusAnalytics = () => {
  const {
    frequency,
    coherence,
    waveState,
    harmonicLock,
    harmonicFidelity,
    probabilityFusion,
    phase,
    isInitialized,
  } = useHarmonicMetrics();

  // Derive harmonic data from real ecosystem metrics
  const resonanceData = {
    frequency: 7.83 + (coherence - 0.5) * 0.15,
    amplitude: coherence * 0.85 + 0.1,
    coherence: coherence,
    fieldStrength: harmonicFidelity || (coherence * 0.9 + 0.05),
  };

  // Harmonics based on fundamental with coherence influence
  const harmonics = [
    { freq: 7.83, amplitude: resonanceData.amplitude, phase: (Date.now() / 100) % 360 },
    { freq: 14.3, amplitude: resonanceData.amplitude * 0.7, phase: ((Date.now() / 100) + 45) % 360 },
    { freq: 20.8, amplitude: resonanceData.amplitude * 0.5, phase: ((Date.now() / 100) + 90) % 360 },
    { freq: 27.3, amplitude: resonanceData.amplitude * 0.35, phase: ((Date.now() / 100) + 135) % 360 },
  ];

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-muted-foreground">Initializing ecosystem...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Base Frequency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {resonanceData.frequency.toFixed(2)} Hz
            </div>
            <Progress value={resonanceData.frequency * 10} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Field Amplitude</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              {(resonanceData.amplitude * 100).toFixed(1)}%
            </div>
            <Progress value={resonanceData.amplitude * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Coherence Γ</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {(resonanceData.coherence * 100).toFixed(1)}%
            </div>
            <Progress value={resonanceData.coherence * 100} className="mt-2" />
            {harmonicLock && (
              <Badge variant="default" className="mt-2 bg-success">528 Hz LOCKED</Badge>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Field Strength</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">
              {(resonanceData.fieldStrength * 100).toFixed(1)}%
            </div>
            <Progress value={resonanceData.fieldStrength * 100} className="mt-2" />
            <Badge variant="outline" className="mt-2">{waveState}</Badge>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Harmonic Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {harmonics.map((harmonic, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <Badge variant="outline">{harmonic.freq.toFixed(1)} Hz</Badge>
                  <div className="text-sm text-muted-foreground">
                    Phase: {harmonic.phase.toFixed(0)}°
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm w-12">{(harmonic.amplitude * 100).toFixed(0)}%</span>
                  <Progress value={harmonic.amplitude * 100} className="w-24" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HarmonicNexusAnalytics;
