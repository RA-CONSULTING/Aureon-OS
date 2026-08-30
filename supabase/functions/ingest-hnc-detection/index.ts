import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

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
    const authorization = req.headers.get('Authorization');
    const token = authorization?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error: authError } = await authClient.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');
    const supabase = createClient(supabaseUrl, supabaseKey);

    const body = await req.json();
    const {
      temporal_id,
      is_lighthouse_detected,
      schumann_power,
      anchor_power,
      love_power,
      unity_power,
      distortion_power,
      imperial_yield,
      harmonic_fidelity,
      bridge_status,
      metadata,
      truth_status,
      source_id,
      source_timestamp,
      generated_values,
    } = body;

    const sourceAgeMs = Date.now() - Date.parse(String(source_timestamp || ''));
    const numbers = [
      schumann_power,
      anchor_power,
      love_power,
      unity_power,
      distortion_power,
      imperial_yield,
      harmonic_fidelity,
    ];
    if (!temporal_id || typeof is_lighthouse_detected !== 'boolean' ||
        !bridge_status || !['live', 'real_derived'].includes(String(truth_status)) ||
        !source_id || generated_values !== false ||
        !Number.isFinite(sourceAgeMs) || sourceAgeMs < -300000 || sourceAgeMs > 300000 ||
        numbers.some((value) => !Number.isFinite(Number(value))) ||
        (metadata !== undefined && (metadata === null || Array.isArray(metadata) || typeof metadata !== 'object'))) {
      throw new Error('FRESH_REAL_HNC_OBSERVATION_REQUIRED');
    }

    console.log(`[ingest-hnc-detection] Ingesting state for temporal_id: ${temporal_id}`);

    const { data, error } = await supabase
      .from('hnc_detection_states')
      .insert({
        user_id: user.id,
        temporal_id,
        timestamp: source_timestamp,
        is_lighthouse_detected,
        schumann_power: Number(schumann_power),
        anchor_power: Number(anchor_power),
        love_power: Number(love_power),
        unity_power: Number(unity_power),
        distortion_power: Number(distortion_power),
        imperial_yield: Number(imperial_yield),
        harmonic_fidelity: Number(harmonic_fidelity),
        bridge_status,
        metadata: metadata ?? null,
        truth_status,
        source_id,
        source_timestamp,
        generated_values: false,
      })
      .select()
      .single();

    if (error) {
      console.error('[ingest-hnc-detection] Error:', error);
      throw error;
    }

    console.log(`[ingest-hnc-detection] Successfully ingested state: ${data.id}`);

    return new Response(JSON.stringify({
      success: true,
      data,
      truthStatus: truth_status,
      sourceId: source_id,
      sourceTimestamp: source_timestamp,
      generatedValues: false,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[ingest-hnc-detection] Error:', message);
    return new Response(JSON.stringify({ error: message }), {
      status: /AUTHENTICATION/.test(message) ? 401 : 409,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
