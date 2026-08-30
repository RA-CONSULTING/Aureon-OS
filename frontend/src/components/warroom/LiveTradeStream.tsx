import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { supabase } from '@/integrations/supabase/client';
import { ArrowUpCircle, ArrowDownCircle, Clock, Zap } from 'lucide-react';

interface TradeExecution {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  status: string;
  exchange: string;
  pnl?: number;
  created_at: string;
}

export function LiveTradeStream() {
  const [trades, setTrades] = useState<TradeExecution[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Load recent trades
    const loadTrades = async () => {
      const { data, error } = await supabase
        .from('trading_executions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(20);

      if (!error && data) {
        setTrades(data.map(t => ({
          id: t.id,
          symbol: t.symbol,
          side: t.side as 'BUY' | 'SELL',
          quantity: t.quantity,
          price: t.executed_price || t.price,
          status: t.status,
          exchange: 'binance',
          pnl: undefined,
          created_at: t.created_at,
        })));
      }
    };

    loadTrades();

    // Subscribe to real-time trades
    const channel = supabase
      .channel('trading-executions-stream')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'trading_executions',
        },
        (payload) => {
          const newTrade = payload.new as any;
          setTrades(prev => [{
            id: newTrade.id,
            symbol: newTrade.symbol,
            side: newTrade.side,
            quantity: newTrade.quantity,
            price: newTrade.price,
            status: newTrade.status,
            exchange: newTrade.exchange || 'binance',
            pnl: newTrade.pnl,
            created_at: newTrade.created_at,
          }, ...prev.slice(0, 19)]);
        }
      )
      .subscribe((status) => {
        setIsConnected(status === 'SUBSCRIBED');
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-lg">
          <span className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-warning" />
            Live Trade Stream
          </span>
          <Badge variant={isConnected ? 'default' : 'secondary'} className={isConnected ? 'bg-success' : ''}>
            {isConnected ? ' LIVE' : ' OFFLINE'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px]">
          {trades.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Clock className="h-8 w-8 mb-2" />
              <p>No trades executed yet</p>
              <p className="text-xs">Trades will appear here in real-time</p>
            </div>
          ) : (
            <div className="space-y-2">
              {trades.map((trade) => (
                <div
                  key={trade.id}
                  className={`p-3 rounded-lg border ${
                    trade.side === 'BUY' 
                      ? 'bg-success/10 border-success/30' 
                      : 'bg-destructive/10 border-destructive/30'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {trade.side === 'BUY' ? (
                        <ArrowUpCircle className="h-5 w-5 text-success" />
                      ) : (
                        <ArrowDownCircle className="h-5 w-5 text-destructive" />
                      )}
                      <span className="font-bold">{trade.symbol}</span>
                      <Badge variant="outline" className="text-xs">
                        {trade.exchange}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatTime(trade.created_at)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1 text-sm">
                    <span>
                      {trade.side} {trade.quantity.toFixed(6)} @ ${trade.price.toFixed(2)}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={trade.status === 'filled' ? 'default' : 'secondary'}
                        className={trade.status === 'filled' ? 'bg-success' : ''}
                      >
                        {trade.status}
                      </Badge>
                      {trade.pnl !== undefined && trade.pnl !== null && (
                        <span className={trade.pnl >= 0 ? 'text-success' : 'text-destructive'}>
                          {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
