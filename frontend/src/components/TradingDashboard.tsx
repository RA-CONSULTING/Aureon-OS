import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';
import { usePositionMonitor } from '@/hooks/usePositionMonitor';

export const TradingDashboard = () => {
  const [executions, setExecutions] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [stats, setStats] = useState({
    totalTrades: 0,
    openPositions: 0,
    totalPnL: 0,
    winRate: 0,
  });

  // Enable position monitoring
  usePositionMonitor(isMonitoring);

  useEffect(() => {
    loadData();
    checkMonitoringStatus();

    // Subscribe to realtime updates
    const channel = supabase
      .channel('trading_updates')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trading_executions' }, loadData)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trading_positions' }, loadData)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const checkMonitoringStatus = async () => {
    const { data } = await supabase
      .from('trading_config')
      .select('is_enabled')
      .single();
    
    setIsMonitoring(data?.is_enabled || false);
  };

  const loadData = async () => {
    // Load executions
    const { data: execData } = await supabase
      .from('trading_executions')
      .select('*')
      .order('executed_at', { ascending: false })
      .limit(10);

    // Load positions
    const { data: posData } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('status', 'open')
      .order('opened_at', { ascending: false });

    setExecutions(execData || []);
    setPositions(posData || []);

    // Calculate stats
    const totalTrades = execData?.length || 0;
    const openPositions = posData?.length || 0;
    const totalPnL = posData?.reduce((sum, pos) => sum + (Number(pos.unrealized_pnl) || 0), 0) || 0;
    const successfulTrades = execData?.filter(e => e.status === 'filled').length || 0;
    const winRate = totalTrades > 0 ? (successfulTrades / totalTrades) * 100 : 0;

    setStats({ totalTrades, openPositions, totalPnL, winRate });
  };

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold">{stats.totalTrades}</p>
            </div>
            <Activity className="h-8 w-8 text-primary" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Open Positions</p>
              <p className="text-2xl font-bold">{stats.openPositions}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-success" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total P&L</p>
              <p className={`text-2xl font-bold ${stats.totalPnL >= 0 ? 'text-success' : 'text-destructive'}`}>
                ${stats.totalPnL.toFixed(2)}
              </p>
            </div>
            <DollarSign className="h-8 w-8 text-warning" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold">{stats.winRate.toFixed(1)}%</p>
            </div>
            <TrendingUp className="h-8 w-8 text-primary" />
          </div>
        </Card>
      </div>

      {/* Open Positions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Open Positions</h3>
        {positions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No open positions</p>
        ) : (
          <div className="space-y-2">
            {positions.map((pos) => (
              <div key={pos.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{pos.symbol}</span>
                    <Badge variant={pos.side === 'LONG' ? 'default' : 'destructive'}>
                      {pos.side}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Entry: ${parseFloat(pos.entry_price).toFixed(2)} | Qty: {parseFloat(pos.quantity).toFixed(8)}
                  </p>
                  {pos.current_price && (
                    <p className="text-sm text-muted-foreground">
                      Current: ${parseFloat(pos.current_price).toFixed(2)}
                    </p>
                  )}
                  {(pos.stop_loss_price || pos.take_profit_price) && (
                    <p className="text-xs text-muted-foreground">
                      {pos.stop_loss_price && `SL: $${parseFloat(pos.stop_loss_price).toFixed(2)}`}
                      {pos.stop_loss_price && pos.take_profit_price && ' | '}
                      {pos.take_profit_price && `TP: $${parseFloat(pos.take_profit_price).toFixed(2)}`}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className={`font-bold ${parseFloat(pos.unrealized_pnl) >= 0 ? 'text-success' : 'text-destructive'}`}>
                    ${parseFloat(pos.unrealized_pnl || 0).toFixed(2)}
                  </p>
                  <p className="text-xs text-muted-foreground">Unrealized P&L</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Recent Executions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Executions</h3>
        {executions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No executions yet</p>
        ) : (
          <div className="space-y-2">
            {executions.map((exec) => (
              <div key={exec.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{exec.symbol}</span>
                    <Badge variant={exec.side === 'BUY' ? 'default' : 'destructive'}>
                      {exec.side}
                    </Badge>
                    <Badge variant="outline">{exec.status}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {parseFloat(exec.quantity).toFixed(8)} @ ${parseFloat(exec.executed_price || exec.price).toFixed(2)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">${parseFloat(exec.position_size_usdt).toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(exec.executed_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
