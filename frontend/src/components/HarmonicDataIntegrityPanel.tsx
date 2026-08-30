import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Shield, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { useEcosystemData } from '@/hooks/useEcosystemData';
import { cn } from '@/lib/utils';

interface IntegrityMetric {
  name: string;
  score: number;
  weight: number;
  description: string;
  hasData: boolean;
}

type DataStatus = 'LIVE' | 'STALE' | 'NO_DATA';

export function HarmonicDataIntegrityPanel() {
  const { metrics, isInitialized } = useEcosystemData();
  const [overallScore, setOverallScore] = useState(0);
  const [status, setStatus] = useState<'valid' | 'suspect' | 'invalid'>('invalid');
  const [integrityMetrics, setIntegrityMetrics] = useState<IntegrityMetric[]>([]);
  const [history, setHistory] = useState<number[]>([]);
  const [dataStatus, setDataStatus] = useState<DataStatus>('NO_DATA');
  const [sourcesWithData, setSourcesWithData] = useState(0);

  useEffect(() => {
    if (!metrics) return;

    // Check actual data presence
    const coherence = metrics.coherence ?? 0;
    const frequency = metrics.frequency ?? 0;
    const harmonicFidelity = metrics.harmonicFidelity ?? 0;
    const temporalAnchor = metrics.temporalAnchorStrength ?? 0;
    
    // Count sources with actual data
    const sources = [
      coherence > 0,
      frequency > 0,
      harmonicFidelity > 0,
      temporalAnchor > 0
    ];
    const activeSourceCount = sources.filter(Boolean).length;
    setSourcesWithData(activeSourceCount);
    
    // Determine overall data status
    if (!isInitialized) {
      setDataStatus('NO_DATA');
    } else if (activeSourceCount >= 2) {
      setDataStatus('LIVE');
    } else if (activeSourceCount === 1) {
      setDataStatus('STALE');
    } else {
      setDataStatus('NO_DATA');
    }

    // Calculate integrity metrics only if we have data
    const cymaticsMatch = coherence > 0 ? Math.min(1, coherence * 1.2) : 0;
    const prismAlignment = frequency > 0 
      ? 1 - Math.abs(528 - frequency) / 528
      : 0;
    const matrixConsensus = (harmonicFidelity > 0 && coherence > 0)
      ? 1 - Math.abs(harmonicFidelity - coherence)
      : 0;
    const temporalSync = temporalAnchor;

    const metricsArray: IntegrityMetric[] = [
      { name: 'Cymatics Pattern Match', score: cymaticsMatch, weight: 0.25, description: 'Water frequency resonance alignment', hasData: coherence > 0 },
      { name: 'Prism Alignment', score: prismAlignment, weight: 0.30, description: 'Distance to 528 Hz love frequency', hasData: frequency > 0 },
      { name: 'Matrix Consensus', score: matrixConsensus, weight: 0.25, description: 'Source agreement level', hasData: harmonicFidelity > 0 && coherence > 0 },
      { name: 'Temporal Sync', score: temporalSync, weight: 0.20, description: 'Timeline coherence quality', hasData: temporalAnchor > 0 },
    ];

    // Calculate weighted overall score (only from sources with data)
    const metricsWithData = metricsArray.filter(m => m.hasData);
    const totalWeight = metricsWithData.reduce((sum, m) => sum + m.weight, 0);
    const overall = totalWeight > 0 
      ? metricsWithData.reduce((sum, m) => sum + m.score * m.weight, 0) / totalWeight
      : 0;
    
    // Determine status based on data presence AND quality
    let newStatus: 'valid' | 'suspect' | 'invalid' = 'invalid';
    if (activeSourceCount === 0) {
      newStatus = 'invalid';
    } else if (activeSourceCount < 3 || overall < 0.4) {
      newStatus = 'suspect';
    } else if (overall >= 0.7) {
      newStatus = 'valid';
    } else {
      newStatus = 'suspect';
    }

    setIntegrityMetrics(metricsArray);
    setOverallScore(overall);
    setStatus(newStatus);
    
    // Update history (keep last 20 values)
    if (activeSourceCount > 0) {
      setHistory(prev => [...prev.slice(-19), overall]);
    }
  }, [metrics, isInitialized]);

  const getDataStatusBadge = () => {
    switch (dataStatus) {
      case 'LIVE':
        return <Badge className="bg-success/20 text-success border-success/30 text-[10px]">LIVE ({sourcesWithData}/4)</Badge>;
      case 'STALE':
        return <Badge className="bg-warning/20 text-warning border-warning/30 text-[10px]">PARTIAL ({sourcesWithData}/4)</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30 text-[10px]">NO DATA</Badge>;
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'valid':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'suspect':
        return <AlertTriangle className="h-4 w-4 text-warning" />;
      default:
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'valid':
        return <Badge className="bg-success/20 text-success border-success/30">🟢 VALID</Badge>;
      case 'suspect':
        return <Badge className="bg-warning/20 text-warning border-warning/30">🟡 SUSPECT</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30">🔴 INVALID</Badge>;
    }
  };

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-2">
            <Shield className="h-3 w-3" />
            HARMONIC DATA INTEGRITY
            {getDataStatusBadge()}
          </CardTitle>
          {getStatusBadge()}
        </div>
        {dataStatus === 'NO_DATA' && (
          <div className="flex items-center gap-1 text-[10px] text-warning mt-1">
            <AlertTriangle className="h-3 w-3" />
            <span>No integrity sources available</span>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Score */}
        <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/30 border border-border/50">
          {getStatusIcon()}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground">Overall Integrity</span>
              <span className={cn(
                "text-xl font-mono font-bold",
                status === 'valid' && "text-success",
                status === 'suspect' && "text-warning",
                status === 'invalid' && "text-destructive"
              )}>
                {(overallScore * 100).toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={overallScore * 100} 
              className={cn(
                "h-2",
                status === 'valid' && "[&>div]:bg-success",
                status === 'suspect' && "[&>div]:bg-warning",
                status === 'invalid' && "[&>div]:bg-destructive"
              )}
            />
          </div>
        </div>

        {/* Metric Breakdown */}
        <div className="space-y-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Breakdown</p>
          {integrityMetrics.map((metric) => (
            <div key={metric.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs">{metric.name}</span>
                  <span className="text-[10px] text-muted-foreground ml-1">({(metric.weight * 100).toFixed(0)}%)</span>
                </div>
                <span className={cn(
                  "text-xs font-mono",
                  metric.score > 0.7 && "text-success",
                  metric.score <= 0.7 && metric.score > 0.4 && "text-warning",
                  metric.score <= 0.4 && "text-destructive"
                )}>
                  {(metric.score * 100).toFixed(0)}%
                </span>
              </div>
              <Progress 
                value={metric.score * 100} 
                className={cn(
                  "h-1",
                  metric.score > 0.7 && "[&>div]:bg-success/60",
                  metric.score <= 0.7 && metric.score > 0.4 && "[&>div]:bg-warning/60",
                  metric.score <= 0.4 && "[&>div]:bg-destructive/60"
                )}
              />
            </div>
          ))}
        </div>

        {/* Mini History Chart */}
        <div className="space-y-1">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">History (last 20 ticks)</p>
          <div className="flex items-end gap-0.5 h-8">
            {history.map((value, i) => (
              <div
                key={i}
                className={cn(
                  "flex-1 rounded-t transition-all",
                  value > 0.7 && "bg-success/60",
                  value <= 0.7 && value > 0.4 && "bg-warning/60",
                  value <= 0.4 && "bg-destructive/60"
                )}
                style={{ height: `${value * 100}%` }}
              />
            ))}
            {history.length === 0 && (
              <div className="w-full h-full flex items-center justify-center">
                <span className="text-[10px] text-muted-foreground">Collecting data...</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
