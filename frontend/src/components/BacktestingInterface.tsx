import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play, RotateCcw, Download, Save, AlertCircle } from "lucide-react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";
import { z } from "zod";

// Input validation schema
const backtestConfigSchema = z.object({
  symbol: z.string().min(1, "Symbol is required").max(20, "Symbol too long"),
  startDate: z.string().refine((date) => !isNaN(Date.parse(date)), "Invalid start date"),
  endDate: z.string().refine((date) => !isNaN(Date.parse(date)), "Invalid end date"),
  initialCapital: z.number().min(10, "Minimum capital is $10").max(1000000000, "Capital too large"),
  tradeSize: z.number().min(0.01, "Minimum 0.01").max(1, "Maximum 1 (100%)"),
  stopLoss: z.number().min(0.1, "Minimum 0.1%").max(50, "Maximum 50%"),
  takeProfit: z.number().min(0.1, "Minimum 0.1%").max(100, "Maximum 100%"),
  coherenceThreshold: z.number().min(0.1, "Minimum 0.1").max(1, "Maximum 1"),
  kellySafety: z.number().min(0.1, "Minimum 0.1").max(1, "Maximum 1"),
  lighthouseConfidence: z.number().min(0.1, "Minimum 0.1").max(1, "Maximum 1"),
  minPrismLevel: z.number().int().min(1, "Minimum 1").max(5, "Maximum 5"),
  requireLHE: z.boolean(),
});

type BacktestConfig = z.infer<typeof backtestConfigSchema>;

interface BacktestResults {
  totalTrades: number;
  winRate: number;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  profitFactor: number;
  avgWin: number;
  avgLoss: number;
  equityCurve: Array<{ date: string; equity: number }>;
  trades: Array<any>;
}

export function BacktestingInterface() {
  const { toast } = useToast();
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Configuration state
  const [config, setConfig] = useState<BacktestConfig>({
    symbol: "BTCUSDT",
    startDate: "2024-01-01",
    endDate: "2024-11-01",
    initialCapital: 10000,
    tradeSize: 0.98,
    stopLoss: 2.0,
    takeProfit: 5.0,
    coherenceThreshold: 0.945,
    kellySafety: 0.5,
    lighthouseConfidence: 0.7,
    minPrismLevel: 3,
    requireLHE: true,
  });

  const validateConfig = (): boolean => {
    try {
      backtestConfigSchema.parse(config);
      
      // Additional validation: end date must be after start date
      if (new Date(config.endDate) <= new Date(config.startDate)) {
        setErrors({ endDate: "End date must be after start date" });
        return false;
      }
      
      setErrors({});
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: Record<string, string> = {};
        error.errors.forEach((err) => {
          if (err.path.length > 0) {
            newErrors[err.path[0].toString()] = err.message;
          }
        });
        setErrors(newErrors);
      }
      return false;
    }
  };

  const runBacktest = async () => {
    if (!validateConfig()) {
      toast({
        title: "Invalid Configuration",
        description: "Please check your input parameters",
        variant: "destructive",
      });
      return;
    }

    setIsRunning(true);
    setResults(null);

    try {
      // Call edge function to run backtest
      const { data, error } = await supabase.functions.invoke('run-backtest', {
        body: {
          config: {
            symbol: config.symbol.trim(),
            startDate: config.startDate,
            endDate: config.endDate,
            initialCapital: config.initialCapital,
            tradeSize: config.tradeSize,
            stopLoss: config.stopLoss,
            takeProfit: config.takeProfit,
            coherenceThreshold: config.coherenceThreshold,
            kellySafety: config.kellySafety,
            lighthouseConfidence: config.lighthouseConfidence,
            minPrismLevel: config.minPrismLevel,
            requireLHE: config.requireLHE,
          }
        }
      });

      if (error) throw error;

      // LIVE DATA ONLY - Use real results from edge function
      if (!data || !data.results) {
        throw new Error('LIVE_DATA_REQUIRED: Backtest edge function did not return results. No simulation allowed.');
      }

      const realResults: BacktestResults = {
        totalTrades: data.results.totalTrades || 0,
        winRate: data.results.winRate || 0,
        totalReturn: data.results.totalReturn || 0,
        sharpeRatio: data.results.sharpeRatio || 0,
        maxDrawdown: data.results.maxDrawdown || 0,
        profitFactor: data.results.profitFactor || 0,
        avgWin: data.results.avgWin || 0,
        avgLoss: data.results.avgLoss || 0,
        equityCurve: data.results.equityCurve || [],
        trades: data.results.trades || [],
      };

      setResults(realResults);

      toast({
        title: "Backtest Complete",
        description: `Analyzed ${realResults.totalTrades} trades with ${realResults.winRate.toFixed(1)}% win rate`,
      });
    } catch (error) {
      console.error('Backtest error:', error);
      toast({
        title: "Backtest Failed",
        description: "An error occurred during backtesting",
        variant: "destructive",
      });
    } finally {
      setIsRunning(false);
    }
  };

  const saveResults = async () => {
    if (!results) return;

    try {
      const { error } = await supabase.from('backtest_results').insert({
        symbol: config.symbol.trim(),
        start_date: config.startDate,
        end_date: config.endDate,
        initial_capital: config.initialCapital,
        final_capital: results.equityCurve[results.equityCurve.length - 1].equity,
        total_trades: results.totalTrades,
        winning_trades: Math.round(results.totalTrades * results.winRate / 100),
        losing_trades: results.totalTrades - Math.round(results.totalTrades * results.winRate / 100),
        win_rate: results.winRate,
        total_return: results.totalReturn,
        max_drawdown: results.maxDrawdown,
        sharpe_ratio: results.sharpeRatio,
        profit_factor: results.profitFactor,
        config: config,
        trades: results.trades,
        equity_curve: results.equityCurve,
        status: 'completed',
      });

      if (error) throw error;

      toast({
        title: "Results Saved",
        description: "Backtest results saved to database",
      });
    } catch (error) {
      console.error('Save error:', error);
      toast({
        title: "Save Failed",
        description: "Could not save results",
        variant: "destructive",
      });
    }
  };

  const resetConfig = () => {
    setConfig({
      symbol: "BTCUSDT",
      startDate: "2024-01-01",
      endDate: "2024-11-01",
      initialCapital: 10000,
      tradeSize: 0.98,
      stopLoss: 2.0,
      takeProfit: 5.0,
      coherenceThreshold: 0.945,
      kellySafety: 0.5,
      lighthouseConfidence: 0.7,
      minPrismLevel: 3,
      requireLHE: true,
    });
    setResults(null);
    setErrors({});
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold">Backtesting Interface</CardTitle>
            <CardDescription>Test strategies on historical data with custom parameters</CardDescription>
          </div>
          <Badge variant="outline" className="text-primary">
            AUREON Engine
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="config" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="results" disabled={!results}>Results</TabsTrigger>
          </TabsList>

          <TabsContent value="config" className="space-y-6 mt-6">
            {/* Basic Settings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                <Select
                  value={config.symbol}
                  onValueChange={(value) => setConfig({ ...config, symbol: value })}
                >
                  <SelectTrigger id="symbol">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="BTCUSDT">BTCUSDT</SelectItem>
                    <SelectItem value="ETHUSDT">ETHUSDT</SelectItem>
                    <SelectItem value="BNBUSDT">BNBUSDT</SelectItem>
                  </SelectContent>
                </Select>
                {errors.symbol && <p className="text-xs text-destructive">{errors.symbol}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="capital">Initial Capital ($)</Label>
                <Input
                  id="capital"
                  type="number"
                  value={config.initialCapital}
                  onChange={(e) => setConfig({ ...config, initialCapital: Number(e.target.value) })}
                  min={10}
                  max={1000000000}
                  className="font-mono"
                />
                {errors.initialCapital && <p className="text-xs text-destructive">{errors.initialCapital}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={config.startDate}
                  onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
                />
                {errors.startDate && <p className="text-xs text-destructive">{errors.startDate}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="endDate">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={config.endDate}
                  onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
                />
                {errors.endDate && <p className="text-xs text-destructive">{errors.endDate}</p>}
              </div>
            </div>

            {/* Risk Parameters */}
            <div className="space-y-4 p-4 bg-muted/30 rounded-lg border border-border/30">
              <h4 className="text-sm font-semibold text-foreground">Risk Parameters</h4>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Trade Size ({(config.tradeSize * 100).toFixed(0)}%)</Label>
                  <span className="text-sm font-mono text-muted-foreground">
                    {formatCurrency(config.initialCapital * config.tradeSize)}
                  </span>
                </div>
                <Slider
                  value={[config.tradeSize]}
                  onValueChange={([value]) => setConfig({ ...config, tradeSize: value })}
                  min={0.01}
                  max={1}
                  step={0.01}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Stop Loss ({config.stopLoss.toFixed(1)}%)</Label>
                </div>
                <Slider
                  value={[config.stopLoss]}
                  onValueChange={([value]) => setConfig({ ...config, stopLoss: value })}
                  min={0.1}
                  max={50}
                  step={0.1}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Take Profit ({config.takeProfit.toFixed(1)}%)</Label>
                </div>
                <Slider
                  value={[config.takeProfit]}
                  onValueChange={([value]) => setConfig({ ...config, takeProfit: value })}
                  min={0.1}
                  max={100}
                  step={0.1}
                />
              </div>
            </div>

            {/* AUREON Parameters */}
            <div className="space-y-4 p-4 bg-primary/5 rounded-lg border border-primary/30">
              <h4 className="text-sm font-semibold text-foreground">AUREON Field Parameters</h4>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Coherence Threshold (Γ min)</Label>
                  <Badge variant="outline" className="font-mono">
                    {config.coherenceThreshold.toFixed(3)}
                  </Badge>
                </div>
                <Slider
                  value={[config.coherenceThreshold]}
                  onValueChange={([value]) => setConfig({ ...config, coherenceThreshold: value })}
                  min={0.1}
                  max={1}
                  step={0.001}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Kelly Safety Factor (φ)</Label>
                  <Badge variant="outline" className="font-mono">
                    {config.kellySafety.toFixed(2)}
                  </Badge>
                </div>
                <Slider
                  value={[config.kellySafety]}
                  onValueChange={([value]) => setConfig({ ...config, kellySafety: value })}
                  min={0.1}
                  max={1}
                  step={0.05}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Lighthouse Confidence</Label>
                  <Badge variant="outline" className="font-mono">
                    {config.lighthouseConfidence.toFixed(2)}
                  </Badge>
                </div>
                <Slider
                  value={[config.lighthouseConfidence]}
                  onValueChange={([value]) => setConfig({ ...config, lighthouseConfidence: value })}
                  min={0.1}
                  max={1}
                  step={0.05}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Minimum Prism Level</Label>
                  <Badge variant="outline" className="font-mono">
                    {config.minPrismLevel}
                  </Badge>
                </div>
                <Slider
                  value={[config.minPrismLevel]}
                  onValueChange={([value]) => setConfig({ ...config, minPrismLevel: Math.round(value) })}
                  min={1}
                  max={5}
                  step={1}
                />
              </div>

              <div className="flex items-center justify-between p-3 bg-background/50 rounded">
                <Label htmlFor="requireLHE">Require LHE (Lighthouse Event)</Label>
                <input
                  id="requireLHE"
                  type="checkbox"
                  checked={config.requireLHE}
                  onChange={(e) => setConfig({ ...config, requireLHE: e.target.checked })}
                  className="h-4 w-4 accent-primary"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                onClick={runBacktest}
                disabled={isRunning}
                className="flex-1"
              >
                {isRunning ? (
                  <>
                    <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Backtest
                  </>
                )}
              </Button>
              <Button onClick={resetConfig} variant="outline">
                <RotateCcw className="h-4 w-4 mr-2" />
                Reset
              </Button>
            </div>

            {Object.keys(errors).length > 0 && (
              <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <div className="text-xs">
                  <p className="font-semibold text-destructive">Configuration Errors</p>
                  <p className="text-muted-foreground">Please correct the errors above</p>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="results" className="space-y-6 mt-6">
            {results && (
              <>
                {/* Performance Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Total Trades</p>
                    <p className="text-2xl font-bold font-mono text-foreground">{results.totalTrades}</p>
                  </div>
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
                    <p className="text-2xl font-bold font-mono text-success">{results.winRate.toFixed(1)}%</p>
                  </div>
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Total Return</p>
                    <p className="text-2xl font-bold font-mono text-primary">{results.totalReturn.toFixed(1)}%</p>
                  </div>
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Sharpe Ratio</p>
                    <p className="text-2xl font-bold font-mono text-foreground">{results.sharpeRatio.toFixed(2)}</p>
                  </div>
                </div>

                {/* Equity Curve */}
                <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                  <h4 className="text-sm font-semibold mb-4 text-foreground">Equity Curve</h4>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={results.equityCurve}>
                        <defs>
                          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                        <XAxis 
                          dataKey="date" 
                          stroke="hsl(var(--muted-foreground))"
                          style={{ fontSize: '12px' }}
                        />
                        <YAxis 
                          stroke="hsl(var(--muted-foreground))"
                          style={{ fontSize: '12px' }}
                          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px'
                          }}
                          formatter={(value: number) => [`${formatCurrency(value)}`, 'Equity']}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="equity" 
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          fillOpacity={1}
                          fill="url(#equityGradient)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Additional Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-background/50 rounded border border-border/30">
                    <p className="text-xs text-muted-foreground">Max Drawdown</p>
                    <p className="text-lg font-bold font-mono text-destructive">-{results.maxDrawdown.toFixed(1)}%</p>
                  </div>
                  <div className="p-3 bg-background/50 rounded border border-border/30">
                    <p className="text-xs text-muted-foreground">Profit Factor</p>
                    <p className="text-lg font-bold font-mono text-foreground">{results.profitFactor.toFixed(2)}</p>
                  </div>
                  <div className="p-3 bg-background/50 rounded border border-border/30">
                    <p className="text-xs text-muted-foreground">Avg Win</p>
                    <p className="text-lg font-bold font-mono text-success">+{results.avgWin.toFixed(2)}%</p>
                  </div>
                  <div className="p-3 bg-background/50 rounded border border-border/30">
                    <p className="text-xs text-muted-foreground">Avg Loss</p>
                    <p className="text-lg font-bold font-mono text-destructive">-{results.avgLoss.toFixed(2)}%</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <Button onClick={saveResults} className="flex-1">
                    <Save className="h-4 w-4 mr-2" />
                    Save Results
                  </Button>
                  <Button variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    Export CSV
                  </Button>
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
