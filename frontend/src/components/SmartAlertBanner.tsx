import { useEffect, useState } from 'react';
import { X, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { backgroundServices, BackgroundAlert } from '@/core/backgroundServices';
import { cn } from '@/lib/utils';

export function SmartAlertBanner() {
  const [alerts, setAlerts] = useState<BackgroundAlert[]>([]);

  useEffect(() => {
    const unsubscribe = backgroundServices.subscribe(setAlerts);
    return unsubscribe;
  }, []);

  if (alerts.length === 0) return null;

  const handleDismiss = (alertId: string) => {
    backgroundServices.dismissAlert(alertId);
  };

  const getAlertStyles = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return 'bg-destructive/10 border-destructive/30 text-destructive';
      case 'warning':
        return 'bg-warning/10 border-warning/30 text-warning';
      case 'info':
        return 'bg-primary/10 border-primary/30 text-primary';
    }
  };

  const getAlertIcon = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />;
      case 'info':
        return <Info className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-1">
      {alerts.slice(0, 3).map((alert) => (
        <div
          key={alert.id}
          className={cn(
            "flex items-center justify-between gap-2 px-4 py-2 border text-sm",
            getAlertStyles(alert.type)
          )}
        >
          <div className="flex items-center gap-2">
            {getAlertIcon(alert.type)}
            <span className="font-medium">{alert.message}</span>
          </div>
          <button
            onClick={() => handleDismiss(alert.id)}
            className="hover:opacity-70 transition-opacity"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
