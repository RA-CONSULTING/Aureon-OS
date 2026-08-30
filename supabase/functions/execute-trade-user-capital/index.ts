import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { decryptCredential } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  console.log('[execute-trade-user-capital] Request received');

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

    // Verify user
    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const anonSupabase = createClient(supabaseUrl, supabaseAnonKey);
    const { data: { user }, error: authError } = await anonSupabase.auth.getUser(token);

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const body = await req.json();
    const { epic, direction, size, stopLevel, profitLevel, dryRun = false } = body;

    if (!epic || !direction || !size) {
      return new Response(
        JSON.stringify({ error: 'Missing required parameters: epic, direction, size' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Get user's Capital.com credentials
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: session, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('capital_api_key_encrypted, capital_password_encrypted, capital_identifier_encrypted, capital_iv')
      .eq('user_id', user.id)
      .single();

    if (sessionError || !session) {
      return new Response(
        JSON.stringify({ error: 'No session found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (!session.capital_api_key_encrypted || !session.capital_password_encrypted || 
        !session.capital_identifier_encrypted || !session.capital_iv) {
      return new Response(
        JSON.stringify({ error: 'Capital.com credentials not configured' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Decrypt credentials
    const apiKey = await decryptCredential(session.capital_api_key_encrypted, session.capital_iv);
    const password = await decryptCredential(session.capital_password_encrypted, session.capital_iv);
    const identifier = await decryptCredential(session.capital_identifier_encrypted, session.capital_iv);

    if (dryRun) {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'PRODUCTION_LIVE_EXECUTION_REQUIRED',
          truthStatus: 'no_data',
          generatedValues: false,
        }),
        { status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const baseUrl = 'https://api-capital.backend-capital.com';

    // Create session
    console.log('[execute-trade-user-capital] Creating session...');
    const sessionResponse = await fetch(`${baseUrl}/api/v1/session`, {
      method: 'POST',
      headers: {
        'X-CAP-API-KEY': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ identifier, password }),
    });

    if (!sessionResponse.ok) {
      return new Response(
        JSON.stringify({ error: 'Capital.com authentication failed' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const cst = sessionResponse.headers.get('CST');
    const securityToken = sessionResponse.headers.get('X-SECURITY-TOKEN');

    if (!cst || !securityToken) {
      return new Response(
        JSON.stringify({ error: 'Authentication failed - missing tokens' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Place order
    const orderPayload: Record<string, any> = {
      epic,
      direction: direction.toUpperCase(),
      size: size.toString(),
    };

    if (stopLevel) orderPayload.stopLevel = stopLevel;
    if (profitLevel) orderPayload.profitLevel = profitLevel;

    console.log('[execute-trade-user-capital] Placing order:', orderPayload);

    const orderResponse = await fetch(`${baseUrl}/api/v1/positions`, {
      method: 'POST',
      headers: {
        'X-CAP-API-KEY': apiKey,
        'CST': cst,
        'X-SECURITY-TOKEN': securityToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderPayload),
    });

    const data = await orderResponse.json();

    if (!orderResponse.ok) {
      console.error('[execute-trade-user-capital] Capital.com error:', data);
      return new Response(
        JSON.stringify({ error: data.errorCode || 'Trade execution failed' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log('[execute-trade-user-capital] Position opened:', data.dealReference);

    return new Response(
      JSON.stringify({
        success: true,
        exchange: 'capital',
        dealReference: data.dealReference,
        epic,
        direction,
        size,
        affectedDeals: data.affectedDeals,
        truthStatus: 'live',
        sourceId: 'capital:/api/v1/positions',
        sourceTimestamp: orderResponse.headers.get('date') || new Date().toISOString(),
        generatedValues: false,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('[execute-trade-user-capital] Error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal error executing Capital.com trade' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
