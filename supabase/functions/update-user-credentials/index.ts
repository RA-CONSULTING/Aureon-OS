import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { encryptCredentialPacked } from '../_shared/credential_crypto.ts';

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
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get user from JWT
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      return new Response(JSON.stringify({ error: 'No authorization header' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const token = authHeader.replace('Bearer ', '');
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    
    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Invalid token' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const body = await req.json();
    const {
      binanceApiKey,
      binanceApiSecret,
      krakenApiKey,
      krakenApiSecret,
      alpacaApiKey,
      alpacaSecretKey,
      capitalApiKey,
      capitalPassword,
      capitalIdentifier
    } = body;

    // Build update object with only provided credentials
    const updateData: Record<string, any> = {
      updated_at: new Date().toISOString()
    };

    // Binance
    if (binanceApiKey && binanceApiSecret) {
      updateData.binance_api_key_encrypted = await encryptCredentialPacked(binanceApiKey);
      updateData.binance_api_secret_encrypted = await encryptCredentialPacked(binanceApiSecret);
      updateData.binance_iv = 'v2';
    }

    // Kraken
    if (krakenApiKey && krakenApiSecret) {
      updateData.kraken_api_key_encrypted = await encryptCredentialPacked(krakenApiKey);
      updateData.kraken_api_secret_encrypted = await encryptCredentialPacked(krakenApiSecret);
      updateData.kraken_iv = 'v2';
    }

    // Alpaca
    if (alpacaApiKey && alpacaSecretKey) {
      updateData.alpaca_api_key_encrypted = await encryptCredentialPacked(alpacaApiKey);
      updateData.alpaca_secret_key_encrypted = await encryptCredentialPacked(alpacaSecretKey);
      updateData.alpaca_iv = 'v2';
    }

    // Capital.com
    if (capitalApiKey && capitalPassword) {
      updateData.capital_api_key_encrypted = await encryptCredentialPacked(capitalApiKey);
      updateData.capital_password_encrypted = await encryptCredentialPacked(capitalPassword);
      if (capitalIdentifier) {
        updateData.capital_identifier_encrypted = await encryptCredentialPacked(capitalIdentifier);
      }
      updateData.capital_iv = 'v2';
    }

    // Check if session exists
    const { data: existingSession } = await supabase
      .from('aureon_user_sessions')
      .select('id')
      .eq('user_id', user.id)
      .single();

    if (existingSession) {
      // Update existing session
      const { error: updateError } = await supabase
        .from('aureon_user_sessions')
        .update(updateData)
        .eq('user_id', user.id);

      if (updateError) {
        console.error('Update error:', updateError);
        return new Response(JSON.stringify({ error: 'Failed to update credentials' }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    } else {
      // Create new session
      const { error: insertError } = await supabase
        .from('aureon_user_sessions')
        .insert({
          user_id: user.id,
          ...updateData,
          is_trading_active: false
        });

      if (insertError) {
        console.error('Insert error:', insertError);
        return new Response(JSON.stringify({ error: 'Failed to create session' }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }

    // Return which exchanges were updated
    const updatedExchanges = [];
    if (updateData.binance_api_key_encrypted) updatedExchanges.push('binance');
    if (updateData.kraken_api_key_encrypted) updatedExchanges.push('kraken');
    if (updateData.alpaca_api_key_encrypted) updatedExchanges.push('alpaca');
    if (updateData.capital_api_key_encrypted) updatedExchanges.push('capital');

    return new Response(JSON.stringify({ 
      success: true, 
      updatedExchanges,
      message: `Updated ${updatedExchanges.length} exchange(s)` 
    }), {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
