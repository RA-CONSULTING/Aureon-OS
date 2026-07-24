import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Calculator, TrendingUp, AlertTriangle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export function KellyCriterionCalculator() {
  const [winRate, setWinRate] = useState(61.3);
  const [avgWin, setAvgWin] = useState(3.24);
  const [avgLoss, setAvgLoss] = useState(1.79);
  const [safetyFactor, setSafetyFactor] = useState(0.5);
  const [capital, setCapital] = useState(10000);

  const [kellyPercent, setKellyPercent] = useState(0);
  const [adjustedPercent, setAdjustedPercent] = useState(0);
  const [positionSize, setPositionSize] = useState(0);

  useEffect(() => {
    // Kelly Criterion: f* = (p·b - (1-p)) / b
    // where p = win probability, b = win/loss ratio
    const p = winRate / 100;
    const b = avgWin / avgLoss;
    
    const kelly = (p * b - (1 - p)) / b;
    const kellyPct = Math.max(0, Math.min(kelly * 100, 100)); // Clamp 0-100%
    
    const adjusted = kellyPct * safetyFactor;
    const position = capital * (adjusted / 100);

    setKellyPercent(kellyPct);
    setAdjustedPercent(adjusted);
    setPositionSize(position);
  }, [winRate, avgWin, avgLoss, safetyFactor, capital]);

  const getRiskLevel = () => {
    if (adjustedPercent < 10) return { label: "Conservative", color: "text-success" };
    if (adjustedPercent < 25) return { label: "Moderate", color: "text-warning" };
    return { label: "Aggressive", color: "text-destructive" };
  };

  const riskLevel = getRiskLevel();

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-xl font-bold">Kelly Criterion Calculator</CardTitle>
            <CardDescription>Optimal position sizing for risk-adjusted returns</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Input Parameters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="capital">Total Capital ($)</Label>
            <Input
              id="capital"
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className="font-mono"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="winRate">Win Rate (%)</Label>
            <Input
              id="winRate"
              type="number"
              value={winRate}
              onChange={(e) => setWinRate(Number(e.target.value))}
              min="0"
              max="100"
              step="0.1"
              className="font-mono"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="avgWin">Average Win (%)</Label>
            <Input
              id="avgWin"
              type="number"
              value={avgWin}
              onChange={(e) => setAvgWin(Number(e.target.value))}
              min="0"
              step="0.01"
              className="font-mono"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="avgLoss">Average Loss (%)</Label>
            <Input
              id="avgLoss"
              type="number"
              value={avgLoss}
              onChange={(e) => setAvgLoss(Number(e.target.value))}
              min="0"
              step="0.01"
              className="font-mono"
            />
          </div>
        </div>

        {/* Safety Factor Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>Safety Factor (φ)</Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="outline" className="font-mono">
                    {safetyFactor.toFixed(2)}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">Reduces Kelly fraction to control variance</p>
                  <p className="text-xs text-muted-foreground">Typical: 0.25-0.5</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Slider
            value={[safetyFactor]}
            onValueChange={([value]) => setSafetyFactor(value)}
            min={0.1}
            max={1}
            step={0.05}
            className="w-full"
          />
        </div>

        {/* Results */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/30 rounded-lg border border-border/30">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Full Kelly %</p>
            <p className="text-2xl font-bold font-mono text-foreground">
              {kellyPercent.toFixed(2)}%
            </p>
          </div>
          
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground">Adjusted %</p>
              <Badge variant="outline" className={riskLevel.color}>
                {riskLevel.label}
              </Badge>
            </div>
            <p className="text-2xl font-bold font-mono text-primary">
              {adjustedPercent.toFixed(2)}%
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Position Size</p>
            <p className="text-2xl font-bold font-mono text-foreground">
              ${positionSize.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Formula Display */}
        <div className="p-4 bg-background/50 rounded-lg border border-border/30 space-y-2">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">Formula</p>
          </div>
          <p className="text-xs font-mono text-muted-foreground">
            f* = (p·b - (1-p)) / b · φ
          </p>
          <p className="text-xs text-muted-foreground">
            Where p = {(winRate/100).toFixed(3)}, b = {(avgWin/avgLoss).toFixed(3)} (win/loss ratio), φ = {safetyFactor}
          </p>
        </div>

        {/* Warning for high allocation */}
        {adjustedPercent > 30 && (
          <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold text-destructive">High Risk Allocation</p>
              <p className="text-muted-foreground">Position size exceeds 30% of capital. Consider reducing safety factor or capital allocation.</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
