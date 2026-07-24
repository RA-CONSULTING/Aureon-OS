/**
 * QGITA Debug Panel
 * Real-time visualization of QGITA signal generation
 */

import { useQGITAMetrics } from '../hooks/useQGITAMetrics';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';

export function QGITADebugPanel() {
  const { metrics, isInitialized } = useQGITAMetrics();

  if (!isInitialized) {
    return (
      <Card className="bg-background/50 border-border/50">
        <CardContent className="p-4">
          <p className="text-muted-foreground text-sm">Initializing QGITA...</p>
        </CardContent>
      </Card>
    );
  }

  const tierColors = {
    1: 'bg-success',
    2: 'bg-warning',
    3: 'bg-destructive',
  };

  const signalColors = {
    BUY: 'bg-success text-white',
    SELL: 'bg-destructive text-white',
    HOLD: 'bg-muted text-muted-foreground',
  };

  return (
    <Card className="bg-background/80 border-border/50 backdrop-blur">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">QGITA Signal Engine</CardTitle>
          <div className="flex gap-2">
            <Badge className={signalColors[metrics.signalType]}>
              {metrics.signalType}
            </Badge>
            <Badge variant="outline" className="font-mono">
              Tier {metrics.tier}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Confidence Bar */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Confidence</span>
            <span className="font-mono">{metrics.confidence.toFixed(1)}%</span>
          </div>
          <Progress value={metrics.confidence} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>Tier 3 (0-60)</span>
            <span>Tier 2 (60-80)</span>
            <span>Tier 1 (80+)</span>
          </div>
        </div>

        {/* FTCP & Lighthouse Status */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 rounded bg-muted/50">
            <div className="text-xs text-muted-foreground mb-1">FTCP Detection</div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${metrics.ftcpDetected ? 'bg-success' : 'bg-destructive'}`} />
              <span className="text-sm font-medium">{metrics.ftcpDetected ? 'Detected' : 'None'}</span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              φ Score: {(metrics.goldenRatioScore * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-2 rounded bg-muted/50">
            <div className="text-xs text-muted-foreground mb-1">Lighthouse Event</div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${metrics.isLHE ? 'bg-warning animate-pulse' : 'bg-muted'}`} />
              <span className="text-sm font-medium">{metrics.isLHE ? 'ACTIVE' : 'Inactive'}</span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              L: {metrics.lighthouseL.toFixed(3)} / {metrics.lighthouseThreshold.toFixed(3)}
            </div>
          </div>
        </div>

        {/* Curvature */}
        <div className="p-2 rounded bg-muted/50">
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Curvature Direction</span>
            <Badge variant="outline" className="text-xs">
              {metrics.curvatureDirection} ({metrics.curvature.toFixed(4)})
            </Badge>
          </div>
        </div>

        {/* Coherence Metrics */}
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Coherence Metrics</div>
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-xs text-muted-foreground">Linear</div>
              <div className="text-sm font-mono">{(metrics.linearCoherence * 100).toFixed(1)}%</div>
            </div>
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-xs text-muted-foreground">Nonlinear</div>
              <div className="text-sm font-mono">{(metrics.nonlinearCoherence * 100).toFixed(1)}%</div>
            </div>
            <div className="text-center p-2 rounded bg-muted/30">
              <div className="text-xs text-muted-foreground">Cross-Scale</div>
              <div className="text-sm font-mono">{(metrics.crossScaleCoherence * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* Anomaly Pointer */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Anomaly Pointer |Q|</span>
            <span className="font-mono">{metrics.anomalyPointer.toFixed(3)}</span>
          </div>
          <Progress value={metrics.anomalyPointer * 100} className="h-1.5" />
        </div>

        {/* Reasoning */}
        <div className="p-2 rounded bg-muted/30 border border-border/30">
          <div className="text-xs text-muted-foreground mb-1">Signal Reasoning</div>
          <p className="text-xs font-mono leading-relaxed">{metrics.reasoning}</p>
        </div>

        {/* Timestamp */}
        <div className="text-xs text-muted-foreground text-right">
          Last update: {metrics.lastUpdate > 0 ? new Date(metrics.lastUpdate).toLocaleTimeString() : 'N/A'}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Compact QGITA status indicator for dashboards
 */
export function QGITAStatusIndicator() {
  const { metrics, isInitialized } = useQGITAMetrics();

  if (!isInitialized) {
    return <Badge variant="outline" className="text-xs">QGITA: Init...</Badge>;
  }

  const bgColor = metrics.signalType === 'BUY' 
    ? 'bg-success/20 text-success border-success/50'
    : metrics.signalType === 'SELL'
    ? 'bg-destructive/20 text-destructive border-destructive/50'
    : 'bg-muted text-muted-foreground';

  return (
    <div className={`flex items-center gap-2 px-2 py-1 rounded border ${bgColor}`}>
      <span className="text-xs font-medium">QGITA</span>
      <span className="text-xs font-mono">{metrics.signalType}</span>
      <span className="text-xs opacity-70">T{metrics.tier}</span>
      <span className="text-xs font-mono">{metrics.confidence.toFixed(0)}%</span>
      {metrics.isLHE && <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />}
    </div>
  );
}
