import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { requireFiniteNumber, requireFreshTimestamp } from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    const token = req.headers.get('Authorization')?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error: authError } = await authClient.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');
    const supabase = createClient(supabaseUrl, supabaseKey);

    const body = await req.json();
    const {
      temporal_id,
      signal_type,
      tier,
      strength,
      confidence,
      curvature,
      curvature_direction,
      ftcp_detected,
      golden_ratio_score,
      lighthouse_l,
      is_lhe,
      lighthouse_threshold,
      linear_coherence,
      nonlinear_coherence,
      cross_scale_coherence,
      anomaly_pointer,
      reasoning,
      coherence_boost,
      phase,
      frequency,
      metadata
    } = body;

    if (!temporal_id || !['BUY', 'SELL', 'HOLD'].includes(signal_type)) {
      throw new Error('INVALID_QGITA_SIGNAL: temporal_id and BUY/SELL/HOLD signal_type are required');
    }
    if (!metadata || typeof metadata !== 'object' || !String(metadata.symbol || '').trim()) {
      throw new Error('INVALID_QGITA_PROVENANCE: metadata.symbol is required');
    }
    if (metadata.truth_status !== 'real_derived' || metadata.generated_values !== false) {
      throw new Error('INVALID_QGITA_PROVENANCE: real_derived non-generated provenance is required');
    }
    if (!String(metadata.source_id || '').trim() || !String(metadata.source_timestamp || '').trim()) {
      throw new Error('INVALID_QGITA_PROVENANCE: metadata.source_id and metadata.source_timestamp are required');
    }
    requireFreshTimestamp(String(metadata.source_timestamp), 5 * 60 * 1000, 'metadata.source_timestamp');
    const validatedTier = requireFiniteNumber(tier, 'tier');
    const validatedStrength = requireFiniteNumber(strength, 'strength');
    const validatedConfidence = requireFiniteNumber(confidence, 'confidence');
    const validatedCoherenceBoost = coherence_boost == null
      ? null
      : requireFiniteNumber(coherence_boost, 'coherence_boost');
    const validatedFrequency = frequency == null
      ? null
      : requireFiniteNumber(frequency, 'frequency');
    if (![1, 2, 3, 4, 5].includes(validatedTier)) throw new Error('INVALID_QGITA_SIGNAL:tier');
    if (validatedConfidence < 0 || validatedConfidence > 100) throw new Error('INVALID_QGITA_SIGNAL:confidence');
    if (!String(phase || '').trim()) throw new Error('INVALID_QGITA_SIGNAL:phase');

    // Log with QGITA-style formatting
    const tierEmoji = tier === 1 ? '🥇' : tier === 2 ? '🥈' : '🥉';
    const signalEmoji = signal_type === 'BUY' ? '🟢' : signal_type === 'SELL' ? '🔴' : '⚪';
    console.log(
      `[ingest-qgita-signal] ${signalEmoji} ${signal_type} ${tierEmoji}T${tier} ` +
        `Conf:${validatedConfidence.toFixed(1)}% LHE:${is_lhe} FTCP:${ftcp_detected} ` +
      `temporal_id: ${temporal_id}`
    );

    const { data, error } = await supabase
      .from('qgita_signal_states')
      .insert({
        user_id: user.id,
        temporal_id,
        timestamp: metadata.source_timestamp,
        signal_type,
        tier: validatedTier,
        strength: validatedStrength,
        confidence: validatedConfidence,
        curvature: curvature == null ? null : requireFiniteNumber(curvature, 'curvature'),
        curvature_direction: curvature_direction ?? null,
        ftcp_detected: ftcp_detected ?? null,
        golden_ratio_score: golden_ratio_score == null ? null : requireFiniteNumber(golden_ratio_score, 'golden_ratio_score'),
        lighthouse_l: lighthouse_l == null ? null : requireFiniteNumber(lighthouse_l, 'lighthouse_l'),
        is_lhe: is_lhe ?? null,
        lighthouse_threshold: lighthouse_threshold == null ? null : requireFiniteNumber(lighthouse_threshold, 'lighthouse_threshold'),
        linear_coherence: linear_coherence == null ? null : requireFiniteNumber(linear_coherence, 'linear_coherence'),
        nonlinear_coherence: nonlinear_coherence == null ? null : requireFiniteNumber(nonlinear_coherence, 'nonlinear_coherence'),
        cross_scale_coherence: cross_scale_coherence == null ? null : requireFiniteNumber(cross_scale_coherence, 'cross_scale_coherence'),
        anomaly_pointer: anomaly_pointer == null ? null : requireFiniteNumber(anomaly_pointer, 'anomaly_pointer'),
        reasoning: reasoning ?? null,
        coherence_boost: validatedCoherenceBoost,
        phase,
        frequency: validatedFrequency,
        metadata: { ...metadata, generated_values: false },
        truth_status: 'real_derived',
        source_id: metadata.source_id,
        source_timestamp: metadata.source_timestamp,
        generated_values: false,
      })
      .select()
      .single();

    if (error) {
      console.error('[ingest-qgita-signal] Error:', error);
      throw error;
    }

    console.log(`[ingest-qgita-signal] Successfully ingested: ${data.id}`);

    return new Response(JSON.stringify({ success: true, data }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[ingest-qgita-signal] Error:', message);
    return new Response(JSON.stringify({ error: message }), {
      status: /AUTHENTICATION/.test(message) ? 401 : 409,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
