import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { ProbabilityMatrix, TradingSignal, HourlyProbabilityWindow, ProbabilityState } from "@/core/hncProbabilityMatrix";

interface HNCProbabilityMatrixPanelProps {
  matrix: ProbabilityMatrix | null;
  signal: TradingSignal | null;
}

const HourStateDisplay = ({ 
  label, 
  hour, 
  isPrimary = false 
}: { 
  label: string; 
  hour: HourlyProbabilityWindow | undefined | null; 
  isPrimary?: boolean;
}) => {
  if (!hour) {
    return (
      <div className="p-3 rounded-lg bg-muted/50 border border-border">
        <div className="text-xs text-muted-foreground mb-1">{label}</div>
        <div className="text-sm text-muted-foreground">No data</div>
      </div>
    );
  }

  const stateColors: Record<ProbabilityState, string> = {
    EXTREME_BULLISH: 'bg-success/20 text-success border-success/30',
    BULLISH: 'bg-success/20 text-success border-success/30',
    SLIGHT_BULLISH: 'bg-success/20 text-success border-success/30',
    EXTREME_BEARISH: 'bg-destructive/20 text-destructive border-destructive/30',
    BEARISH: 'bg-destructive/20 text-destructive border-destructive/30',
    SLIGHT_BEARISH: 'bg-destructive/20 text-destructive border-destructive/30',
    NEUTRAL: 'bg-warning/20 text-warning border-warning/30',
  };

  const stateEmoji: Record<ProbabilityState, string> = {
    EXTREME_BULLISH: '🟢',
    BULLISH: '🟢',
    SLIGHT_BULLISH: '🟢',
    EXTREME_BEARISH: '🔴',
    BEARISH: '🔴',
    SLIGHT_BEARISH: '🔴',
    NEUTRAL: '⚪',
  };

  return (
    <div className={`p-3 rounded-lg border ${isPrimary ? 'bg-primary/10 border-primary/30 ring-1 ring-primary/20' : 'bg-muted/50 border-border'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs ${isPrimary ? 'text-primary font-semibold' : 'text-muted-foreground'}`}>
          {label} {isPrimary && '⭐'}
        </span>
        <Badge variant="outline" className={stateColors[hour.state]}>
          {stateEmoji[hour.state]} {hour.state}
        </Badge>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Bull Probability</span>
          <span className="font-mono">{(hour.bullishProbability * 100).toFixed(1)}%</span>
        </div>
        <Progress value={hour.bullishProbability * 100} className="h-1.5" />
        
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Confidence</span>
          <span className="font-mono">{(hour.confidence * 100).toFixed(1)}%</span>
        </div>
        
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Signal Strength</span>
          <span className="font-mono">{(hour.signalStrength * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};

export function HNCProbabilityMatrixPanel({ matrix, signal }: HNCProbabilityMatrixPanelProps) {
  if (!matrix || !signal) {
    return (
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <span>📊</span>
            HNC Probability Matrix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            Awaiting temporal data...
          </div>
        </CardContent>
      </Card>
    );
  }

  const actionColors: Record<string, string> = {
    BUY: 'bg-success',
    SELL: 'bg-destructive',
    HOLD: 'bg-warning',
  };

  const actionEmoji: Record<string, string> = {
    BUY: '🟢',
    SELL: '🔴',
    HOLD: '⚪',
  };

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>📊</span>
            HNC Probability Matrix
          </div>
          <Badge className={`${actionColors[signal.action]} text-white`}>
            {actionEmoji[signal.action]} {signal.action}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 4-Hour Timeline */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <HourStateDisplay label="Hour -1 (Lookback)" hour={matrix.hourMinus1} />
          <HourStateDisplay label="Hour 0 (Now)" hour={matrix.hour0} />
          <HourStateDisplay label="Hour +1 (Forecast)" hour={matrix.hourPlus1} isPrimary />
          <HourStateDisplay label="Hour +2 (Fine-tune)" hour={matrix.hourPlus2} />
        </div>

        {/* Signal Summary */}
        <div className="p-4 rounded-lg bg-muted/30 border border-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Trading Signal</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl">{actionEmoji[signal.action]}</span>
              <span className="font-bold text-lg">{signal.action}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground text-xs">Probability</div>
              <div className="font-mono font-semibold">{(signal.probability * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Confidence</div>
              <div className="font-mono font-semibold">{(signal.confidence * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Position Modifier</div>
              <div className="font-mono font-semibold">{signal.modifier.toFixed(2)}x</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Fine-tune Adj.</div>
              <div className="font-mono font-semibold">{(signal.fineTune * 100).toFixed(1)}%</div>
            </div>
          </div>

          {/* Combined Probability Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Combined Probability</span>
              <span className="font-mono">{(matrix.combinedProbability * 100).toFixed(1)}%</span>
            </div>
            <Progress value={matrix.combinedProbability * 100} className="h-2" />
          </div>

          {/* Fine-tuned Probability Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Fine-tuned Probability</span>
              <span className="font-mono">{(matrix.fineTunedProbability * 100).toFixed(1)}%</span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
              <div 
                className="h-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500"
                style={{ width: `${matrix.fineTunedProbability * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Matrix Metadata */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Symbol: {matrix.symbol}</span>
          <span>Generated: {new Date(matrix.generatedAt).toLocaleTimeString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}
