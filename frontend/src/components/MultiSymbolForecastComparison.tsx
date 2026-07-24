import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { TrendingUp, TrendingDown, Minus, Sparkles, RefreshCw, BarChart3, AlertCircle } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from "@/hooks/use-toast";

interface SymbolForecast {
  symbol: string;
  bestDay: string;
  bestHours: number[];
  peakCoherence: number;
  avgCoherence: number;
  optimalDaysCount: number;
  trend: string;
  confidence: string;
  dataPoints: number;
}

const AVAILABLE_SYMBOLS = [
  { value: 'BTCUSDT', label: 'Bitcoin (BTC)' },
  { value: 'ETHUSDT', label: 'Ethereum (ETH)' },
  { value: 'BNBUSDT', label: 'Binance Coin (BNB)' },
  { value: 'SOLUSDT', label: 'Solana (SOL)' },
  { value: 'XRPUSDT', label: 'Ripple (XRP)' },
  { value: 'ADAUSDT', label: 'Cardano (ADA)' },
];

export const MultiSymbolForecastComparison = () => {
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['BTCUSDT']);
  const [forecasts, setForecasts] = useState<SymbolForecast[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols(prev => 
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  const generateComparison = async () => {
    if (selectedSymbols.length === 0) {
      toast({
        title: "No Symbols Selected",
        description: "Please select at least one cryptocurrency to analyze.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setError(null);
    setForecasts([]);

    try {
      console.log('Generating forecasts for:', selectedSymbols);

      const forecastPromises = selectedSymbols.map(async (symbol) => {
        const { data, error: functionError } = await supabase.functions.invoke('forecast-coherence', {
          body: { symbol },
        });

        if (functionError) {
          console.error(`Error forecasting ${symbol}:`, functionError);
          return null;
        }

        if (data.error) {
          console.log(`Insufficient data for ${symbol}`);
          return null;
        }

        // Extract key metrics
        const optimalDays = data.forecast.filter((f: any) => f.predictedCoherence >= 0.945).length;
        const allCoherences = data.forecast.map((f: any) => f.predictedCoherence);
        const avgCoherence = allCoherences.reduce((a: number, b: number) => a + b, 0) / allCoherences.length;

        return {
          symbol,
          bestDay: data.trends.bestDay,
          bestHours: data.trends.bestHours,
          peakCoherence: data.trends.peakCoherence,
          avgCoherence,
          optimalDaysCount: optimalDays,
          trend: data.trends.overall,
          confidence: data.confidence,
          dataPoints: data.metadata.historicalDataPoints,
        };
      });

      const results = await Promise.all(forecastPromises);
      const validForecasts = results.filter(f => f !== null) as SymbolForecast[];

      if (validForecasts.length === 0) {
        setError('No sufficient data available for the selected cryptocurrencies. Continue running the system to collect data.');
        toast({
          title: "Insufficient Data",
          description: "No forecasts could be generated. Continue collecting data.",
          variant: "default",
        });
      } else {
        // Sort by peak coherence descending
        validForecasts.sort((a, b) => b.peakCoherence - a.peakCoherence);
        setForecasts(validForecasts);

        toast({
          title: "Comparison Complete",
          description: `Generated forecasts for ${validForecasts.length} cryptocurrencies.`,
          duration: 5000,
        });
      }

    } catch (error) {
      console.error('Error generating comparison:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate comparison');
      toast({
        title: "Comparison Error",
        description: "Failed to generate multi-symbol forecast. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'improving': return <TrendingUp className="h-4 w-4 text-success" />;
      case 'stable': return <Minus className="h-4 w-4 text-primary" />;
      case 'declining': return <TrendingDown className="h-4 w-4 text-warning" />;
      default: return null;
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case 'high': return 'text-success';
      case 'medium': return 'text-warning';
      case 'low': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  const formatHours = (hours: number[]): string => {
    if (hours.length === 0) return 'None';
    if (hours.length <= 3) return hours.map(h => `${h}:00`).join(', ');
    return `${hours[0]}:00-${hours[hours.length - 1] + 1}:00`;
  };

  return (
    <Card className="border-primary/20 bg-card/50 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Multi-Symbol Forecast Comparison
            </CardTitle>
            <CardDescription>
              Compare coherence predictions across cryptocurrencies to identify best opportunities
            </CardDescription>
          </div>
          <Button
            onClick={generateComparison}
            disabled={isLoading || selectedSymbols.length === 0}
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
                Compare {selectedSymbols.length} Symbol{selectedSymbols.length !== 1 ? 's' : ''}
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Symbol Selection */}
        <Card className="bg-background/50">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Select Cryptocurrencies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {AVAILABLE_SYMBOLS.map(({ value, label }) => (
                <div key={value} className="flex items-center space-x-2">
                  <Checkbox
                    id={value}
                    checked={selectedSymbols.includes(value)}
                    onCheckedChange={() => toggleSymbol(value)}
                  />
                  <label
                    htmlFor={value}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    {label}
                  </label>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Error State */}
        {error && forecasts.length === 0 && (
          <Card className="bg-warning/10 border-warning/20">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-warning mt-0.5" />
                <div>
                  <h4 className="font-semibold text-sm mb-1">Insufficient Data</h4>
                  <p className="text-xs text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Comparison Results */}
        {forecasts.length > 0 && (
          <div className="space-y-4">
            {/* Ranking Header */}
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-success" />
                  Best Opportunities (Ranked by Peak Coherence)
                </h3>
                <p className="text-xs text-muted-foreground">
                  Higher peak coherence indicates better trading conditions and more optimal windows
                </p>
              </CardContent>
            </Card>

            {/* Forecast Cards */}
            {forecasts.map((forecast, index) => {
              const isTop = index === 0;
              const isOptimal = forecast.peakCoherence >= 0.945;
              const isHigh = forecast.peakCoherence >= 0.92;

              return (
                <Card 
                  key={forecast.symbol}
                  className={`${
                    isTop 
                      ? 'bg-success/10 border-success/30 border-2' 
                      : isOptimal
                      ? 'bg-success/5 border-success/20'
                      : isHigh
                      ? 'bg-warning/5 border-warning/20'
                      : 'bg-background/50'
                  }`}
                >
                  <CardContent className="p-4">
                    <div className="space-y-4">
                      {/* Header */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant={isTop ? "default" : "secondary"} className="text-lg px-3 py-1">
                            #{index + 1}
                          </Badge>
                          <div>
                            <h4 className="font-bold text-lg">{forecast.symbol.replace('USDT', '/USDT')}</h4>
                            <p className="text-xs text-muted-foreground">
                              {AVAILABLE_SYMBOLS.find(s => s.value === forecast.symbol)?.label}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground mb-1">Peak C(t)</p>
                          <p className={`text-2xl font-bold ${
                            isOptimal ? 'text-success' : isHigh ? 'text-warning' : 'text-foreground'
                          }`}>
                            {forecast.peakCoherence.toFixed(3)}
                          </p>
                        </div>
                      </div>

                      {/* Metrics Grid */}
                      <div className="grid grid-cols-4 gap-3">
                        <div className="rounded-lg bg-background/50 p-2">
                          <p className="text-xs text-muted-foreground mb-1">Avg C(t)</p>
                          <p className="text-sm font-bold">{forecast.avgCoherence.toFixed(3)}</p>
                        </div>
                        <div className="rounded-lg bg-background/50 p-2">
                          <p className="text-xs text-muted-foreground mb-1">Optimal Days</p>
                          <p className="text-sm font-bold">{forecast.optimalDaysCount}/7</p>
                        </div>
                        <div className="rounded-lg bg-background/50 p-2">
                          <p className="text-xs text-muted-foreground mb-1">Trend</p>
                          <div className="flex items-center gap-1">
                            {getTrendIcon(forecast.trend)}
                            <p className="text-xs font-medium capitalize">{forecast.trend}</p>
                          </div>
                        </div>
                        <div className="rounded-lg bg-background/50 p-2">
                          <p className="text-xs text-muted-foreground mb-1">Confidence</p>
                          <p className={`text-xs font-bold capitalize ${getConfidenceColor(forecast.confidence)}`}>
                            {forecast.confidence}
                          </p>
                        </div>
                      </div>

                      {/* Best Windows */}
                      <div className="rounded-lg bg-primary/5 border border-primary/20 p-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <p className="text-xs text-muted-foreground mb-1">Best Day</p>
                            <p className="font-semibold">{forecast.bestDay}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground mb-1">Best Hours</p>
                            <p className="font-mono text-sm">{formatHours(forecast.bestHours)}</p>
                          </div>
                        </div>
                      </div>

                      {/* Data Quality */}
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{forecast.dataPoints} historical data points</span>
                        {isTop && (
                          <Badge variant="default" className="gap-1">
                            <Sparkles className="h-3 w-3" />
                            Top Pick
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Initial State */}
        {forecasts.length === 0 && !error && !isLoading && (
          <div className="text-center py-12">
            <BarChart3 className="h-16 w-16 mx-auto mb-4 text-primary opacity-50" />
            <h3 className="text-lg font-semibold mb-2">Ready to Compare</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Select cryptocurrencies and generate forecasts to compare opportunities
            </p>
            <p className="text-xs text-muted-foreground">
              Tip: Compare 2-3 symbols for best results
            </p>
          </div>
        )}

        {/* Information */}
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-3">
            <div className="space-y-2">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                How to Use This Comparison
              </h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Select multiple cryptocurrencies to analyze simultaneously</li>
                <li>• Rankings are based on predicted peak coherence values</li>
                <li>• Higher peak coherence = more stable and predictable trading conditions</li>
                <li>• Look for symbols with high optimal day counts (≥4 days)</li>
                <li>• "Improving" trends indicate strengthening market conditions</li>
                <li>• Each symbol needs separate historical data collection</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
};
