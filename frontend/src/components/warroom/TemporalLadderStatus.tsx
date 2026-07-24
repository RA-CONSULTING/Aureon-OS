import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Network, Activity, Zap, AlertTriangle } from 'lucide-react';
import { temporalLadder, type TemporalLadderState, type FallbackEvent } from '@/core/temporalLadder';

export function TemporalLadderStatus() {
  const [state, setState] = useState<TemporalLadderState | null>(null);
  const [recentEvents, setRecentEvents] = useState<FallbackEvent[]>([]);

  useEffect(() => {
    // Get initial state
    setState(temporalLadder.getState());
    setRecentEvents(temporalLadder.getFallbackHistory().slice(-3));

    // Subscribe to updates
    const unsubscribe = temporalLadder.subscribe((newState) => {
      setState(newState);
      setRecentEvents(temporalLadder.getFallbackHistory().slice(-3));
    });

    return unsubscribe;
  }, []);

  if (!state) {
    return (
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
            <Network className="h-3 w-3" /> TEMPORAL LADDER
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Initializing hive mind...</p>
        </CardContent>
      </Card>
    );
  }

  const activeSystems = Array.from(state.systems.values()).filter(s => s.active);
  const healthySystems = activeSystems.filter(s => s.health > 0.7);

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
          <Network className="h-3 w-3" /> TEMPORAL LADDER
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Hive Mind Coherence */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Hive Mind Coherence</span>
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full rounded-full transition-all",
                  state.hiveMindCoherence > 0.8 ? "bg-success" :
                  state.hiveMindCoherence > 0.5 ? "bg-warning" : "bg-destructive"
                )}
                style={{ width: `${state.hiveMindCoherence * 100}%` }}
              />
            </div>
            <span className="text-xs font-mono">{(state.hiveMindCoherence * 100).toFixed(0)}%</span>
          </div>
        </div>

        {/* Active Systems */}
        <div className="space-y-1">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Active Systems</p>
          <div className="grid grid-cols-2 gap-1">
            {Array.from(state.systems.entries()).slice(0, 6).map(([name, status]) => (
              <div key={name} className="flex items-center gap-1.5 text-xs">
                <div className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  status.active && status.health > 0.7 ? "bg-success" :
                  status.active && status.health > 0.3 ? "bg-warning" :
                  status.active ? "bg-destructive" : "bg-muted-foreground/30"
                )} />
                <span className={cn(
                  "truncate max-w-[80px]",
                  status.active ? "text-foreground" : "text-muted-foreground"
                )}>
                  {name.replace('-', ' ').split(' ').map(w => w.charAt(0).toUpperCase()).join('')}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Status Summary */}
        <div className="flex items-center justify-between pt-2 border-t border-border/30">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs">{activeSystems.length} active</span>
          </div>
          <div className="flex items-center gap-1">
            <Zap className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs">{healthySystems.length} healthy</span>
          </div>
          <Badge variant={state.fallbackInProgress ? "destructive" : "secondary"} className="text-[9px]">
            {state.fallbackInProgress ? 'FAILOVER' : 'STABLE'}
          </Badge>
        </div>

        {/* Recent Fallback Events */}
        {recentEvents.length > 0 && (
          <div className="space-y-1 pt-2 border-t border-border/30">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <AlertTriangle className="h-2.5 w-2.5" /> Recent Events
            </p>
            {recentEvents.map((event, i) => (
              <div key={i} className="text-[10px] text-muted-foreground">
                {event.fromSystem} → {event.toSystem}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
