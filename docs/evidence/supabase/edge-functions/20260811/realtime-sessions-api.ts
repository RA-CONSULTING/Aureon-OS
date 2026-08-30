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
    const body = await req.json().catch(() => ({}));
    const { action, session_id, prompt } = body;

    // Handle list sessions
    if (action === 'list') {
      const { data: sessions, error } = await supabase
        .from('realtime_sessions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);

      if (error) {
        return new Response(JSON.stringify({ 
          error: { 
            type: 'internal_error',
            message: error.message 
          }
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      return new Response(JSON.stringify({ 
        object: 'list',
        data: sessions || [],
        has_more: false
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Handle delete session
    if (action === 'delete' && session_id) {
      const { error } = await supabase
        .from('realtime_sessions')
        .update({ 
          status: 'expired', 
          updated_at: new Date().toISOString() 
        })
        .eq('session_id', session_id);

      if (error) {
        return new Response(JSON.stringify({ 
          error: { 
            type: 'internal_error',
            message: error.message 
          }
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      return new Response(JSON.stringify({ 
        object: 'realtime.session.deleted',
        id: session_id,
        deleted: true 
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // Handle create session (default)
    if (prompt?.id && prompt?.version) {
      const sessionId = `sess_${crypto.randomUUID().replace(/-/g, '')}`;
      const expiresAt = new Date(Date.now() + 3600000);
      
      const { data: sessionData, error: dbError } = await supabase
        .from('realtime_sessions')
        .insert({
          session_id: sessionId,
          prompt_id: prompt.id,
          prompt_version: prompt.version,
          status: 'active',
          expires_at: expiresAt.toISOString(),
          metadata: {
            created_via: 'realtime_api',
            prompt_data: prompt,
            api_version: 'v1'
          }
        })
        .select()
        .single();

      if (dbError) {
        return new Response(JSON.stringify({ 
          error: { 
            type: 'internal_error',
            message: 'Failed to create session' 
          }
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }

      const response = {
        id: sessionId,
        object: 'realtime.session',
        model: 'gpt-4o-realtime-preview-2024-10-01',
        expires_at: Math.floor(expiresAt.getTime() / 1000),
        modalities: ['text', 'audio'],
        instructions: `Realtime session for prompt ${prompt.id} v${prompt.version}`,
        voice: 'alloy',
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        temperature: 0.8,
        max_response_output_tokens: 4096
      };

      return new Response(JSON.stringify(response), {
        status: 201,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ 
      error: { 
        type: 'invalid_request_error',
        message: 'Invalid request parameters' 
      }
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });

  } catch (error) {
    return new Response(JSON.stringify({ 
      error: { 
        type: 'internal_error',
        message: 'Internal server error'
      }
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});
