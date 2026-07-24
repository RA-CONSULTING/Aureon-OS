import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useBackendHealth } from '@/hooks/useBackendHealth';
import { useHealthAlerts } from '@/hooks/useHealthAlerts';
import { HealthAlertSettings } from '@/components/HealthAlertSettings';
import { AlertCircle, CheckCircle, RefreshCw, XCircle, Clock, AlertTriangle, Settings } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

export function BackendHealthMonitor() {
  const { healthReport, loading, lastChecked, refresh } = useBackendHealth(true, 60000);
  const { config, updateConfig, clearAlertHistory } = useHealthAlerts(healthReport);
  const [showSettings, setShowSettings] = useState(false);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-warning" />;
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-destructive" />;
      case 'not_configured':
      case 'skipped':
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: { [key: string]: any } = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive',
      not_configured: 'outline',
      skipped: 'outline',
    };
    return (
      <Badge variant={variants[status] || 'outline'} className="capitalize">
        {status}
      </Badge>
    );
  };

  return (
    <div className="space-y-4">
      <Card className="p-6 bg-card/50 backdrop-blur border-primary/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold">Backend Health Monitor</h3>
          {healthReport && (
            <Badge
              variant={
                healthReport.overall_status === 'healthy'
                  ? 'default'
                  : healthReport.overall_status === 'degraded'
                  ? 'secondary'
                  : 'destructive'
              }
              className="uppercase"
            >
              {healthReport.overall_status}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastChecked && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(lastChecked, { addSuffix: true })}
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {!healthReport && loading && (
        <div className="text-center py-8 text-muted-foreground">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p>Running health checks...</p>
        </div>
      )}

      {healthReport && (
        <div className="space-y-4">
          {/* Errors */}
          {healthReport.errors.length > 0 && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <XCircle className="h-5 w-5 text-destructive mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-destructive mb-2">Critical Issues</h4>
                  <ul className="space-y-1">
                    {healthReport.errors.map((error, i) => (
                      <li key={i} className="text-sm text-destructive/90">• {error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Warnings */}
          {healthReport.warnings.length > 0 && (
            <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-warning mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-warning mb-2">Warnings</h4>
                  <ul className="space-y-1">
                    {healthReport.warnings.map((warning, i) => (
                      <li key={i} className="text-sm text-warning/90">• {warning}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Individual Checks */}
          <div className="grid gap-3">
            {Object.entries(healthReport.checks).map(([key, check]) => (
              <div
                key={key}
                className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-background/50"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(check.status)}
                  <div>
                    <p className="font-medium capitalize">
                      {key.replace(/_/g, ' ').replace('edge function ', '')}
                    </p>
                    <p className="text-sm text-muted-foreground">{check.message}</p>
                  </div>
                </div>
                {getStatusBadge(check.status)}
              </div>
            ))}
          </div>
        </div>
      )}
      </Card>

      {showSettings && (
        <HealthAlertSettings
          config={config}
          onConfigChange={updateConfig}
          onClearHistory={clearAlertHistory}
        />
      )}
    </div>
  );
}
