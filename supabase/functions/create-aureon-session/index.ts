import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { encryptCredentialPacked } from "../_shared/credential_crypto.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  console.log('[create-aureon-session] Request received');

  try {
    const body = await req.json();
    const { 
      userId, 
      // Binance (required)
      apiKey, 
      apiSecret,
      // Kraken (optional)
      krakenApiKey,
      krakenApiSecret,
      // Alpaca (optional)
      alpacaApiKey,
      alpacaSecretKey,
      // Capital.com (optional)
      capitalApiKey,
      capitalPassword,
      capitalIdentifier
    } = body;

    console.log('[create-aureon-session] Processing for userId:', userId);

    if (!userId) {
      console.error('[create-aureon-session] Missing userId');
      return new Response(
        JSON.stringify({ error: 'Missing userId' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY');
    if (!supabaseUrl || !supabaseServiceKey || !supabaseAnonKey) {
      console.error('[create-aureon-session] Missing env vars');
      return new Response(
        JSON.stringify({ error: 'Server configuration error' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // === SECURITY: Verify the JWT token matches the userId ===
    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      console.error('[create-aureon-session] Missing authorization token');
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const anonSupabase = createClient(supabaseUrl, supabaseAnonKey);
    const { data: { user }, error: authError } = await anonSupabase.auth.getUser(token);

    if (authError || !user) {
      console.error('[create-aureon-session] Invalid token:', authError?.message);
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    if (user.id !== userId) {
      console.error('[create-aureon-session] User ID mismatch');
      return new Response(
        JSON.stringify({ error: 'Unauthorized: user mismatch' }),
        { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log('[create-aureon-session] User verified:', user.id);

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const sessionData: Record<string, any> = {
      user_id: userId
    };

    // Encrypt Binance credentials (required)
    if (apiKey && apiSecret) {
      console.log('[create-aureon-session] Encrypting Binance credentials...');
      sessionData.binance_api_key_encrypted = await encryptCredentialPacked(apiKey);
      sessionData.binance_api_secret_encrypted = await encryptCredentialPacked(apiSecret);
      sessionData.binance_iv = 'v2';
    }

    // Encrypt Kraken credentials (optional)
    if (krakenApiKey && krakenApiSecret) {
      console.log('[create-aureon-session] Encrypting Kraken credentials...');
      sessionData.kraken_api_key_encrypted = await encryptCredentialPacked(krakenApiKey);
      sessionData.kraken_api_secret_encrypted = await encryptCredentialPacked(krakenApiSecret);
      sessionData.kraken_iv = 'v2';
    }

    // Encrypt Alpaca credentials (optional)
    if (alpacaApiKey && alpacaSecretKey) {
      console.log('[create-aureon-session] Encrypting Alpaca credentials...');
      sessionData.alpaca_api_key_encrypted = await encryptCredentialPacked(alpacaApiKey);
      sessionData.alpaca_secret_key_encrypted = await encryptCredentialPacked(alpacaSecretKey);
      sessionData.alpaca_iv = 'v2';
    }

    // Encrypt Capital.com credentials (optional)
    if (capitalApiKey && capitalPassword && capitalIdentifier) {
      console.log('[create-aureon-session] Encrypting Capital.com credentials...');
      sessionData.capital_api_key_encrypted = await encryptCredentialPacked(capitalApiKey);
      sessionData.capital_password_encrypted = await encryptCredentialPacked(capitalPassword);
      sessionData.capital_identifier_encrypted = await encryptCredentialPacked(capitalIdentifier);
      sessionData.capital_iv = 'v2';
    }

    console.log('[create-aureon-session] Upserting session...');

    const { data, error } = await supabase
      .from('aureon_user_sessions')
      .upsert(sessionData, { onConflict: 'user_id' })
      .select()
      .single();

    if (error) {
      console.error('[create-aureon-session] Database error:', error);
      return new Response(
        JSON.stringify({ error: 'Session creation failed. Please try again.' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log('[create-aureon-session] Session created successfully');

    return new Response(
      JSON.stringify({ success: true, sessionId: data?.id }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('[create-aureon-session] Unexpected error:', error);
    return new Response(
      JSON.stringify({ error: 'An unexpected error occurred. Please try again.' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
