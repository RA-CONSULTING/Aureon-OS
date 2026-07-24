/**
 * Full Ecosystem Status Component
 * Displays real-time health of ALL 25+ systems
 */

import React from 'react';
import { useEcosystemData } from '@/hooks/useEcosystemData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Activity, 
  Cpu, 
  Zap, 
  Radio, 
  Globe, 
  Shield, 
  Hexagon,
  Waves,
  Target,
  Network,
  Eye,
  Heart
} from 'lucide-react';

const SYSTEM_ICONS: Record<string, React.ReactNode> = {
  'harmonic-nexus': <Hexagon className="w-4 h-4" />,
  'master-equation': <Cpu className="w-4 h-4" />,
  'earth-integration': <Globe className="w-4 h-4" />,
  'nexus-feed': <Radio className="w-4 h-4" />,
  'quantum-quackers': <Zap className="w-4 h-4" />,
  'akashic-mapper': <Eye className="w-4 h-4" />,
  'zero-point': <Target className="w-4 h-4" />,
  'dimensional-dialler': <Waves className="w-4 h-4" />,
  'IntegralAQAL': <Network className="w-4 h-4" />,
  'StargateLattice': <Globe className="w-4 h-4" />,
  'FTCPDetector': <Activity className="w-4 h-4" />,
  'QGITASignal': <Radio className="w-4 h-4" />,
  'HNCImperial': <Shield className="w-4 h-4" />,
  'SmartRouter': <Network className="w-4 h-4" />,
  'TemporalAnchor': <Target className="w-4 h-4" />,
  'HiveController': <Hexagon className="w-4 h-4" />,
  'DecisionFusion': <Cpu className="w-4 h-4" />,
  'ElephantMemory': <Eye className="w-4 h-4" />,
  'Prism': <Heart className="w-4 h-4" />,
  'UnityDetector': <Zap className="w-4 h-4" />,
  '6DHarmonic': <Waves className="w-4 h-4" />,
  'ProbabilityMatrix': <Activity className="w-4 h-4" />,
};

export function FullEcosystemStatus() {
  const { 
    metrics, 
    ecosystemState, 
    systemHealth, 
    isInitialized 
  } = useEcosystemData();

  if (!isInitialized) {
    return (
      <Card className="bg-background/50 backdrop-blur border-border/50">
        <CardContent className="p-6 text-center">
          <div className="animate-pulse flex flex-col items-center gap-2">
            <Activity className="w-8 h-8 text-primary animate-spin" />
            <p className="text-muted-foreground">Initializing Ecosystem...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const onlinePercentage = metrics.totalSystems > 0 
    ? (metrics.systemsOnline / metrics.totalSystems) * 100 
    : 0;

  return (
    <Card className="bg-background/50 backdrop-blur border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Network className="w-5 h-5 text-primary" />
            Full Ecosystem Status
          </CardTitle>
          <Badge 
            variant={onlinePercentage > 90 ? 'default' : onlinePercentage > 50 ? 'secondary' : 'destructive'}
          >
            {metrics.systemsOnline}/{metrics.totalSystems} Online
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Overview Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard 
            label="Hive Mind" 
            value={`${(metrics.hiveMindCoherence * 100).toFixed(0)}%`}
            color={metrics.hiveMindCoherence > 0.8 ? 'text-success' : 'text-warning'}
          />
          <MetricCard 
            label="Consensus" 
            value={metrics.consensusSignal}
            color={
              metrics.consensusSignal === 'BUY' ? 'text-success' :
              metrics.consensusSignal === 'SELL' ? 'text-destructive' :
              'text-muted-foreground'
            }
          />
          <MetricCard 
            label="Confidence" 
            value={`${(metrics.consensusConfidence * 100).toFixed(0)}%`}
            color={metrics.consensusConfidence > 0.7 ? 'text-success' : 'text-warning'}
          />
          <MetricCard 
            label="JSON Loaded" 
            value={ecosystemState?.jsonEnhancementsLoaded ? '✓' : '✗'}
            color={ecosystemState?.jsonEnhancementsLoaded ? 'text-success' : 'text-destructive'}
          />
        </div>

        {/* Health Progress */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">System Health</span>
            <span className="font-mono">{onlinePercentage.toFixed(0)}%</span>
          </div>
          <Progress value={onlinePercentage} className="h-2" />
        </div>

        {/* System Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {systemHealth.map((system) => (
            <SystemBadge 
              key={system.name} 
              system={system} 
              icon={SYSTEM_ICONS[system.name]}
            />
          ))}
        </div>

        {/* Advanced Metrics */}
        <div className="border-t border-border/50 pt-3 space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Advanced Systems</h4>
          
          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* QGITA */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">QGITA Signal</span>
              <Badge variant="outline" className="text-xs">
                Tier {metrics.qgitaTier} | {metrics.qgitaConfidence.toFixed(0)}%
              </Badge>
            </div>
            
            {/* 6D Harmonic */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">6D Wave</span>
              <span className={metrics.harmonicLock ? 'text-success' : 'text-muted-foreground'}>
                {metrics.waveState} {metrics.harmonicLock && ''}
              </span>
            </div>
            
            {/* Stargate */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Stargate Grid</span>
              <span>{metrics.activeNodes} nodes | {(metrics.stargateNetworkStrength * 100).toFixed(0)}%</span>
            </div>
            
            {/* AQAL */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">AQAL Level</span>
              <span>{(metrics.evolutionaryLevel * 100).toFixed(0)}% | {metrics.dominantQuadrant}</span>
            </div>
            
            {/* HNC */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">HNC Fidelity</span>
              <span className={metrics.rainbowBridgeOpen ? 'text-success' : 'text-muted-foreground'}>
                {metrics.harmonicFidelity.toFixed(0)}% {metrics.rainbowBridgeOpen && ''}
              </span>
            </div>
            
            {/* Temporal */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Temporal Anchor</span>
              <span className={metrics.temporalAnchorStrength > 0.7 ? 'text-success' : 'text-warning'}>
                {(metrics.temporalAnchorStrength * 100).toFixed(0)}% {metrics.surgeWindowActive && ''}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-muted/30 rounded-lg p-2 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`font-mono font-bold ${color}`}>{value}</div>
    </div>
  );
}

function SystemBadge({ 
  system, 
  icon 
}: { 
  system: { name: string; online: boolean; coherence: number; publishedToBus: boolean };
  icon?: React.ReactNode;
}) {
  const statusColor = system.online 
    ? system.coherence > 0.8 
      ? 'bg-success/20 text-success border-success/30' 
      : 'bg-warning/20 text-warning border-warning/30'
    : 'bg-destructive/20 text-destructive border-destructive/30';

  return (
    <div className={`flex items-center gap-1.5 px-2 py-1 rounded border text-xs ${statusColor}`}>
      {icon || <Activity className="w-3 h-3" />}
      <span className="truncate">{formatSystemName(system.name)}</span>
      {system.publishedToBus && <span className="text-[10px]"></span>}
    </div>
  );
}

function formatSystemName(name: string): string {
  return name
    .replace(/-/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .slice(0, 2)
    .join(' ');
}

export default FullEcosystemStatus;
