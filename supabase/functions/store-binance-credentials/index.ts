import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.81.1';
import { encryptCredentialPacked } from '../_shared/credential_crypto.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { userId, apiKey, apiSecret } = await req.json();

    if (!userId || !apiKey || !apiSecret) {
      throw new Error('Missing required fields: userId, apiKey, apiSecret');
    }

    const token = req.headers.get('Authorization')?.replace('Bearer ', '');
    if (!token) throw new Error('Unauthorized');
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);
    if (authError || !user || user.id !== userId) throw new Error('Unauthorized');

    console.log('[store-binance-credentials] Encrypting credentials for user:', userId);

    const encryptedApiKey = await encryptCredentialPacked(apiKey);
    const encryptedApiSecret = await encryptCredentialPacked(apiSecret);

    const { error: insertError } = await supabase
      .from('user_binance_credentials')
      .upsert({
        user_id: userId,
        api_key_encrypted: encryptedApiKey,
        api_secret_encrypted: encryptedApiSecret,
        iv: 'v2',
        last_used_at: new Date().toISOString()
      }, { onConflict: 'user_id' });

    if (insertError) throw new Error(`Failed to store credentials: ${insertError.message}`);

    // Log audit trail
    await supabase
      .from('data_access_audit')
      .insert({
        user_id: userId,
        accessed_by: userId,
        access_type: 'CREATE',
        resource_type: 'BINANCE_CREDENTIALS',
        metadata: {
          action: 'store_encrypted_credentials',
          timestamp: new Date().toISOString()
        }
      });

    console.log('[store-binance-credentials] Credentials stored successfully');

    return new Response(
      JSON.stringify({ 
        success: true,
        message: 'Credentials encrypted and stored securely'
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );

  } catch (error) {
    console.error('[store-binance-credentials] Error:', error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : 'Unknown error',
        details: 'Failed to store Binance credentials',
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});
