/**
 * Multi-Exchange Panel
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Displays multi-exchange balances and routing status
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, Zap, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useMultiExchangeBalances } from '@/hooks/useMultiExchangeBalances';
import { ExchangeType, EXCHANGE_FEES } from '@/core/unifiedExchangeClient';

const EXCHANGE_COLORS: Record<ExchangeType, string> = {
  binance: 'text-warning',
  kraken: 'text-primary',
  alpaca: 'text-success',
  capital: 'text-primary',
};

const EXCHANGE_ICONS: Record<ExchangeType, string> = {
  binance: '',
  kraken: '',
  alpaca: '',
  capital: '',
};

export function MultiExchangePanel() {
  const {
    exchangeStatuses,
    consolidatedBalances,
    totalEquityUsd,
    isLoading,
    error,
    refresh,
    lastRoutingDecision
  } = useMultiExchangeBalances();

  const connectedCount = exchangeStatuses.filter(e => e.connected).length;
  const totalExchanges = exchangeStatuses.length;

  return (
    <div className="space-y-4">
      {/* Exchange Status Header */}
      <Card className="bg-card/50 border-primary/20">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary" />
              Multi-Exchange Status
            </CardTitle>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={refresh}
              disabled={isLoading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Connection Status */}
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              {connectedCount === totalExchanges ? (
                <CheckCircle2 className="h-5 w-5 text-success" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-warning" />
              )}
              <span className="text-sm">
                {connectedCount}/{totalExchanges} Exchanges Active
              </span>
            </div>
            <Badge variant={connectedCount === totalExchanges ? 'default' : 'secondary'}>
              ${totalEquityUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })} Total
            </Badge>
          </div>

          {/* Exchange Grid */}
          <div className="grid grid-cols-2 gap-3">
            {exchangeStatuses.map((status) => (
              <div
                key={status.exchange}
                className={`p-3 rounded-lg border ${
                  status.connected 
                    ? 'bg-success/10 border-success/30' 
                    : 'bg-destructive/10 border-destructive/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-lg ${EXCHANGE_COLORS[status.exchange]}`}>
                    {EXCHANGE_ICONS[status.exchange]} {status.exchange.toUpperCase()}
                  </span>
                  <Badge variant={status.connected ? 'default' : 'destructive'} className="text-xs">
                    {status.connected ? 'LIVE' : 'OFFLINE'}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div className="flex justify-between">
                    <span>Balance:</span>
                    <span className="font-mono">
                      ${status.totalUsdValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Fee:</span>
                    <span className="font-mono">
                      {(EXCHANGE_FEES[status.exchange].taker * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Assets:</span>
                    <span className="font-mono">{status.balanceCount}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-3 p-2 rounded bg-destructive/10 border border-destructive/30">
              <p className="text-xs text-destructive">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Consolidated Balances */}
      <Card className="bg-card/50 border-primary/20">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Consolidated Balances
          </CardTitle>
        </CardHeader>
        <CardContent>
          {consolidatedBalances.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No balances found
            </p>
          ) : (
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {consolidatedBalances.slice(0, 10).map((balance) => (
                <div
                  key={balance.asset}
                  className="flex items-center justify-between p-2 rounded bg-background/50"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm">{balance.asset}</span>
                    <div className="flex gap-1">
                      {Object.entries(balance.balances).map(([exchange, bal]) => (
                        (bal.free + bal.locked) > 0 && (
                          <span 
                            key={exchange} 
                            className={`text-xs ${EXCHANGE_COLORS[exchange as ExchangeType]}`}
                            title={`${exchange}: ${(bal.free + bal.locked).toFixed(6)}`}
                          >
                            {EXCHANGE_ICONS[exchange as ExchangeType]}
                          </span>
                        )
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm">
                      {balance.grandTotal.toFixed(6)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      ${balance.usdValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Smart Order Router Status */}
      {lastRoutingDecision && (
        <Card className="bg-card/50 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Zap className="h-5 w-5 text-warning" />
              Last Routing Decision
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Symbol:</span>
                <span className="font-mono">{lastRoutingDecision.bestQuote.symbol}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Best Exchange:</span>
                <span className={EXCHANGE_COLORS[lastRoutingDecision.recommendedExchange]}>
                  {EXCHANGE_ICONS[lastRoutingDecision.recommendedExchange]}{' '}
                  {lastRoutingDecision.recommendedExchange.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Best Price:</span>
                <span className="font-mono text-success">
                  ${lastRoutingDecision.bestQuote.price.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Savings:</span>
                <span className="font-mono text-primary">
                  ${lastRoutingDecision.savings.toFixed(4)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {lastRoutingDecision.reasoning}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
