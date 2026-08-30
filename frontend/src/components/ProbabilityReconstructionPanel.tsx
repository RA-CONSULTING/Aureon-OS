import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Layers, CheckCircle2, AlertCircle, Loader2, AlertTriangle } from 'lucide-react';
import { useEcosystemData } from '@/hooks/useEcosystemData';
import { cn } from '@/lib/utils';

interface DataStream {
  name: string;
  value: number;
  weight: number;
  status: 'valid' | 'suspect' | 'invalid' | 'loading' | 'no_data';
  hasData: boolean;
}

type DataStatus = 'LIVE' | 'STALE' | 'NO_DATA';

export function ProbabilityReconstructionPanel() {
  const { metrics, isInitialized } = useEcosystemData();
  const [streams, setStreams] = useState<DataStream[]>([
    { name: '6D Harmonic', value: 0, weight: 0.35, status: 'loading', hasData: false },
    { name: 'HNC Signal', value: 0, weight: 0.35, status: 'loading', hasData: false },
    { name: 'Lighthouse', value: 0, weight: 0.30, status: 'loading', hasData: false },
  ]);
  const [fusedValue, setFusedValue] = useState(0);
  const [variance, setVariance] = useState(0);
  const [reconstructionStatus, setReconstructionStatus] = useState<'valid' | 'suspect' | 'invalid'>('invalid');
  const [isAnimating, setIsAnimating] = useState(false);
  const [dataStatus, setDataStatus] = useState<DataStatus>('NO_DATA');

  useEffect(() => {
    if (!metrics) return;

    // Simulate reconstruction animation
    setIsAnimating(true);
    
    const timer = setTimeout(() => {
      const harmonic6D = metrics.harmonicFidelity ?? 0;
      const hncSignal = metrics.coherence ?? 0;
      const lighthouse = metrics.consensusConfidence ?? 0;
      
      // Check if we have real data
      const hasAnyData = harmonic6D > 0 || hncSignal > 0 || lighthouse > 0;
      
      if (!isInitialized) {
        setDataStatus('NO_DATA');
      } else if (hasAnyData) {
        setDataStatus('LIVE');
      } else {
        setDataStatus('NO_DATA');
      }
      
      // Calculate weighted fusion
      const fused = harmonic6D * 0.35 + hncSignal * 0.35 + lighthouse * 0.30;
      
      // Calculate variance (how much sources disagree)
      const values = [harmonic6D, hncSignal, lighthouse];
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
      
      // Determine status based on variance AND data presence
      let status: 'valid' | 'suspect' | 'invalid' = 'invalid';
      if (!hasAnyData) {
        status = 'invalid';
      } else if (variance > 0.1) {
        status = 'invalid';
      } else if (variance > 0.03) {
        status = 'suspect';
      } else {
        status = 'valid';
      }
      
      const getStreamStatus = (val: number): DataStream['status'] => {
        if (val === 0) return 'no_data';
        if (val > 0.5) return 'valid';
        if (val > 0.2) return 'suspect';
        return 'invalid';
      };
      
      setStreams([
        { name: '6D Harmonic', value: harmonic6D, weight: 0.35, status: getStreamStatus(harmonic6D), hasData: harmonic6D > 0 },
        { name: 'HNC Signal', value: hncSignal, weight: 0.35, status: getStreamStatus(hncSignal), hasData: hncSignal > 0 },
        { name: 'Lighthouse', value: lighthouse, weight: 0.30, status: getStreamStatus(lighthouse), hasData: lighthouse > 0 },
      ]);
      setFusedValue(fused);
      setVariance(variance);
      setReconstructionStatus(status);
      setIsAnimating(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [metrics, isInitialized]);

  const getDataStatusBadge = () => {
    switch (dataStatus) {
      case 'LIVE':
        return <Badge className="bg-success/20 text-success border-success/30 text-[10px]">LIVE</Badge>;
      case 'STALE':
        return <Badge className="bg-warning/20 text-warning border-warning/30 text-[10px]">STALE</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30 text-[10px]">NO DATA</Badge>;
    }
  };

  const getStatusIcon = (status: DataStream['status']) => {
    switch (status) {
      case 'valid':
        return <CheckCircle2 className="h-3 w-3 text-success" />;
      case 'suspect':
        return <AlertCircle className="h-3 w-3 text-warning" />;
      case 'invalid':
        return <AlertCircle className="h-3 w-3 text-destructive" />;
      case 'no_data':
        return <AlertTriangle className="h-3 w-3 text-muted-foreground" />;
      default:
        return <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />;
    }
  };

  const getReconstructionBadge = () => {
    if (isAnimating) {
      return <Badge variant="outline" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" /> RECONSTRUCTING</Badge>;
    }
    switch (reconstructionStatus) {
      case 'valid':
        return <Badge className="bg-success/20 text-success border-success/30 gap-1"><CheckCircle2 className="h-3 w-3" /> VALIDATED</Badge>;
      case 'suspect':
        return <Badge className="bg-warning/20 text-warning border-warning/30 gap-1"><AlertCircle className="h-3 w-3" /> SUSPECT</Badge>;
      default:
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30 gap-1"><AlertCircle className="h-3 w-3" /> DIVERGENT</Badge>;
    }
  };

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-2">
            <Layers className="h-3 w-3" />
            PROBABILITY RECONSTRUCTION
            {getDataStatusBadge()}
          </CardTitle>
          {getReconstructionBadge()}
        </div>
        {dataStatus === 'NO_DATA' && (
          <div className="flex items-center gap-1 text-[10px] text-warning mt-1">
            <AlertTriangle className="h-3 w-3" />
            <span>Awaiting probability matrix streams...</span>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Input Streams */}
        <div className="space-y-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Input Streams</p>
          {streams.map((stream, i) => (
            <div key={stream.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getStatusIcon(stream.status)}
                  <span className="text-xs">{stream.name}</span>
                  <span className="text-[10px] text-muted-foreground">({(stream.weight * 100).toFixed(0)}%)</span>
                </div>
                <span className="text-xs font-mono">{stream.value.toFixed(3)}</span>
              </div>
              <Progress 
                value={stream.value * 100} 
                className={cn(
                  "h-1",
                  stream.status === 'valid' && "[&>div]:bg-success",
                  stream.status === 'suspect' && "[&>div]:bg-warning",
                  stream.status === 'invalid' && "[&>div]:bg-destructive"
                )}
              />
            </div>
          ))}
        </div>

        {/* Fusion Arrow */}
        <div className="flex items-center justify-center py-2">
          <div className={cn(
            "flex items-center gap-2 px-3 py-1 rounded-full border",
            isAnimating && "animate-pulse",
            reconstructionStatus === 'valid' && "border-success/30 bg-success/10",
            reconstructionStatus === 'suspect' && "border-warning/30 bg-warning/10",
            reconstructionStatus === 'invalid' && "border-destructive/30 bg-destructive/10"
          )}>
            <span className="text-[10px] text-muted-foreground">MATRIX FUSION</span>
            <span className="text-lg">→</span>
          </div>
        </div>

        {/* Fused Output */}
        <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">Reconstructed Probability</span>
            <span className={cn(
              "text-lg font-mono font-bold",
              fusedValue > 0.6 ? "text-success" : fusedValue > 0.4 ? "text-warning" : "text-destructive"
            )}>
              {(fusedValue * 100).toFixed(1)}%
            </span>
          </div>
          <Progress 
            value={fusedValue * 100} 
            className={cn(
              "h-2",
              fusedValue > 0.6 && "[&>div]:bg-gradient-to-r [&>div]:from-success [&>div]:to-success",
              fusedValue <= 0.6 && fusedValue > 0.4 && "[&>div]:bg-gradient-to-r [&>div]:from-warning [&>div]:to-warning",
              fusedValue <= 0.4 && "[&>div]:bg-gradient-to-r [&>div]:from-destructive [&>div]:to-destructive"
            )}
          />
          <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
            <span>Variance: {variance.toFixed(4)}</span>
            <span>Consensus: {variance < 0.03 ? 'STRONG' : variance < 0.1 ? 'WEAK' : 'NONE'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
