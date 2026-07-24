import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { TrendingUp, TrendingDown, AlertCircle, Loader2, Search } from "lucide-react";
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Balance {
  asset: string;
  free: number;
  price: number;
  usdtValue: number;
}

interface TradingSymbol {
  symbol: string;
  baseAsset: string;
  price: number;
  volume24h: number;
  priceChange24h: number;
  minNotional: number;
}

interface QuickTradeProps {
  balances: Balance[];
  canTrade: boolean;
}

export const QuickTrade = ({ balances, canTrade }: QuickTradeProps) => {
  const [symbol, setSymbol] = useState<string>('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [amount, setAmount] = useState<string>('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [allSymbols, setAllSymbols] = useState<TradingSymbol[]>([]);
  const [isLoadingSymbols, setIsLoadingSymbols] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { toast } = useToast();

  // Fetch all available trading symbols on mount
  useEffect(() => {
    fetchAllSymbols();
  }, []);

  const fetchAllSymbols = async () => {
    setIsLoadingSymbols(true);
    try {
      const { data, error } = await supabase.functions.invoke('fetch-binance-symbols');
      
      if (error) throw error;
      if (data.symbols) {
        setAllSymbols(data.symbols);
        console.log(`Loaded ${data.symbols.length} tradable symbols`);
      }
    } catch (error) {
      console.error('Error fetching symbols:', error);
      toast({
        title: "Failed to Load Trading Pairs",
        description: "Using portfolio assets only",
        variant: "destructive",
      });
    } finally {
      setIsLoadingSymbols(false);
    }
  };

  // Combine portfolio assets and all available symbols
  const getAvailableSymbols = () => {
    if (allSymbols.length === 0) {
      // Fallback to portfolio assets only
      return balances
        .filter(b => b.asset !== 'USDT')
        .map(b => ({
          symbol: `${b.asset}USDT`,
          baseAsset: b.asset,
          price: b.price,
          volume24h: 0,
          priceChange24h: 0,
          minNotional: 10,
          inPortfolio: true,
          balance: b.free,
        }));
    }

    // Use all available symbols with portfolio info where available
    return allSymbols.map(s => {
      const portfolioAsset = balances.find(b => b.asset === s.baseAsset);
      return {
        ...s,
        inPortfolio: !!portfolioAsset,
        balance: portfolioAsset?.free || 0,
      };
    });
  };

  const availableSymbols = getAvailableSymbols();

  // Filter symbols based on search query
  const filteredSymbols = searchQuery
    ? availableSymbols.filter(s => 
        s.baseAsset.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.symbol.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : availableSymbols;

  // For SELL, only show assets in portfolio
  const displaySymbols = side === 'SELL' 
    ? filteredSymbols.filter(s => s.inPortfolio && s.balance > 0)
    : filteredSymbols;

  const selectedSymbol = availableSymbols.find(s => s.symbol === symbol);
  const baseAsset = symbol.replace('USDT', '');
  const portfolioBalance = balances.find(b => b.asset === baseAsset);
  const usdtBalance = balances.find(b => b.asset === 'USDT');

  const executeTrade = async () => {
    if (!symbol || !amount || parseFloat(amount) <= 0) {
      toast({
        title: "Invalid Input",
        description: "Please select a symbol and enter a valid amount",
        variant: "destructive",
      });
      return;
    }

    if (!canTrade) {
      toast({
        title: "Trading Disabled",
        description: "Your API key doesn't have trading permissions",
        variant: "destructive",
      });
      return;
    }

    setIsExecuting(true);

    try {
      // Get trading config
      const { data: config } = await supabase
        .from('trading_config')
        .select('*')
        .single();

      if (!config?.is_enabled) {
        throw new Error('Trading is currently disabled in system settings');
      }

      const tradingSymbol = symbol;
      const currentPrice = selectedSymbol?.price || 0;
      
      if (!currentPrice) {
        throw new Error('Unable to fetch current price');
      }

      // Calculate quantity based on amount (in USDT)
      const amountUsdt = parseFloat(amount);
      const quantity = amountUsdt / currentPrice;

      // Validate minimum notional (Binance requires ~$10 minimum)
      const minNotional = selectedSymbol?.minNotional || 10;
      if (amountUsdt < minNotional) {
        throw new Error(`Minimum order value is $${minNotional.toFixed(2)}`);
      }

      // Check if user has enough balance
      if (side === 'SELL') {
        const availableBalance = portfolioBalance?.free || 0;
        if (quantity > availableBalance) {
          throw new Error(`Insufficient ${baseAsset} balance. Available: ${availableBalance.toFixed(6)}`);
        }
      } else {
        // For BUY, check USDT balance
        if (!usdtBalance || amountUsdt > usdtBalance.free) {
          throw new Error(`Insufficient USDT balance. Available: $${usdtBalance?.free.toFixed(2) || 0}`);
        }
      }

      // Create a manual signal first
      const { data: signal, error: signalError } = await supabase
        .from('trading_signals')
        .insert({
          signal_type: side === 'BUY' ? 'LONG' : 'SHORT',
          coherence: 0.85, // Manual trades get high coherence
          lighthouse_value: 0.9,
          prism_level: 4,
          reason: `🎯 Manual ${side} order - ${baseAsset} @ $${currentPrice.toFixed(2)}`,
          strength: 0.8,
        })
        .select()
        .single();

      if (signalError || !signal) {
        throw new Error('Failed to create trading signal');
      }

      // Execute the trade
      const { data, error } = await supabase.functions.invoke('execute-trade', {
        body: {
          signalId: signal.id,
          lighthouseEventId: null,
          symbol: tradingSymbol,
          signalType: side === 'BUY' ? 'LONG' : 'SHORT',
          coherence: 0.85,
          lighthouseValue: 0.9,
          lighthouseConfidence: 0.85,
          prismLevel: 4,
          currentPrice,
        },
      });

      if (error) throw error;
      if (data.error) throw new Error(data.error);

      toast({
        title: "Trade Executed! 🎉",
        description: data.message,
      });

      // Reset form
      setAmount('');
      
    } catch (error) {
      console.error('Trade execution error:', error);
      toast({
        title: "Trade Failed",
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        variant: "destructive",
      });
    } finally {
      setIsExecuting(false);
    }
  };

  if (!canTrade) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardContent className="p-6">
          <div className="flex items-start gap-3 text-center">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-sm">Trading Disabled</p>
              <p className="text-xs text-muted-foreground mt-1">
                Your Binance API key doesn't have trading permissions enabled.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Quick Trade
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="symbol">Trading Pair</Label>
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search symbol (e.g. BTC, ETH, SOL)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger id="symbol">
                <SelectValue placeholder={isLoadingSymbols ? "Loading symbols..." : "Select trading pair"} />
              </SelectTrigger>
              <SelectContent>
                <ScrollArea className="h-[300px]">
                  {displaySymbols.length === 0 ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                      {side === 'SELL' ? 'No assets in portfolio' : 'No trading pairs available'}
                    </div>
                  ) : (
                    displaySymbols.map((sym) => (
                      <SelectItem key={sym.symbol} value={sym.symbol}>
                        <div className="flex items-center justify-between w-full gap-4 pr-4">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold">{sym.baseAsset}</span>
                            {sym.inPortfolio && (
                              <Badge variant="secondary" className="text-xs">Portfolio</Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground text-right">
                            <div className="font-mono">${sym.price?.toFixed(2) || 'N/A'}</div>
                            {sym.priceChange24h !== undefined && (
                              <div className={sym.priceChange24h >= 0 ? 'text-success' : 'text-destructive'}>
                                {sym.priceChange24h >= 0 ? '+' : ''}{sym.priceChange24h?.toFixed(2)}%
                              </div>
                            )}
                          </div>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </ScrollArea>
              </SelectContent>
            </Select>
          </div>
          {isLoadingSymbols && (
            <p className="text-xs text-muted-foreground">Loading {allSymbols.length > 0 ? allSymbols.length : ''} trading pairs...</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Side</Label>
          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant={side === 'BUY' ? 'default' : 'outline'}
              onClick={() => setSide('BUY')}
              className="gap-2"
            >
              <TrendingUp className="h-4 w-4" />
              Buy
            </Button>
            <Button
              type="button"
              variant={side === 'SELL' ? 'default' : 'outline'}
              onClick={() => setSide('SELL')}
              className="gap-2"
            >
              <TrendingDown className="h-4 w-4" />
              Sell
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="amount">Amount (USDT)</Label>
          <Input
            id="amount"
            type="number"
            placeholder="Enter amount in USDT"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            min="0"
            step="0.01"
          />
          {selectedSymbol && amount && parseFloat(amount) > 0 && (
            <div className="text-xs text-muted-foreground mt-1">
              ≈ {(parseFloat(amount) / selectedSymbol.price).toFixed(6)} {baseAsset}
            </div>
          )}
        </div>

        {selectedSymbol && (
          <div className="p-3 rounded-lg bg-muted/50 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Current Price:</span>
              <span className="font-mono font-semibold">${selectedSymbol.price.toFixed(2)}</span>
            </div>
            {selectedSymbol.priceChange24h !== undefined && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">24h Change:</span>
                <span className={`font-mono ${selectedSymbol.priceChange24h >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {selectedSymbol.priceChange24h >= 0 ? '+' : ''}{selectedSymbol.priceChange24h.toFixed(2)}%
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Your Balance:</span>
              <span className="font-mono">
                {portfolioBalance ? `${portfolioBalance.free.toFixed(6)} ${baseAsset}` : `0 ${baseAsset}`}
              </span>
            </div>
            {side === 'BUY' && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">USDT Available:</span>
                <span className="font-mono">
                  ${(usdtBalance?.free || 0).toFixed(2)}
                </span>
              </div>
            )}
            <div className="flex justify-between text-xs pt-2 border-t border-border/50">
              <span className="text-muted-foreground">Min Order:</span>
              <span className="font-mono">${selectedSymbol.minNotional?.toFixed(2) || '10.00'}</span>
            </div>
          </div>
        )}

        <Button
          onClick={executeTrade}
          disabled={isExecuting || !symbol || !amount}
          className="w-full"
          size="lg"
        >
          {isExecuting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Executing Trade...
            </>
          ) : (
            <>
              {side === 'BUY' ? <TrendingUp className="h-4 w-4 mr-2" /> : <TrendingDown className="h-4 w-4 mr-2" />}
              Execute {side} Order
            </>
          )}
        </Button>

        <div className="pt-2 border-t border-border/50">
          <p className="text-xs text-muted-foreground text-center">
            <Badge variant="outline" className="text-xs">Paper Trading Mode</Badge>
            <br />
            Check trading config to enable live trading
          </p>
        </div>
      </CardContent>
    </Card>
  );
};