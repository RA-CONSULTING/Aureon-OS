// 10-9-1 Prime Seal Status Panel
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Lock, Unlock, Sparkles, Heart } from 'lucide-react';
import type { SealPacket, TimelineMarker } from '@/lib/earth-data-loader';

interface Props {
  primeSeal: {
    isLocked: boolean;
    coherence: number;
    packetValue: number;
    intent: string;
    weights: { unity: number; flow: number; anchor: number };
  } | null;
  currentMarker: TimelineMarker | null;
}

export function PrimeSealPanel({ primeSeal, currentMarker }: Props) {
  if (!primeSeal) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-muted-foreground animate-pulse">Loading Prime Seal...</div>
        </CardContent>
      </Card>
    );
  }
  
  const sealColor = primeSeal.isLocked 
    ? 'from-success/20 to-success/20 border-success/50' 
    : 'from-warning/20 to-warning/20 border-warning/50';
    
  const sealGlow = primeSeal.isLocked
    ? 'shadow-[0_0_30px_rgba(34,197,94,0.3)]'
    : 'shadow-[0_0_30px_rgba(245,158,11,0.3)]';
  
  return (
    <Card className={`bg-gradient-to-br ${sealColor} backdrop-blur border ${sealGlow} transition-all duration-500`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            {primeSeal.isLocked ? (
              <Lock className="w-5 h-5 text-success" />
            ) : (
              <Unlock className="w-5 h-5 text-warning" />
            )}
            10-9-1 Prime Seal
          </CardTitle>
          <Badge 
            variant={primeSeal.isLocked ? "default" : "secondary"}
            className={primeSeal.isLocked ? "bg-success animate-pulse" : ""}
          >
            {primeSeal.isLocked ? '🔒 SEALED' : '🔓 OPEN'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Intent display */}
        <div className="p-4 bg-background/30 rounded-lg text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Heart className="w-5 h-5 text-primary" />
            <span className="text-sm text-muted-foreground">Intent Broadcast</span>
          </div>
          <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
            "{primeSeal.intent}"
          </div>
        </div>
        
        {/* Coherence meter */}
        <div className="p-3 bg-background/30 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Prime Coherence</span>
            <span className={`text-xl font-bold ${primeSeal.coherence >= 0.945 ? 'text-success' : 'text-warning'}`}>
              {(primeSeal.coherence * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={primeSeal.coherence * 100} className="h-3" />
          <div className="flex justify-between mt-1">
            <span className="text-xs text-muted-foreground">0%</span>
            <span className="text-xs text-success">Lock: 94.5%</span>
            <span className="text-xs text-muted-foreground">100%</span>
          </div>
        </div>
        
        {/* 10-9-1 Weights */}
        <div className="grid grid-cols-3 gap-2">
          <div className="p-3 bg-background/30 rounded-lg text-center border-2 border-primary/30">
            <div className="text-xs text-muted-foreground mb-1">Unity (10)</div>
            <div className="text-2xl font-bold text-primary">{primeSeal.weights.unity}</div>
            <Sparkles className="w-4 h-4 mx-auto mt-1 text-primary" />
          </div>
          <div className="p-3 bg-background/30 rounded-lg text-center border-2 border-primary/30">
            <div className="text-xs text-muted-foreground mb-1">Flow (9)</div>
            <div className="text-2xl font-bold text-primary">{primeSeal.weights.flow}</div>
            <Sparkles className="w-4 h-4 mx-auto mt-1 text-primary" />
          </div>
          <div className="p-3 bg-background/30 rounded-lg text-center border-2 border-warning/30">
            <div className="text-xs text-muted-foreground mb-1">Anchor (1)</div>
            <div className="text-2xl font-bold text-warning">{primeSeal.weights.anchor}</div>
            <Sparkles className="w-4 h-4 mx-auto mt-1 text-warning" />
          </div>
        </div>
        
        {/* Current timeline marker */}
        {currentMarker && (
          <div className="p-3 bg-background/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-muted-foreground">Timeline Phase</div>
                <div className="font-bold">{currentMarker.marker}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">State</div>
                <Badge variant="outline">{currentMarker.seal_state}</Badge>
              </div>
            </div>
          </div>
        )}
        
        {/* Packet value */}
        <div className="text-center text-sm">
          <span className="text-muted-foreground">Packet Value: </span>
          <span className="font-bold text-primary">{primeSeal.packetValue.toFixed(3)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
