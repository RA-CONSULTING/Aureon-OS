import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const NUMBER_FIELDS = new Set([
  'fear_greed', 'btc_price', 'btc_dominance', 'btc_change_24h',
  'manipulation_probability', 'truth_score', 'spoof_score',
  'prediction_confidence', 'overall_accuracy', 'total_predictions',
  'bullish_accuracy', 'bearish_accuracy', 'evolved_generation',
  'evolved_win_rate', 'quantum_coherence', 'planetary_gamma',
  'cascade_multiplier', 'lambda_field', 'probability_edge',
  'harmonic_signal', 'hnc_probability', 'sandbox_generation',
  'sandbox_win_rate', 'position_size_pct', 'piano_lambda',
  'piano_coherence', 'diamond_coherence', 'diamond_phi_alignment',
]);

const ARRAY_FIELDS = new Set([
  'red_flags', 'green_flags', 'council_arguments', 'self_critique', 'speculations',
]);

const OBJECT_FIELDS = new Set([
  'live_pulse', 'wisdom_consensus', 'civilization_actions', 'dreams',
  'exit_targets', 'reflection', 'full_state',
]);

const BOOLEAN_FIELDS = new Set(['is_lighthouse', 'should_trade']);

const STRING_FIELDS = new Set([
  'fear_greed_class', 'council_consensus', 'council_action', 'brain_directive',
  'learning_directive', 'prediction_direction', 'entry_filter_reason', 'rainbow_state',
]);

serve(async (req) => {
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

    const payload = await req.json();
    const truthStatus = String(payload.truth_status || '');
    const sourceId = String(payload.source_id || '').trim();
    const sourceTimestamp = String(payload.source_timestamp || '');
    const sourceAgeMs = Date.now() - Date.parse(sourceTimestamp);
    if (!['live', 'real_derived'].includes(truthStatus) || !sourceId ||
        payload.generated_values !== false || !Number.isFinite(sourceAgeMs) ||
        sourceAgeMs < -300000 || sourceAgeMs > 300000) {
      throw new Error('FRESH_REAL_BRAIN_STATE_PROVENANCE_REQUIRED');
    }

    const row: Record<string, unknown> = {
      user_id: user.id,
      timestamp: sourceTimestamp,
      truth_status: truthStatus,
      source_id: sourceId,
      source_timestamp: sourceTimestamp,
      generated_values: false,
    };

    for (const field of NUMBER_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
      const value = Number(payload[field]);
      if (!Number.isFinite(value)) throw new Error(`INVALID_BRAIN_STATE_NUMBER:${field}`);
      row[field] = value;
    }
    for (const field of ARRAY_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
      if (!Array.isArray(payload[field])) throw new Error(`INVALID_BRAIN_STATE_ARRAY:${field}`);
      row[field] = payload[field];
    }
    for (const field of OBJECT_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
      const value = payload[field];
      if (value === null || Array.isArray(value) || typeof value !== 'object') {
        throw new Error(`INVALID_BRAIN_STATE_OBJECT:${field}`);
      }
      row[field] = value;
    }
    for (const field of BOOLEAN_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
      if (typeof payload[field] !== 'boolean') throw new Error(`INVALID_BRAIN_STATE_BOOLEAN:${field}`);
      row[field] = payload[field];
    }
    for (const field of STRING_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
      if (typeof payload[field] !== 'string' || !payload[field].trim()) {
        throw new Error(`INVALID_BRAIN_STATE_STRING:${field}`);
      }
      row[field] = payload[field].trim();
    }

    if (Object.keys(row).length === 6) throw new Error('BRAIN_STATE_MEASUREMENTS_REQUIRED');
    const supabase = createClient(supabaseUrl, serviceKey);
    const { data, error } = await supabase.from('brain_states').insert(row).select().single();
    if (error || !data) throw new Error(`BRAIN_STATE_WRITE_FAILED:${error?.message || 'no row'}`);

    return new Response(JSON.stringify({
      success: true,
      id: data.id,
      truthStatus,
      sourceId,
      sourceTimestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[ingest-brain-state]', message);
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
