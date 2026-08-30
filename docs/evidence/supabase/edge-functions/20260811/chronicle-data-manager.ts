export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { action, data } = await req.json();

    switch (action) {
      case 'create_session':
        return await createChronicleSession(data);
      case 'record_sensor_data':
        return await recordSensorData(data);
      case 'record_schumann_data':
        return await recordSchumannData(data);
      case 'record_analysis_result':
        return await recordAnalysisResult(data);
      case 'get_time_series':
        return await getTimeSeriesData(data);
      case 'export_data':
        return await exportData(data);
      default:
        return new Response(JSON.stringify({ error: 'Invalid action' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
    }
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});

async function createChronicleSession(data: any) {
  const { supabase } = await import('https://esm.sh/@supabase/supabase-js@2');
  const supabaseClient = supabase(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { data: session, error } = await supabaseClient
    .from('chronicle_sessions')
    .insert({
      session_name: data.name,
      description: data.description,
      metadata: data.metadata || {}
    })
    .select()
    .single();

  if (error) throw error;

  return new Response(JSON.stringify({ session }), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

async function recordSensorData(data: any) {
  const { supabase } = await import('https://esm.sh/@supabase/supabase-js@2');
  const supabaseClient = supabase(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const readings = Array.isArray(data.readings) ? data.readings : [data.readings];
  
  const { data: result, error } = await supabaseClient
    .from('sensor_readings')
    .insert(readings.map(reading => ({
      session_id: data.session_id,
      sensor_type: reading.sensor_type,
      sensor_id: reading.sensor_id,
      timestamp: reading.timestamp,
      value: reading.value,
      unit: reading.unit,
      quality_score: reading.quality_score || 1.0,
      metadata: reading.metadata || {}
    })));

  if (error) throw error;

  return new Response(JSON.stringify({ success: true, count: readings.length }), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}
