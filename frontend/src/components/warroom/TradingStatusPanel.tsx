import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { CheckCircle2, XCircle, AlertCircle, Activity } from 'lucide-react';

interface GateStatus {
  name: string;
  passed: boolean;
  value: string;
  threshold: string;
}

export function TradingStatusPanel() {
  const [gates, setGates] = useState<GateStatus[]>([]);
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [lastScanTime, setLastScanTime] = useState<string>('--');
  const [opportunitiesFound, setOpportunitiesFound] = useState(0);

  useEffect(() => {
    // Load latest trading config and states
    const loadStatus = async () => {
      try {
        // Get trading config
        const { data: config } = await supabase
          .from('trading_config')
          .select('*')
          .single();

        // Get latest master equation state
        const { data: masterEq } = await supabase
          .from('master_equation_field_history')
          .select('coherence, lambda')
          .order('timestamp', { ascending: false })
          .limit(1)
          .single();

        // Get latest lighthouse event
        const { data: lighthouse } = await supabase
          .from('lighthouse_events')
          .select('confidence, is_lhe')
          .order('timestamp', { ascending: false })
          .limit(1)
          .single();

        // Get latest QGITA signal
        const { data: qgita } = await supabase
          .from('qgita_signal_states')
          .select('tier, confidence')
          .order('timestamp', { ascending: false })
          .limit(1)
          .single();

        const currentCoherence = masterEq?.coherence || 0;
        const currentConfidence = lighthouse?.confidence || 0;
        const isLHE = lighthouse?.is_lhe || false;
        const qgitaTier = qgita?.tier || 3;

        const minCoherence = config?.min_coherence || 0.35;
        const minConfidence = config?.min_lighthouse_confidence || 0.40;
        const requireLHE = config?.require_lhe || false;

        setTradingMode((config?.trading_mode as 'paper' | 'live') || 'paper');

        setGates([
          {
            name: 'Coherence Gate',
            passed: currentCoherence >= minCoherence,
            value: currentCoherence.toFixed(3),
            threshold: `≥ ${minCoherence}`,
          },
          {
            name: 'Lighthouse Confidence',
            passed: currentConfidence >= minConfidence,
            value: currentConfidence.toFixed(3),
            threshold: `≥ ${minConfidence}`,
          },
          {
            name: 'LHE Required',
            passed: !requireLHE || isLHE,
            value: isLHE ? 'YES' : 'NO',
            threshold: requireLHE ? 'Required' : 'Not Required',
          },
          {
            name: 'QGITA Tier',
            passed: qgitaTier <= 3, // All tiers allowed now
            value: `Tier ${qgitaTier}`,
            threshold: 'Any Tier',
          },
          {
            name: 'Data Fresh',
            passed: !!masterEq,
            value: masterEq ? '✓' : '✗',
            threshold: 'Live Data',
          },
        ]);

        setLastScanTime(new Date().toLocaleTimeString());
      } catch (err) {
        console.error('Error loading trading status:', err);
      }
    };

    loadStatus();
    const interval = setInterval(loadStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const allGatesPassed = gates.length > 0 && gates.every(g => g.passed);

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-lg">
          <span className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Trading Gates
          </span>
          <Badge variant={tradingMode === 'live' ? 'destructive' : 'secondary'}>
            {tradingMode === 'live' ? ' LIVE' : ' PAPER'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Overall Status */}
        <div className={`p-3 rounded-lg ${allGatesPassed ? 'bg-success/20 border border-success/30' : 'bg-destructive/20 border border-destructive/30'}`}>
          <div className="flex items-center justify-between">
            <span className="font-semibold">
              {allGatesPassed ? ' READY TO TRADE' : ' GATES BLOCKED'}
            </span>
            <span className="text-xs text-muted-foreground">
              Last scan: {lastScanTime}
            </span>
          </div>
        </div>

        {/* Gate List */}
        <div className="space-y-2">
          {gates.map((gate, idx) => (
            <div key={idx} className="flex items-center justify-between p-2 rounded bg-muted/30">
              <div className="flex items-center gap-2">
                {gate.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
                <span className="text-sm">{gate.name}</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className={gate.passed ? 'text-success' : 'text-destructive'}>
                  {gate.value}
                </span>
                <span className="text-muted-foreground">({gate.threshold})</span>
              </div>
            </div>
          ))}
        </div>

        {/* Opportunities */}
        <div className="flex items-center justify-between text-sm p-2 rounded bg-muted/30">
          <span className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-warning" />
            Opportunities Found
          </span>
          <Badge variant="outline">{opportunitiesFound}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
