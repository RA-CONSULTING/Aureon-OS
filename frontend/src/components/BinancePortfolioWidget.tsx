import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Wallet, RefreshCw, AlertCircle, TrendingUp, CheckCircle, XCircle, PieChart, List, Settings } from "lucide-react";
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

interface Balance {
  asset: string;
  total: number;
  usdtValue: number;
}

interface PortfolioData {
  balances: Balance[];
  totalUSDT: number;
  totalBTC: number;
  canTrade: boolean;
  fetchedAt: string;
}

export const BinancePortfolioWidget = () => {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchPortfolio = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Get the current session to pass auth token
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('Please sign in to view your portfolio');
      }

      const { data, error: functionError } = await supabase.functions.invoke('fetch-binance-portfolio', {
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });

      if (functionError) throw functionError;
      if (data.error) throw new Error(data.error);

      setPortfolio(data);
      toast({
        title: "Portfolio Synced",
        description: `Live data from your Binance account`,
        duration: 2000,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch portfolio';
      setError(errorMessage);
      
      // Show helpful error messages
      let errorDescription = errorMessage;
      if (errorMessage.includes('credentials not configured') || errorMessage.includes('add your API credentials')) {
        errorDescription = 'Please add your Binance API credentials in account settings to view your portfolio.';
      }
      
      toast({
        title: "Portfolio Sync Failed",
        description: errorDescription,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const topHoldings = portfolio?.balances
    .filter(b => b.usdtValue > 1)
    .sort((a, b) => b.usdtValue - a.usdtValue)
    .slice(0, 5) || [];

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Binance Portfolio</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchPortfolio}
            disabled={isLoading}
            className="h-8 w-8 p-0"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error && !portfolio && (
          <div className="flex items-start gap-2 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0 space-y-2">
              <p className="text-sm font-semibold text-destructive">
                {error.includes('IP restriction') ? 'Binance IP Restriction Detected' : 'Portfolio Unavailable'}
              </p>
              
              {error.includes('IP restriction') ? (
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">Your Binance API key has IP restrictions enabled. Fix this in 3 steps:</p>
                  <ol className="list-decimal list-inside space-y-1 ml-1">
                    <li>Go to <a href="https://www.binance.com/en/my/settings/api-management" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">Binance API Management</a></li>
                    <li>Click "Edit" on your API key</li>
                    <li>Set "Restrict access to trusted IPs only" to <strong className="text-foreground">OFF (Unrestricted)</strong></li>
                  </ol>
                  <p className="text-xs text-muted-foreground mt-2 pt-2 border-t border-border/50">
                    Note: Lovable Cloud uses dynamic IPs, so IP whitelisting is not possible.
                  </p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">{error}</p>
              )}
              
              {error.includes('credentials') && (
                <Button 
                  variant="link" 
                  size="sm" 
                  className="h-auto p-0 mt-2 text-xs"
                  onClick={() => window.location.href = '/settings'}
                >
                  Add Binance API Credentials →
                </Button>
              )}
            </div>
          </div>
        )}

        {isLoading && !portfolio && (
          <div className="text-center py-12">
            <RefreshCw className="h-8 w-8 mx-auto mb-2 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">Connecting to your Binance account...</p>
          </div>
        )}

        {portfolio && (
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <PieChart className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="holdings" className="flex items-center gap-2">
                <List className="h-4 w-4" />
                Holdings
              </TabsTrigger>
              <TabsTrigger value="account" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Account
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                  <p className="text-xs text-muted-foreground mb-1">Total Value</p>
                  <p className="text-2xl font-bold text-foreground">
                    {formatCurrency(portfolio.totalUSDT)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-secondary/5 border border-secondary/10">
                  <p className="text-xs text-muted-foreground mb-1">BTC Value</p>
                  <p className="text-lg font-semibold text-foreground">
                    {portfolio.totalBTC.toFixed(6)} BTC
                  </p>
                </div>
              </div>

              {topHoldings.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-foreground">Top 5 Holdings</p>
                  <div className="space-y-2">
                    {topHoldings.map((balance) => (
                      <div key={balance.asset} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                        <div className="flex items-center gap-3">
                          <Badge variant="secondary" className="font-mono text-xs">
                            {balance.asset}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {balance.total < 1 ? balance.total.toFixed(6) : balance.total.toFixed(4)}
                          </span>
                        </div>
                        <span className="text-sm font-semibold">
                          {formatCurrency(balance.usdtValue)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="holdings" className="space-y-3 mt-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-foreground">All Assets ({portfolio.balances.length})</p>
                <p className="text-xs text-muted-foreground">Showing balances &gt; $1</p>
              </div>
              <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                {portfolio.balances
                  .filter(b => b.usdtValue > 1)
                  .sort((a, b) => b.usdtValue - a.usdtValue)
                  .map((balance) => (
                    <div key={balance.asset} className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                      <div className="flex flex-col gap-1">
                        <Badge variant="outline" className="font-mono text-xs w-fit">
                          {balance.asset}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {balance.total < 1 ? balance.total.toFixed(6) : balance.total.toFixed(4)} {balance.asset}
                        </span>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">
                          {formatCurrency(balance.usdtValue)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {((balance.usdtValue / portfolio.totalUSDT) * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </TabsContent>

            <TabsContent value="account" className="space-y-4 mt-4">
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 mb-3">
                    {portfolio.canTrade ? (
                      <>
                        <CheckCircle className="h-5 w-5 text-success" />
                        <span className="text-sm font-medium">Trading Enabled</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-5 w-5 text-destructive" />
                        <span className="text-sm font-medium">Trading Disabled</span>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {portfolio.canTrade 
                      ? 'Your API key has trading permissions enabled.'
                      : 'Your API key does not have trading permissions. Enable them in Binance API Management.'}
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-muted/50 space-y-2">
                  <p className="text-sm font-medium">Account Statistics</p>
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div>
                      <p className="text-xs text-muted-foreground">Total Assets</p>
                      <p className="text-lg font-semibold">{portfolio.balances.length}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Active Holdings</p>
                      <p className="text-lg font-semibold">
                        {portfolio.balances.filter(b => b.usdtValue > 1).length}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground mb-1">Last Updated</p>
                  <p className="text-sm font-medium">
                    {new Date(portfolio.fetchedAt).toLocaleString()}
                  </p>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
};
