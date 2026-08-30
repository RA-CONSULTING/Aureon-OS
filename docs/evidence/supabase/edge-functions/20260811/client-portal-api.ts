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
    const url = new URL(req.url);
    const path = url.pathname;
    const method = req.method;

    // Get client projects
    if (path === '/projects' && method === 'GET') {
      const clientId = url.searchParams.get('client_id');
      if (!clientId) {
        return new Response(JSON.stringify({ error: 'Client ID required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const { data, error } = await supabase
        .from('projects')
        .select(`
          *,
          project_team_members(
            user_profiles(id, full_name, email, avatar_url)
          )
        `)
        .eq('client_id', clientId)
        .order('created_at', { ascending: false });

      return new Response(JSON.stringify({ data, error }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get client invoices
    if (path === '/invoices' && method === 'GET') {
      const clientId = url.searchParams.get('client_id');
      if (!clientId) {
        return new Response(JSON.stringify({ error: 'Client ID required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const { data, error } = await supabase
        .from('invoices')
        .select('*, projects(name)')
        .eq('client_id', clientId)
        .order('created_at', { ascending: false });

      return new Response(JSON.stringify({ data, error }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Get project messages
    if (path === '/messages' && method === 'GET') {
      const projectId = url.searchParams.get('project_id');
      if (!projectId) {
        return new Response(JSON.stringify({ error: 'Project ID required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }

      const { data, error } = await supabase
        .from('messages')
        .select(`
          *,
          user_profiles(full_name, avatar_url),
          clients(company_name)
        `)
        .eq('project_id', projectId)
        .order('created_at', { ascending: true });

      return new Response(JSON.stringify({ data, error }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Send message
    if (path === '/messages' && method === 'POST') {
      const body = await req.json();
      const { data, error } = await supabase
        .from('messages')
        .insert(body)
        .select(`
          *,
          user_profiles(full_name, avatar_url),
          clients(company_name)
        `)
        .single();

      return new Response(JSON.stringify({ data, error }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
