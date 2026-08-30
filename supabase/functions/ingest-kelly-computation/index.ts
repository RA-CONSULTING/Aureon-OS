import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

function configuredPositive(name: string): number {
  const value = Number(Deno.env.get(name));
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name}_NOT_CONFIGURED`);
  return value;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')?.trim();
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')?.trim();
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')?.trim();
    if (!supabaseUrl || !serviceKey || !anonKey) throw new Error('SUPABASE_RUNTIME_NOT_CONFIGURED');
    const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error: authError } = await authClient.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

    const lookbackTrades = configuredPositive('KELLY_LOOKBACK_TRADES');
    const maxSampleAgeHours = configuredPositive('KELLY_MAX_SAMPLE_AGE_HOURS');
    const maxPositionPct = configuredPositive('KELLY_MAX_POSITION_PCT');
    const minPositionPct = configuredPositive('KELLY_MIN_POSITION_PCT');
    if (!Number.isInteger(lookbackTrades) || lookbackTrades > 10000 || minPositionPct > maxPositionPct || maxPositionPct > 100) {
      throw new Error('INVALID_KELLY_CONFIGURATION');
    }

    const supabase = createClient(supabaseUrl, serviceKey);
    const { data: trades, error: fetchError } = await supabase
      .from('calibration_trades')
      .select('id, pnl_percent, is_win, exit_source_id, exit_source_timestamp, generated_values')
      .eq('user_id', user.id)
      .eq('truth_status', 'live')
      .eq('generated_values', false)
      .not('exit_source_timestamp', 'is', null)
      .order('exit_source_timestamp', { ascending: false })
      .limit(lookbackTrades);
    if (fetchError) throw new Error(`KELLY_SAMPLE_READ_FAILED:${fetchError.message}`);
    if (!trades || trades.length === 0) throw new Error('KELLY_PROVIDER_TRADE_SAMPLE_REQUIRED');

    const sourceTimestamp = String(trades[0].exit_source_timestamp || '');
    const sourceAgeMs = Date.now() - Date.parse(sourceTimestamp);
    if (!Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > maxSampleAgeHours * 60 * 60 * 1000) {
      throw new Error('KELLY_TRADE_SAMPLE_STALE');
    }

    const wins = trades.filter((trade: any) => trade.is_win === true);
    const losses = trades.filter((trade: any) => trade.is_win === false);
    if (wins.length === 0 || losses.length === 0) throw new Error('KELLY_REQUIRES_OBSERVED_WINS_AND_LOSSES');
    const winValues = wins.map((trade: any) => Number(trade.pnl_percent));
    const lossValues = losses.map((trade: any) => Math.abs(Number(trade.pnl_percent)));
    if (winValues.some((value) => !Number.isFinite(value) || value <= 0) ||
        lossValues.some((value) => !Number.isFinite(value) || value <= 0)) {
      throw new Error('KELLY_SAMPLE_HAS_INVALID_PNL');
    }

    const totalTrades = trades.length;
    const winRate = wins.length / totalTrades;
    const avgWin = winValues.reduce((sum, value) => sum + value, 0) / winValues.length;
    const avgLoss = lossValues.reduce((sum, value) => sum + value, 0) / lossValues.length;
    const winLossRatio = avgWin / avgLoss;
    const rawKellyFraction = (winLossRatio * winRate - (1 - winRate)) / winLossRatio;
    const kellyFraction = Math.max(0, Math.min(rawKellyFraction, maxPositionPct / 100));
    const kellyHalf = kellyFraction / 2;
    const kellyQuarter = kellyFraction / 4;
    const recommendedPositionPct = Math.min(kellyHalf * 100, maxPositionPct);
    const computedAt = new Date().toISOString();

    const record = {
      user_id: user.id,
      temporal_id: `kelly:${user.id}:${sourceTimestamp}:${totalTrades}`,
      timestamp: computedAt,
      total_trades: totalTrades,
      winning_trades: wins.length,
      losing_trades: losses.length,
      win_rate: winRate,
      avg_win: avgWin,
      avg_loss: avgLoss,
      win_loss_ratio: winLossRatio,
      kelly_fraction: kellyFraction,
      kelly_half: kellyHalf,
      kelly_quarter: kellyQuarter,
      recommended_position_pct: recommendedPositionPct,
      max_position_pct: maxPositionPct,
      min_position_pct: minPositionPct,
      metadata: {
        formula: 'kelly=(b*p-(1-p))/b; recommendation=half-kelly bounded by configured maximum',
        sample_trade_ids: trades.map((trade: any) => trade.id),
        sample_size: totalTrades,
        computed_at: computedAt,
      },
      truth_status: 'real_derived',
      source_id: 'supabase:calibration_trades:provider_exit_receipts',
      source_timestamp: sourceTimestamp,
      generated_values: false,
    };
    const { data, error } = await supabase.from('kelly_computation_states').insert(record).select().single();
    if (error || !data) throw new Error(`KELLY_STATE_WRITE_FAILED:${error?.message || 'no row'}`);

    return new Response(JSON.stringify({
      success: true,
      id: data.id,
      kellyFraction,
      recommendedPositionPct,
      winRate,
      truthStatus: 'real_derived',
      sourceId: record.source_id,
      sourceTimestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[ingest-kelly-computation]', message);
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
