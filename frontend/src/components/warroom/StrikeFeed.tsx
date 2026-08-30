import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Trash2, CheckCircle, XCircle, Clock, Zap } from 'lucide-react';
import type { StrikeEvent } from '@/hooks/useStrikeFeed';

interface StrikeFeedProps {
  events: StrikeEvent[];
  executionCount: { success: number; failed: number };
  onClear: () => void;
}

export function StrikeFeed({ events, executionCount, onClear }: StrikeFeedProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-destructive" />;
      default:
        return <Clock className="h-4 w-4 text-warning" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'border-l-green-500 bg-success/5';
      case 'failed':
        return 'border-l-red-500 bg-destructive/5';
      default:
        return 'border-l-yellow-500 bg-warning/5';
    }
  };

  const renderEvent = (event: StrikeEvent) => (
    <div
      key={event.id}
      className={`flex items-start gap-3 p-3 rounded-lg border-l-4 ${getStatusColor(event.status)} transition-all hover:bg-background/80`}
    >
      <div className="mt-0.5">
        {getStatusIcon(event.status)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-muted-foreground">
            {formatTime(event.timestamp)}
          </span>
          {event.symbol && (
            <Badge variant="outline" className="text-xs">
              {event.symbol}
            </Badge>
          )}
          {event.coherence && (
            <Badge variant="secondary" className="text-xs">
              Γ {event.coherence.toFixed(3)}
            </Badge>
          )}
          {event.lighthouse && (
            <Badge variant="secondary" className="text-xs">
              L {event.lighthouse.toFixed(3)}
            </Badge>
          )}
        </div>
        <p className="text-sm">{event.message}</p>
        {event.pnl !== undefined && (
          <p className={`text-xs mt-1 ${event.pnl >= 0 ? 'text-success' : 'text-destructive'}`}>
            P&L: {event.pnl >= 0 ? '+' : ''}${event.pnl.toFixed(2)}
          </p>
        )}
      </div>
    </div>
  );

  const executions = events.filter(e => e.type === 'execution');
  const lighthouseEvents = events.filter(e => e.type === 'lighthouse');
  const errors = events.filter(e => e.status === 'failed');

  return (
    <Card className="p-4 bg-card/50 backdrop-blur border-primary/20">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Zap className="h-5 w-5 text-warning" />
          📋 LIVE STRIKE FEED ({events.length})
        </h3>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-success/10">
            ✅ {executionCount.success}
          </Badge>
          <Badge variant="outline" className="bg-destructive/10">
            ❌ {executionCount.failed}
          </Badge>
          <Button size="sm" variant="ghost" onClick={onClear}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="all">All ({events.length})</TabsTrigger>
          <TabsTrigger value="lhe">LHE ({lighthouseEvents.length})</TabsTrigger>
          <TabsTrigger value="errors">Errors ({errors.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <ScrollArea className="h-[500px]">
            <div className="space-y-2">
              {events.map(renderEvent)}
              {events.length === 0 && (
                <div className="text-center text-muted-foreground py-12">
                  💤 No activity yet
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="lhe">
          <ScrollArea className="h-[500px]">
            <div className="space-y-2">
              {lighthouseEvents.map(renderEvent)}
              {lighthouseEvents.length === 0 && (
                <div className="text-center text-muted-foreground py-12">
                  🔦 No Lighthouse Events detected
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="errors">
          <ScrollArea className="h-[500px]">
            <div className="space-y-2">
              {errors.map(renderEvent)}
              {errors.length === 0 && (
                <div className="text-center text-muted-foreground py-12">
                  ✅ No errors - all systems operational
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
