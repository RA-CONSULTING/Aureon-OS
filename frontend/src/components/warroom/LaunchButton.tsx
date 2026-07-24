import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';
import { useGlobalState } from '@/hooks/useGlobalState';
import { unifiedOrchestrator } from '@/core/unifiedOrchestrator';
import { Rocket, Square, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface LaunchButtonProps {
  onLaunch: () => void;
  onStop: () => void;
  status: 'idle' | 'active' | 'emergency_stopped';
}

export function LaunchButton({ onLaunch, onStop, status }: LaunchButtonProps) {
  const { toast } = useToast();
  const globalState = useGlobalState();
  const [isLaunching, setIsLaunching] = useState(false);
  const [showLiveConfirm, setShowLiveConfirm] = useState(false);
  const [validationStatus, setValidationStatus] = useState<{
    credentials: boolean;
    config: boolean;
    gasBalance: boolean;
  } | null>(null);

  const validateAndLaunch = async (forceLive: boolean = false) => {
    setIsLaunching(true);
    
    try {
      // Step 1: Validate credentials exist
      const { data: session } = await supabase
        .from('aureon_user_sessions')
        .select('binance_api_key_encrypted, trading_mode, gas_tank_balance')
        .eq('user_id', globalState.userId)
        .single();

      const hasCredentials = !!session?.binance_api_key_encrypted;
      const isLiveMode = session?.trading_mode === 'live';
      const hasGasBalance = (session?.gas_tank_balance || 0) > 0;

      setValidationStatus({
        credentials: hasCredentials,
        config: true,
        gasBalance: hasGasBalance || !isLiveMode, // Gas only required for live
      });

      if (!hasCredentials) {
        toast({
          title: 'Missing Credentials',
          description: 'Please configure your exchange API keys in Settings.',
          variant: 'destructive',
        });
        setIsLaunching(false);
        return;
      }

      // Check if switching to live requires confirmation
      if (isLiveMode && !forceLive) {
        setShowLiveConfirm(true);
        setIsLaunching(false);
        return;
      }

      // Step 2: Enable trading config
      await supabase
        .from('trading_config')
        .update({ is_enabled: true, updated_at: new Date().toISOString() })
        .eq('id', 'dd282f03-11b4-4f70-b8c2-dd5523ed73e2');

      // Step 3: Set orchestrator mode
      unifiedOrchestrator.setDryRun(!isLiveMode);

      // Step 4: Launch trading
      onLaunch();

      toast({
        title: ' AUREON Launched!',
        description: isLiveMode 
          ? 'Live trading is now active. Monitor your positions closely.'
          : 'Paper trading started. No real funds at risk.',
      });
    } catch (err) {
      console.error('Launch validation failed:', err);
      toast({
        title: 'Launch Failed',
        description: 'Could not validate trading readiness.',
        variant: 'destructive',
      });
    } finally {
      setIsLaunching(false);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      // Disable trading config
      await supabase
        .from('trading_config')
        .update({ is_enabled: false, updated_at: new Date().toISOString() })
        .eq('id', 'dd282f03-11b4-4f70-b8c2-dd5523ed73e2');

      onStop();

      toast({
        title: ' Trading Stopped',
        description: 'All automated trading has been halted.',
      });
    } catch (err) {
      console.error('Stop failed:', err);
    }
  };

  const confirmLiveLaunch = () => {
    setShowLiveConfirm(false);
    validateAndLaunch(true);
  };

  return (
    <>
      <Card className="bg-gradient-to-r from-primary/10 to-destructive/10 border-primary/30">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Status */}
            <div className="flex items-center gap-4">
              <div className={`w-4 h-4 rounded-full ${
                status === 'active' ? 'bg-success animate-pulse' :
                status === 'emergency_stopped' ? 'bg-destructive' : 'bg-muted'
              }`} />
              <div>
                <h3 className="text-xl font-bold">
                  {status === 'active' ? ' TRADING ACTIVE' :
                   status === 'emergency_stopped' ? ' STOPPED' : ' READY TO LAUNCH'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {status === 'active' ? 'Autonomous trading is running' :
                   status === 'emergency_stopped' ? 'Trading was halted' : 'System ready for launch'}
                </p>
              </div>
            </div>

            {/* Validation Badges */}
            {validationStatus && (
              <div className="flex items-center gap-2">
                <Badge variant={validationStatus.credentials ? 'default' : 'destructive'}>
                  {validationStatus.credentials ? <CheckCircle2 className="h-3 w-3 mr-1" /> : <AlertTriangle className="h-3 w-3 mr-1" />}
                  Keys
                </Badge>
                <Badge variant={validationStatus.config ? 'default' : 'destructive'}>
                  {validationStatus.config ? <CheckCircle2 className="h-3 w-3 mr-1" /> : <AlertTriangle className="h-3 w-3 mr-1" />}
                  Config
                </Badge>
              </div>
            )}

            {/* Action Button */}
            <div>
              {status === 'idle' && (
                <Button
                  size="lg"
                  onClick={() => validateAndLaunch()}
                  disabled={isLaunching}
                  className="bg-gradient-to-r from-success to-primary hover:from-success hover:to-primary/90 text-white font-bold text-lg px-8"
                >
                  {isLaunching ? (
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <Rocket className="h-5 w-5 mr-2" />
                  )}
                  {isLaunching ? 'VALIDATING...' : ' LAUNCH AUREON'}
                </Button>
              )}
              {status === 'active' && (
                <Button
                  size="lg"
                  variant="destructive"
                  onClick={handleEmergencyStop}
                  className="font-bold text-lg px-8 animate-pulse"
                >
                  <Square className="h-5 w-5 mr-2" />
                   STOP TRADING
                </Button>
              )}
              {status === 'emergency_stopped' && (
                <Button
                  size="lg"
                  onClick={() => validateAndLaunch()}
                  disabled={isLaunching}
                  className="bg-gradient-to-r from-warning to-warning hover:from-warning hover:to-warning text-white font-bold text-lg px-8"
                >
                  <Rocket className="h-5 w-5 mr-2" />
                   RESUME TRADING
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Live Trading Confirmation Dialog */}
      <AlertDialog open={showLiveConfirm} onOpenChange={setShowLiveConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Confirm LIVE Trading
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                You are about to start <strong>LIVE trading</strong> with real funds.
              </p>
              <ul className="list-disc list-inside text-sm space-y-1">
                <li>Real orders will be placed on exchanges</li>
                <li>Your account balance will be at risk</li>
                <li>Losses can occur rapidly in volatile markets</li>
              </ul>
              <p className="font-semibold">
                Are you sure you want to proceed?
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmLiveLaunch}
              className="bg-destructive hover:bg-destructive/90"
            >
              Yes, Start Live Trading
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
