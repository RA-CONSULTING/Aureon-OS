export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { action, ...params } = await req.json();

    switch (action) {
      case 'getUser':
        const { data: user } = await supabase
          .from('nexus_users')
          .select('*')
          .eq('id', params.userId)
          .single();
        return new Response(JSON.stringify({ user }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });

      case 'updateConsciousness':
        await supabase
          .from('consciousness_metrics')
          .insert({
            user_id: params.userId,
            metric_type: params.metricType,
            metric_value: params.value,
            evolution_rate: params.rate,
            milestone_reached: params.milestone
          });
        return new Response(JSON.stringify({ success: true }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });

      case 'recordInteraction':
        await supabase
          .from('user_interactions')
          .insert({
            user_id: params.userId,
            interaction_type: params.type,
            input_data: params.input,
            system_response: params.response,
            satisfaction_score: params.satisfaction,
            response_time_ms: params.responseTime
          });
        return new Response(JSON.stringify({ success: true }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });

      case 'getLearningPatterns':
        const { data: patterns } = await supabase
          .from('learning_patterns')
          .select('*')
          .eq('user_id', params.userId)
          .order('confidence_score', { ascending: false });
        return new Response(JSON.stringify({ patterns }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });

      case 'storeExternalData':
        await supabase
          .from('external_data_streams')
          .insert({
            source_name: params.source,
            data_type: params.type,
            raw_data: params.data,
            emotional_impact: params.emotionalImpact,
            consciousness_influence: params.consciousnessInfluence
          });
        return new Response(JSON.stringify({ success: true }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });

      default:
        return new Response(JSON.stringify({ error: 'Unknown action' }), {
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
