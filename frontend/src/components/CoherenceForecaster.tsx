import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, Sparkles, Calendar, Clock, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from "@/hooks/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ForecastDay {
  day: string;
  hours: number[];
  predictedCoherence: number;
  confidence: string;
  reasoning: string;
}

interface Trends {
  overall: string;
  bestDay: string;
  bestHours: number[];
  peakCoherence: number;
}

interface ForecastData {
  forecast: ForecastDay[];
  trends: Trends;
  recommendations: string[];
  confidence: string;
  dataQuality: string;
  metadata?: {
    generatedAt: string;
    historicalDataPoints: number;
    analysisWindow: string;
    forecastWindow: string;
  };
}

const DAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export const CoherenceForecaster = () => {
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const generateForecast = async () => {
    setIsLoading(true);
    setError(null);

    try {
      console.log('Calling forecast-coherence function...');

      const { data, error: functionError } = await supabase.functions.invoke('forecast-coherence', {
        body: {},
      });

      if (functionError) {
        console.error('Function error:', functionError);
        throw functionError;
      }

      if (data.error) {
        setError(data.message || data.error);
        toast({
          title: "Insufficient Data",
          description: data.message || "Not enough historical data for forecasting.",
          variant: "default",
        });
        return;
      }

      console.log('Forecast data received:', data);
      setForecastData(data);

      toast({
        title: "Forecast Generated",
        description: `Analyzed ${data.metadata?.historicalDataPoints || 0} data points to predict optimal trading windows.`,
        duration: 5000,
      });

    } catch (error) {
      console.error('Error generating forecast:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate forecast');
      toast({
        title: "Forecast Error",
        description: "Failed to generate coherence forecast. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatHours = (hours: number[]): string => {
    if (hours.length === 0) return '';
    if (hours.length === 1) return `${hours[0]}:00`;
    
    // Group consecutive hours
    const ranges: string[] = [];
    let start = hours[0];
    let prev = hours[0];
    
    for (let i = 1; i <= hours.length; i++) {
      if (i === hours.length || hours[i] !== prev + 1) {
        if (start === prev) {
          ranges.push(`${start}:00`);
        } else {
          ranges.push(`${start}:00-${prev + 1}:00`);
        }
        if (i < hours.length) {
          start = hours[i];
          prev = hours[i];
        }
      } else {
        prev = hours[i];
      }
    }
    
    return ranges.join(', ');
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case 'high': return 'text-success';
      case 'medium': return 'text-warning';
      case 'low': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'improving': return <TrendingUp className="h-4 w-4 text-success" />;
      case 'stable': return <CheckCircle2 className="h-4 w-4 text-primary" />;
      case 'declining': return <AlertTriangle className="h-4 w-4 text-warning" />;
      default: return null;
    }
  };

  return (
    <Card className="border-primary/20 bg-card/50 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Coherence Forecaster
            </CardTitle>
            <CardDescription>
              Predict optimal trading windows for the upcoming week using time-series analysis
            </CardDescription>
          </div>
          <Button
            onClick={generateForecast}
            disabled={isLoading}
            className="gap-2"
          >
            {isLoading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate Forecast
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && !forecastData && (
          <Card className="bg-warning/10 border-warning/20">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-warning mt-0.5" />
                <div>
                  <h4 className="font-semibold text-sm mb-1">Insufficient Data</h4>
                  <p className="text-xs text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!forecastData && !error && (
          <div className="text-center py-12">
            <Sparkles className="h-16 w-16 mx-auto mb-4 text-primary opacity-50" />
            <h3 className="text-lg font-semibold mb-2">Ready to Forecast</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Generate AI-powered predictions for optimal trading windows
            </p>
            <p className="text-xs text-muted-foreground">
              Requires at least 50 historical data points
            </p>
          </div>
        )}

        {forecastData && (
          <Tabs defaultValue="forecast" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="forecast">Weekly Forecast</TabsTrigger>
              <TabsTrigger value="trends">Trends & Analysis</TabsTrigger>
              <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
            </TabsList>

            <TabsContent value="forecast" className="space-y-4">
              {/* Metadata */}
              {forecastData.metadata && (
                <div className="grid grid-cols-4 gap-3">
                  <Card className="bg-background/50">
                    <CardContent className="p-3">
                      <p className="text-xs text-muted-foreground mb-1">Data Points</p>
                      <p className="text-lg font-bold">{forecastData.metadata.historicalDataPoints}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-background/50">
                    <CardContent className="p-3">
                      <p className="text-xs text-muted-foreground mb-1">Analysis Window</p>
                      <p className="text-lg font-bold">{forecastData.metadata.analysisWindow}</p>
                    </CardContent>
                  </Card>
                  <Card className={`${getConfidenceColor(forecastData.confidence)} bg-background/50`}>
                    <CardContent className="p-3">
                      <p className="text-xs text-muted-foreground mb-1">Confidence</p>
                      <p className="text-lg font-bold capitalize">{forecastData.confidence}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-background/50">
                    <CardContent className="p-3">
                      <p className="text-xs text-muted-foreground mb-1">Data Quality</p>
                      <p className="text-lg font-bold capitalize">{forecastData.dataQuality}</p>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Daily Forecasts */}
              <div className="space-y-3">
                {DAYS_ORDER.map(dayName => {
                  const dayForecast = forecastData.forecast.find(f => f.day === dayName);
                  
                  if (!dayForecast) {
                    return (
                      <Card key={dayName} className="bg-background/30 opacity-50">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Calendar className="h-5 w-5 text-muted-foreground" />
                              <span className="font-semibold">{dayName}</span>
                            </div>
                            <span className="text-xs text-muted-foreground">No optimal windows predicted</span>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  }

                  const isOptimal = dayForecast.predictedCoherence >= 0.945;
                  const isHigh = dayForecast.predictedCoherence >= 0.92;

                  return (
                    <Card 
                      key={dayName} 
                      className={`${isOptimal ? 'bg-success/10 border-success/20' : isHigh ? 'bg-warning/10 border-warning/20' : 'bg-background/50'}`}
                    >
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Calendar className="h-5 w-5" />
                              <span className="font-semibold text-lg">{dayForecast.day}</span>
                              <Badge variant={isOptimal ? "default" : "secondary"}>
                                {isOptimal ? 'OPTIMAL' : 'HIGH'}
                              </Badge>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-muted-foreground">Predicted C(t)</p>
                              <p className={`text-xl font-bold ${isOptimal ? 'text-success' : 'text-warning'}`}>
                                {dayForecast.predictedCoherence.toFixed(3)}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-start gap-2">
                            <Clock className="h-4 w-4 mt-0.5 text-muted-foreground" />
                            <div className="flex-1">
                              <p className="text-sm font-medium mb-1">Optimal Hours</p>
                              <p className="text-sm font-mono text-muted-foreground">
                                {formatHours(dayForecast.hours)}
                              </p>
                            </div>
                          </div>

                          <div className="bg-background/50 rounded-lg p-2">
                            <p className="text-xs text-muted-foreground">{dayForecast.reasoning}</p>
                          </div>

                          <div className="flex items-center gap-2 text-xs">
                            <span className={`font-semibold ${getConfidenceColor(dayForecast.confidence)}`}>
                              {dayForecast.confidence.toUpperCase()} CONFIDENCE
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="trends" className="space-y-4">
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Overall Trend Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-primary/5">
                    <div className="flex items-center gap-2">
                      {getTrendIcon(forecastData.trends.overall)}
                      <span className="font-semibold">Overall Trend</span>
                    </div>
                    <span className="text-lg font-bold capitalize">{forecastData.trends.overall}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-success/10 border border-success/20">
                      <p className="text-xs text-muted-foreground mb-1">Best Day</p>
                      <p className="text-lg font-bold text-success">{forecastData.trends.bestDay}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-success/10 border border-success/20">
                      <p className="text-xs text-muted-foreground mb-1">Peak Coherence</p>
                      <p className="text-lg font-bold text-success">{forecastData.trends.peakCoherence.toFixed(3)}</p>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <p className="text-xs text-muted-foreground mb-2">Best Hours (across all days)</p>
                    <p className="text-sm font-mono">{formatHours(forecastData.trends.bestHours)}</p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="recommendations" className="space-y-3">
              {forecastData.recommendations.map((rec, idx) => (
                <Card key={idx} className="bg-background/50">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-success mt-0.5" />
                      <p className="text-sm">{rec}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
          </Tabs>
        )}

        {/* Information */}
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-3">
            <div className="space-y-2">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                About This Forecast
              </h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Uses Lovable AI (Google Gemini 2.5 Flash) for time-series analysis</li>
                <li>• Analyzes 14 days of historical coherence patterns</li>
                <li>• Predicts optimal windows based on recurring daily and weekly cycles</li>
                <li>• Confidence levels reflect data quality and pattern strength</li>
                <li>• Forecasts are most accurate 3-7 days ahead</li>
                <li>• Re-generate periodically as new data becomes available</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
};
