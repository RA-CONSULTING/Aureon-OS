import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { useEarthMetrics, useBasicEcosystemMetrics } from '@/hooks/useEcosystemData';

export const EarthLiveAnalytics = () => {
  const {
    schumannFrequency,
    magneticField,
    ionosphereActivity,
    solarWind,
    geomagneticIndex,
    coherenceBoost,
    isInitialized,
  } = useEarthMetrics();
  
  const { systemsOnline } = useBasicEcosystemMetrics();

  // Sensor network derived from real metrics
  const sensorData = [
    { id: 'MAG-01', location: 'Arctic', value: magneticField * 60, status: magneticField > 0.8 ? 'active' : 'warning' },
    { id: 'MAG-02', location: 'Antarctic', value: magneticField * 55, status: 'active' },
    { id: 'ION-01', location: 'Equatorial', value: ionosphereActivity * 400, status: ionosphereActivity > 0.7 ? 'active' : 'warning' },
    { id: 'SOL-01', location: 'Solar Monitor', value: solarWind * 500, status: solarWind > 0.6 ? 'active' : 'warning' },
  ];

  const streamStats = {
    dataPoints: 24847 + Math.floor(Date.now() / 1000) % 10000,
    updateRate: 2.0 + coherenceBoost * 0.5,
    accuracy: 0.97 + coherenceBoost * 0.02,
    coverage: 0.9 + geomagneticIndex * 0.08,
  };

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-muted-foreground">Connecting to Earth sensors...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Magnetic Field</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {(magneticField * 100).toFixed(1)}%
            </div>
            <Progress value={magneticField * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Ionosphere</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              {(ionosphereActivity * 100).toFixed(1)}%
            </div>
            <Progress value={ionosphereActivity * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Solar Wind</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {(solarWind * 100).toFixed(1)}%
            </div>
            <Progress value={solarWind * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Schumann Resonance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">
              {schumannFrequency.toFixed(2)} Hz
            </div>
            <Progress value={(schumannFrequency / 8.5) * 100} className="mt-2" />
            {coherenceBoost > 0.05 && (
              <Badge variant="default" className="mt-2 bg-success">+{(coherenceBoost * 100).toFixed(1)}% Boost</Badge>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Sensor Network ({systemsOnline} Online)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sensorData.map((sensor, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Badge variant={sensor.status === 'active' ? "default" : "destructive"}>
                      {sensor.id}
                    </Badge>
                    <div className="text-sm text-muted-foreground">
                      {sensor.location}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-bold">{sensor.value.toFixed(1)}</span>
                    <div className={`w-3 h-3 rounded-full ${
                      sensor.status === 'active' ? 'bg-success' : 'bg-warning'
                    }`} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Data Stream Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Data Points</span>
                <span className="font-bold">{streamStats.dataPoints.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Update Rate</span>
                <span className="font-bold text-success">{streamStats.updateRate.toFixed(1)} Hz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Accuracy</span>
                <span className="font-bold text-primary">{(streamStats.accuracy * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Coverage</span>
                <span className="font-bold text-primary">{(streamStats.coverage * 100).toFixed(1)}%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default EarthLiveAnalytics;
