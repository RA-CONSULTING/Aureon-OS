import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { useExchangeDataVerification } from '@/hooks/useExchangeDataVerification';

interface DataSourceIndicatorProps {
  compact?: boolean;
  showDetails?: boolean;
}

/**
 * DATA SOURCE INDICATOR
 * 
 * Shows whether the system is receiving LIVE data
 * NO SIMULATION ALLOWED - Shows error when not connected
 */
export const DataSourceIndicator: React.FC<DataSourceIndicatorProps> = ({
  compact = false,
  showDetails = true,
}) => {
  const { 
    verification, 
    isLiveData, 
    liveExchangeCount, 
    totalExchangeCount,
    isLoading 
  } = useExchangeDataVerification();

  if (isLoading && !verification) {
    return (
      <Badge variant="outline" className="animate-pulse">
        <Wifi className="h-3 w-3 mr-1" />
        Connecting...
      </Badge>
    );
  }

  if (isLiveData) {
    return (
      <Badge className="bg-success/20 text-success border-success/50">
        <Wifi className="h-3 w-3 mr-1" />
        {compact ? 'LIVE' : 'LIVE DATA'}
        {showDetails && !compact && (
          <span className="ml-1 text-success">
            ({liveExchangeCount}/{totalExchangeCount})
          </span>
        )}
      </Badge>
    );
  }

  if (verification?.overallStatus === 'PARTIAL_LIVE') {
    return (
      <Badge className="bg-warning/20 text-warning border-warning/50">
        <AlertTriangle className="h-3 w-3 mr-1" />
        {compact ? 'PARTIAL' : 'PARTIAL LIVE'}
        {showDetails && !compact && (
          <span className="ml-1 text-warning">
            ({liveExchangeCount}/{totalExchangeCount})
          </span>
        )}
      </Badge>
    );
  }

  // NO SIMULATION - Show error state
  return (
    <Badge variant="destructive" className="animate-pulse">
      <WifiOff className="h-3 w-3 mr-1" />
      {compact ? '⛔ OFFLINE' : '⛔ NO LIVE DATA'}
    </Badge>
  );
};

/**
 * Critical warning banner when live data unavailable
 * NO SIMULATION ALLOWED - Trading blocked
 */
export const DemoModeWarningBanner: React.FC = () => {
  const { isLiveData, hasGhostData } = useExchangeDataVerification();

  // Only show if NOT live data (no simulation fallback)
  if (isLiveData && !hasGhostData) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-destructive/95 text-white px-4 py-2 text-center">
      <div className="flex items-center justify-center gap-2">
        <WifiOff className="h-4 w-4" />
        <span className="font-bold">
          ⛔ TRADING BLOCKED - NO LIVE DATA CONNECTION - CHECK EXCHANGE CREDENTIALS ⛔
        </span>
        <WifiOff className="h-4 w-4" />
      </div>
    </div>
  );
};
