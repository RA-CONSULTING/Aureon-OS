import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { useAurisMetrics, useBasicEcosystemMetrics } from '@/hooks/useEcosystemData';

const AURIS_SYMBOLS = ['Tiger', 'Falcon', 'Hummingbird', 'Dolphin', 'Deer', 'Owl', 'Panda', 'CargoShip', 'Clownfish'];

export const AurisAnalytics = () => {
  const auris = useAurisMetrics();
  const basic = useBasicEcosystemMetrics();
  const hasObservation = auris.dominantNode != null && basic.coherence != null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Auris Nodes</CardTitle>
            <Badge variant={hasObservation ? 'default' : 'secondary'}>
              {hasObservation ? 'real_derived' : 'no_data'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!hasObservation && (
            <p className="text-muted-foreground">
              No fresh market observation has completed the Auris calculation. Activity, throughput, latency, and resonance are not fabricated.
            </p>
          )}
          {hasObservation && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {AURIS_SYMBOLS.map((name) => (
                <div key={name} className="rounded border p-2 flex justify-between gap-2">
                  <span>{name}</span>
                  <Badge variant={name === auris.dominantNode ? 'default' : 'outline'}>
                    {name === auris.dominantNode ? 'Dominant' : 'Observed'}
                  </Badge>
                </div>
              ))}
            </div>
          )}
          <div className="text-sm text-muted-foreground">Evidence-bearing systems online: {basic.systemsOnline}</div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AurisAnalytics;
