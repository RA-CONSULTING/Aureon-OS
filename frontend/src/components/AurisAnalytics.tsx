import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { useAurisMetrics, useBasicEcosystemMetrics } from '@/hooks/useEcosystemData';

// 9 Auris nodes with their frequencies
const AURIS_SYMBOLS = [
  { symbol: '🐯', name: 'Tiger', frequency: 174 },
  { symbol: '🦅', name: 'Falcon', frequency: 285 },
  { symbol: '🐦', name: 'Hummingbird', frequency: 396 },
  { symbol: '🐬', name: 'Dolphin', frequency: 417 },
  { symbol: '🦌', name: 'Deer', frequency: 528 },
  { symbol: '🦉', name: 'Owl', frequency: 639 },
  { symbol: '🐼', name: 'Panda', frequency: 741 },
  { symbol: '🚢', name: 'CargoShip', frequency: 852 },
  { symbol: '🐠', name: 'Clownfish', frequency: 963 },
];

export const AurisAnalytics = () => {
  const {
    compilationRate,
    symbolProcessing,
    quantumEntanglement,
    dataIntegrity,
    dominantNode,
    isInitialized,
  } = useAurisMetrics();
  
  const { coherence, systemsOnline } = useBasicEcosystemMetrics();

  // Generate symbol activity based on dominant node and coherence
  const symbols = AURIS_SYMBOLS.map((s, i) => ({
    ...s,
    resonance: s.name === dominantNode 
      ? 0.9 + coherence * 0.1 
      : 0.5 + coherence * 0.4 + (Math.sin(Date.now() / 1000 + i) * 0.05),
    active: s.name === dominantNode || coherence > 0.6 + (i * 0.03),
  }));

  const streamData = {
    packetsProcessed: 15847 + Math.floor(Date.now() / 500) % 5000,
    errorRate: (1 - dataIntegrity) * 0.1,
    throughput: 1.5 + compilationRate * 1.5,
    latency: Math.max(5, 15 - compilationRate * 8),
  };

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-muted-foreground">Initializing Auris nodes...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Compilation Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {(compilationRate * 100).toFixed(1)}%
            </div>
            <Progress value={compilationRate * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Symbol Processing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              {(symbolProcessing * 100).toFixed(1)}%
            </div>
            <Progress value={symbolProcessing * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Quantum Link</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              {(quantumEntanglement * 100).toFixed(1)}%
            </div>
            <Progress value={quantumEntanglement * 100} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Data Integrity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">
              {(dataIntegrity * 100).toFixed(1)}%
            </div>
            <Progress value={dataIntegrity * 100} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Auris Nodes ({symbols.filter(s => s.active).length}/9 Active)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {symbols.map((symbol, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="text-2xl">{symbol.symbol}</div>
                    <div className="text-sm text-muted-foreground">
                      {symbol.name} • {symbol.frequency} Hz
                    </div>
                    <Badge variant={symbol.active ? "default" : "secondary"}>
                      {symbol.name === dominantNode ? "DOMINANT" : symbol.active ? "Active" : "Idle"}
                    </Badge>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm w-12">{(symbol.resonance * 100).toFixed(0)}%</span>
                    <Progress value={symbol.resonance * 100} className="w-20" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Stream Analytics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Packets Processed</span>
                <span className="font-bold">{streamData.packetsProcessed.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Error Rate</span>
                <span className="font-bold text-destructive">{(streamData.errorRate * 100).toFixed(3)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Throughput</span>
                <span className="font-bold text-success">{streamData.throughput.toFixed(1)} MB/s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Latency</span>
                <span className="font-bold text-primary">{streamData.latency.toFixed(0)} ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Systems Online</span>
                <span className="font-bold text-primary">{systemsOnline}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AurisAnalytics;
