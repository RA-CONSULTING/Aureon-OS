import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useState, useRef } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { Volume2, VolumeX } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface StrikeEvent {
  id: string;
  timestamp: string;
  type: 'execution' | 'lhe' | 'position_close';
  message: string;
  severity: 'info' | 'success' | 'critical';
}

export function LiveStrikeStream() {
  const [events, setEvents] = useState<StrikeEvent[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const [soundEnabled, setSoundEnabled] = useState(true);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Initialize audio
  useEffect(() => {
    audioRef.current = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBjaO1fPTgjMGHm7A7+OZQQ0PVqzn77BaGAg+ltv1xWwcBiuF0PLaizsKFl+z7OqnVRQKRp/g8r5sIQY2j9Xz04IzBh5uwO/jmUENEFar5++xWhgIPpbb9cVsHAYrhdDy2os7ChZfs+zqp1UUCkaf4PK+bCEGNo/V89OCMwYebsDv45lBDRBWq+fvsVoYCD6W2/XFbBwGK4XQ8tqLOwoWX7Ps6qdVFApGn+DyvmwhBjaP1fPTgjMGHm7A7+OZQQ0QVqvn77FaGAg+ltv1xWwcBiuF0PLaizsKFl+z7OqnVRQKRp/g8r5sIQY2j9Xz04IzBh5uwO/jmUENEFar5++xWhgIPpbb9cVsHAYrhdDy2os7ChZfs+zqp1UUCkaf4PK+bCEGNo/V89OCMwYebsDv45lBDRBWq+fvsVoYCD6W2/XFbBwGK4XQ8tqLOwoWX7Ps6qdVFApGn+DyvmwhBjaP1fPTgjMGHm7A7+OZQQ0QVqvn77FaGAg+ltv1xWwcBiuF0PLaizsKFl+z7OqnVRQKRp/g8r5sIQY2j9Xz04IzBh5uwO/jmUENEFar5++xWhgIPpbb9cVsHAYrhdDy2os7ChZfs+zqp1UUCkaf4PK+bCEGNo/V89OCMwYebsDv45lBDRBWq+fvsVoYCD6W2/XFbBwGK4XQ8tqLOwoWX7Ps6qdVFApGn+DyvmwhBjaP1fPTgjMGHm7A7+OZQQ0QVqvn77FaGAg=');
  }, []);

  const playSound = () => {
    if (soundEnabled && audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(e => console.log('Sound play failed:', e));
    }
  };

  useEffect(() => {
    // Subscribe to real-time trading executions
    const channel = supabase
      .channel('strike-stream')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'trading_executions',
        },
        (payload: any) => {
          const exec = payload.new;
          const severity: 'info' | 'success' | 'critical' = exec.status === 'executed' ? 'success' : 'info';
          const newEvent = {
            id: exec.id,
            timestamp: exec.executed_at || exec.created_at,
            type: 'execution' as const,
            message: `${exec.side} ${exec.symbol} @ $${exec.executed_price?.toFixed(2) || 'MARKET'}`,
            severity,
          };
          
          setEvents(prev => [newEvent, ...prev].slice(0, 50));
          
          // Show toast notification for trades
          toast({
            title: ` ${exec.side} Trade Executed`,
            description: `${exec.symbol} @ $${exec.executed_price?.toFixed(2) || 'MARKET'} | Coherence: ${(exec.coherence * 100).toFixed(1)}%`,
            duration: 3000,
          });
          
          playSound();
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'lighthouse_events',
        },
        (payload: any) => {
          const event = payload.new;
          if (event.is_lhe) {
            const newEvent = {
              id: event.id,
              timestamp: event.timestamp,
              type: 'lhe' as const,
              message: ` LHE DETECTED - Γ=${(event.coherence * 100).toFixed(1)}% L=${event.lighthouse_signal.toFixed(2)}`,
              severity: 'critical' as const,
            };
            
            setEvents(prev => [newEvent, ...prev].slice(0, 50));
            
            // Show critical toast for LHE events
            toast({
              title: ' LIGHTHOUSE HARMONIC EVENT',
              description: `Coherence: ${(event.coherence * 100).toFixed(1)}% | Signal: ${event.lighthouse_signal.toFixed(2)}`,
              variant: 'destructive',
              duration: 5000,
            });
            
            playSound();
          }
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'trading_positions',
        },
        (payload: any) => {
          const position = payload.new;
          if (position.status === 'closed' && position.realized_pnl) {
            const pnl = parseFloat(String(position.realized_pnl));
            const severity: 'info' | 'success' | 'critical' = pnl > 0 ? 'success' : 'info';
            setEvents(prev => [
              {
                id: position.id,
                timestamp: position.closed_at,
                type: 'position_close' as const,
                message: `Position closed: ${position.symbol} P&L $${pnl.toFixed(2)}`,
                severity,
              },
              ...prev,
            ].slice(0, 50));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  // Auto-scroll to top on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-destructive text-destructive-foreground';
      case 'success': return 'bg-success/20 text-success border-success/50';
      default: return 'bg-primary/20 text-primary border-primary/50';
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span> Live Strike Stream</span>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{events.length} events</Badge>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="h-8 w-8"
            >
              {soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-80" ref={scrollRef}>
          <div className="space-y-2">
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Waiting for strikes...
              </p>
            ) : (
              events.map((event) => (
                <div
                  key={event.id}
                  className={`p-3 rounded-lg border ${getSeverityColor(event.severity)}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium flex-1">{event.message}</p>
                    <p className="text-xs opacity-70 whitespace-nowrap">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
