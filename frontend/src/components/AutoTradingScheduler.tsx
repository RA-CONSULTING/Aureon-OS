import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { supabase } from "@/integrations/supabase/client";
import { Clock, Play, Pause, Settings, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { SchedulerHistoryCharts } from "./SchedulerHistoryCharts";
import { PredictiveWindowsPanel } from "./PredictiveWindowsPanel";

interface SchedulerConfig {
  enabled: boolean;
  min_coherence_threshold: number;
  require_lhe_in_window: boolean;
  cooldown_hours: number;
  max_daily_activations: number;
}

interface SchedulerStatus {
  timestamp: string;
  action: string;
  reason: string;
  schedulerEnabled: boolean;
  currentState: {
    hour: number;
    coherence: number;
    lighthouseEvents: number;
    isOptimal: boolean;
    tradingEnabled: boolean;
  };
  statistics: {
    dailyActivations: number;
    maxDailyActivations: number;
    avgCoherence: number;
    totalOptimalHours: number;
  };
  nextOptimalWindows: any[];
}

export const AutoTradingScheduler = () => {
  const [config, setConfig] = useState<SchedulerConfig>({
    enabled: false,
    min_coherence_threshold: 0.75,
    require_lhe_in_window: true,
    cooldown_hours: 2,
    max_daily_activations: 5,
  });
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const checkScheduler = async () => {
    try {
      const { data, error } = await supabase.functions.invoke('auto-trading-scheduler', {
        body: { config },
      });
      
      if (error) throw error;
      setStatus(data);

      // Show notification if action was taken
      if (data.action === 'enable') {
        toast.success('Auto-Scheduler', {
          description: `Trading activated: ${data.reason}`,
        });
      } else if (data.action === 'disable') {
        toast.warning('Auto-Scheduler', {
          description: `Trading paused: ${data.reason}`,
        });
      }
    } catch (error) {
      console.error('Error checking scheduler:', error);
      toast.error('Scheduler Error', {
        description: 'Failed to check auto-trading scheduler',
      });
    }
  };

  const runScheduler = async () => {
    setIsLoading(true);
    await checkScheduler();
    setIsLoading(false);
  };

  useEffect(() => {
    if (config.enabled) {
      // Initial check
      runScheduler();
      
      // Check every 15 minutes when enabled
      const interval = setInterval(runScheduler, 15 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [config.enabled]);

  const handleConfigChange = (key: keyof SchedulerConfig, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const formatHour = (hour: number) => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}${period}`;
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'enable': return 'default';
      case 'disable': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Clock className="h-6 w-6 text-primary" />
            Auto-Trading Scheduler
          </h2>
          <p className="text-sm text-muted-foreground">
            Automatically activate trading during optimal windows
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={runScheduler}
            disabled={isLoading || !config.enabled}
          >
            {isLoading ? 'Checking...' : 'Check Now'}
          </Button>
        </div>
      </div>

      {/* Main Status Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-full ${config.enabled ? 'bg-primary/10' : 'bg-muted'}`}>
              {config.enabled ? (
                <Play className="h-6 w-6 text-primary" />
              ) : (
                <Pause className="h-6 w-6 text-muted-foreground" />
              )}
            </div>
            <div>
              <h3 className="font-semibold">Scheduler Status</h3>
              <p className="text-sm text-muted-foreground">
                {config.enabled ? 'Active - Monitoring field coherence' : 'Paused - Manual control only'}
              </p>
            </div>
          </div>
          <Switch
            checked={config.enabled}
            onCheckedChange={(checked) => handleConfigChange('enabled', checked)}
          />
        </div>

        {status && (
          <div className="space-y-4">
            {/* Current State */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 bg-muted rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">Current Hour</div>
                <div className="text-2xl font-bold">{formatHour(status.currentState.hour)}</div>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">Field Coherence</div>
                <div className="text-2xl font-bold">
                  {(status.currentState.coherence * 100).toFixed(0)}%
                </div>
                {status.currentState.isOptimal && (
                  <Badge variant="default" className="mt-1">Optimal</Badge>
                )}
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">Trading Status</div>
                <div className="flex items-center gap-2 mt-1">
                  {status.currentState.tradingEnabled ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-success" />
                      <span className="font-bold">Active</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      <span className="font-bold">Paused</span>
                    </>
                  )}
                </div>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">Daily Activations</div>
                <div className="text-2xl font-bold">
                  {status.statistics.dailyActivations}/{status.statistics.maxDailyActivations}
                </div>
              </div>
            </div>

            {/* Last Action */}
            {status.action !== 'none' && (
              <div className="p-4 bg-primary/5 border-l-4 border-primary rounded">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={getActionColor(status.action) as any}>
                    {status.action.toUpperCase()}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {new Date(status.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm">{status.reason}</p>
              </div>
            )}

            {/* Next Optimal Windows */}
            {status.nextOptimalWindows.length > 0 && (
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Next Optimal Windows
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {status.nextOptimalWindows.map((window, idx) => (
                    <div key={idx} className="p-3 bg-muted rounded-lg">
                      <div className="font-medium">
                        {formatHour(window.startHour)} - {formatHour(window.endHour)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {window.duration}h duration
                      </div>
                      <div className="text-sm font-medium mt-1">
                        {(window.avgCoherence * 100).toFixed(0)}% coherence
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!status && config.enabled && (
          <div className="text-center py-8 text-muted-foreground">
            Waiting for first scheduler check...
          </div>
        )}

        {!config.enabled && (
          <div className="text-center py-8">
            <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-3" />
            <p className="text-muted-foreground">
              Enable the scheduler to automatically manage trading based on field coherence
            </p>
          </div>
        )}
      </Card>

      {/* Settings Panel */}
      {showSettings && (
        <Card className="p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Scheduler Configuration
          </h3>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Min Coherence Threshold</Label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={config.min_coherence_threshold}
                  onChange={(e) => handleConfigChange('min_coherence_threshold', parseFloat(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">
                  Minimum unified field coherence to enable trading
                </p>
              </div>

              <div className="space-y-2">
                <Label>Max Daily Activations</Label>
                <Input
                  type="number"
                  min="1"
                  max="20"
                  value={config.max_daily_activations}
                  onChange={(e) => handleConfigChange('max_daily_activations', parseInt(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">
                  Maximum times trading can be auto-enabled per day
                </p>
              </div>

              <div className="space-y-2">
                <Label>Cooldown Hours</Label>
                <Input
                  type="number"
                  min="0"
                  max="24"
                  value={config.cooldown_hours}
                  onChange={(e) => handleConfigChange('cooldown_hours', parseInt(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">
                  Hours to wait between activation cycles
                </p>
              </div>

              <div className="space-y-2 flex items-center gap-3">
                <Switch
                  checked={config.require_lhe_in_window}
                  onCheckedChange={(checked) => handleConfigChange('require_lhe_in_window', checked)}
                />
                <div>
                  <Label>Require LHE Events</Label>
                  <p className="text-xs text-muted-foreground">
                    Only enable if Lighthouse Events detected
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Safety Information */}
      <Card className="p-6 bg-warning/5 border-warning/20">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-warning mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold mb-2">Safety Features</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Automatic pause when field coherence drops below threshold</li>
              <li>• Daily activation limits prevent over-trading</li>
              <li>• Cooldown periods between activation cycles</li>
              <li>• Manual override available at any time</li>
              <li>• Real-time monitoring of all earth and space systems</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground text-center">
        Auto-scheduler checks every 15 minutes when enabled • Based on unified field coherence analysis
      </div>

      {/* Scheduler History & Analytics */}
      <div className="space-y-4">
        <div>
          <h3 className="text-xl font-bold mb-2">Scheduler History & Analytics</h3>
          <p className="text-sm text-muted-foreground">
            Historical decision patterns, coherence trends, and activation timelines
          </p>
        </div>
        
        {/* Predictive Analytics */}
        <PredictiveWindowsPanel />
        
        {/* Historical Charts */}
        <SchedulerHistoryCharts />
      </div>
    </div>
  );
};
