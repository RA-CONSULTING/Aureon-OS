import { useState, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

export interface HiveSession {
  id: string;
  user_id: string;
  root_hive_id: string;
  status: 'running' | 'paused' | 'stopped';
  initial_capital: number;
  current_equity: number;
  total_hives_spawned: number;
  total_agents: number;
  total_trades: number;
  steps_executed: number;
  started_at: string;
  stopped_at: string | null;
}

export interface HiveInstance {
  id: string;
  parent_hive_id: string | null;
  generation: number;
  initial_balance: number;
  current_balance: number;
  status: string;
  num_agents: number;
}

export interface HiveAgent {
  id: string;
  hive_id: string;
  agent_index: number;
  current_symbol: string;
  position_open: boolean;
  total_pnl: number;
  trades_count: number;
}

export function useQueenHive() {
  const [session, setSession] = useState<HiveSession | null>(null);
  const [hives, setHives] = useState<HiveInstance[]>([]);
  const [agents, setAgents] = useState<HiveAgent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const { toast } = useToast();

  // Fetch session status
  const fetchStatus = useCallback(async (sessionId: string) => {
    try {
      const { data, error } = await supabase.functions.invoke('queen-hive-orchestrator', {
        body: { action: 'status', sessionId },
      });

      if (error) throw error;

      if (data.success) {
        setSession(data.session);
        setHives(data.hives);
        setAgents(data.agents);
        setIsRunning(data.session.status === 'running');
      }
    } catch (error) {
      console.error('Failed to fetch hive status:', error);
    }
  }, []);

  // Start new hive session
  const startHive = useCallback(async (initialCapital: number, liveExecutionConfirmed: boolean) => {
    if (isStarting || isRunning) return;

    try {
      setIsStarting(true);
      
      const { data, error } = await supabase.functions.invoke('queen-hive-orchestrator', {
        body: { action: 'start', initialCapital, liveExecutionConfirmed },
      });

      if (error) throw error;

      if (data.success) {
        setSession(data.session);
        setIsRunning(true);
        
        toast({
          title: "🐝 Queen-Hive Deployed",
          description: data.message,
        });

        return data.session;
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      console.error('Failed to start hive:', error);
      toast({
        title: "❌ Failed to Start Hive",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive",
      });
      setIsRunning(false);
    } finally {
      setIsStarting(false);
    }
  }, [isStarting, isRunning, toast]);

  // Execute trading step
  const executeStep = useCallback(async (sessionId: string) => {
    try {
      const { data, error } = await supabase.functions.invoke('queen-hive-orchestrator', {
        body: { action: 'step', sessionId },
      });

      if (error) throw error;

      if (data.success) {
        // Fetch updated status
        await fetchStatus(sessionId);

        const equityText = Number.isFinite(Number(data.equity)) ? `$${Number(data.equity).toFixed(2)}` : 'unavailable';
        console.log(`Live step ${data.step}: ${data.trades} provider-confirmed trades, ${equityText} equity`);
        toast({
          title: 'Live step completed',
          description: `${data.trades} provider-confirmed trades; ${data.skipped?.length ?? 0} routes skipped`,
        });
      } else {
        throw new Error(data.error || 'LIVE_STEP_FAILED');
      }
    } catch (error) {
      console.error('Failed to execute step:', error);
    }
  }, [fetchStatus, toast]);

  // Stop hive session
  const stopHive = useCallback(async (sessionId: string) => {
    try {
      setIsRunning(false);

      const { data, error } = await supabase.functions.invoke('queen-hive-orchestrator', {
        body: { action: 'stop', sessionId },
      });

      if (error) throw error;

      if (data.success) {
        toast({
          title: "🛑 Queen-Hive Stopped",
          description: "All trading activity halted",
        });

        // Fetch final status
        await fetchStatus(sessionId);
      }
    } catch (error) {
      console.error('Failed to stop hive:', error);
      toast({
        title: "❌ Failed to Stop Hive",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive",
      });
    }
  }, [toast, fetchStatus]);

  // Manual step execution (for testing)
  const manualStep = useCallback(async () => {
    if (!session) return;
    await executeStep(session.id);
  }, [session, executeStep]);

  // ROI calculation
  const roi = session && Number.isFinite(session.current_equity) && session.initial_capital > 0
    ? ((session.current_equity - session.initial_capital) / session.initial_capital) * 100
    : null;

  return {
    session,
    hives,
    agents,
    isRunning,
    isStarting,
    roi,
    startHive,
    stopHive,
    manualStep,
    fetchStatus,
  };
}
