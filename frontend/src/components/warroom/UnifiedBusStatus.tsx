import { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { unifiedBus, type BusSnapshot, type SystemState } from '@/core/unifiedBus';
import { elephantMemory, type ElephantState } from '@/core/elephantMemory';
import { Activity, Brain, Zap, Heart, Database, Shield, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

const systemIcons: Record<string, React.ReactNode> = {
  DataIngestion: <Database className="h-4 w-4" />,
  MasterEquation: <Brain className="h-4 w-4" />,
  Lighthouse: <Zap className="h-4 w-4" />,
  RainbowBridge: <Heart className="h-4 w-4" />,
  ElephantMemory: <Shield className="h-4 w-4" />,
};

const signalColors: Record<string, string> = {
  BUY: 'bg-success/20 text-success border-success/50',
  SELL: 'bg-destructive/20 text-destructive border-destructive/50',
  NEUTRAL: 'bg-muted text-muted-foreground border-border',
};

const SignalIcon = ({ signal }: { signal: string }) => {
  if (signal === 'BUY') return <TrendingUp className="h-3 w-3" />;
  if (signal === 'SELL') return <TrendingDown className="h-3 w-3" />;
  return <Minus className="h-3 w-3" />;
};

// Animated value that pulses on change
function AnimatedValue({ value, format = 'percent' }: { value: number; format?: 'percent' | 'number' }) {
  const [isAnimating, setIsAnimating] = useState(false);
  const prevValueRef = useRef(value);
  
  useEffect(() => {
    if (Math.abs(value - prevValueRef.current) > 0.001) {
      setIsAnimating(true);
      prevValueRef.current = value;
      const timer = setTimeout(() => setIsAnimating(false), 300);
      return () => clearTimeout(timer);
    }
  }, [value]);
  
  const displayValue = format === 'percent' 
    ? `${(value * 100).toFixed(1)}%` 
    : value.toFixed(3);
  
  return (
    <span className={cn(
      "transition-all duration-300 font-mono",
      isAnimating && "text-primary scale-110"
    )}>
      {displayValue}
    </span>
  );
}

function SystemCard({ name, state }: { name: string; state: SystemState | undefined }) {
  if (!state) {
    return (
      <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-muted">
            {systemIcons[name] || <Activity className="h-4 w-4" />}
          </div>
          <span className="font-medium text-sm">{name}</span>
          <Badge variant="outline" className="ml-auto text-xs">OFFLINE</Badge>
        </div>
        <Progress value={0} className="h-1" />
      </div>
    );
  }

  return (
    <div className={`p-3 rounded-lg border ${state.ready ? 'bg-card/50 border-primary/20' : 'bg-muted/30 border-border/50'}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded ${state.ready ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
          {systemIcons[name] || <Activity className="h-4 w-4" />}
        </div>
        <span className="font-medium text-sm">{name}</span>
        <Badge variant="outline" className={`ml-auto text-xs ${signalColors[state.signal]}`}>
          <SignalIcon signal={state.signal} />
          <span className="ml-1">{state.signal}</span>
        </Badge>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Coherence</span>
          <AnimatedValue value={state.coherence} format="percent" />
        </div>
        <Progress value={state.coherence * 100} className="h-1 transition-all duration-300" />
      </div>
      
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>Confidence</span>
        <AnimatedValue value={state.confidence} format="percent" />
      </div>
    </div>
  );
}

function ElephantMemoryCard({ state }: { state: ElephantState }) {
  return (
    <div className="p-3 rounded-lg bg-card/50 border border-primary/20">
      <div className="flex items-center gap-2 mb-3">
        <div className="p-1.5 rounded bg-primary/20 text-primary">
          <Shield className="h-4 w-4" />
        </div>
        <span className="font-medium text-sm">Elephant Memory</span>
        <Badge variant="outline" className="ml-auto text-xs">
          {state.totalTrades} trades
        </Badge>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-muted-foreground">Win Rate</span>
          <p className="font-mono text-success">{(state.overallWinRate * 100).toFixed(1)}%</p>
        </div>
        <div>
          <span className="text-muted-foreground">Total P&L</span>
          <p className={`font-mono ${state.totalProfit >= 0 ? 'text-success' : 'text-destructive'}`}>
            ${state.totalProfit.toFixed(2)}
          </p>
        </div>
        <div>
          <span className="text-muted-foreground">Blacklisted</span>
          <p className="font-mono text-destructive">{state.blacklistedSymbols.length}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Cooldown</span>
          <p className="font-mono text-warning">{state.cooldownSymbols.length}</p>
        </div>
      </div>
    </div>
  );
}

export function UnifiedBusStatus() {
  const [snapshot, setSnapshot] = useState<BusSnapshot | null>(null);
  const [elephantState, setElephantState] = useState<ElephantState>(elephantMemory.getState());
  
  useEffect(() => {
    // Initial snapshot
    setSnapshot(unifiedBus.snapshot());
    
    // Subscribe to updates
    const unsubscribe = unifiedBus.subscribe((newSnapshot) => {
      setSnapshot(newSnapshot);
      setElephantState(elephantMemory.getState());
    });
    
    // Poll for updates if no subscription fires
    const interval = setInterval(() => {
      setSnapshot(unifiedBus.snapshot());
      setElephantState(elephantMemory.getState());
    }, 1000);
    
    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, []);
  
  const requiredSystems = ['DataIngestion', 'Lighthouse', 'MasterEquation', 'RainbowBridge'];
  
  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-primary animate-pulse" />
          Unified Bus Status
          <span className="ml-2 flex items-center gap-1 text-xs text-success">
            <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
            LIVE
          </span>
          {snapshot && (
            <Badge 
              variant="outline" 
              className={`ml-auto ${signalColors[snapshot.consensusSignal]}`}
            >
              <SignalIcon signal={snapshot.consensusSignal} />
              <span className="ml-1">{snapshot.consensusSignal}</span>
              <span className="ml-2 opacity-70">
                {(snapshot.consensusConfidence * 100).toFixed(0)}%
              </span>
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Consensus Bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Systems Ready</span>
            <span>{snapshot?.systemsReady ?? 0} / {snapshot?.totalSystems ?? 0}</span>
          </div>
          <Progress 
            value={snapshot ? (snapshot.systemsReady / Math.max(snapshot.totalSystems, 1)) * 100 : 0} 
            className="h-2" 
          />
        </div>
        
        {/* System Cards */}
        <div className="grid grid-cols-2 gap-2">
          {requiredSystems.map(name => (
            <SystemCard 
              key={name} 
              name={name} 
              state={snapshot?.states[name]} 
            />
          ))}
        </div>
        
        {/* Elephant Memory */}
        <ElephantMemoryCard state={elephantState} />
      </CardContent>
    </Card>
  );
}
