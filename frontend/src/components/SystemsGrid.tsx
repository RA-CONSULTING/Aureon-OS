import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

interface SystemModule {
  id: string;
  name: string;
  description: string;
  status: 'online' | 'offline' | 'maintenance' | 'error';
  uptime: number;
  connections: string[];
  dataFlow: number;
  glyphSymbol: string;
}

const systemModules: SystemModule[] = [
  {
    id: 'harmonic-nexus',
    name: 'Harmonic Nexus Core',
    description: 'Quantum field harmonization and phase locking',
    status: 'online',
    uptime: 99.7,
    connections: ['auris-compiler', 'quantum-matrix', 'schumann-lattice'],
    dataFlow: 85,
    glyphSymbol: '🌌'
  },
  {
    id: 'auris-compiler',
    name: 'Auris Symbolic Compiler',
    description: 'Intent-to-frequency synthesis engine',
    status: 'online',
    uptime: 97.2,
    connections: ['harmonic-nexus', 'validation-protocol'],
    dataFlow: 62,
    glyphSymbol: '🔮'
  },
  {
    id: 'quantum-matrix',
    name: 'Quantum Field Matrix',
    description: 'Multi-dimensional field visualization',
    status: 'maintenance',
    uptime: 94.8,
    connections: ['harmonic-nexus', 'schumann-lattice'],
    dataFlow: 0,
    glyphSymbol: '⚛️'
  },
  {
    id: 'schumann-lattice',
    name: 'Schumann Resonance Lattice',
    description: 'Earth frequency monitoring and mapping',
    status: 'online',
    uptime: 98.9,
    connections: ['earth-streams', 'harmonic-nexus'],
    dataFlow: 78,
    glyphSymbol: '🌍'
  },
  {
    id: 'earth-streams',
    name: 'Earth Live Data Streams',
    description: 'Real-time planetary data ingestion',
    status: 'online',
    uptime: 96.1,
    connections: ['schumann-lattice', 'validation-protocol'],
    dataFlow: 91,
    glyphSymbol: '📡'
  },
  {
    id: 'validation-protocol',
    name: 'Live Validation Protocol',
    description: 'Real-time system validation and verification',
    status: 'online',
    uptime: 99.2,
    connections: ['auris-compiler', 'earth-streams'],
    dataFlow: 73,
    glyphSymbol: '✅'
  },
  {
    id: 'paw-simulator',
    name: 'PAW Atomic Simulator',
    description: 'Phased Atomic Weaver control system',
    status: 'offline',
    uptime: 0,
    connections: [],
    dataFlow: 0,
    glyphSymbol: '⚡'
  },
  {
    id: 'temporal-unity',
    name: 'Temporal Unity Console',
    description: 'Timeline synchronization and orchestration',
    status: 'error',
    uptime: 45.3,
    connections: ['harmonic-nexus'],
    dataFlow: 12,
    glyphSymbol: '⏰'
  }
];

export default function SystemsGrid() {
  const [selectedSystem, setSelectedSystem] = useState<SystemModule | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-success text-white';
      case 'maintenance': return 'bg-warning text-black';
      case 'error': return 'bg-destructive text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'online': return 'bg-success animate-pulse';
      case 'maintenance': return 'bg-warning';
      case 'error': return 'bg-destructive animate-pulse';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className="w-full space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {systemModules.map((system) => (
          <Card 
            key={system.id}
            className={`cursor-pointer transition-all hover:scale-105 ${
              selectedSystem?.id === system.id ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => setSelectedSystem(system)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{system.glyphSymbol}</span>
                  <div className={`w-2 h-2 rounded-full ${getStatusDot(system.status)}`} />
                </div>
                <Badge className={getStatusColor(system.status)}>
                  {system.status.toUpperCase()}
                </Badge>
              </div>
              <CardTitle className="text-sm font-semibold leading-tight">
                {system.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                {system.description}
              </p>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span>Uptime</span>
                  <span className="font-mono">{system.uptime.toFixed(1)}%</span>
                </div>
                <Progress value={system.uptime} className="h-1" />
                <div className="flex justify-between text-xs">
                  <span>Data Flow</span>
                  <span className="font-mono">{system.dataFlow}%</span>
                </div>
                <Progress value={system.dataFlow} className="h-1" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedSystem && (
        <Card className="border-primary/50 bg-primary/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <span className="text-3xl">{selectedSystem.glyphSymbol}</span>
              <div>
                <div className="text-xl">{selectedSystem.name}</div>
                <div className="text-sm text-muted-foreground">{selectedSystem.description}</div>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h4 className="font-semibold mb-2">System Status</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <Badge className={getStatusColor(selectedSystem.status)}>
                      {selectedSystem.status.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Uptime:</span>
                    <span className="font-mono">{selectedSystem.uptime.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Data Flow:</span>
                    <span className="font-mono">{selectedSystem.dataFlow}%</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Connections</h4>
                <div className="space-y-1">
                  {selectedSystem.connections.length > 0 ? (
                    selectedSystem.connections.map(conn => (
                      <Badge key={conn} variant="outline" className="text-xs">
                        {conn}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">No active connections</span>
                  )}
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Actions</h4>
                <div className="space-y-2">
                  <Button size="sm" className="w-full">
                    View Details
                  </Button>
                  <Button size="sm" variant="outline" className="w-full">
                    System Logs
                  </Button>
                  <Button size="sm" variant="outline" className="w-full">
                    Configure
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}