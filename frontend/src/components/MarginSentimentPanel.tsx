import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { AlertTriangle, TrendingDown, TrendingUp, Activity } from 'lucide-react';
import { useBinanceMarginData } from '@/hooks/useBinanceMarginData';

interface MarginSentimentPanelProps {
  symbol?: string;
}

export function MarginSentimentPanel({ symbol = 'BTC' }: MarginSentimentPanelProps) {
  const { marginData, isLoading, error } = useBinanceMarginData(symbol);

  if (isLoading && !marginData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 animate-pulse" />
            Loading Margin Sentiment...
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Margin Data Error
          </CardTitle>
          <CardDescription>{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!marginData) return null;

  const { crossMargin, recentLiquidations, sentiment } = marginData;
  const healthColor = sentiment.marketHealth > 0.7 ? 'text-success' : 
                      sentiment.marketHealth > 0.4 ? 'text-warning' : 'text-destructive';
  const riskColor = sentiment.leverageRisk < 0.3 ? 'text-success' :
                    sentiment.leverageRisk < 0.6 ? 'text-warning' : 'text-destructive';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Margin Sentiment
          </CardTitle>
          <Badge variant={crossMargin.riskLevel === 'SAFE' ? 'outline' : 'destructive'}>
            {crossMargin.riskLevel}
          </Badge>
        </div>
        <CardDescription>
          Real-time margin market analysis
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Market Health Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Market Health</span>
            <span className={`font-bold ${healthColor}`}>
              {(sentiment.marketHealth * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={sentiment.marketHealth * 100} className="h-2" />
          <p className="text-xs text-muted-foreground">
            {sentiment.marketHealth > 0.7 ? '🟢 Healthy market conditions' :
             sentiment.marketHealth > 0.4 ? '🟡 Moderate market stress' :
             '🔴 High market stress'}
          </p>
        </div>

        {/* Leverage Risk */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Leverage Risk</span>
            <span className={`font-bold ${riskColor}`}>
              {(sentiment.leverageRisk * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={sentiment.leverageRisk * 100} className="h-2" />
          <p className="text-xs text-muted-foreground">
            Margin Level: {crossMargin.marginLevel.toFixed(2)}x
          </p>
        </div>

        {/* Recent Liquidations */}
        <div className="space-y-2 pt-2 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Recent Liquidations</span>
            {recentLiquidations.count > 0 ? (
              <TrendingDown className="h-4 w-4 text-destructive" />
            ) : (
              <TrendingUp className="h-4 w-4 text-success" />
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-muted-foreground">Count</div>
              <div className="font-medium">{recentLiquidations.count}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Volume</div>
              <div className="font-medium">
                ${(recentLiquidations.totalVolume / 1000).toFixed(1)}K
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground">
            Liquidation Pressure: {(sentiment.liquidationPressure * 100).toFixed(0)}%
          </div>
        </div>

        {/* Cross Margin Stats */}
        <div className="space-y-2 pt-2 border-t">
          <div className="text-sm font-medium">Cross Margin Account</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-muted-foreground">Total Assets</div>
              <div className="font-medium">{crossMargin.totalAssetOfBtc.toFixed(4)} BTC</div>
            </div>
            <div>
              <div className="text-muted-foreground">Net Assets</div>
              <div className="font-medium">{crossMargin.totalNetAssetOfBtc.toFixed(4)} BTC</div>
            </div>
          </div>
        </div>

        {/* Trading Signal Impact */}
        <div className="pt-2 border-t">
          <div className="text-xs text-muted-foreground">
            💡 <strong>QGITA Impact:</strong> {
              sentiment.marketHealth > 0.7 && sentiment.leverageRisk < 0.3
                ? 'Bullish bias - healthy margins support upside'
                : sentiment.marketHealth < 0.4 || sentiment.leverageRisk > 0.7
                ? 'Bearish bias - high risk suggests caution'
                : 'Neutral - monitor for changes'
            }
          </div>
        </div>
      </CardContent>
    </Card>
  );
}