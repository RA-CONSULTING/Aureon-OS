import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Rocket, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  AlertTriangle,
  DollarSign,
  TrendingUp,
  Shield
} from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';

interface TradeResult {
  success: boolean;
  orderId?: string;
  symbol?: string;
  side?: string;
  quantity?: number;
  price?: number;
  status?: string;
  error?: string;
  executionId?: string;
}

interface LiveTradingTestPanelProps {
  hasCredentials: boolean;
  userId?: string;
}

export const LiveTradingTestPanel = ({ hasCredentials, userId }: LiveTradingTestPanelProps) => {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TradeResult | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  const MIN_POSITION_USD = 10;

  const fetchCurrentPrice = async (): Promise<number> => {
    const { data, error } = await supabase.functions.invoke('fetch-binance-market-data', {
      body: { symbol: 'BTCUSDT' }
    });
    
    if (error || !data?.price) {
      throw new Error('Failed to fetch current price');
    }
    
    return parseFloat(data.price);
  };

  const executeTestTrade = async () => {
    if (!userId) {
      toast.error('User not authenticated');
      return;
    }

    if (!hasCredentials) {
      toast.error('Please add your Binance API credentials first');
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      // Step 1: Fetch current BTC price
      toast.info('Fetching current BTCUSDT price...');
      const price = await fetchCurrentPrice();
      setCurrentPrice(price);

      // Step 2: Calculate minimum quantity for $10
      const quantity = MIN_POSITION_USD / price;
      const formattedQuantity = parseFloat(quantity.toFixed(6));

      toast.info(`Executing test BUY order: ${formattedQuantity} BTC @ $${price.toFixed(2)}`);

      // Step 3: Execute the trade
      const { data, error } = await supabase.functions.invoke('execute-trade', {
        body: {
          userId,
          symbol: 'BTCUSDT',
          side: 'BUY',
          quantity: formattedQuantity,
          positionSizeUsdt: MIN_POSITION_USD,
          coherence: 0.8, // Test value above threshold
          lighthouseConfidence: 0.7,
          prismLevel: 3,
          isTestTrade: true
        }
      });

      if (error) {
        throw new Error(error.message || 'Trade execution failed');
      }

      if (data?.success) {
        setTestResult({
          success: true,
          orderId: data.orderId,
          symbol: 'BTCUSDT',
          side: 'BUY',
          quantity: formattedQuantity,
          price: price,
          status: data.status || 'FILLED',
          executionId: data.executionId
        });
        toast.success(`Test trade executed! Order ID: ${data.orderId}`);
      } else {
        throw new Error(data?.error || 'Trade execution returned unsuccessful');
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setTestResult({
        success: false,
        error: errorMessage
      });
      toast.error(`Test trade failed: ${errorMessage}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card className="p-6 border-primary/20">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Rocket className="h-5 w-5 text-primary" />
              Live Trading Test
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Execute a $10 minimum test trade to verify the pipeline
            </p>
          </div>
          <Badge variant={hasCredentials ? "default" : "destructive"}>
            {hasCredentials ? 'Ready' : 'Not Ready'}
          </Badge>
        </div>

        {/* Prerequisites */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2 text-sm">
            {hasCredentials ? (
              <CheckCircle2 className="h-4 w-4 text-success" />
            ) : (
              <XCircle className="h-4 w-4 text-destructive" />
            )}
            <span>Binance Credentials</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-success" />
            <span>Edge Function Ready</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="h-4 w-4 text-primary" />
            <span>Min Position: ${MIN_POSITION_USD}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <TrendingUp className="h-4 w-4 text-primary" />
            <span>Symbol: BTCUSDT</span>
          </div>
        </div>

        {/* Safety Warning */}
        <Alert className="border-warning/30 bg-warning/5">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <AlertDescription className="text-warning">
            This will execute a REAL trade on Binance using your credentials.
            Ensure you have at least ${MIN_POSITION_USD} USDT available.
          </AlertDescription>
        </Alert>

        {/* Current Price */}
        {currentPrice && (
          <div className="flex items-center justify-between bg-muted/50 rounded-lg p-3">
            <span className="text-sm text-muted-foreground">Current BTC Price</span>
            <span className="font-mono font-bold">${currentPrice.toLocaleString()}</span>
          </div>
        )}

        {/* Execute Button */}
        <Button
          onClick={executeTestTrade}
          disabled={testing || !hasCredentials}
          className="w-full"
          size="lg"
        >
          {testing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Executing Test Trade...
            </>
          ) : (
            <>
              <Shield className="mr-2 h-4 w-4" />
              Execute $10 Test Trade
            </>
          )}
        </Button>

        {/* Test Result */}
        {testResult && (
          <div className={`rounded-lg p-4 ${
            testResult.success 
              ? 'bg-success/10 border border-success/20' 
              : 'bg-destructive/10 border border-destructive/20'
          }`}>
            <div className="flex items-center gap-2 mb-3">
              {testResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-success" />
              ) : (
                <XCircle className="h-5 w-5 text-destructive" />
              )}
              <span className={`font-semibold ${
                testResult.success ? 'text-success' : 'text-destructive'
              }`}>
                {testResult.success ? 'Trade Executed Successfully!' : 'Trade Failed'}
              </span>
            </div>

            {testResult.success ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Order ID</span>
                  <span className="font-mono">{testResult.orderId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Symbol</span>
                  <span>{testResult.symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Side</span>
                  <Badge variant="default">{testResult.side}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Quantity</span>
                  <span className="font-mono">{testResult.quantity?.toFixed(6)} BTC</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Price</span>
                  <span className="font-mono">${testResult.price?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant="outline" className="text-success border-success">
                    {testResult.status}
                  </Badge>
                </div>
                {testResult.executionId && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Execution ID</span>
                    <span className="font-mono text-xs">{testResult.executionId.slice(0, 8)}...</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-destructive">{testResult.error}</p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
