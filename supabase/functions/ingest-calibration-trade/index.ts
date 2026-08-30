import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

function finite(value: unknown, field: string, positive = false): number {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue) || (positive && numberValue <= 0)) {
    throw new Error(`INVALID_CALIBRATION_VALUE:${field}`);
  }
  return numberValue;
}

function requireLiveReceipt(value: any): { sourceId: string; sourceTimestamp: string } {
  const sourceId = String(value?.source_id || '').trim();
  const sourceTimestamp = String(value?.source_timestamp || '');
  const ageMs = Date.now() - Date.parse(sourceTimestamp);
  if (value?.truth_status !== 'live' || value?.generated_values !== false || !sourceId ||
      !Number.isFinite(ageMs) || ageMs < -300000 || ageMs > 300000) {
    throw new Error('FRESH_LIVE_CALIBRATION_RECEIPT_REQUIRED');
  }
  return { sourceId, sourceTimestamp };
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

    const supabase = createClient(supabaseUrl, serviceKey);
    const body = await req.json();
    const action = String(body.action || '');
    const trade = body.trade;

    if (action === 'log_entry') {
      const provenance = requireLiveReceipt(trade);
      const requiredStrings = ['temporal_id', 'symbol', 'side', 'frequency_band', 'exchange', 'order_id', 'regime'];
      for (const field of requiredStrings) {
        if (!String(trade?.[field] || '').trim()) throw new Error(`CALIBRATION_ENTRY_FIELD_REQUIRED:${field}`);
      }
      const entryTime = String(trade.entry_time || '');
      if (entryTime !== provenance.sourceTimestamp) throw new Error('CALIBRATION_ENTRY_TIMESTAMP_MUST_MATCH_RECEIPT');
      const side = String(trade.side).toUpperCase();
      if (!['BUY', 'SELL', 'LONG', 'SHORT'].includes(side)) throw new Error('INVALID_CALIBRATION_SIDE');
      const qgitaTier = finite(trade.qgita_tier, 'qgita_tier');
      if (!Number.isInteger(qgitaTier)) throw new Error('INVALID_QGITA_TIER');

      const row = {
        user_id: user.id,
        temporal_id: String(trade.temporal_id),
        symbol: String(trade.symbol).toUpperCase(),
        side,
        entry_price: finite(trade.entry_price, 'entry_price', true),
        entry_time: entryTime,
        quantity: finite(trade.quantity, 'quantity', true),
        position_size_usd: finite(trade.position_size_usd, 'position_size_usd', true),
        frequency_band: String(trade.frequency_band),
        prism_frequency: finite(trade.prism_frequency, 'prism_frequency', true),
        coherence_at_entry: finite(trade.coherence_at_entry, 'coherence_at_entry'),
        lambda_at_entry: finite(trade.lambda_at_entry, 'lambda_at_entry'),
        lighthouse_confidence: finite(trade.lighthouse_confidence, 'lighthouse_confidence'),
        hnc_probability: finite(trade.hnc_probability, 'hnc_probability'),
        qgita_tier: qgitaTier,
        exchange: String(trade.exchange).toLowerCase(),
        order_id: String(trade.order_id),
        regime: String(trade.regime),
        cosmic_phase: trade.cosmic_phase == null ? null : String(trade.cosmic_phase),
        is_forced: typeof trade.is_forced === 'boolean' ? trade.is_forced : null,
        metadata: trade.metadata ?? null,
        truth_status: 'live',
        source_id: provenance.sourceId,
        source_timestamp: provenance.sourceTimestamp,
        generated_values: false,
      };
      const { data, error } = await supabase.from('calibration_trades').insert(row).select().single();
      if (error || !data) throw new Error(`CALIBRATION_ENTRY_WRITE_FAILED:${error?.message || 'no row'}`);
      return new Response(JSON.stringify({
        success: true,
        data,
        truthStatus: 'live',
        sourceId: provenance.sourceId,
        sourceTimestamp: provenance.sourceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (action === 'log_exit') {
      const provenance = requireLiveReceipt(trade);
      if (!trade?.id || !trade?.exit_order_id || !trade?.exit_time) throw new Error('COMPLETE_EXIT_RECEIPT_REQUIRED');
      if (String(trade.exit_time) !== provenance.sourceTimestamp) throw new Error('CALIBRATION_EXIT_TIMESTAMP_MUST_MATCH_RECEIPT');
      const pnl = finite(trade.pnl, 'pnl');
      const pnlPercent = finite(trade.pnl_percent, 'pnl_percent');
      const derivedWin = pnl > 0;
      if (trade.is_win !== undefined && trade.is_win !== derivedWin) throw new Error('CALIBRATION_WIN_FLAG_CONTRADICTS_PNL');
      const { data, error } = await supabase
        .from('calibration_trades')
        .update({
          exit_price: finite(trade.exit_price, 'exit_price', true),
          exit_time: String(trade.exit_time),
          pnl,
          pnl_percent: pnlPercent,
          is_win: derivedWin,
          exit_source_id: provenance.sourceId,
          exit_source_timestamp: provenance.sourceTimestamp,
          exit_order_id: String(trade.exit_order_id),
          generated_values: false,
        })
        .eq('id', String(trade.id))
        .eq('user_id', user.id)
        .select()
        .single();
      if (error || !data) throw new Error(`CALIBRATION_EXIT_WRITE_FAILED:${error?.message || 'no row'}`);
      return new Response(JSON.stringify({
        success: true,
        data,
        truthStatus: 'live',
        sourceId: provenance.sourceId,
        sourceTimestamp: provenance.sourceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (action === 'get_calibration') {
      const limit = Number(body.limit);
      if (!Number.isInteger(limit) || limit <= 0 || limit > 1000) throw new Error('CALIBRATION_WINDOW_LIMIT_REQUIRED');
      const { data: trades, error } = await supabase
        .from('calibration_trades')
        .select('*')
        .eq('user_id', user.id)
        .not('exit_source_timestamp', 'is', null)
        .order('exit_source_timestamp', { ascending: false })
        .limit(limit);
      if (error) throw new Error(`CALIBRATION_READ_FAILED:${error.message}`);
      if (!trades || trades.length === 0) {
        return new Response(JSON.stringify({
          success: false,
          error: 'NO_PROVIDER_CONFIRMED_CLOSED_TRADES',
          calibration: null,
          trades: [],
          truthStatus: 'no_data',
          generatedValues: false,
        }), { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
      }

      const wins = trades.filter((item: any) => item.is_win === true);
      const pnlValues = trades.map((item: any) => finite(item.pnl, `${item.id}.pnl`));
      const pnlPercentValues = trades.map((item: any) => finite(item.pnl_percent, `${item.id}.pnl_percent`));
      const grossProfit = pnlValues.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
      const grossLoss = Math.abs(pnlValues.filter((value) => value < 0).reduce((sum, value) => sum + value, 0));
      const grouped = (field: 'frequency_band' | 'qgita_tier') => Object.fromEntries(
        [...new Set(trades.map((item: any) => String(item[field])))]
          .map((key) => {
            const rows = trades.filter((item: any) => String(item[field]) === key);
            return [key, {
              trades: rows.length,
              winRate: rows.filter((item: any) => item.is_win === true).length / rows.length,
              avgPnl: rows.reduce((sum: number, item: any) => sum + finite(item.pnl_percent, `${item.id}.pnl_percent`), 0) / rows.length,
            }];
          }),
      );
      const sourceTimestamp = String(trades[0].exit_source_timestamp);
      return new Response(JSON.stringify({
        success: true,
        calibration: {
          totalTrades: trades.length,
          winRate: wins.length / trades.length,
          avgPnlPercent: pnlPercentValues.reduce((sum, value) => sum + value, 0) / trades.length,
          profitFactor: grossLoss > 0 ? grossProfit / grossLoss : null,
          bandPerformance: grouped('frequency_band'),
          tierPerformance: grouped('qgita_tier'),
        },
        trades,
        truthStatus: 'real_derived',
        sourceId: 'supabase:calibration_trades:provider_receipts',
        sourceTimestamp,
        generatedValues: false,
      }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    throw new Error('INVALID_CALIBRATION_ACTION');
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[ingest-calibration-trade]', message);
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
