/**
 * Temporal Ladder Dashboard
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Real-time visualization of the hive-mind system interconnection network.
 * Shows system health, fallback chains, and inter-system coordination.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Radio, 
  ArrowDown,
  Clock,
  Zap
} from 'lucide-react';
import { temporalLadder, type TemporalLadderState, type SystemStatus, type FallbackEvent } from '@/core/temporalLadder';

export function TemporalLadderDashboard() {
  const [ladderState, setLadderState] = useState<TemporalLadderState | null>(null);
  const [fallbackHistory, setFallbackHistory] = useState<FallbackEvent[]>([]);

  useEffect(() => {
    // Subscribe to ladder state updates
    const unsubscribe = temporalLadder.subscribe(state => {
      setLadderState(state);
    });

    // Fetch initial history
    setFallbackHistory(temporalLadder.getFallbackHistory());

    // Poll for history updates
    const historyInterval = setInterval(() => {
      setFallbackHistory(temporalLadder.getFallbackHistory());
    }, 2000);

    return () => {
      unsubscribe();
      clearInterval(historyInterval);
    };
  }, []);

  if (!ladderState) {
    return (
      <Card className="bg-black/40 border-gray-700">
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            Initializing Temporal Ladder...
          </div>
        </CardContent>
      </Card>
    );
  }

  const systemsArray = Array.from(ladderState.systems.values());
  const activeSystems = systemsArray.filter(s => s.active);
  const recentFallbacks = fallbackHistory.slice(-10).reverse();

  return (
    <div className="space-y-4">
      <Card className="bg-gradient-to-br from-primary/20 via-black to-primary/20 border-primary/30">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Radio className="w-6 h-6 text-primary" />
                Temporal Ladder
                <Badge variant={ladderState.hiveMindCoherence > 0.7 ? "default" : "secondary"}>
                  {ladderState.fallbackInProgress ? 'FAILOVER' : 'OPERATIONAL'}
                </Badge>
              </CardTitle>
              <CardDescription>
                Hive-mind system interconnection network
              </CardDescription>
            </div>
            <div className="text-right">
              <div className="text-xs text-muted-foreground mb-1">Hive Mind Coherence</div>
              <div className="text-2xl font-bold text-primary">
                {(ladderState.hiveMindCoherence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Active Chain */}
          <div className="bg-black/40 p-4 rounded-lg border border-primary/30">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold">Active System Chain</h3>
              <Badge variant="outline">{activeSystems.length} systems</Badge>
            </div>
            <div className="space-y-2">
              {ladderState.activeChain.length > 0 ? (
                ladderState.activeChain.map((systemName, i) => {
                  const status = ladderState.systems.get(systemName);
                  if (!status) return null;
                  
                  return (
                    <div key={systemName}>
                      <div className="flex items-center gap-3 p-2 bg-black/30 rounded">
                        <div className="flex items-center gap-2 flex-1">
                          <span className="text-xs text-muted-foreground">#{i + 1}</span>
                          <CheckCircle className="w-4 h-4 text-success" />
                          <span className="font-mono text-sm">{systemName}</span>
                          {systemName === ladderState.primarySystem && (
                            <Badge variant="default" className="ml-2 text-xs">PRIMARY</Badge>
                          )}
                        </div>
                        <Progress value={status.health * 100} className="w-24 h-2" />
                        <span className="text-xs text-muted-foreground w-12 text-right">
                          {(status.health * 100).toFixed(0)}%
                        </span>
                      </div>
                      {i < ladderState.activeChain.length - 1 && (
                        <div className="flex justify-center my-1">
                          <ArrowDown className="w-4 h-4 text-primary/50" />
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center text-muted-foreground text-sm py-4">
                  No active systems
                </div>
              )}
            </div>
          </div>

          {/* All Systems Status */}
          <div className="bg-black/40 p-4 rounded-lg border border-border/30">
            <h3 className="text-sm font-semibold mb-3">System Status Grid</h3>
            <div className="grid grid-cols-2 gap-3">
              {systemsArray.map(system => (
                <SystemCard key={system.name} system={system} />
              ))}
            </div>
          </div>

          {/* Fallback History */}
          {recentFallbacks.length > 0 && (
            <div className="bg-black/40 p-4 rounded-lg border border-warning/30">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-warning" />
                <h3 className="text-sm font-semibold">Recent Fallback Events</h3>
                <Badge variant="outline">{recentFallbacks.length}</Badge>
              </div>
              <ScrollArea className="h-48">
                <div className="space-y-2">
                  {recentFallbacks.map((event, i) => (
                    <div key={i} className="p-2 bg-black/30 rounded text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Clock className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <Badge variant={event.success ? "default" : "destructive"} className="text-xs">
                          {event.success ? 'SUCCESS' : 'FAILED'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono">{event.fromSystem}</span>
                        <ArrowDown className="w-3 h-3 text-warning" />
                        <span className="font-mono">{event.toSystem}</span>
                      </div>
                      <div className="text-muted-foreground mt-1">
                        Reason: {event.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* System Info */}
          <div className="bg-gradient-to-r from-primary/10 to-primary/10 p-3 rounded-lg border border-border/30">
            <div className="flex items-start gap-2">
              <Zap className="w-4 h-4 text-primary mt-0.5" />
              <div className="text-xs text-muted-foreground">
                <strong>Temporal Ladder Protocol:</strong> Each system monitors its health and can request 
                assistance from others in the chain. When a system fails or degrades, the ladder automatically 
                initiates failover to the next available system. All systems maintain awareness of the hive-mind 
                coherence level and coordinate actions through broadcast events.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SystemCard({ system }: { system: SystemStatus }) {
  const getHealthColor = (health: number) => {
    if (health > 0.8) return 'text-success border-success/50';
    if (health > 0.5) return 'text-warning border-warning/50';
    return 'text-destructive border-destructive/50';
  };

  const getHealthBg = (health: number) => {
    if (health > 0.8) return 'from-success/10 to-success/5';
    if (health > 0.5) return 'from-warning/10 to-warning/5';
    return 'from-destructive/10 to-destructive/5';
  };

  const timeSinceHeartbeat = Date.now() - system.lastHeartbeat;
  const isRecent = timeSinceHeartbeat < 3000;

  return (
    <div className={`p-3 rounded-lg border bg-gradient-to-br ${getHealthBg(system.health)} ${getHealthColor(system.health)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs truncate flex-1">{system.name}</span>
        <Badge variant={system.active ? "default" : "secondary"} className="text-xs">
          {system.active ? 'ON' : 'OFF'}
        </Badge>
      </div>
      <Progress value={system.health * 100} className="h-1.5 mb-2" />
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">
          {(system.health * 100).toFixed(0)}%
        </span>
        <div className="flex items-center gap-1">
          <Radio className={`w-3 h-3 ${isRecent ? 'text-success animate-pulse' : 'text-gray-500'}`} />
          <span className="text-muted-foreground text-xs">
            {isRecent ? 'live' : `${Math.floor(timeSinceHeartbeat / 1000)}s`}
          </span>
        </div>
      </div>
      {system.fallbackTarget && (
        <div className="mt-2 pt-2 border-t border-border/30 text-xs text-muted-foreground">
          Fallback: <span className="font-mono">{system.fallbackTarget}</span>
        </div>
      )}
    </div>
  );
}
