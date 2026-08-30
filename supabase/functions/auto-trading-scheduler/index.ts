import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7';
import { requireFiniteNumber, requireFreshTimestamp } from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface SchedulerConfig {
  enabled: boolean;
  min_coherence_threshold: number;
  require_lhe_in_window: boolean;
  cooldown_hours: number;
  max_daily_executions: number;
}

function validateConfig(value: unknown): SchedulerConfig {
  if (!value || typeof value !== 'object') throw new Error('EXPLICIT_SCHEDULER_CONFIG_REQUIRED');
  const config = value as Record<string, unknown>;
  if (typeof config.enabled !== 'boolean' || typeof config.require_lhe_in_window !== 'boolean') {
    throw new Error('INVALID_SCHEDULER_BOOLEAN_CONFIG');
  }
  const min = requireFiniteNumber(config.min_coherence_threshold, 'min_coherence_threshold');
  const cooldown = requireFiniteNumber(config.cooldown_hours, 'cooldown_hours');
  const maxDaily = requireFiniteNumber(config.max_daily_executions, 'max_daily_executions');
  if (min < 0 || min > 1 || cooldown < 0 || !Number.isInteger(maxDaily) || maxDaily < 0) {
    throw new Error('INVALID_SCHEDULER_CONFIG_RANGE');
  }
  return {
    enabled: config.enabled,
    min_coherence_threshold: min,
    require_lhe_in_window: config.require_lhe_in_window,
    cooldown_hours: cooldown,
    max_daily_executions: maxDaily,
  };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')?.trim();
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
    if (!supabaseUrl || !anonKey || !serviceKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');

    const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error: authError } = await authClient.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

    const { config: rawConfig } = await req.json();
    const config = validateConfig(rawConfig);
    if (!config.enabled) {
      return new Response(JSON.stringify({
        success: true,
        recommendation: 'none',
        reason: 'Scheduler disabled by supplied owner configuration',
        requiresOwnerConfirmation: true,
        truthStatus: 'no_data',
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const supabase = createClient(supabaseUrl, serviceKey);
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('is_trading_active')
      .eq('user_id', user.id)
      .single();
    if (sessionError || !session) throw new Error('USER_SESSION_NOT_FOUND');

    const cutoff = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const { data: signal, error: signalError } = await supabase
      .from('qgita_signal_states')
      .select('id, signal_type, tier, confidence, cross_scale_coherence, is_lhe, truth_status, source_id, source_timestamp, generated_values')
      .eq('user_id', user.id)
      .eq('truth_status', 'real_derived')
      .eq('generated_values', false)
      .gte('source_timestamp', cutoff)
      .order('source_timestamp', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (signalError) throw new Error(`QGITA_SIGNAL_READ_FAILED:${signalError.message}`);
    if (!signal) throw new Error('NO_FRESH_QGITA_OBSERVATION');
    requireFreshTimestamp(String(signal.source_timestamp), 5 * 60 * 1000, 'qgita.source_timestamp');

    const coherence = requireFiniteNumber(signal.cross_scale_coherence, 'qgita.cross_scale_coherence');
    const confidence = requireFiniteNumber(signal.confidence, 'qgita.confidence');
    const signalType = String(signal.signal_type).toUpperCase();
    const tier = requireFiniteNumber(signal.tier, 'qgita.tier');
    if (coherence < 0 || coherence > 1 || confidence < 0 || confidence > 100 ||
        !['BUY', 'SELL', 'HOLD'].includes(signalType) || ![1, 2, 3, 4, 5].includes(tier)) {
      throw new Error('INVALID_QGITA_OBSERVATION');
    }

    const todayStart = new Date();
    todayStart.setUTCHours(0, 0, 0, 0);
    const { count: dailyExecutions, error: executionError } = await supabase
      .from('trading_executions')
      .select('id', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('truth_status', 'live')
      .eq('generated_values', false)
      .gte('source_timestamp', todayStart.toISOString());
    if (executionError || dailyExecutions === null) throw new Error('LIVE_EXECUTION_COUNT_FAILED');

    const { data: latestExecution, error: latestExecutionError } = await supabase
      .from('trading_executions')
      .select('source_timestamp')
      .eq('user_id', user.id)
      .eq('truth_status', 'live')
      .eq('generated_values', false)
      .order('source_timestamp', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (latestExecutionError) throw new Error('LATEST_LIVE_EXECUTION_READ_FAILED');
    const lastExecutionTime = latestExecution?.source_timestamp
      ? Date.parse(latestExecution.source_timestamp)
      : null;
    const cooldownReady = lastExecutionTime === null ||
      Date.now() - lastExecutionTime >= config.cooldown_hours * 60 * 60 * 1000;

    const qgitaActionable = ['BUY', 'SELL'].includes(signalType) && tier <= 2;
    const coherenceReady = coherence >= config.min_coherence_threshold;
    const lighthouseReady = !config.require_lhe_in_window || signal.is_lhe === true;
    const limitReady = dailyExecutions < config.max_daily_executions;
    const recommendation = qgitaActionable && coherenceReady && lighthouseReady && limitReady && cooldownReady
      ? 'enable'
      : session.is_trading_active ? 'disable' : 'none';

    const reasons = [
      !qgitaActionable && 'QGITA is not actionable',
      !coherenceReady && 'Coherence is below the supplied HNC threshold',
      !lighthouseReady && 'A Lighthouse Event is required but not observed',
      !limitReady && 'Daily live-execution limit reached',
      !cooldownReady && 'Live-execution cooldown is still active',
    ].filter(Boolean);

    return new Response(JSON.stringify({
      success: true,
      recommendation,
      reason: reasons.length > 0 ? reasons.join('; ') : 'Fresh QGITA coherence conditions are satisfied',
      currentTradingState: session.is_trading_active === true,
      requiresOwnerConfirmation: true,
      observation: {
        qgitaSignalId: signal.id,
        signalType,
        tier,
        coherence,
        confidence,
        isLhe: signal.is_lhe,
        dailyExecutions,
        lastExecutionSourceTimestamp: latestExecution?.source_timestamp ?? null,
      },
      truthStatus: 'real_derived',
      sourceId: signal.source_id,
      sourceTimestamp: signal.source_timestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return new Response(JSON.stringify({
      success: false,
      error: message,
      truthStatus: 'no_data',
      generatedValues: false,
    }), {
      status: /AUTHENTICATION/.test(message) ? 401 : 409,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
