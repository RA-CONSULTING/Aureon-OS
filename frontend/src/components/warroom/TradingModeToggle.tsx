import { useState, useEffect } from 'react';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
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
import { unifiedOrchestrator } from '@/core/unifiedOrchestrator';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

interface TradingModeToggleProps {
  userId?: string | null;
}

export function TradingModeToggle({ userId }: TradingModeToggleProps) {
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  // Load trading mode from database
  useEffect(() => {
    async function loadTradingMode() {
      if (!userId) {
        setLoading(false);
        return;
      }

      const { data } = await supabase
        .from('aureon_user_sessions')
        .select('trading_mode')
        .eq('user_id', userId)
        .single();

      if (data) {
        const isLive = data.trading_mode === 'live';
        setIsLiveMode(isLive);
        unifiedOrchestrator.setDryRun(!isLive);
      }
      setLoading(false);
    }

    loadTradingMode();
  }, [userId]);

  const handleToggle = (checked: boolean) => {
    if (checked) {
      // Switching to LIVE - show confirmation
      setShowConfirmDialog(true);
    } else {
      // Switching to PAPER - no confirmation needed
      confirmModeChange(false);
    }
  };

  const confirmModeChange = async (toLive: boolean) => {
    setIsLiveMode(toLive);
    unifiedOrchestrator.setDryRun(!toLive);

    // Persist to database
    if (userId) {
      await supabase
        .from('aureon_user_sessions')
        .update({ trading_mode: toLive ? 'live' : 'paper' })
        .eq('user_id', userId);
    }

    toast({
      title: toLive ? ' LIVE TRADING ENABLED' : ' Paper Trading Mode',
      description: toLive 
        ? 'Real orders will be executed on your exchange account!' 
        : 'Trades will be simulated, no real money at risk.',
      variant: toLive ? 'destructive' : 'default',
      duration: 5000,
    });

    setShowConfirmDialog(false);
  };

  if (loading) {
    return <div className="animate-pulse h-8 w-32 bg-muted rounded" />;
  }

  return (
    <>
      <div className="flex items-center gap-3 p-3 rounded-lg bg-card/50 border border-border/50">
        <Label htmlFor="trading-mode" className="text-sm font-medium">
          Trading Mode
        </Label>
        <Switch
          id="trading-mode"
          checked={isLiveMode}
          onCheckedChange={handleToggle}
          className={isLiveMode ? 'data-[state=checked]:bg-destructive' : ''}
        />
        <Badge 
          variant={isLiveMode ? 'destructive' : 'secondary'}
          className={isLiveMode ? 'animate-pulse' : ''}
        >
          {isLiveMode ? ' LIVE' : ' PAPER'}
        </Badge>
      </div>

      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-destructive">
               Enable Live Trading?
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                You are about to enable <strong className="text-destructive">LIVE TRADING</strong>. 
                This means:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>Real orders will be placed on your exchange account</li>
                <li>Real money will be at risk</li>
                <li>Trades cannot be undone once executed</li>
                <li>You are fully responsible for any profits or losses</li>
              </ul>
              <p className="font-semibold mt-4">
                Make sure your API credentials are correctly configured and 
                you understand the trading parameters.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => confirmModeChange(true)}
              className="bg-destructive hover:bg-destructive/90"
            >
              Enable Live Trading
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
