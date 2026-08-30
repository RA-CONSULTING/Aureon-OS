import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Shield, AlertTriangle, TrendingDown, DollarSign, Lock } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";

interface RiskMetrics {
  currentDrawdown: number;
  maxDrawdownLimit: number;
  positionSize: number;
  maxPositionSize: number;
  dailyLoss: number;
  maxDailyLoss: number;
  openPositions: number;
  maxPositions: number;
  capitalDeployed: number;
  totalCapital: number;
}

export function RiskManagementDashboard() {
  const [metrics, setMetrics] = useState<RiskMetrics>({
    currentDrawdown: 12.3,
    maxDrawdownLimit: 30,
    positionSize: 4500,
    maxPositionSize: 50000,
    dailyLoss: 180,
    maxDailyLoss: 500,
    openPositions: 3,
    maxPositions: 10,
    capitalDeployed: 9800,
    totalCapital: 10000,
  });

  useEffect(() => {
    loadRiskMetrics();
  }, []);

  const loadRiskMetrics = async () => {
    try {
      // Fetch open positions
      const { data: positions, error: posError } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('status', 'open');

      if (posError) throw posError;

      if (positions) {
        const totalPositionValue = positions.reduce((sum, pos) => sum + pos.position_value_usdt, 0);
        const openCount = positions.length;

        setMetrics(prev => ({
          ...prev,
          positionSize: totalPositionValue,
          openPositions: openCount,
        }));
      }
    } catch (error) {
      console.error('Error loading risk metrics:', error);
    }
  };

  const getRiskLevel = (value: number, limit: number) => {
    const percentage = (value / limit) * 100;
    if (percentage >= 80) return { label: "High Risk", color: "text-destructive", bg: "bg-destructive/10" };
    if (percentage >= 50) return { label: "Moderate", color: "text-warning", bg: "bg-warning/10" };
    return { label: "Safe", color: "text-success", bg: "bg-success/10" };
  };

  const drawdownRisk = getRiskLevel(metrics.currentDrawdown, metrics.maxDrawdownLimit);
  const positionRisk = getRiskLevel(metrics.positionSize, metrics.maxPositionSize);
  const lossRisk = getRiskLevel(metrics.dailyLoss, metrics.maxDailyLoss);

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-xl font-bold">Risk Management Dashboard</CardTitle>
            <CardDescription>Real-time risk monitoring and position limits</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Risk Overview Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Drawdown Monitor */}
          <div className={`p-4 rounded-lg border ${drawdownRisk.bg} border-border/30`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingDown className={`h-4 w-4 ${drawdownRisk.color}`} />
                <p className="text-sm font-semibold text-foreground">Current Drawdown</p>
              </div>
              <Badge variant="outline" className={drawdownRisk.color}>
                {drawdownRisk.label}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <p className={`text-3xl font-bold font-mono ${drawdownRisk.color}`}>
                  {metrics.currentDrawdown.toFixed(1)}%
                </p>
                <p className="text-sm text-muted-foreground">
                  / {metrics.maxDrawdownLimit}% limit
                </p>
              </div>
              <Progress 
                value={(metrics.currentDrawdown / metrics.maxDrawdownLimit) * 100} 
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Hard stop at 30% drawdown protects capital
              </p>
            </div>
          </div>

          {/* Position Size Monitor */}
          <div className={`p-4 rounded-lg border ${positionRisk.bg} border-border/30`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <DollarSign className={`h-4 w-4 ${positionRisk.color}`} />
                <p className="text-sm font-semibold text-foreground">Position Size</p>
              </div>
              <Badge variant="outline" className={positionRisk.color}>
                {positionRisk.label}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <p className={`text-3xl font-bold font-mono ${positionRisk.color}`}>
                  ${metrics.positionSize.toFixed(0)}
                </p>
                <p className="text-sm text-muted-foreground">
                  / ${metrics.maxPositionSize.toLocaleString()} max
                </p>
              </div>
              <Progress 
                value={(metrics.positionSize / metrics.maxPositionSize) * 100} 
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Maximum per-symbol position limit
              </p>
            </div>
          </div>

          {/* Daily Loss Monitor */}
          <div className={`p-4 rounded-lg border ${lossRisk.bg} border-border/30`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`h-4 w-4 ${lossRisk.color}`} />
                <p className="text-sm font-semibold text-foreground">Daily Loss</p>
              </div>
              <Badge variant="outline" className={lossRisk.color}>
                {lossRisk.label}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <p className={`text-3xl font-bold font-mono ${lossRisk.color}`}>
                  ${metrics.dailyLoss.toFixed(0)}
                </p>
                <p className="text-sm text-muted-foreground">
                  / ${metrics.maxDailyLoss} limit
                </p>
              </div>
              <Progress 
                value={(metrics.dailyLoss / metrics.maxDailyLoss) * 100} 
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Trading halts if limit reached
              </p>
            </div>
          </div>

          {/* Capital Deployment */}
          <div className="p-4 rounded-lg border bg-muted/30 border-border/30">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-primary" />
                <p className="text-sm font-semibold text-foreground">Capital Deployment</p>
              </div>
              <Badge variant="outline" className="text-primary">
                {((metrics.capitalDeployed / metrics.totalCapital) * 100).toFixed(1)}%
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline gap-2">
                <p className="text-3xl font-bold font-mono text-primary">
                  ${metrics.capitalDeployed.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">
                  / ${metrics.totalCapital.toLocaleString()}
                </p>
              </div>
              <Progress 
                value={(metrics.capitalDeployed / metrics.totalCapital) * 100} 
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                98% deployment target (2% reserve)
              </p>
            </div>
          </div>
        </div>

        {/* Open Positions Summary */}
        <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-foreground">Open Positions</h4>
            <Badge variant="outline">
              {metrics.openPositions} / {metrics.maxPositions}
            </Badge>
          </div>
          <Progress 
            value={(metrics.openPositions / metrics.maxPositions) * 100} 
            className="h-2 mb-2"
          />
          <p className="text-xs text-muted-foreground">
            Maximum {metrics.maxPositions} concurrent positions allowed. Currently using {metrics.openPositions} slots.
          </p>
        </div>

        {/* Risk Management Rules */}
        <div className="p-4 bg-background/50 rounded-lg border border-border/30 space-y-3">
          <h4 className="text-sm font-semibold text-foreground">Active Risk Controls</h4>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <div className="h-5 w-5 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <div className="h-2 w-2 rounded-full bg-success" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground">Dynamic Stop-Loss</p>
                <p className="text-xs text-muted-foreground">Volatility-adjusted (2-5% typical)</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="h-5 w-5 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <div className="h-2 w-2 rounded-full bg-success" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground">Kelly Criterion</p>
                <p className="text-xs text-muted-foreground">Safety factor φ = 0.5 reduces variance</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="h-5 w-5 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <div className="h-2 w-2 rounded-full bg-success" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground">Coherence Filtering</p>
                <p className="text-xs text-muted-foreground">Trades only at Γ &gt; 0.945 (high field agreement)</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="h-5 w-5 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <div className="h-2 w-2 rounded-full bg-success" />
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground">Rate Limiting</p>
                <p className="text-xs text-muted-foreground">Maximum 50 trades/day (API constraint)</p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
