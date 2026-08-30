import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, TrendingUp, TrendingDown, X } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

interface Position {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  current_price: number;
  quantity: number;
  position_value_usdt: number;
  unrealized_pnl: number;
  stop_loss_price: number;
  take_profit_price: number;
  opened_at: string;
  status: string;
}

export function ActivePositionsPanel() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [closingId, setClosingId] = useState<string | null>(null);
  const { toast } = useToast();

  // Load and subscribe to positions
  useEffect(() => {
    async function loadPositions() {
      const { data } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('status', 'open')
        .order('created_at', { ascending: false });

      if (data) {
        setPositions(data as unknown as Position[]);
      }
      setLoading(false);
    }

    loadPositions();

    // Subscribe to real-time updates
    const channel = supabase
      .channel('active-positions')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'trading_positions' },
        (payload) => {
          if (payload.eventType === 'INSERT') {
            const newPos = payload.new as Position;
            if (newPos.status === 'open') {
              setPositions(prev => [newPos, ...prev]);
            }
          } else if (payload.eventType === 'UPDATE') {
            const updated = payload.new as Position;
            if (updated.status === 'closed') {
              setPositions(prev => prev.filter(p => p.id !== updated.id));
            } else {
              setPositions(prev => prev.map(p => p.id === updated.id ? updated : p));
            }
          } else if (payload.eventType === 'DELETE') {
            setPositions(prev => prev.filter(p => p.id !== (payload.old as any).id));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const closePosition = async (position: Position) => {
    setClosingId(position.id);

    try {
      const { data, error } = await supabase.functions.invoke('close-position', {
        body: { positionId: position.id }
      });

      if (error) throw error;

      toast({
        title: 'Position Closed',
        description: `${position.symbol} closed with P&L: $${data?.pnl?.toFixed(2) || 'N/A'}`,
      });
    } catch (err: any) {
      toast({
        title: 'Failed to close position',
        description: err.message || 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setClosingId(null);
    }
  };

  const totalPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);
  const totalValue = positions.reduce((sum, p) => sum + (p.position_value_usdt || 0), 0);

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span> Active Positions</span>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{positions.length} open</Badge>
            <Badge 
              variant={totalPnl >= 0 ? 'default' : 'destructive'}
              className={totalPnl >= 0 ? 'bg-success' : ''}
            >
              {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)} USD
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No open positions</p>
            <p className="text-sm mt-1">Trades will appear here when executed</p>
          </div>
        ) : (
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {positions.map(position => {
                const pnlPercent = ((position.current_price - position.entry_price) / position.entry_price) * 100 * (position.side === 'LONG' ? 1 : -1);
                const isProfit = pnlPercent >= 0;
                
                return (
                  <div
                    key={position.id}
                    className="p-3 rounded-lg bg-background/50 border border-border/50"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={position.side === 'LONG' ? 'default' : 'destructive'}>
                          {position.side}
                        </Badge>
                        <span className="font-bold">{position.symbol}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => closePosition(position)}
                        disabled={closingId === position.id}
                      >
                        {closingId === position.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <X className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <p className="text-muted-foreground">Entry</p>
                        <p className="font-medium">${position.entry_price.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Current</p>
                        <p className="font-medium">${position.current_price?.toFixed(2) || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">P&L</p>
                        <p className={`font-medium flex items-center gap-1 ${isProfit ? 'text-success' : 'text-destructive'}`}>
                          {isProfit ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                          {pnlPercent.toFixed(2)}%
                        </p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                      <div>
                        <p className="text-muted-foreground">Size</p>
                        <p className="font-medium">${position.position_value_usdt?.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">SL</p>
                        <p className="font-medium text-destructive">${position.stop_loss_price?.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">TP</p>
                        <p className="font-medium text-success">${position.take_profit_price?.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
        
        {positions.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/50 flex justify-between text-sm">
            <span className="text-muted-foreground">Total Exposure</span>
            <span className="font-bold">${totalValue.toFixed(2)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
