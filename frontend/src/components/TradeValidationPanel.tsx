import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RefreshCw, CheckCircle, Clock, XCircle, AlertTriangle, Activity } from 'lucide-react';
import { useTradeValidation } from '@/hooks/useTradeValidation';

interface TradeValidationPanelProps {
  className?: string;
  compact?: boolean;
}

export function TradeValidationPanel({ className, compact = false }: TradeValidationPanelProps) {
  const {
    trades,
    stats,
    isLoading,
    lastPolled,
    pollConfirmations,
    filterByStatus,
    getPendingTrades,
    getRecentTrades,
  } = useTradeValidation();

  const [isPolling, setIsPolling] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  const handlePoll = async () => {
    setIsPolling(true);
    try {
      await pollConfirmations();
    } catch (error) {
      console.error('Poll failed:', error);
    } finally {
      setIsPolling(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'confirmed':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-warning animate-pulse" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-destructive" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'FILLED':
        return 'bg-success/20 text-success';
      case 'PARTIALLY_FILLED':
        return 'bg-primary/20 text-primary';
      case 'ORDER_SUBMITTED':
        return 'bg-warning/20 text-warning';
      case 'ORDER_CONFIRMED':
        return 'bg-primary/20 text-primary';
      case 'FAILED':
      case 'CANCELED':
        return 'bg-destructive/20 text-destructive';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const displayTrades = activeTab === 'all' 
    ? getRecentTrades(compact ? 5 : 20)
    : filterByStatus(activeTab);

  const pendingCount = getPendingTrades().length;

  if (compact) {
    return (
      <Card className={className}>
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Trade Validation
            </CardTitle>
            <div className="flex items-center gap-2">
              {pendingCount > 0 && (
                <Badge variant="outline" className="bg-warning/20 text-warning">
                  {pendingCount} pending
                </Badge>
              )}
              <Badge variant="outline">
                {stats.confirmationRate.toFixed(0)}% confirmed
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="py-2">
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-success" />
              {stats.confirmed}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-warning" />
              {stats.pending}
            </span>
            <span className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-destructive" />
              {stats.failed}
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Trade Validation
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handlePoll}
            disabled={isPolling || isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isPolling ? 'animate-spin' : ''}`} />
            {isPolling ? 'Polling...' : 'Poll Confirmations'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Stats Summary */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="bg-muted/50 rounded-lg p-3 text-center">
            <div className="text-2xl font-semibold">{stats.total}</div>
            <div className="text-xs text-muted-foreground">Total</div>
          </div>
          <div className="bg-success/10 rounded-lg p-3 text-center">
            <div className="text-2xl font-semibold text-success">{stats.confirmed}</div>
            <div className="text-xs text-muted-foreground">Confirmed</div>
          </div>
          <div className="bg-warning/10 rounded-lg p-3 text-center">
            <div className="text-2xl font-semibold text-warning">{stats.pending}</div>
            <div className="text-xs text-muted-foreground">Pending</div>
          </div>
          <div className="bg-destructive/10 rounded-lg p-3 text-center">
            <div className="text-2xl font-semibold text-destructive">{stats.failed}</div>
            <div className="text-xs text-muted-foreground">Failed</div>
          </div>
        </div>

        {/* Confirmation Rate */}
        <div className="mb-4 p-3 bg-muted/30 rounded-lg">
          <div className="flex justify-between items-center text-sm mb-1">
            <span>Confirmation Rate</span>
            <span className="font-semibold">{stats.confirmationRate.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-success transition-all"
              style={{ width: `${stats.confirmationRate}%` }}
            />
          </div>
          {stats.avgConfirmationTime > 0 && (
            <div className="text-xs text-muted-foreground mt-1">
              Avg confirmation: {stats.avgConfirmationTime.toFixed(1)}s
            </div>
          )}
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="confirmed">Confirmed</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab}>
            <ScrollArea className="h-[300px]">
              {displayTrades.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No trades found
                </div>
              ) : (
                <div className="space-y-2">
                  {displayTrades.map((trade) => (
                    <div
                      key={trade.id}
                      className="p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(trade.validationStatus)}
                          <span className="font-mono font-medium">{trade.symbol}</span>
                          <Badge variant="outline" className={getStageColor(trade.stage)}>
                            {trade.stage}
                          </Badge>
                        </div>
                        <Badge variant="outline" className="capitalize">
                          {trade.exchange}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Order ID: </span>
                          <span className="font-mono">{trade.externalOrderId?.slice(-8) || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Side: </span>
                          <span className={trade.side === 'BUY' ? 'text-success' : 'text-destructive'}>
                            {trade.side}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Qty: </span>
                          <span>{trade.executedQty || trade.quantity}</span>
                        </div>
                      </div>

                      {trade.executedPrice && (
                        <div className="text-xs mt-1">
                          <span className="text-muted-foreground">Executed @ </span>
                          <span className="font-mono">${trade.executedPrice.toLocaleString()}</span>
                          {trade.commission && (
                            <span className="text-muted-foreground ml-2">
                              Fee: {trade.commission} {trade.commissionAsset}
                            </span>
                          )}
                        </div>
                      )}

                      {trade.validationMessage && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {trade.validationMessage}
                        </div>
                      )}

                      <div className="text-xs text-muted-foreground mt-1">
                        {new Date(trade.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>

        {lastPolled && (
          <div className="text-xs text-muted-foreground text-center mt-4">
            Last polled: {lastPolled.toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
