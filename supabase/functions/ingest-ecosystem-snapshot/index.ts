import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { requireFiniteNumber, requireFreshTimestamp } from '../_shared/real_data.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

function requireInteger(value: unknown, field: string): number {
  const parsed = requireFiniteNumber(value, field);
  if (!Number.isInteger(parsed)) throw new Error(`INVALID_INTEGER:${field}`);
  return parsed;
}

function requireObject(value: unknown, field: string): Record<string, unknown> {
  if (value === null || Array.isArray(value) || typeof value !== 'object') {
    throw new Error(`INVALID_OBJECT:${field}`);
  }
  return value as Record<string, unknown>;
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

    const payload = await req.json();
    const temporalId = String(payload.temporal_id || '').trim();
    const truthStatus = String(payload.truth_status || '').trim();
    const sourceId = String(payload.source_id || '').trim();
    const sourceEventId = String(payload.source_event_id || '').trim();
    const sourceTimestamp = String(payload.source_timestamp || '').trim();
    if (!temporalId || !sourceId || !sourceEventId) throw new Error('ECOSYSTEM_IDENTITY_REQUIRED');
    if (!['live', 'real_derived'].includes(truthStatus) || payload.generated_values !== false) {
      throw new Error('REAL_ECOSYSTEM_PROVENANCE_REQUIRED');
    }
    requireFreshTimestamp(sourceTimestamp, 5 * 60 * 1000, 'source_timestamp');

    const systemsOnline = requireInteger(payload.systems_online, 'systems_online');
    const totalSystems = requireInteger(payload.total_systems, 'total_systems');
    const coherence = requireFiniteNumber(payload.hive_mind_coherence, 'hive_mind_coherence');
    const confidence = requireFiniteNumber(payload.bus_confidence, 'bus_confidence');
    const consensus = String(payload.bus_consensus || '').trim();
    if (systemsOnline < 0 || totalSystems <= 0 || systemsOnline > totalSystems) {
      throw new Error('INVALID_SYSTEM_COUNTS');
    }
    if (coherence < 0 || coherence > 1 || confidence < 0 || confidence > 1) {
      throw new Error('INVALID_ECOSYSTEM_UNIT_INTERVAL');
    }
    if (!consensus) throw new Error('BUS_CONSENSUS_REQUIRED');
    if (typeof payload.json_enhancements_loaded !== 'boolean') {
      throw new Error('JSON_ENHANCEMENTS_OBSERVATION_REQUIRED');
    }

    const row = {
      user_id: user.id,
      temporal_id: temporalId,
      timestamp: sourceTimestamp,
      systems_online: systemsOnline,
      total_systems: totalSystems,
      hive_mind_coherence: coherence,
      bus_consensus: consensus,
      bus_confidence: confidence,
      json_enhancements_loaded: payload.json_enhancements_loaded,
      system_states: requireObject(payload.system_states, 'system_states'),
      metadata: payload.metadata === undefined ? {} : requireObject(payload.metadata, 'metadata'),
      truth_status: truthStatus,
      source_id: sourceId,
      source_event_id: sourceEventId,
      source_timestamp: sourceTimestamp,
      generated_values: false,
    };

    const supabase = createClient(supabaseUrl, serviceKey);
    const { data, error } = await supabase.from('ecosystem_snapshots').insert(row).select().single();
    if (error || !data) throw new Error(`ECOSYSTEM_SNAPSHOT_WRITE_FAILED:${error?.message || 'no row'}`);

    return new Response(JSON.stringify({
      success: true,
      id: data.id,
      truthStatus,
      sourceId,
      sourceEventId,
      sourceTimestamp,
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[ingest-ecosystem-snapshot]', message);
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
