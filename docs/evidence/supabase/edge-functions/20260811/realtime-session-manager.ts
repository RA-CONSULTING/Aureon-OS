export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { method, url } = req;
    const urlPath = new URL(url).pathname;

    if (method === 'POST' && (urlPath.includes('/sessions') || urlPath.includes('/realtime/sessions'))) {
      const body = await req.json();
      const { prompt } = body;

      if (!prompt?.id || !prompt?.version) {
        return new Response(JSON.stringify({ error: 'Invalid prompt data' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      // Generate session ID
      const sessionId = `sess_${crypto.randomUUID().replace(/-/g, '')}`;
      const expiresAt = new Date(Date.now() + 3600000); // 1 hour
      
      // Store session in database
      const { data: sessionData, error: dbError } = await supabase
        .from('realtime_sessions')
        .insert({
          session_id: sessionId,
          prompt_id: prompt.id,
          prompt_version: prompt.version,
          status: 'active',
          expires_at: expiresAt.toISOString(),
          metadata: {
            created_via: 'api',
            client_info: req.headers.get('user-agent') || 'unknown',
            prompt_data: prompt
          },
          performance_metrics: {
            created_at: Date.now(),
            initial_latency: 0
          }
        })
        .select()
        .single();

      if (dbError) {
        console.error('Database error:', dbError);
        return new Response(JSON.stringify({ error: 'Failed to create session' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      // OpenAI Realtime API compatible response
      const response = {
        id: sessionId,
        object: 'realtime.session',
        model: 'gpt-4o-realtime-preview-2024-10-01',
        expires_at: Math.floor(expiresAt.getTime() / 1000),
        modalities: ['text', 'audio'],
        instructions: `Session created for prompt ${prompt.id} version ${prompt.version}`,
        voice: 'alloy',
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        input_audio_transcription: { model: 'whisper-1' },
        turn_detection: {
          type: 'server_vad',
          threshold: 0.5,
          prefix_padding_ms: 300,
          silence_duration_ms: 200
        },
        tools: [],
        tool_choice: 'auto',
        temperature: 0.8,
        max_response_output_tokens: 4096,
        session_data: sessionData
      };

      return new Response(JSON.stringify(response), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    if (method === 'GET' && urlPath.includes('/sessions')) {
      const { data: sessions, error } = await supabase
        .from('realtime_sessions')
        .select(`
          *,
          realtime_session_analytics(*)
        `)
        .order('created_at', { ascending: false })
        .limit(50);

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      return new Response(JSON.stringify({ sessions: sessions || [] }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    if (method === 'DELETE' && urlPath.includes('/sessions/')) {
      const sessionId = urlPath.split('/').pop();
      
      const { error } = await supabase
        .from('realtime_sessions')
        .update({ status: 'expired', updated_at: new Date().toISOString() })
        .eq('session_id', sessionId);

      if (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      return new Response(JSON.stringify({ success: true }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ error: 'Endpoint not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });

  } catch (error) {
    console.error('Function error:', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      details: error.message 
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});
