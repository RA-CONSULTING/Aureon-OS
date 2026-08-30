/**
 * HNC/Auris view over evidence-backed state. Canonical node frequencies are
 * shown as reference constants; they are never presented as sensor readings.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { Activity, Sparkles, Target, Atom } from 'lucide-react';
import type { GlobalState } from '@/core/globalSystemsManager';

interface QuantumTabContentProps {
  globalState: GlobalState;
}

const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const display = (value: number | null | undefined, decimals = 4): string =>
  finite(value) ? value.toFixed(decimals) : 'Unavailable';

const AURIS_REFERENCES = [
  { name: 'Tiger', frequency: 741, role: 'Momentum' },
  { name: 'Falcon', frequency: 852, role: 'Trend' },
  { name: 'Hummingbird', frequency: 963, role: 'HF Signals' },
  { name: 'Dolphin', frequency: 528, role: 'Harmony' },
  { name: 'Deer', frequency: 396, role: 'Fear/Greed' },
  { name: 'Owl', frequency: 432, role: 'Night' },
  { name: 'Panda', frequency: 412, role: 'Patience' },
  { name: 'Cargoship', frequency: 174, role: 'Volume' },
  { name: 'Clownfish', frequency: 639, role: 'Connection' },
] as const;

export function QuantumTabContent({ globalState }: QuantumTabContentProps) {
  const {
    coherence,
    lambda,
    dominantNode,
    prismLevel,
    prismState,
    substrate,
    observer,
    echo,
    prismOutput,
    busSnapshot,
  } = globalState;

  const frequency = finite(prismOutput?.frequency) ? prismOutput.frequency : null;
  const resonance = finite(prismOutput?.resonance) ? prismOutput.resonance : null;
  const is528Lock = finite(frequency) && frequency >= 520 && frequency <= 536;
  const coherenceReady = finite(coherence) && coherence >= 0.7;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Atom className="h-4 w-4 text-primary" />Λ(t) Master Equation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-3xl font-mono font-bold text-center">{display(lambda)}</div>
            <EquationRow label="Substrate S(t)" value={substrate} />
            <EquationRow label="Observer O(t)" value={observer} />
            <EquationRow label="Echo E(t)" value={echo} />
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Activity className="h-4 w-4 text-primary" />Γ Coherence Metric</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className={cn('text-3xl font-mono font-bold text-center', coherenceReady && 'text-success')}>
              {display(coherence)}
            </div>
            {finite(coherence) && <Progress value={Math.max(0, Math.min(100, coherence * 100))} className="h-3" />}
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Trade threshold: 0.70</span>
              <span className={coherenceReady ? 'text-success' : 'text-muted-foreground'}>
                {!finite(coherence) ? 'NO DATA' : coherenceReady ? 'READY' : 'WAITING'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" />The Prism</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className={cn('text-3xl font-mono font-bold text-center', is528Lock && 'text-success')}>
              {finite(frequency) ? `${frequency.toFixed(1)} Hz` : 'Unavailable'}
            </div>
            <div className="flex justify-between"><span className="text-muted-foreground">Lock</span><span>{!finite(frequency) ? 'No data' : is528Lock ? '528 Hz band' : 'Not locked'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Level</span><span>{finite(prismLevel) ? `${prismLevel}/5` : 'Unavailable'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">State</span><span>{prismState ?? 'Unavailable'}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Resonance</span><span>{finite(resonance) ? `${(resonance * 100).toFixed(0)}%` : 'Unavailable'}</span></div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2"><Target className="h-4 w-4 text-primary" />9 Auris node references</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground mb-3">Frequencies below are native HNC reference constants, not live sensor measurements.</p>
          <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
            {AURIS_REFERENCES.map((node) => (
              <div key={node.name} className={cn('flex flex-col items-center p-2 rounded-lg border', dominantNode === node.name ? 'border-primary bg-primary/10' : 'border-border/30')}>
                <span className="text-[10px] font-medium">{node.name}</span>
                <span className="text-[8px] text-muted-foreground">{node.frequency} Hz ref</span>
                <span className="text-[8px] text-muted-foreground">{node.role}</span>
                {dominantNode === node.name && <Badge className="text-[8px] mt-1 px-1">OBSERVED</Badge>}
              </div>
            ))}
          </div>
          {!dominantNode && <p className="text-xs text-muted-foreground text-center mt-3">No dominant Auris node has been observed.</p>}
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Evidence-publishing systems</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(busSnapshot?.states ?? {}).map(([name, state]) => (
            <div key={name} className="flex justify-between p-2 rounded border border-border/30 text-xs">
              <span>{name}</span>
              <span className="font-mono">Γ {display(state.coherence, 3)}</span>
            </div>
          ))}
          {Object.keys(busSnapshot?.states ?? {}).length === 0 && <p className="text-xs text-muted-foreground">No evidence-backed system observations are available.</p>}
        </CardContent>
      </Card>
    </div>
  );
}

function EquationRow({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div>
      <div className="flex justify-between text-xs"><span className="text-muted-foreground">{label}</span><span className="font-mono">{display(value)}</span></div>
      {finite(value) && <Progress value={Math.max(0, Math.min(100, Math.abs(value) * 100))} className="h-1 mt-1" />}
    </div>
  );
}
