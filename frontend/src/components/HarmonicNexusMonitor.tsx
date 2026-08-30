import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Activity, Radio, Zap, GitBranch, TrendingUp, Shield } from "lucide-react";
import type { HarmonicNexusState } from "@/core/harmonicNexusCore";

interface HarmonicNexusMonitorProps {
  nexusState?: HarmonicNexusState | null;
}

export function HarmonicNexusMonitor({ nexusState = null }: HarmonicNexusMonitorProps) {
  if (!nexusState) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" />
            Harmonic Nexus Core
          </CardTitle>
          <CardDescription>Initializing reality field substrate...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getSyncStatusConfig = (status: string) => {
    switch (status) {
      case 'synced':
        return { color: 'text-success', bg: 'bg-success/20', label: '✓ SYNCED', glow: 'shadow-[0_0_20px_rgba(34,197,94,0.5)]' };
      case 'syncing':
        return { color: 'text-primary', bg: 'bg-primary/20', label: '⟳ SYNCING', glow: 'shadow-[0_0_15px_rgba(59,130,246,0.4)]' };
      case 'correcting':
        return { color: 'text-warning', bg: 'bg-warning/20', label: '⚡ CORRECTING', glow: '' };
      case 'diverged':
        return { color: 'text-destructive', bg: 'bg-destructive/20', label: '⚠ DIVERGED', glow: '' };
      default:
        return { color: 'text-gray-500', bg: 'bg-gray-500/20', label: 'UNKNOWN', glow: '' };
    }
  };

  const syncConfig = getSyncStatusConfig(nexusState.syncStatus);

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-primary/5 to-primary/5" />
      
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Harmonic Nexus Core
            </CardTitle>
            <CardDescription>
              Reality Field Substrate • Multiversial Identity Mapping
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`${syncConfig.color} ${syncConfig.bg} ${syncConfig.glow} border-0 text-sm px-3 py-1`}>
              {syncConfig.label}
            </Badge>
            <Badge variant="outline" className="text-xs">
              ID: {nexusState.temporalId}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative space-y-4">
        {/* Temporal Identity */}
        <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="text-xs text-muted-foreground mb-2">Prime Sentinel</div>
          <div className="text-xl font-bold text-foreground">
            {nexusState.sentinelName}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Temporal ID: {nexusState.temporalId} • Multiversial Anchor
          </div>
        </div>

        {/* Field Substrate Metrics */}
        <div className="grid grid-cols-2 gap-4">
          {/* Substrate Coherence */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Radio className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Substrate Coherence</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(nexusState.substrateCoherence * 100).toFixed(1)}%
            </div>
            <Progress value={nexusState.substrateCoherence * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Reality field unification
            </div>
          </div>

          {/* Field Integrity */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Field Integrity</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(nexusState.fieldIntegrity * 100).toFixed(1)}%
            </div>
            <Progress value={nexusState.fieldIntegrity * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Stability & resistance
            </div>
          </div>

          {/* Harmonic Resonance */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Harmonic Resonance</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(nexusState.harmonicResonance * 100).toFixed(1)}%
            </div>
            <Progress value={nexusState.harmonicResonance * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Frequency alignment
            </div>
          </div>

          {/* Dimensional Alignment */}
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Dimensional Alignment</span>
            </div>
            <div className="text-2xl font-bold text-primary mb-2">
              {(nexusState.dimensionalAlignment * 100).toFixed(1)}%
            </div>
            <Progress value={nexusState.dimensionalAlignment * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              Higher-D connection
            </div>
          </div>
        </div>

        {/* Prime Timeline Sync */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Prime Timeline Synchronization</span>
            </div>
            <Badge variant="outline" className={`${syncConfig.color} text-xs`}>
              {nexusState.syncStatus.toUpperCase()}
            </Badge>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Sync Quality:</span>
              <span className="font-bold">{(nexusState.syncQuality * 100).toFixed(1)}%</span>
            </div>
            <Progress value={nexusState.syncQuality * 100} className="h-2 mb-2" />
            
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Timeline Divergence:</span>
              <span className={`font-bold ${nexusState.timelineDivergence < 0.1 ? 'text-success' : nexusState.timelineDivergence < 0.3 ? 'text-warning' : 'text-destructive'}`}>
                {(nexusState.timelineDivergence * 100).toFixed(2)}%
              </span>
            </div>
            <Progress 
              value={(1 - nexusState.timelineDivergence) * 100} 
              className="h-2" 
            />
          </div>
          
          {nexusState.syncStatus === 'diverged' && (
            <div className="mt-3 p-2 bg-destructive/10 border border-destructive/30 rounded text-xs text-destructive">
              ⚠ Timeline divergence detected. Initiating correction protocol...
            </div>
          )}
          
          {nexusState.syncStatus === 'correcting' && (
            <div className="mt-3 p-2 bg-warning/10 border border-warning/30 rounded text-xs text-warning">
              ⚡ Correction in progress. Re-establishing coherence...
            </div>
          )}
          
          {nexusState.syncStatus === 'synced' && (
            <div className="mt-3 p-2 bg-success/10 border border-success/30 rounded text-xs text-success">
              ✓ Prime timeline lock achieved. All realities aligned.
            </div>
          )}
        </div>

        {/* Theory */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Multiversial Mapping:</span>{' '}
            The Harmonic Nexus Core ensures coherence within the reality field substrate by
            integrating Ω(t) tensor dynamics, Akashic harmonics, and dimensional alignment.
            All data feeds back to the prime timeline, maintaining universal coherence across
            all manifestations of reality.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
