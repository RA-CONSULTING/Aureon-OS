import { ValidationTrace, ValidationStep } from '@/core/forceValidatedTrade';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle2, XCircle, Loader2, Clock, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ValidationTracePanelProps {
  trace: ValidationTrace | null;
  isRunning?: boolean;
}

const STEP_ICONS: Record<string, string> = {
  DataIngestion: '📊',
  MasterEquation: '🔮',
  LighthouseConsensus: '🏮',
  RainbowBridge: '🌈',
  Prism: '💎',
  'PrimeSeal10-9-1': '🔐',
  QGITASignal: '⚡',
  ElephantMemory: '🐘',
  SmartOrderRouter: '🛣️',
  TradeExecution: '🎯',
};

function StepRow({ step, isLast }: { step: ValidationStep; isLast: boolean }) {
  const icon = STEP_ICONS[step.name] || '•';
  
  return (
    <div className="relative">
      <div className={cn(
        'flex items-start gap-3 p-3 rounded-lg transition-colors',
        step.status === 'success' && 'bg-success/10',
        step.status === 'failed' && 'bg-destructive/10',
        step.status === 'running' && 'bg-primary/10 animate-pulse',
        step.status === 'pending' && 'bg-muted/50',
      )}>
        {/* Status icon */}
        <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
          {step.status === 'success' && <CheckCircle2 className="h-5 w-5 text-success" />}
          {step.status === 'failed' && <XCircle className="h-5 w-5 text-destructive" />}
          {step.status === 'running' && <Loader2 className="h-5 w-5 text-primary animate-spin" />}
          {step.status === 'pending' && <Clock className="h-5 w-5 text-muted-foreground" />}
        </div>

        {/* Step info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <span className="font-medium text-sm">Step {step.step}: {step.name}</span>
            <Badge variant={step.status === 'success' ? 'default' : step.status === 'failed' ? 'destructive' : 'secondary'} className="text-xs">
              {step.status.toUpperCase()}
            </Badge>
          </div>

          {/* Input/Output */}
          {step.output && (
            <div className="mt-2 text-xs font-mono bg-background/50 rounded p-2 overflow-x-auto">
              {Object.entries(step.output).slice(0, 5).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <span className="text-muted-foreground">{key}:</span>
                  <span className="text-foreground">
                    {typeof value === 'number' ? value.toFixed(4) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {step.error && (
            <div className="mt-2 text-xs text-destructive bg-destructive/10 rounded p-2">
              Error: {step.error}
            </div>
          )}
        </div>
      </div>

      {/* Connector arrow */}
      {!isLast && (
        <div className="flex justify-center py-1">
          <ArrowRight className="h-4 w-4 text-muted-foreground rotate-90" />
        </div>
      )}
    </div>
  );
}

export function ValidationTracePanel({ trace, isRunning }: ValidationTracePanelProps) {
  if (!trace && !isRunning) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Validation Trace</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            <p>No validation trace available</p>
            <p className="text-xs mt-1">Click "Force Cycle 1 Trade" to run validation</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const steps = trace?.steps || [];
  const completedSteps = steps.filter(s => s.status === 'success').length;
  const failedSteps = steps.filter(s => s.status === 'failed').length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Validation Trace</CardTitle>
          {trace && (
            <div className="flex items-center gap-2">
              <Badge variant={trace.success ? 'default' : 'destructive'}>
                {trace.success ? '✅ ALL PASSED' : `❌ ${failedSteps} FAILED`}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {completedSteps}/10 steps
              </span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-1">
            {isRunning && steps.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2">Running validation pipeline...</span>
              </div>
            ) : (
              steps.map((step, idx) => (
                <StepRow key={step.step} step={step} isLast={idx === steps.length - 1} />
              ))
            )}
          </div>
        </ScrollArea>

        {trace?.tradeId && (
          <div className="mt-4 pt-4 border-t text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Trade ID:</span>
              <span className="font-mono">{trace.tradeId.slice(0, 8)}...</span>
            </div>
            {trace.orderId && (
              <div className="flex justify-between mt-1">
                <span>Order ID:</span>
                <span className="font-mono">{trace.orderId}</span>
              </div>
            )}
            <div className="flex justify-between mt-1">
              <span>Duration:</span>
              <span>
                {trace.endTime && trace.startTime
                  ? `${(new Date(trace.endTime).getTime() - new Date(trace.startTime).getTime())}ms`
                  : '-'}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
