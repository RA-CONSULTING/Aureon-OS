import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useExchangeDataVerification } from '@/hooks/useExchangeDataVerification';
import { useDataStreamMonitor } from '@/hooks/useDataStreamMonitor';
import { useBackendHealth } from '@/hooks/useBackendHealth';
import { usePrimeSeal } from '@/hooks/usePrimeSeal';
import { IgnitionButton } from '@/components/IgnitionButton';
import { ValidationTracePanel } from '@/components/ValidationTracePanel';
import { ForceTradeResult } from '@/core/forceValidatedTrade';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  RefreshCw, 
  Wifi, 
  WifiOff,
  Server,
  Key,
  Activity,
  Lock,
  Unlock,
  Flame
} from 'lucide-react';

interface SystemCheck {
  name: string;
  status: 'ok' | 'warning' | 'error' | 'offline';
  message: string;
  isRealData: boolean;
  actionNeeded?: string;
}

interface SystemHealthPanelProps {
  userId?: string;
  tradingMode?: 'paper' | 'live';
}

export function SystemHealthPanel({ userId, tradingMode = 'paper' }: SystemHealthPanelProps) {
  const { verification, isLiveData, isDemoMode, liveExchangeCount, verify, getExchangeStatus } = useExchangeDataVerification();
  const { overallHealth, healthyEndpoints, unhealthyEndpoints } = useDataStreamMonitor();
  const { healthReport, refresh: refreshHealth } = useBackendHealth();
  const primeSeal = usePrimeSeal();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [validationResult, setValidationResult] = useState<ForceTradeResult | null>(null);
  const [showTrace, setShowTrace] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([verify(), refreshHealth()]);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  // Helper to check exchange status
  const getExchangeCheck = (exchangeName: string, displayName: string, isRequired: boolean = false): SystemCheck => {
    const exchange = getExchangeStatus(exchangeName);
    const isConnected = exchange?.status === 'LIVE';
    
    return {
      name: `${displayName} Connection`,
      status: isConnected ? 'ok' : 'offline',
      message: isConnected 
        ? 'Connected with live data' 
        : isRequired ? 'Not connected - add API keys' : 'Not configured',
      isRealData: isConnected,
      actionNeeded: !isConnected 
        ? `Add ${displayName} API credentials ${isRequired ? '' : '(optional)'}` 
        : undefined
    };
  };

  // Build system checks
  const systemChecks: SystemCheck[] = [
    // Exchange Connections
    getExchangeCheck('binance', 'Binance', true),
    getExchangeCheck('kraken', 'Kraken', false),
    getExchangeCheck('alpaca', 'Alpaca', false),
    getExchangeCheck('capital', 'Capital.com', false),
    // Backend Health
    {
      name: 'Backend Services',
      status: healthReport?.overall_status === 'healthy' ? 'ok' : healthReport?.overall_status === 'degraded' ? 'warning' : 'error',
      message: healthReport?.overall_status === 'healthy' 
        ? 'All backend services operational' 
        : `${healthReport?.errors?.length || 0} issues detected`,
      isRealData: true,
      actionNeeded: healthReport?.overall_status !== 'healthy' 
        ? healthReport?.errors?.[0] 
        : undefined
    },
    // Data Streams
    {
      name: 'Data Streams',
      status: overallHealth === 'healthy' ? 'ok' : overallHealth === 'degraded' ? 'warning' : 'error',
      message: `${healthyEndpoints.length} healthy, ${unhealthyEndpoints.length} unhealthy`,
      isRealData: !isDemoMode,
      actionNeeded: unhealthyEndpoints.length > 0 
        ? `Fix: ${unhealthyEndpoints.join(', ')}` 
        : undefined
    },
    // Overall Data Mode
    {
      name: 'Trading Data',
      status: isLiveData ? 'ok' : isDemoMode ? 'offline' : 'warning',
      message: isLiveData 
        ? `Live data from ${liveExchangeCount} exchange(s)` 
        : 'SIMULATED - No live exchange data',
      isRealData: isLiveData,
      actionNeeded: !isLiveData 
        ? 'Connect at least one exchange for live trading' 
        : undefined
    },
    // 10-9-1 Prime Seal Status
    {
      name: '10-9-1 Prime Seal',
      status: primeSeal.isLocked ? 'ok' : primeSeal.primeCoherence > 0.7 ? 'warning' : 'error',
      message: primeSeal.isLocked 
        ? `🔒 SEALED at Γ=${primeSeal.primeCoherence.toFixed(4)}` 
        : `🔓 UNLOCKED Γ=${primeSeal.primeCoherence.toFixed(4)} < 0.945`,
      isRealData: primeSeal.systemsContributing.length > 0,
      actionNeeded: !primeSeal.isLocked 
        ? 'Coherence must reach 0.945 to enable trading' 
        : undefined
    }
  ];

  const workingCount = systemChecks.filter(c => c.status === 'ok').length;
  const needsFixCount = systemChecks.filter(c => c.status === 'error' || c.status === 'offline').length;
  const warningCount = systemChecks.filter(c => c.status === 'warning').length;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok': return <CheckCircle className="h-5 w-5 text-success" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-warning" />;
      case 'error': return <XCircle className="h-5 w-5 text-destructive" />;
      case 'offline': return <WifiOff className="h-5 w-5 text-muted-foreground" />;
      default: return <Activity className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getDataBadge = (isReal: boolean) => {
    if (isReal) {
      return <Badge className="bg-success/20 text-success border-success/30">🟢 LIVE</Badge>;
    }
    return <Badge variant="secondary" className="bg-muted text-muted-foreground">🔴 OFFLINE</Badge>;
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            System Health & Data Status
          </CardTitle>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        
        {/* Summary badges */}
        <div className="flex gap-2 mt-2 flex-wrap">
          <Badge className="bg-success/20 text-success">
            ✅ {workingCount} Working
          </Badge>
          {warningCount > 0 && (
            <Badge className="bg-warning/20 text-warning">
              ⚠️ {warningCount} Warnings
            </Badge>
          )}
          {needsFixCount > 0 && (
            <Badge className="bg-destructive/20 text-destructive">
              ❌ {needsFixCount} Need Fix
            </Badge>
          )}
          <Badge variant={isLiveData ? "default" : "secondary"} className={isLiveData ? "bg-success" : ""}>
            {isLiveData ? '🟢 LIVE DATA' : '🔴 SIMULATED'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {systemChecks.map((check, index) => (
          <div 
            key={index}
            className={`p-3 rounded-lg border ${
              check.status === 'ok' ? 'border-success/30 bg-success/5' :
              check.status === 'warning' ? 'border-warning/30 bg-warning/5' :
              check.status === 'offline' ? 'border-muted bg-muted/20' :
              'border-destructive/30 bg-destructive/5'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(check.status)}
                <div>
                  <div className="font-medium flex items-center gap-2">
                    {check.name}
                    {getDataBadge(check.isRealData)}
                  </div>
                  <p className="text-sm text-muted-foreground">{check.message}</p>
                </div>
              </div>
            </div>
            
            {check.actionNeeded && (
              <div className="mt-2 p-2 rounded bg-background/50 border border-dashed">
                <p className="text-sm flex items-center gap-2">
                  <Key className="h-4 w-4 text-primary" />
                  <span className="text-primary font-medium">Action needed:</span>
                  {check.actionNeeded}
                </p>
              </div>
            )}
          </div>
        ))}

        {/* 10-9-1 Prime Seal Status */}
        <div className={`p-3 rounded-lg border ${
          primeSeal.isLocked 
            ? 'border-success/50 bg-success/10' 
            : 'border-warning/50 bg-warning/10'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {primeSeal.isLocked ? (
                <Lock className="h-5 w-5 text-success" />
              ) : (
                <Unlock className="h-5 w-5 text-warning" />
              )}
              <span className="font-bold">10-9-1 Prime Seal</span>
            </div>
            <Badge className={primeSeal.isLocked ? 'bg-success' : 'bg-warning'}>
              {primeSeal.isLocked ? 'LOCKED' : 'UNLOCKED'}
            </Badge>
          </div>
          <Progress 
            value={primeSeal.primeCoherence * 100} 
            className="h-2 mb-1"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Unity: {(primeSeal.unityCoherence * 100).toFixed(0)}% (10×)</span>
            <span>Flow: {(primeSeal.flowCoherence * 100).toFixed(0)}% (9×)</span>
            <span>Anchor: {(primeSeal.anchorCoherence * 100).toFixed(0)}% (1×)</span>
          </div>
        </div>

        {/* Cycle 1 Ignition Section */}
        {userId && (
          <div className="p-4 rounded-lg border-2 border-dashed border-primary/30 bg-primary/5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Flame className="h-5 w-5 text-warning" />
                <span className="font-bold">Cycle 1 Validation</span>
              </div>
              {validationResult && (
                <Badge variant={validationResult.success ? "default" : "destructive"}>
                  {validationResult.success ? '✅ PASSED' : '❌ FAILED'}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              Force a single fully validated trade through all 10 system steps to verify the pipeline is operational.
            </p>
            <div className="flex items-center gap-3">
              <IgnitionButton 
                userId={userId} 
                tradingMode={tradingMode}
                onComplete={(result) => {
                  setValidationResult(result);
                  setShowTrace(true);
                }}
              />
              {validationResult && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setShowTrace(!showTrace)}
                >
                  {showTrace ? 'Hide Trace' : 'Show Trace'}
                </Button>
              )}
            </div>
            {showTrace && validationResult && (
              <div className="mt-4">
                <ValidationTracePanel trace={validationResult.trace} />
              </div>
            )}
          </div>
        )}

        {/* Overall status message */}
        <div className={`p-4 rounded-lg text-center ${
          isLiveData && primeSeal.isLocked ? 'bg-success/10 border border-success/30' : 'bg-destructive/10 border border-destructive/30'
        }`}>
          {isLiveData && primeSeal.isLocked ? (
            <div className="flex items-center justify-center gap-2 text-success">
              <Wifi className="h-5 w-5" />
              <Lock className="h-4 w-4" />
              <span className="font-bold">LIVE TRADING READY</span>
              <span className="text-sm">- Seal locked, {liveExchangeCount} exchange(s)</span>
            </div>
          ) : !isLiveData ? (
            <div className="flex flex-col items-center gap-2 text-destructive">
              <div className="flex items-center gap-2">
                <WifiOff className="h-5 w-5" />
                <span className="font-bold">OFFLINE - SIMULATED MODE</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Connect at least one exchange to enable live trading
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-warning">
              <div className="flex items-center gap-2">
                <Unlock className="h-5 w-5" />
                <span className="font-bold">AWAITING SEAL LOCK</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Coherence at {(primeSeal.primeCoherence * 100).toFixed(1)}% - needs 94.5% to trade
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
