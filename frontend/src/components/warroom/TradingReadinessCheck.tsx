import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useGlobalState } from '@/hooks/useGlobalState';

interface ReadinessCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn' | 'checking';
  message: string;
}

export function TradingReadinessCheck() {
  const [checks, setChecks] = useState<ReadinessCheck[]>([]);
  const [isReady, setIsReady] = useState(false);
  const globalState = useGlobalState();

  useEffect(() => {
    runChecks();
  }, [globalState.userId, globalState.isRunning]);

  async function runChecks() {
    const results: ReadinessCheck[] = [];

    // Check 1: Authentication
    results.push({
      name: 'Authentication',
      status: globalState.isAuthenticated ? 'pass' : 'fail',
      message: globalState.isAuthenticated ? 'User authenticated' : 'Not logged in',
    });

    // Check 2: Quantum Systems
    results.push({
      name: 'Quantum Systems',
      status: globalState.isRunning ? 'pass' : 'warn',
      message: globalState.isRunning ? 'All systems online' : 'Systems not initialized',
    });

    // Check 3: Coherence Level
    const coherenceOk = globalState.coherence >= 0.35;
    results.push({
      name: 'Coherence Level',
      status: coherenceOk ? 'pass' : 'warn',
      message: `Γ = ${(globalState.coherence * 100).toFixed(1)}% (min: 35%)`,
    });

    // Check 4: Exchange Credentials
    if (globalState.userId) {
      const { data } = await supabase
        .from('aureon_user_sessions')
        .select('binance_api_key_encrypted, trading_mode')
        .eq('user_id', globalState.userId)
        .single();

      const hasCredentials = !!data?.binance_api_key_encrypted;
      results.push({
        name: 'Exchange Credentials',
        status: hasCredentials ? 'pass' : 'fail',
        message: hasCredentials ? 'Binance API configured' : 'No exchange credentials',
      });

      // Check 5: Trading Mode
      results.push({
        name: 'Trading Mode',
        status: 'pass',
        message: data?.trading_mode === 'live' ? ' LIVE MODE' : ' Paper Mode',
      });
    } else {
      results.push({
        name: 'Exchange Credentials',
        status: 'fail',
        message: 'Login required',
      });
    }

    // Check 6: Trading Config
    const { data: config } = await supabase
      .from('trading_config')
      .select('is_enabled')
      .single();

    results.push({
      name: 'Trading Config',
      status: config?.is_enabled ? 'pass' : 'warn',
      message: config?.is_enabled ? 'Trading enabled' : 'Trading disabled in config',
    });

    setChecks(results);
    setIsReady(results.every(c => c.status !== 'fail'));
  }

  const passCount = checks.filter(c => c.status === 'pass').length;
  const failCount = checks.filter(c => c.status === 'fail').length;

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span> Trading Readiness</span>
          <Badge 
            variant={isReady ? 'default' : 'destructive'}
            className={isReady ? 'bg-success' : ''}
          >
            {isReady ? 'READY' : `${failCount} ISSUES`}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {checks.map((check, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-lg bg-background/50"
            >
              <div className="flex items-center gap-2">
                {check.status === 'checking' && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                {check.status === 'pass' && <CheckCircle2 className="h-4 w-4 text-success" />}
                {check.status === 'fail' && <XCircle className="h-4 w-4 text-destructive" />}
                {check.status === 'warn' && <AlertTriangle className="h-4 w-4 text-warning" />}
                <span className="text-sm font-medium">{check.name}</span>
              </div>
              <span className="text-xs text-muted-foreground">{check.message}</span>
            </div>
          ))}
        </div>
        
        <div className="mt-3 pt-3 border-t border-border/50 text-center">
          <p className="text-xs text-muted-foreground">
            {passCount}/{checks.length} checks passed
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
