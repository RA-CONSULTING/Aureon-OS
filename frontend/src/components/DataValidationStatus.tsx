/**
 * Data Validation Status Component
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Displays real-time data validation status for all exchanges
 */

import React from 'react';
import { Activity, AlertTriangle, CheckCircle, XCircle, Clock, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  getExchangeStatuses, 
  getDataHealthScore, 
  hasStaleData,
  type ExchangeValidationStatus 
} from '@/core/marketDataValidator';

interface DataValidationStatusProps {
  className?: string;
  compact?: boolean;
}

export function DataValidationStatus({ className = '', compact = false }: DataValidationStatusProps) {
  const [statuses, setStatuses] = React.useState<ExchangeValidationStatus[]>([]);
  const [health, setHealth] = React.useState<{ score: number; status: 'healthy' | 'degraded' | 'critical' }>({ score: 0, status: 'critical' });
  const [hasStale, setHasStale] = React.useState(false);

  // Update status every second
  React.useEffect(() => {
    const update = () => {
      setStatuses(getExchangeStatuses());
      setHealth(getDataHealthScore());
      setHasStale(hasStaleData());
    };
    
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: 'healthy' | 'degraded' | 'critical') => {
    switch (status) {
      case 'healthy': return 'text-success';
      case 'degraded': return 'text-warning';
      case 'critical': return 'text-destructive';
    }
  };

  const getStatusIcon = (status: 'healthy' | 'degraded' | 'critical') => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4 text-success" />;
      case 'degraded': return <AlertTriangle className="w-4 h-4 text-warning" />;
      case 'critical': return <XCircle className="w-4 h-4 text-destructive" />;
    }
  };

  const formatTimestamp = (ts: number) => {
    if (!ts) return 'Never';
    const ago = Date.now() - ts;
    if (ago < 1000) return 'Just now';
    if (ago < 60000) return `${Math.floor(ago / 1000)}s ago`;
    if (ago < 3600000) return `${Math.floor(ago / 60000)}m ago`;
    return `${Math.floor(ago / 3600000)}h ago`;
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        {getStatusIcon(health.status)}
        <span className={`text-xs font-mono ${getStatusColor(health.status)}`}>
          DATA {health.status.toUpperCase()}
        </span>
        {hasStale && (
          <Badge variant="outline" className="text-warning border-warning/50 text-[10px] px-1">
            STALE
          </Badge>
        )}
      </div>
    );
  }

  return (
    <Card className={`bg-background/50 border-border/50 ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Data Validation Status
          {getStatusIcon(health.status)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Overall Health */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Health Score</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-background rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-500 ${
                  health.status === 'healthy' ? 'bg-success' :
                  health.status === 'degraded' ? 'bg-warning' : 'bg-destructive'
                }`}
                style={{ width: `${health.score * 100}%` }}
              />
            </div>
            <span className={`text-xs font-mono ${getStatusColor(health.status)}`}>
              {(health.score * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Exchange Status List */}
        <div className="space-y-2">
          {statuses.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-2">
              No data streams active
            </div>
          ) : (
            statuses.map(status => (
              <div 
                key={status.exchange}
                className="flex items-center justify-between p-2 bg-background/30 rounded border border-border/30"
              >
                <div className="flex items-center gap-2">
                  {status.isStale ? (
                    <Clock className="w-3 h-3 text-warning" />
                  ) : status.consecutiveErrors > 0 ? (
                    <XCircle className="w-3 h-3 text-destructive" />
                  ) : (
                    <Zap className="w-3 h-3 text-success" />
                  )}
                  <span className="text-xs font-medium uppercase">{status.exchange}</span>
                </div>
                
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>
                    ${status.lastPrice?.toLocaleString(undefined, { maximumFractionDigits: 2 }) || '—'}
                  </span>
                  <span>{formatTimestamp(status.lastValidTimestamp)}</span>
                  {status.errorCount > 0 && (
                    <Badge variant="outline" className="text-destructive border-destructive/50 text-[10px] px-1">
                      {status.errorCount} err
                    </Badge>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Stale Data Warning */}
        {hasStale && (
          <div className="flex items-center gap-2 p-2 bg-warning/10 rounded border border-warning/30">
            <AlertTriangle className="w-4 h-4 text-warning" />
            <span className="text-xs text-warning">
              Some exchanges have stale data (&gt;30s old)
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
