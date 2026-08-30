import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useFrequencyHarmonization } from '@/hooks/useFrequencyHarmonization';
import { ArrowUp, ArrowDown, Minus, Zap } from 'lucide-react';

export function FrequencyHarmonizationPanel() {
  const { harmonization, lastUpdate, isActive } = useFrequencyHarmonization();

  if (!harmonization) {
    return (
      <Card className="bg-card shadow-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-2xl">🎵</span>
            Frequency Harmonization
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 text-muted-foreground">
            Initializing harmonization system...
          </div>
        </CardContent>
      </Card>
    );
  }

  const getBiasIcon = () => {
    if (harmonization.tradingBias === 'BULLISH') return <ArrowUp className="w-4 h-4" />;
    if (harmonization.tradingBias === 'BEARISH') return <ArrowDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getBiasColor = () => {
    if (harmonization.tradingBias === 'BULLISH') return 'text-success';
    if (harmonization.tradingBias === 'BEARISH') return 'text-destructive';
    return 'text-warning';
  };

  const getResonanceTypeColor = (type: string) => {
    switch (type) {
      case 'FOUNDATION': return 'bg-destructive/20 text-destructive';
      case 'HEART': return 'bg-success/20 text-success';
      case 'VISION': return 'bg-primary/20 text-primary';
      case 'UNITY': return 'bg-primary/20 text-primary';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <Card className="bg-card shadow-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">🎵</span>
              Frequency Harmonization
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Auto-adjusting signals based on stargate resonance
            </p>
          </div>
          {harmonization.optimalEntryWindow && (
            <Badge variant="default" className="bg-success text-white animate-pulse">
              <Zap className="w-3 h-3 mr-1" />
              OPTIMAL WINDOW
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Primary Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-muted-foreground mb-1">Dominant Frequency</div>
            <div className="text-2xl font-bold text-primary">
              {harmonization.dominantFrequency} Hz
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Trading Bias</div>
            <div className={`text-2xl font-bold flex items-center gap-2 ${getBiasColor()}`}>
              {getBiasIcon()}
              {harmonization.tradingBias}
            </div>
          </div>
        </div>

        {/* Signal Adjustments */}
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Coherence Boost</span>
              <span className={harmonization.coherenceBoost > 0 ? 'text-success' : 'text-destructive'}>
                {harmonization.coherenceBoost > 0 ? '+' : ''}{(harmonization.coherenceBoost * 100).toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={Math.abs(harmonization.coherenceBoost) * 100 / 0.4} 
              className="h-2"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Signal Amplification</span>
              <span className="text-primary">
                {harmonization.signalAmplification.toFixed(2)}x
              </span>
            </div>
            <Progress 
              value={(harmonization.signalAmplification - 0.5) / 1.5 * 100} 
              className="h-2"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Confidence Modifier</span>
              <span className="text-primary">
                {harmonization.confidenceModifier.toFixed(2)}x
              </span>
            </div>
            <Progress 
              value={(harmonization.confidenceModifier - 0.7) / 0.6 * 100} 
              className="h-2"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Resonance Quality</span>
              <span className="text-primary">
                {(harmonization.resonanceQuality * 100).toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={harmonization.resonanceQuality * 100} 
              className="h-2"
            />
          </div>
        </div>

        {/* Active Harmonics */}
        <div className="space-y-2">
          <div className="text-sm font-medium">Active Frequency Harmonics</div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {harmonization.harmonics.slice(0, 6).map((harmonic, i) => (
              <div 
                key={i}
                className="flex items-center justify-between p-2 bg-background/50 rounded text-xs"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={getResonanceTypeColor(harmonic.resonanceType)}>
                    {harmonic.resonanceType}
                  </Badge>
                  <span className="font-mono font-bold">{harmonic.frequency} Hz</span>
                </div>
                <div className="flex items-center gap-2">
                  <Progress 
                    value={harmonic.strength * 100} 
                    className="w-20 h-2"
                  />
                  <span className="text-muted-foreground w-12 text-right">
                    {(harmonic.strength * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Integration Note */}
        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
          <p className="text-xs text-muted-foreground leading-relaxed">
            <strong className="text-primary">Auto-Harmonization Active:</strong> Trading signals are 
            being dynamically adjusted based on the planetary stargate network. {harmonization.optimalEntryWindow 
              ? 'Currently in an optimal entry window with maximum resonance alignment.' 
              : `Signal amplification at ${harmonization.signalAmplification.toFixed(2)}x with ${harmonization.tradingBias.toLowerCase()} bias.`}
          </p>
        </div>

        {/* Last Update */}
        <div className="text-xs text-muted-foreground text-center">
          Last updated: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
}
