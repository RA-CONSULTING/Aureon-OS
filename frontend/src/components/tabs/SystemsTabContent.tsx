/**
 * Systems Tab Content - Displays all system statuses
 * 
 * This component is a PURE VIEW that reads from global state.
 * All systems run continuously in GlobalSystemsManager regardless of which tab is active.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Brain, Activity, Radio, Sparkles, Database, Router, Wifi, Clock, CheckCircle, XCircle } from 'lucide-react';
import type { GlobalState } from '@/core/globalSystemsManager';
import { temporalLadder } from '@/core/temporalLadder';
import { unifiedBus } from '@/core/unifiedBus';
import { useEffect, useState } from 'react';

interface SystemsTabContentProps {
  globalState: GlobalState;
}

interface SystemHealth {
  name: string;
  registered: boolean;
  lastHeartbeat: number | null;
  coherence: number;
  status: 'online' | 'stale' | 'offline';
}

export function SystemsTabContent({ globalState }: SystemsTabContentProps) {
  const { systemStatus, busSnapshot, ecosystemHealth } = globalState;
  const [systemsHealth, setSystemsHealth] = useState<SystemHealth[]>([]);

  // Poll Temporal Ladder for registered systems
  useEffect(() => {
    const updateSystemsHealth = () => {
      const ladderState = temporalLadder.getState();
      const busStates = unifiedBus.snapshot()?.states || {};
      
      const health: SystemHealth[] = [];
      const now = Date.now();
      
      // Get all registered systems from Temporal Ladder
      Object.entries(ladderState.systems || {}).forEach(([name, system]: [string, any]) => {
        const busState = busStates[name];
        const lastHeartbeat = system.lastHeartbeat || null;
        const timeSince = lastHeartbeat ? now - lastHeartbeat : Infinity;
        
        health.push({
          name,
          registered: true,
          lastHeartbeat,
          coherence: busState?.coherence || 0,
          status: timeSince < 5000 ? 'online' : timeSince < 15000 ? 'stale' : 'offline'
        });
      });
      
      // Sort by status (online first) then name
      health.sort((a, b) => {
        const statusOrder = { online: 0, stale: 1, offline: 2 };
        if (statusOrder[a.status] !== statusOrder[b.status]) {
          return statusOrder[a.status] - statusOrder[b.status];
        }
        return a.name.localeCompare(b.name);
      });
      
      setSystemsHealth(health);
    };

    updateSystemsHealth();
    const interval = setInterval(updateSystemsHealth, 2000);
    return () => clearInterval(interval);
  }, []);

  const onlineCount = systemsHealth.filter(s => s.status === 'online').length;
  const staleCount = systemsHealth.filter(s => s.status === 'stale').length;
  const offlineCount = systemsHealth.filter(s => s.status === 'offline').length;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return <CheckCircle className="h-3 w-3 text-success" />;
      case 'stale': return <Clock className="h-3 w-3 text-warning" />;
      default: return <XCircle className="h-3 w-3 text-destructive" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online': return <Badge variant="default" className="text-[9px]">ONLINE</Badge>;
      case 'stale': return <Badge variant="secondary" className="text-[9px]">STALE</Badge>;
      default: return <Badge variant="destructive" className="text-[9px]">OFFLINE</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Total Systems</span>
              <Badge variant="outline">{systemsHealth.length}</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-border/50 border-success/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Online</span>
              <Badge variant="default" className="bg-success">{onlineCount}</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-border/50 border-warning/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Stale</span>
              <Badge variant="secondary">{staleCount}</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-border/50 border-destructive/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Offline</span>
              <Badge variant="destructive">{offlineCount}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Core Systems Status */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" />
            Core Trading Systems
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { name: 'Master Equation', active: systemStatus.masterEquation, icon: Activity },
              { name: 'Lighthouse', active: systemStatus.lighthouse, icon: Radio },
              { name: 'Rainbow Bridge', active: systemStatus.rainbowBridge, icon: Sparkles },
              { name: 'Elephant Memory', active: systemStatus.elephantMemory, icon: Database },
              { name: 'Order Router', active: systemStatus.orderRouter, icon: Router },
            ].map((sys) => (
              <div 
                key={sys.name}
                className={cn(
                  "flex flex-col items-center p-3 rounded-lg border transition-all",
                  sys.active ? "border-success/50 bg-success/5" : "border-border/30"
                )}
              >
                <sys.icon className={cn("h-6 w-6 mb-1", sys.active ? "text-success" : "text-muted-foreground")} />
                <span className="text-xs text-center">{sys.name}</span>
                <div className={cn(
                  "h-1.5 w-1.5 rounded-full mt-1",
                  sys.active ? "bg-success animate-pulse" : "bg-muted-foreground"
                )} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Unified Bus States */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wifi className="h-4 w-4 text-primary" />
            Unified Bus States (10-9-1 Weighting)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-48">
            <div className="space-y-2">
              {Object.entries(busSnapshot?.states || {}).map(([name, state]: [string, any]) => (
                <div 
                  key={name}
                  className="flex items-center justify-between p-2 rounded border border-border/30 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "h-2 w-2 rounded-full",
                      state.ready ? "bg-success" : "bg-muted-foreground"
                    )} />
                    <span className="font-mono">{name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">Γ: {state.coherence?.toFixed(3) || '0.000'}</span>
                    <Badge variant={state.signal === 'BUY' ? 'default' : state.signal === 'SELL' ? 'destructive' : 'secondary'} className="text-[9px]">
                      {state.signal || 'NEUTRAL'}
                    </Badge>
                  </div>
                </div>
              ))}
              {Object.keys(busSnapshot?.states || {}).length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  No systems publishing to bus yet...
                </p>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Temporal Ladder Registry */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Temporal Ladder Registry
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64">
            <div className="space-y-1">
              {systemsHealth.map((system) => (
                <div 
                  key={system.name}
                  className="flex items-center justify-between p-2 rounded border border-border/30 text-xs"
                >
                  <div className="flex items-center gap-2">
                    {getStatusIcon(system.status)}
                    <span className="font-mono">{system.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">
                      {system.lastHeartbeat 
                        ? `${((Date.now() - system.lastHeartbeat) / 1000).toFixed(0)}s ago`
                        : 'Never'
                      }
                    </span>
                    {getStatusBadge(system.status)}
                  </div>
                </div>
              ))}
              {systemsHealth.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  No systems registered with Temporal Ladder...
                </p>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
