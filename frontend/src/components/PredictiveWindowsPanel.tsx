import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { usePredictiveWindows } from '@/hooks/usePredictiveWindows';
import { Calendar, TrendingUp, Clock, Activity } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';

export function PredictiveWindowsPanel() {
  const { predictions, isAnalyzing, error, nextOptimalWindow } = usePredictiveWindows(7);

  if (isAnalyzing) {
    return (
      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Predictive Analytics
          </CardTitle>
          <CardDescription>Loading forecasted optimal trading windows...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <TrendingUp className="h-5 w-5" />
            Predictive Analytics
          </CardTitle>
          <CardDescription>Failed to generate predictions: {error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (predictions.length === 0) {
    return (
      <Card className="border-muted">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
            Predictive Analytics
          </CardTitle>
          <CardDescription>
            Insufficient historical data to generate predictions. Predictions will be available after collecting more scheduler history.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-success';
    if (confidence >= 0.6) return 'text-warning';
    return 'text-warning';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Predictive Analytics
        </CardTitle>
        <CardDescription>
          Forecasted optimal trading windows based on historical patterns (next 7 days)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Next Optimal Window Highlight */}
        {nextOptimalWindow && (
          <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                <h4 className="font-semibold text-foreground">Next Optimal Window</h4>
              </div>
              <Badge variant="default" className={getConfidenceColor(nextOptimalWindow.confidence)}>
                {(nextOptimalWindow.confidence * 100).toFixed(0)}% {getConfidenceLabel(nextOptimalWindow.confidence)}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div>
                <p className="text-sm text-muted-foreground">Start Time</p>
                <p className="text-sm font-medium text-foreground">
                  {format(nextOptimalWindow.startTime, 'MMM dd, HH:mm')}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(nextOptimalWindow.startTime, { addSuffix: true })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Expected</p>
                <p className="text-sm font-medium text-foreground">
                  Coherence: {nextOptimalWindow.expectedCoherence.toFixed(3)}
                </p>
                <p className="text-xs text-muted-foreground">
                  LHE: {nextOptimalWindow.expectedLHECount.toFixed(1)}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{nextOptimalWindow.reasoning}</p>
          </div>
        )}

        {/* Upcoming Windows */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Upcoming Predicted Windows
          </h4>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {predictions.slice(0, 10).map((prediction, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors border border-border"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {prediction.dayOfWeek} {prediction.hourRange}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {format(prediction.startTime, 'MMM dd, yyyy')}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={`${getConfidenceColor(prediction.confidence)} border-current`}
                  >
                    {(prediction.confidence * 100).toFixed(0)}%
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Coherence: </span>
                    <span className="text-foreground font-medium">
                      {prediction.expectedCoherence.toFixed(3)}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">LHE: </span>
                    <span className="text-foreground font-medium">
                      {prediction.expectedLHECount.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {predictions.length > 10 && (
          <p className="text-xs text-muted-foreground text-center">
            Showing 10 of {predictions.length} predicted windows
          </p>
        )}
      </CardContent>
    </Card>
  );
}
