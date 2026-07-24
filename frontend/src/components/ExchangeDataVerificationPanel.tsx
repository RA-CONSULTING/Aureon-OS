import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle2, XCircle, RefreshCw, Wifi, WifiOff, Radio } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';

interface ExchangeStatus {
  exchange: string;
  status: 'LIVE' | 'DEMO' | 'OFFLINE' | 'ERROR';
  hasCredentials: boolean;
  lastPrice?: number;
  lastTimestamp?: number;
  latencyMs?: number;
  errorMessage?: string;
}

interface VerificationResult {
  success: boolean;
  timestamp: number;
  exchanges: ExchangeStatus[];
  overallStatus: 'ALL_LIVE' | 'PARTIAL_LIVE' | 'ALL_DEMO' | 'OFFLINE';
  priceVariance?: number;
  warnings: string[];
}

export const ExchangeDataVerificationPanel: React.FC = () => {
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);

  const runVerification = async () => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.functions.invoke('verify-exchange-connectivity');
      
      if (error) throw error;
      
      setVerification(data);
      setLastCheck(new Date());
    } catch (error) {
      console.error('Verification failed:', error);
      setVerification({
        success: false,
        timestamp: Date.now(),
        exchanges: [],
        overallStatus: 'OFFLINE',
        warnings: ['Failed to verify exchange connectivity'],
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    runVerification();
    // Auto-refresh every 30 seconds
    const interval = setInterval(runVerification, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: ExchangeStatus['status']) => {
    switch (status) {
      case 'LIVE':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'DEMO':
        return <Radio className="h-4 w-4 text-warning animate-pulse" />;
      case 'OFFLINE':
        return <WifiOff className="h-4 w-4 text-destructive" />;
      case 'ERROR':
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  const getStatusBadge = (status: ExchangeStatus['status']) => {
    switch (status) {
      case 'LIVE':
        return <Badge className="bg-success/20 text-success border-success/50">LIVE</Badge>;
      case 'DEMO':
        return <Badge className="bg-warning/20 text-warning border-warning/50 animate-pulse">DEMO</Badge>;
      case 'OFFLINE':
        return <Badge variant="destructive">OFFLINE</Badge>;
      case 'ERROR':
        return <Badge variant="destructive">ERROR</Badge>;
    }
  };

  const getOverallStatusBadge = () => {
    if (!verification) return null;
    
    switch (verification.overallStatus) {
      case 'ALL_LIVE':
        return (
          <Badge className="bg-success/20 text-success border-success/50 text-lg px-4 py-1">
            <Wifi className="h-4 w-4 mr-2" />
            ALL EXCHANGES LIVE
          </Badge>
        );
      case 'PARTIAL_LIVE':
        return (
          <Badge className="bg-warning/20 text-warning border-warning/50 text-lg px-4 py-1">
            <AlertTriangle className="h-4 w-4 mr-2" />
            PARTIAL LIVE DATA
          </Badge>
        );
      case 'ALL_DEMO':
        return (
          <Badge className="bg-warning/20 text-warning border-warning/50 text-lg px-4 py-1 animate-pulse">
            <Radio className="h-4 w-4 mr-2" />
            ⚠️ ALL DEMO MODE
          </Badge>
        );
      case 'OFFLINE':
        return (
          <Badge variant="destructive" className="text-lg px-4 py-1">
            <WifiOff className="h-4 w-4 mr-2" />
            OFFLINE
          </Badge>
        );
    }
  };

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Wifi className="h-5 w-5 text-primary" />
            Exchange Data Verification
          </CardTitle>
          <div className="flex items-center gap-2">
            {getOverallStatusBadge()}
            <Button
              variant="ghost"
              size="sm"
              onClick={runVerification}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        {lastCheck && (
          <p className="text-xs text-muted-foreground">
            Last verified: {lastCheck.toLocaleTimeString()}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Exchange Status Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {verification?.exchanges.map((exchange) => (
            <div
              key={exchange.exchange}
              className={`p-3 rounded-lg border ${
                exchange.status === 'LIVE'
                  ? 'border-success/30 bg-success/5'
                  : exchange.status === 'DEMO'
                  ? 'border-warning/30 bg-warning/5'
                  : 'border-destructive/30 bg-destructive/5'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold uppercase text-sm">
                  {exchange.exchange}
                </span>
                {getStatusIcon(exchange.status)}
              </div>
              {getStatusBadge(exchange.status)}
              
              {exchange.lastPrice && (
                <p className="text-xs text-muted-foreground mt-2">
                  BTC: ${exchange.lastPrice.toLocaleString()}
                </p>
              )}
              {exchange.latencyMs !== undefined && (
                <p className="text-xs text-muted-foreground">
                  Latency: {exchange.latencyMs}ms
                </p>
              )}
              {exchange.errorMessage && (
                <p className="text-xs text-destructive mt-1 truncate" title={exchange.errorMessage}>
                  {exchange.errorMessage}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Warnings */}
        {verification?.warnings && verification.warnings.length > 0 && (
          <div className="space-y-2">
            {verification.warnings.map((warning, index) => (
              <div
                key={index}
                className="flex items-start gap-2 p-2 rounded bg-warning/10 border border-warning/30"
              >
                <AlertTriangle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                <span className="text-sm text-warning">{warning}</span>
              </div>
            ))}
          </div>
        )}

        {/* Price Variance */}
        {verification?.priceVariance !== undefined && verification.priceVariance > 0 && (
          <div className={`p-2 rounded border ${
            verification.priceVariance > 5 
              ? 'border-destructive/30 bg-destructive/5' 
              : 'border-success/30 bg-success/5'
          }`}>
            <p className="text-sm">
              <span className="text-muted-foreground">Cross-Exchange Price Variance: </span>
              <span className={verification.priceVariance > 5 ? 'text-destructive' : 'text-success'}>
                {verification.priceVariance.toFixed(3)}%
              </span>
            </p>
          </div>
        )}

        {/* Trading Safety Indicator */}
        <div className={`p-3 rounded-lg border ${
          verification?.overallStatus === 'ALL_LIVE'
            ? 'border-success/50 bg-success/10'
            : verification?.overallStatus === 'ALL_DEMO'
            ? 'border-warning/50 bg-warning/10'
            : 'border-destructive/50 bg-destructive/10'
        }`}>
          <div className="flex items-center gap-2">
            {verification?.overallStatus === 'ALL_LIVE' ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-success" />
                <span className="text-success font-semibold">SAFE FOR LIVE TRADING</span>
              </>
            ) : verification?.overallStatus === 'PARTIAL_LIVE' ? (
              <>
                <AlertTriangle className="h-5 w-5 text-warning" />
                <span className="text-warning font-semibold">PARTIAL DATA - TRADE WITH CAUTION</span>
              </>
            ) : verification?.overallStatus === 'ALL_DEMO' ? (
              <>
                <Radio className="h-5 w-5 text-warning animate-pulse" />
                <span className="text-warning font-semibold">⚠️ SIMULATED DATA ONLY - NOT REAL</span>
              </>
            ) : (
              <>
                <XCircle className="h-5 w-5 text-destructive" />
                <span className="text-destructive font-semibold">TRADING BLOCKED - NO DATA</span>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
