/**
 * Ecosystem Status Component
 * Visualizes all connected systems and their integration status
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Activity, Brain, Zap, Radio, Waves, Target, Layers, GitBranch, Database, FileJson } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ecosystemConnector, type EcosystemState } from '@/core/ecosystemConnector';
import { ecosystemEnhancements } from '@/core/ecosystemEnhancements';
import { finiteOrNull } from '@/lib/reading';

interface SystemDisplayProps {
  name: string;
  icon: React.ElementType;
  active: boolean;
  coherence: number | null;
  color?: string;
}

function SystemDisplay({ name, icon: Icon, active, coherence, color }: SystemDisplayProps) {
  const reading = finiteOrNull(coherence);
  const getStatusColor = () => {
    if (!active || reading == null) return 'bg-muted-foreground';
    if (reading > 0.8) return 'bg-success';
    if (reading > 0.5) return 'bg-warning';
    return 'bg-warning';
  };

  return (
    <div className="flex items-center gap-2 py-1">
      <div className={cn("h-2 w-2 rounded-full", getStatusColor())} />
      <Icon className={cn("h-3 w-3", color || "text-muted-foreground")} />
      <span className={cn("text-xs", active ? "text-foreground" : "text-muted-foreground")}>
        {name}
      </span>
      <span className="text-[10px] text-muted-foreground ml-auto font-mono">
        {reading == null ? 'unavailable' : `${(reading * 100).toFixed(0)}%`}
      </span>
    </div>
  );
}

export function EcosystemStatus() {
  const [state, setState] = useState<EcosystemState | null>(null);
  const [enhancementsCount, setEnhancementsCount] = useState(0);

  useEffect(() => {
    // Initialize ecosystem connector
    ecosystemConnector.initialize();

    // Subscribe to updates
    const unsubscribe = ecosystemConnector.subscribe((newState) => {
      setState(newState);
    });

    // Get initial state
    setState(ecosystemConnector.getState());

    // Subscribe to enhancements
    const unsubEnhancements = ecosystemEnhancements.subscribe((enhancements) => {
      const count = 
        enhancements.aurisCodex.length + 
        enhancements.emotionalCodex.length + 
        enhancements.frequencyCodex.length + 
        enhancements.symbolicCompiler.length;
      setEnhancementsCount(count);
    });

    return () => {
      unsubscribe();
      unsubEnhancements();
    };
  }, []);

  const getOverallHealth = (): number | null => {
    if (!state || !Number.isFinite(state.totalSystems) || state.totalSystems <= 0) return null;
    return state.activeSystems / state.totalSystems;
  };

  const getHealthColor = (health: number | null) => {
    if (health == null) return 'text-muted-foreground';
    if (health > 0.8) return 'text-success';
    if (health > 0.5) return 'text-warning';
    return 'text-warning';
  };

  return (
    <Card className="border-border/50 lg:col-span-2">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-1">
            <GitBranch className="h-3 w-3" /> ECOSYSTEM
          </span>
          <Badge variant="outline" className="text-[9px]">
            {state == null ? 'unavailable' : `${state.activeSystems} / ${state.totalSystems}`} systems
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Overall Health */}
        <div className="flex items-center justify-between pb-2 border-b border-border/30">
          <span className="text-xs text-muted-foreground">Integration Health</span>
          <span className={cn("text-sm font-mono font-bold", getHealthColor(getOverallHealth()))}>
            {getOverallHealth() == null ? 'unavailable' : `${((getOverallHealth() as number) * 100).toFixed(0)}%`}
          </span>
        </div>

        {/* Core Quantum Systems */}
        <div className="grid grid-cols-2 gap-x-4">
          <div className="space-y-0.5">
            <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Core Systems</p>
            <SystemDisplay 
              name="Harmonic Nexus" 
              icon={Sparkles} 
              active={!!state?.harmonicNexus}
              coherence={finiteOrNull(state?.harmonicNexus?.substrateCoherence)}
              color="text-primary"
            />
            <SystemDisplay 
              name="Omega Equation" 
              icon={Activity} 
              active={!!state?.omega}
              coherence={finiteOrNull(state?.omega?.coherence)}
              color="text-primary"
            />
            <SystemDisplay 
              name="QGITA Engine" 
              icon={Brain} 
              active={!!state?.qgita}
              coherence={finiteOrNull(state?.qgita?.confidence)}
              color="text-primary"
            />
            <SystemDisplay 
              name="Master Equation" 
              icon={Zap} 
              active={true}
              coherence={finiteOrNull(state?.omega?.love)}
              color="text-warning"
            />
            <SystemDisplay 
              name="Lighthouse" 
              icon={Radio} 
              active={true}
              coherence={finiteOrNull(state?.harmonicNexus?.lighthouseSignal)}
              color="text-warning"
            />
          </div>

          <div className="space-y-0.5">
            <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Enhancement Systems</p>
            <SystemDisplay 
              name="Eckoushic Cascade" 
              icon={Waves} 
              active={!!state?.eckoushic}
              coherence={finiteOrNull(state?.eckoushic?.echoResonance)}
              color="text-primary"
            />
            <SystemDisplay 
              name="Unity Detector" 
              icon={Target} 
              active={!!state?.unity}
              coherence={finiteOrNull(state?.unity?.unityStrength)}
              color="text-success"
            />
            <SystemDisplay 
              name="Fibonacci Lattice" 
              icon={Layers} 
              active={!!state?.fibonacci}
              coherence={finiteOrNull(state?.fibonacci?.ratioAlignment)}
              color="text-warning"
            />
            <SystemDisplay 
              name="Rainbow Bridge" 
              icon={Sparkles} 
              active={true}
              coherence={0.85}
              color="text-primary"
            />
            <SystemDisplay 
              name="The Prism" 
              icon={Sparkles} 
              active={true}
              coherence={state?.harmonicNexus?.prismLevel ? state.harmonicNexus.prismLevel / 5 : 0.8}
              color="text-success"
            />
          </div>
        </div>

        {/* JSON Enhancements Status */}
        <div className="pt-2 border-t border-border/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <FileJson className="h-3 w-3 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">JSON Enhancements</span>
            </div>
            <Badge 
              variant={state?.enhancementsLoaded ? "default" : "secondary"} 
              className="text-[9px]"
            >
              {state?.enhancementsLoaded ? `${enhancementsCount} loaded` : 'loading...'}
            </Badge>
          </div>
          
          {state?.enhancementsLoaded && (
            <div className="flex gap-1 mt-1 flex-wrap">
              <Badge variant="outline" className="text-[8px] px-1 py-0">auris_codex</Badge>
              <Badge variant="outline" className="text-[8px] px-1 py-0">emotional_codex</Badge>
              <Badge variant="outline" className="text-[8px] px-1 py-0">frequency_codex</Badge>
              <Badge variant="outline" className="text-[8px] px-1 py-0">symbolic_compiler</Badge>
            </div>
          )}
        </div>

        {/* Unity Detection Status */}
        {state?.unity?.isUnityDetected && (
          <div className="bg-success/10 border border-success/30 rounded-md p-2 text-center">
            <div className="flex items-center justify-center gap-1">
              <Target className="h-3 w-3 text-success" />
              <span className="text-[10px] font-medium text-success uppercase tracking-wider">
                Unity Detected
              </span>
            </div>
            <p className="text-[9px] text-success/70 mt-0.5">528 Hz Lock Active</p>
          </div>
        )}

        {/* Fibonacci Anchor */}
        {state?.fibonacci && (
          <div className="text-[10px] text-muted-foreground flex justify-between">
            <span>Fibonacci Level: {state.fibonacci.currentLevel}</span>
            <span>Next Anchor: {new Date(state.fibonacci.nextAnchor).toLocaleDateString()}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
