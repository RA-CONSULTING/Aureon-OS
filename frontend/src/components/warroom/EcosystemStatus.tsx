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

interface SystemDisplayProps {
  name: string;
  icon: React.ElementType;
  active: boolean;
  coherence: number;
  color?: string;
}

function SystemDisplay({ name, icon: Icon, active, coherence, color }: SystemDisplayProps) {
  const getStatusColor = () => {
    if (!active) return 'bg-muted-foreground';
    if (coherence > 0.8) return 'bg-success';
    if (coherence > 0.5) return 'bg-warning';
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
        {(coherence * 100).toFixed(0)}%
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

  const getOverallHealth = () => {
    if (!state) return 0;
    return state.activeSystems / state.totalSystems;
  };

  const getHealthColor = (health: number) => {
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
            {state?.activeSystems || 0}/{state?.totalSystems || 0} systems
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Overall Health */}
        <div className="flex items-center justify-between pb-2 border-b border-border/30">
          <span className="text-xs text-muted-foreground">Integration Health</span>
          <span className={cn("text-sm font-mono font-bold", getHealthColor(getOverallHealth()))}>
            {(getOverallHealth() * 100).toFixed(0)}%
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
              coherence={state?.harmonicNexus?.substrateCoherence || 0}
              color="text-primary"
            />
            <SystemDisplay 
              name="Omega Equation" 
              icon={Activity} 
              active={!!state?.omega}
              coherence={state?.omega?.coherence || 0}
              color="text-primary"
            />
            <SystemDisplay 
              name="QGITA Engine" 
              icon={Brain} 
              active={!!state?.qgita}
              coherence={state?.qgita?.confidence || 0}
              color="text-primary"
            />
            <SystemDisplay 
              name="Master Equation" 
              icon={Zap} 
              active={true}
              coherence={state?.omega?.love || 0}
              color="text-warning"
            />
            <SystemDisplay 
              name="Lighthouse" 
              icon={Radio} 
              active={true}
              coherence={state?.harmonicNexus?.lighthouseSignal || 0.7}
              color="text-warning"
            />
          </div>

          <div className="space-y-0.5">
            <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Enhancement Systems</p>
            <SystemDisplay 
              name="Eckoushic Cascade" 
              icon={Waves} 
              active={!!state?.eckoushic}
              coherence={state?.eckoushic?.echoResonance || 0}
              color="text-primary"
            />
            <SystemDisplay 
              name="Unity Detector" 
              icon={Target} 
              active={!!state?.unity}
              coherence={state?.unity?.unityStrength || 0}
              color="text-success"
            />
            <SystemDisplay 
              name="Fibonacci Lattice" 
              icon={Layers} 
              active={!!state?.fibonacci}
              coherence={state?.fibonacci?.ratioAlignment || 0}
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
