/**
 * Exchange Learning Panel - Displays multi-exchange performance metrics
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { exchangeLearningTracker, ExchangeType } from '@/core/exchangeLearningTracker';
import { TrendingUp, TrendingDown, Activity, Target, Zap, Clock } from 'lucide-react';

const EXCHANGE_COLORS: Record<ExchangeType, string> = {
  binance: 'bg-warning/20 text-warning border-warning/30',
  kraken: 'bg-primary/20 text-primary border-primary/30',
  alpaca: 'bg-success/20 text-success border-success/30',
  capital: 'bg-primary/20 text-primary border-primary/30'
};

const EXCHANGE_LABELS: Record<ExchangeType, string> = {
  binance: '🟡 Binance',
  kraken: '🐙 Kraken',
  alpaca: '🦙 Alpaca',
  capital: '💼 Capital.com'
};

export function ExchangeLearningPanel() {
  const [metrics, setMetrics] = useState(exchangeLearningTracker.getAllExchangeMetrics());
  const [overallWinRate, setOverallWinRate] = useState(0.5);
  const [confidence, setConfidence] = useState(0.5);

  useEffect(() => {
    // Load historical data on mount
    exchangeLearningTracker.loadFromDatabase();

    const interval = setInterval(() => {
      setMetrics(exchangeLearningTracker.getAllExchangeMetrics());
      setOverallWinRate(exchangeLearningTracker.getOverallWinRate());
      setConfidence(exchangeLearningTracker.getLearningConfidence());
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const totalTrades = exchangeLearningTracker.getTotalTrades();

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Exchange Learning
          </span>
          <Badge variant="outline" className="font-mono text-xs">
            {totalTrades} trades
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-background/50 rounded-lg p-3 border border-border/30">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Target className="h-3 w-3" />
              Overall Win Rate
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold ${overallWinRate > 0.51 ? 'text-success' : 'text-destructive'}`}>
                {(overallWinRate * 100).toFixed(1)}%
              </span>
              {overallWinRate > 0.51 ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
            </div>
          </div>
          
          <div className="bg-background/50 rounded-lg p-3 border border-border/30">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Zap className="h-3 w-3" />
              Learning Confidence
            </div>
            <div className="space-y-1">
              <span className="text-lg font-bold">{(confidence * 100).toFixed(0)}%</span>
              <Progress value={confidence * 100} className="h-1" />
            </div>
          </div>
        </div>

        {/* Per-Exchange Metrics */}
        <div className="space-y-2">
          {metrics.map(m => (
            <div 
              key={m.exchange}
              className={`rounded-lg p-3 border ${EXCHANGE_COLORS[m.exchange]}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{EXCHANGE_LABELS[m.exchange]}</span>
                <Badge variant="secondary" className="text-xs">
                  {m.totalTrades} trades
                </Badge>
              </div>
              
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div>
                  <div className="text-muted-foreground">Win Rate</div>
                  <div className={`font-mono font-bold ${m.winRate > 0.51 ? 'text-success' : 'text-muted-foreground'}`}>
                    {(m.winRate * 100).toFixed(1)}%
                  </div>
                </div>
                
                <div>
                  <div className="text-muted-foreground">Avg Profit</div>
                  <div className={`font-mono font-bold ${m.avgProfit > 0 ? 'text-success' : 'text-destructive'}`}>
                    {m.avgProfit > 0 ? '+' : ''}{m.avgProfit.toFixed(2)}%
                  </div>
                </div>
                
                <div>
                  <div className="text-muted-foreground">Latency</div>
                  <div className="font-mono flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {m.avgLatency.toFixed(0)}ms
                  </div>
                </div>
                
                <div>
                  <div className="text-muted-foreground">Success</div>
                  <div className={`font-mono font-bold ${m.successRate > 0.95 ? 'text-success' : 'text-warning'}`}>
                    {(m.successRate * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
              
              {m.bestSymbol && (
                <div className="mt-2 pt-2 border-t border-border/30 flex justify-between text-xs">
                  <span className="text-muted-foreground">
                    Best: <span className="text-success font-mono">{m.bestSymbol}</span>
                  </span>
                  {m.worstSymbol && (
                    <span className="text-muted-foreground">
                      Worst: <span className="text-destructive font-mono">{m.worstSymbol}</span>
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
