import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { finiteOrNull, readingText } from '@/lib/reading';

interface GasTankState {
  balance: number | null;
  initialBalance: number | null;
  highWaterMark: number | null;
  feeRate: number | null;
  membershipType: 'founder' | 'standard';
  feesPaidToday: number | null;
  totalFeesPaid: number | null;
  status: 'ACTIVE' | 'LOW' | 'CRITICAL' | 'EMPTY' | 'PAUSED';
  canTrade: boolean;
  isLoading: boolean;
}

export const useGasTank = (userId: string | null) => {
  const { toast } = useToast();
  const [state, setState] = useState<GasTankState>({
    balance: null,
    initialBalance: null,
    highWaterMark: null,
    feeRate: null,
    membershipType: 'standard',
    feesPaidToday: null,
    totalFeesPaid: null,
    status: 'PAUSED',
    canTrade: false,
    isLoading: true,
  });

  // Fetch initial gas tank data
  useEffect(() => {
    if (!userId) {
      setState(prev => ({ ...prev, isLoading: false }));
      return;
    }

    const fetchGasTank = async () => {
      const { data, error } = await supabase
        .from('gas_tank_accounts')
        .select('*')
        .eq('user_id', userId)
        .single();

      if (error && error.code !== 'PGRST116') {
        console.error('Error fetching gas tank:', error);
        setState(prev => ({ ...prev, isLoading: false }));
        return;
      }

      if (data) {
        setState({
          balance: finiteOrNull(data.balance),
          initialBalance: finiteOrNull(data.initial_balance),
          highWaterMark: finiteOrNull(data.high_water_mark),
          feeRate: finiteOrNull(data.fee_rate),
          membershipType: data.membership_type as 'founder' | 'standard',
          feesPaidToday: finiteOrNull(data.fees_paid_today),
          totalFeesPaid: finiteOrNull(data.total_fees_paid),
          status: data.status as any,
          canTrade: data.balance > 0 && data.status !== 'PAUSED' && data.status !== 'EMPTY',
          isLoading: false,
        });
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    fetchGasTank();
  }, [userId]);

  // Subscribe to real-time updates
  useEffect(() => {
    if (!userId) return;

    const channel = supabase
      .channel('gas-tank-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'gas_tank_accounts',
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          console.log('Gas tank updated:', payload);
          const data = payload.new as any;
          
          if (data) {
            const newState = {
              balance: finiteOrNull(data.balance),
              initialBalance: finiteOrNull(data.initial_balance),
              highWaterMark: finiteOrNull(data.high_water_mark),
              feeRate: finiteOrNull(data.fee_rate),
              membershipType: data.membership_type as 'founder' | 'standard',
              feesPaidToday: finiteOrNull(data.fees_paid_today),
              totalFeesPaid: finiteOrNull(data.total_fees_paid),
              status: data.status as any,
              canTrade: data.balance > 0 && data.status !== 'PAUSED' && data.status !== 'EMPTY',
              isLoading: false,
            };

            setState(newState);

            // Show status change toasts
            if (data.status === 'LOW' && state.status !== 'LOW') {
              toast({
                title: '🟡 Gas Tank Low',
                description: `Balance: ${readingText(data.balance, (balance) => `£${balance.toFixed(2)}`)}. Consider topping up.`,
                variant: 'default',
              });
            } else if (data.status === 'CRITICAL' && state.status !== 'CRITICAL') {
              toast({
                title: '🔴 Gas Tank Critical',
                description: `Balance: ${readingText(data.balance, (balance) => `£${balance.toFixed(2)}`)}. Top up soon!`,
                variant: 'destructive',
              });
            } else if (data.status === 'EMPTY' && state.status !== 'EMPTY') {
              toast({
                title: '⚫ Gas Tank Empty',
                description: 'Trading paused. Please top up to resume.',
                variant: 'destructive',
              });
            }
          }
        }
      )
      .subscribe();

    // Subscribe to transactions for fee deduction notifications
    const transactionsChannel = supabase
      .channel('gas-tank-transactions')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'gas_tank_transactions',
        },
        async (payload) => {
          const transaction = payload.new as any;
          
          // Check if this transaction belongs to current user
          const { data: account } = await supabase
            .from('gas_tank_accounts')
            .select('user_id')
            .eq('id', transaction.account_id)
            .single();

          if (account && account.user_id === userId && transaction.type === 'FEE_DEDUCTION') {
            // Play sound effect
            const audio = new Audio('/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(console.error);

            toast({
              title: '⛽ Fee Deducted',
              description: `£${Math.abs(parseFloat(transaction.amount)).toFixed(2)} performance fee deducted`,
              variant: 'default',
            });
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      supabase.removeChannel(transactionsChannel);
    };
  }, [userId, state.status, toast]);

  const topUp = async (amount: number, membershipType: 'founder' | 'standard' = 'standard') => {
    if (!userId) {
      toast({
        title: 'Error',
        description: 'User not authenticated',
        variant: 'destructive',
      });
      return { success: false };
    }

    try {
      const { data, error } = await supabase.functions.invoke('gas-tank-topup', {
        body: { userId, amount, membershipType },
      });

      if (error) throw error;

      if (data.success) {
        toast({
          title: '✅ Top-up Successful',
          description: `Added £${amount.toFixed(2)} to your gas tank`,
          variant: 'default',
        });
        return { success: true, data: data.account };
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      console.error('Top-up error:', error);
      toast({
        title: 'Top-up Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
      return { success: false };
    }
  };

  return {
    ...state,
    topUp,
  };
};
