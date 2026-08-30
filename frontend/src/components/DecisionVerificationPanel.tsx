import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { decisionExplainer, DecisionExplanation } from '@/core/decisionExplainer';
import { decisionAccuracyTracker, AccuracyMetrics } from '@/core/decisionAccuracyTracker';
import { TrendingUp, TrendingDown, Pause, CheckCircle, XCircle, Target, Activity } from 'lucide-react';

const DecisionVerificationPanel: React.FC = () => {
  const [latestDecision, setLatestDecision] = useState<DecisionExplanation | null>(null);
  const [recentDecisions, setRecentDecisions] = useState<DecisionExplanation[]>([]);
  const [accuracy, setAccuracy] = useState<AccuracyMetrics | null>(null);

  useEffect(() => {
    // Initial load
    setLatestDecision(decisionExplainer.getLatest());
    setRecentDecisions(decisionExplainer.getExplanations().slice(0, 10));
    setAccuracy(decisionAccuracyTracker.getMetrics());

    // Subscribe to updates
    const unsubExplainer = decisionExplainer.subscribe((explanation) => {
      setLatestDecision(explanation);
      setRecentDecisions(decisionExplainer.getExplanations().slice(0, 10));
    });

    const unsubAccuracy = decisionAccuracyTracker.subscribe((metrics) => {
      setAccuracy(metrics);
    });

    return () => {
      unsubExplainer();
      unsubAccuracy();
    };
  }, []);

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'BUY': return <TrendingUp className="h-8 w-8" />;
      case 'SELL': return <TrendingDown className="h-8 w-8" />;
      default: return <Pause className="h-8 w-8" />;
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'bg-success/20 text-success border-success/50';
      case 'SELL': return 'bg-destructive/20 text-destructive border-destructive/50';
      default: return 'bg-warning/20 text-warning border-warning/50';
    }
  };

  return (
    <div className="space-y-4">
      {/* Main Decision Display */}
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            Current Decision
          </CardTitle>
        </CardHeader>
        <CardContent>
          {latestDecision ? (
            <div className="space-y-4">
              {/* Big Action Display */}
              <div className={`flex items-center justify-center gap-4 p-6 rounded-lg border-2 ${getActionColor(latestDecision.action)}`}>
                {getActionIcon(latestDecision.action)}
                <div className="text-center">
                  <div className="text-3xl font-bold">{latestDecision.action}</div>
                  <div className="text-sm opacity-80">
                    {(latestDecision.confidence * 100).toFixed(0)}% confidence
                  </div>
                </div>
              </div>

              {/* Summary */}
              <p className="text-sm text-muted-foreground text-center">
                {latestDecision.summary}
              </p>

              {/* Factors Grid */}
              <div className="grid grid-cols-2 gap-2">
                {latestDecision.factors.map((factor, idx) => (
                  <div 
                    key={idx}
                    className={`p-2 rounded text-xs ${
                      factor.passed 
                        ? 'bg-success/10 border border-success/30' 
                        : 'bg-muted/30 border border-border/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{factor.name}</span>
                      {factor.passed ? (
                        <CheckCircle className="h-3 w-3 text-success" />
                      ) : (
                        <XCircle className="h-3 w-3 text-muted-foreground" />
                      )}
                    </div>
                    <div className="text-muted-foreground mt-1">
                      {typeof factor.value === 'number' 
                        ? factor.value.toFixed(2) 
                        : factor.value} / {factor.threshold}
                    </div>
                  </div>
                ))}
              </div>

              {/* Reasoning */}
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {latestDecision.reasoning.map((reason, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground font-mono">
                    {reason}
                  </div>
                ))}
              </div>

              {/* Prism Info */}
              <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border/30 pt-2">
                <span>Prism: Level {latestDecision.prismLevel}</span>
                <span>{latestDecision.outputFrequency.toFixed(0)} Hz</span>
                <span>{latestDecision.waveState}</span>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              Waiting for first decision...
            </div>
          )}
        </CardContent>
      </Card>

      {/* Accuracy Metrics */}
      {accuracy && accuracy.total > 0 && (
        <Card className="bg-card/50 backdrop-blur border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Decision Accuracy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Time-based accuracy */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span>1 min accuracy</span>
                <span className="font-mono">{(accuracy.accuracy1m * 100).toFixed(0)}%</span>
              </div>
              <Progress value={accuracy.accuracy1m * 100} className="h-1.5" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span>5 min accuracy</span>
                <span className="font-mono">{(accuracy.accuracy5m * 100).toFixed(0)}%</span>
              </div>
              <Progress value={accuracy.accuracy5m * 100} className="h-1.5" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span>15 min accuracy</span>
                <span className="font-mono">{(accuracy.accuracy15m * 100).toFixed(0)}%</span>
              </div>
              <Progress value={accuracy.accuracy15m * 100} className="h-1.5" />
            </div>

            {/* Action-based accuracy */}
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/30">
              <div className="text-center">
                <div className="text-lg font-bold text-success">
                  {(accuracy.buyAccuracy * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">BUY</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-destructive">
                  {(accuracy.sellAccuracy * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">SELL</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-warning">
                  {(accuracy.holdAccuracy * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-muted-foreground">HOLD</div>
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
              <span>{accuracy.total} decisions tracked</span>
              <Badge variant="outline" className="text-xs">
                {accuracy.recentStreak} streak
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Decisions */}
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Recent Decisions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {recentDecisions.length > 0 ? (
              recentDecisions.map((decision) => (
                <div 
                  key={decision.id}
                  className="flex items-center justify-between p-2 rounded bg-muted/20 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${
                        decision.action === 'BUY' ? 'text-success border-success/50' :
                        decision.action === 'SELL' ? 'text-destructive border-destructive/50' :
                        'text-warning border-warning/50'
                      }`}
                    >
                      {decision.action}
                    </Badge>
                    <span className="text-muted-foreground">{decision.symbol}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono">
                      {(decision.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="text-muted-foreground">
                      {new Date(decision.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-muted-foreground py-4">
                No decisions yet
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DecisionVerificationPanel;
