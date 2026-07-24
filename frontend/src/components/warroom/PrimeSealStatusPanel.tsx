/**
 * Prime Seal Status Panel for War Room
 * Displays 10-9-1 Prime Seal state from UnifiedBus/primeSealComputer
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Lock, Unlock, Sparkles, Heart, Shield } from 'lucide-react';
import { primeSealComputer, type PrimeSealState } from '@/core/primeSealComputer';
import { unifiedBus } from '@/core/unifiedBus';

export function PrimeSealStatusPanel() {
  const [sealState, setSealState] = useState<PrimeSealState | null>(null);
  
  useEffect(() => {
    // Subscribe to prime seal updates
    const unsubscribeSeal = primeSealComputer.subscribe((state) => {
      setSealState(state);
    });
    
    // Also compute on bus updates
    const unsubscribeBus = unifiedBus.subscribe((snapshot) => {
      const computed = primeSealComputer.compute(snapshot);
      setSealState(computed);
    });
    
    // Initial computation
    const snapshot = unifiedBus.snapshot();
    const initial = primeSealComputer.compute(snapshot);
    setSealState(initial);
    
    return () => {
      unsubscribeSeal();
      unsubscribeBus();
    };
  }, []);
  
  if (!sealState) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="flex items-center justify-center h-32">
          <div className="text-muted-foreground animate-pulse">Loading Prime Seal...</div>
        </CardContent>
      </Card>
    );
  }
  
  const { packet, unityCoherence, flowCoherence, anchorCoherence } = sealState;
  const isLocked = packet.seal_lock;
  
  return (
    <Card className={`bg-card/50 backdrop-blur border-2 transition-all duration-500 ${
      isLocked ? 'border-success/50 shadow-[0_0_20px_rgba(34,197,94,0.3)]' : 'border-warning/50'
    }`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className={`w-5 h-5 ${isLocked ? 'text-success' : 'text-warning'}`} />
            10-9-1 Prime Seal
          </CardTitle>
          <Badge 
            variant={isLocked ? "default" : "secondary"}
            className={isLocked ? "bg-success animate-pulse" : ""}
          >
            {isLocked ? <><Lock className="w-3 h-3 mr-1" /> SEALED</> : <><Unlock className="w-3 h-3 mr-1" /> OPEN</>}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Intent Broadcast */}
        <div className="p-3 bg-background/30 rounded-lg text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <Heart className="w-4 h-4 text-primary" />
            <span className="text-xs text-muted-foreground">Intent</span>
          </div>
          <div className="text-sm font-medium bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
            {packet.intent_text}
          </div>
        </div>
        
        {/* Prime Coherence Meter */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">Prime Coherence</span>
            <span className={`text-sm font-bold ${packet.prime_coherence >= 0.945 ? 'text-success' : 'text-warning'}`}>
              {(packet.prime_coherence * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={packet.prime_coherence * 100} className="h-2" />
          <div className="flex justify-between mt-0.5">
            <span className="text-[10px] text-muted-foreground">0%</span>
            <span className="text-[10px] text-success">Lock: 94.5%</span>
            <span className="text-[10px] text-muted-foreground">100%</span>
          </div>
        </div>
        
        {/* 10-9-1 Weights Display */}
        <div className="grid grid-cols-3 gap-2">
          <div className="p-2 bg-primary/10 rounded-lg text-center border border-primary/30">
            <div className="text-[10px] text-muted-foreground mb-0.5">Unity (×10)</div>
            <div className="text-lg font-bold text-primary">{(unityCoherence * 100).toFixed(0)}%</div>
            <Sparkles className="w-3 h-3 mx-auto mt-0.5 text-primary" />
          </div>
          <div className="p-2 bg-primary/10 rounded-lg text-center border border-primary/30">
            <div className="text-[10px] text-muted-foreground mb-0.5">Flow (×9)</div>
            <div className="text-lg font-bold text-primary">{(flowCoherence * 100).toFixed(0)}%</div>
            <Sparkles className="w-3 h-3 mx-auto mt-0.5 text-primary" />
          </div>
          <div className="p-2 bg-warning/10 rounded-lg text-center border border-warning/30">
            <div className="text-[10px] text-muted-foreground mb-0.5">Anchor (×1)</div>
            <div className="text-lg font-bold text-warning">{(anchorCoherence * 100).toFixed(0)}%</div>
            <Sparkles className="w-3 h-3 mx-auto mt-0.5 text-warning" />
          </div>
        </div>
        
        {/* Signal */}
        <div className="flex items-center justify-between p-2 bg-background/30 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Signal:</span>
            <Badge variant={packet.consensus_signal === 'BUY' ? 'default' : packet.consensus_signal === 'SELL' ? 'destructive' : 'secondary'}>
              {packet.consensus_signal}
            </Badge>
          </div>
          <div className="text-right">
            <span className="text-xs text-muted-foreground">Packet Value: </span>
            <span className="text-sm font-bold">{packet.packet_value.toFixed(2)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
