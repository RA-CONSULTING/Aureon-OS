import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { useEarthMetrics } from '@/hooks/useEcosystemData';

const valueOrUnavailable = (value: number | null, suffix = '', digits = 2) =>
  value == null ? 'Unavailable' : `${value.toFixed(digits)}${suffix}`;

export const EarthLiveAnalytics = () => {
  const metrics = useEarthMetrics();

  if (!metrics.isEarthDataLoaded) {
    return (
      <Card>
        <CardHeader><CardTitle>Earth Data</CardTitle></CardHeader>
        <CardContent className="text-muted-foreground">
          No fresh NOAA source observation is available. No cached, demo, or generated sensor values are shown.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <CardTitle>NOAA-derived Earth Proxy</CardTitle>
            <Badge variant="outline">real_derived</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Metric label="Derived fundamental" value={valueOrUnavailable(metrics.schumannFrequency, ' Hz')} />
            <Metric label="Geomagnetic disturbance" value={valueOrUnavailable(metrics.geomagneticIndex, '', 3)} />
            <Metric label="Coherence boost" value={valueOrUnavailable(metrics.coherenceBoost, '', 4)} />
          </div>
          <p className="text-sm text-muted-foreground">{metrics.derivation}</p>
          <div className="text-xs font-mono text-muted-foreground break-all">
            Source: {metrics.sourceId} · {metrics.sourceTimestamp}
          </div>
          <p className="text-sm text-muted-foreground">
            Magnetic field, electric field, ionosphere, and solar-wind values are unavailable on this connector; they are not inferred from unrelated inputs.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}

export default EarthLiveAnalytics;
