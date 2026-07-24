/**
 * Prediction Accuracy Panel - Shows HNC probability prediction accuracy
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { tradeLogger, CalibrationData } from '@/core/tradeLogger';
import { Target, TrendingUp, BarChart3, Percent } from 'lucide-react';

export default function PredictionAccuracyPanel() {
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);

  useEffect(() => {
    // Load calibration data
    const loadCalibration = () => {
      const data = tradeLogger.exportCalibration();
      setCalibration(data);
    };

    loadCalibration();
    const interval = setInterval(loadCalibration, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, []);

  if (!calibration) {
    return (
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading calibration data...
        </CardContent>
      </Card>
    );
  }

  const { predictionAccuracy, winRate, bandPerformance, tierPerformance, bestHours } = calibration;
  const accuracyPct = (predictionAccuracy.accuracy * 100).toFixed(1);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Target className="w-5 h-5 text-primary" />
          Prediction Accuracy & Learning
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Accuracy Stats */}
        <div className="grid grid-cols-4 gap-3">
          <div className="text-center p-3 rounded-lg bg-muted/30 border border-border/30">
            <Percent className="w-5 h-5 mx-auto mb-1 text-primary" />
            <div className="text-2xl font-bold text-foreground">{accuracyPct}%</div>
            <div className="text-xs text-muted-foreground">Prediction Accuracy</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30 border border-border/30">
            <TrendingUp className="w-5 h-5 mx-auto mb-1 text-success" />
            <div className="text-2xl font-bold text-foreground">{(winRate * 100).toFixed(1)}%</div>
            <div className="text-xs text-muted-foreground">Win Rate</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30 border border-border/30">
            <BarChart3 className="w-5 h-5 mx-auto mb-1 text-primary" />
            <div className="text-2xl font-bold text-foreground">{predictionAccuracy.total}</div>
            <div className="text-xs text-muted-foreground">Total Predictions</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30 border border-border/30">
            <Target className="w-5 h-5 mx-auto mb-1 text-warning" />
            <div className="text-2xl font-bold text-foreground">{predictionAccuracy.correct}</div>
            <div className="text-xs text-muted-foreground">Correct</div>
          </div>
        </div>

        {/* Accuracy by Confidence Level */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Accuracy by Confidence Level</h4>
          <div className="grid grid-cols-3 gap-2">
            {['high', 'medium', 'low'].map((level) => {
              const data = predictionAccuracy.byConfidence[level] || { total: 0, correct: 0 };
              const acc = data.total > 0 ? (data.correct / data.total * 100) : 0;
              return (
                <div key={level} className="p-2 rounded bg-muted/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs capitalize text-muted-foreground">{level}</span>
                    <span className="text-xs font-mono">{acc.toFixed(0)}%</span>
                  </div>
                  <Progress value={acc} className="h-1" />
                  <div className="text-xs text-muted-foreground mt-1">
                    {data.correct}/{data.total} correct
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Performance by Frequency Band */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Performance by Frequency Band</h4>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(bandPerformance)
              .filter(([, data]) => data.trades > 0)
              .slice(0, 4)
              .map(([band, data]) => (
                <div key={band} className="p-2 rounded bg-muted/20">
                  <div className="text-xs font-bold text-foreground mb-1">{band}</div>
                  <div className={`text-sm font-mono ${data.winRate >= 0.5 ? 'text-success' : 'text-destructive'}`}>
                    {(data.winRate * 100).toFixed(0)}% win
                  </div>
                  <div className="text-xs text-muted-foreground">{data.trades} trades</div>
                </div>
              ))}
          </div>
        </div>

        {/* QGITA Tier Performance */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Performance by QGITA Tier</h4>
          <div className="grid grid-cols-3 gap-2">
            {([1, 2, 3] as const).map((tier) => {
              const data = tierPerformance[tier];
              return (
                <div key={tier} className="p-2 rounded bg-muted/20">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={tier === 1 ? 'default' : tier === 2 ? 'secondary' : 'outline'}>
                      Tier {tier}
                    </Badge>
                  </div>
                  <div className={`text-sm font-mono ${data.winRate >= 0.5 ? 'text-success' : 'text-destructive'}`}>
                    {(data.winRate * 100).toFixed(0)}% win
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {data.trades} trades • Avg: {data.avgPnl.toFixed(2)}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Best Trading Hours */}
        {bestHours.length > 0 && (
          <div className="pt-2 border-t border-border/30">
            <h4 className="text-sm font-medium text-muted-foreground mb-2">Best Trading Hours (UTC)</h4>
            <div className="flex flex-wrap gap-1">
              {bestHours.map((hour) => (
                <Badge key={hour} variant="outline" className="text-xs bg-success/10 text-success border-success/30">
                  {hour.toString().padStart(2, '0')}:00
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
