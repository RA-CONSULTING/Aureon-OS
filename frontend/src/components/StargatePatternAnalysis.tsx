import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useStargatePatterns } from '@/hooks/useStargatePatterns';
import { RefreshCw, TrendingUp, Clock, AlertCircle } from 'lucide-react';

export function StargatePatternAnalysis() {
  const { 
    analysis, 
    isAnalyzing, 
    analyzePatterns, 
    nextOptimalWindow,
    patterns,
    recommendation,
  } = useStargatePatterns();

  const getOpportunityColor = (opportunity: string) => {
    switch (opportunity) {
      case 'excellent': return 'text-success';
      case 'good': return 'text-primary';
      case 'moderate': return 'text-warning';
      case 'poor': return 'text-destructive';
      default: return 'text-muted-foreground';
    }
  };

  const getOpportunityBadge = (opportunity: string) => {
    switch (opportunity) {
      case 'excellent': return 'default';
      case 'good': return 'secondary';
      case 'moderate': return 'outline';
      case 'poor': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <Card className="p-6 bg-gradient-to-br from-background to-secondary/20 border-primary/20">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold">AI Pattern Recognition</h3>
          {isAnalyzing && (
            <RefreshCw className="w-4 h-4 animate-spin text-primary" />
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => analyzePatterns()}
          disabled={isAnalyzing}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Analyze
        </Button>
      </div>

      {!analysis && !isAnalyzing && (
        <div className="text-center py-8 text-muted-foreground">
          <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No pattern analysis available yet</p>
          <p className="text-sm mt-1">Click Analyze to start</p>
        </div>
      )}

      {analysis && (
        <div className="space-y-6">
          {/* Current Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-secondary/30 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {analysis.dataPoints}
              </div>
              <div className="text-xs text-muted-foreground">Data Points</div>
            </div>
            <div className="text-center p-3 bg-secondary/30 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {(analysis.currentMetrics.avgNetworkStrength * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted-foreground">Avg Strength</div>
            </div>
            <div className="text-center p-3 bg-secondary/30 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {(analysis.currentMetrics.avgCoherence * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted-foreground">Avg Coherence</div>
            </div>
            <div className="text-center p-3 bg-secondary/30 rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {analysis.currentMetrics.highCoherencePeriods}
              </div>
              <div className="text-xs text-muted-foreground">Peak Periods</div>
            </div>
          </div>

          {/* Next Optimal Window */}
          {nextOptimalWindow && (
            <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg border border-primary/20">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-primary" />
                  <h4 className="font-semibold">Next Optimal Trading Window</h4>
                </div>
                <Badge variant={getOpportunityBadge(nextOptimalWindow.tradingOpportunity)}>
                  {nextOptimalWindow.tradingOpportunity.toUpperCase()}
                </Badge>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Start Time:</span>
                  <span className="font-mono">
                    {new Date(nextOptimalWindow.startTime).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">End Time:</span>
                  <span className="font-mono">
                    {new Date(nextOptimalWindow.endTime).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Expected Strength:</span>
                  <span className={getOpportunityColor(nextOptimalWindow.tradingOpportunity)}>
                    {(nextOptimalWindow.expectedNetworkStrength * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Confidence:</span>
                  <span className="text-primary">
                    {(nextOptimalWindow.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-3 pt-3 border-t border-primary/10">
                  <p className="text-xs text-muted-foreground italic">
                    {nextOptimalWindow.reasoning}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Detected Patterns */}
          {patterns.length > 0 && (
            <div>
              <h4 className="font-semibold mb-3">Detected Patterns</h4>
              <div className="space-y-2">
                {patterns.map((pattern, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-secondary/20 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">
                          {pattern.type.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Confidence: {(pattern.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm">{pattern.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-primary">
                        {(pattern.strength * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Strength</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendation */}
          {recommendation && (
            <div className="p-4 bg-secondary/30 rounded-lg">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-primary" />
                AI Recommendation
              </h4>
              <p className="text-sm text-muted-foreground">{recommendation}</p>
            </div>
          )}

          {/* Analysis Timestamp */}
          <div className="text-xs text-center text-muted-foreground pt-4 border-t">
            Last analyzed: {new Date(analysis.timestamp).toLocaleString()}
          </div>
        </div>
      )}
    </Card>
  );
}
