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

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { credentials } = await req.json();

    if (!credentials || !Array.isArray(credentials)) {
      throw new Error('credentials must be an array of { name, apiKey, apiSecret }');
    }

    console.log(`[update-bot-credentials] Processing ${credentials.length} credentials`);

    const results = [];

    for (const cred of credentials) {
      const { name, apiKey, apiSecret } = cred;

      if (!name || !apiKey || !apiSecret) {
        console.error(`[update-bot-credentials] Missing fields for credential: ${name}`);
        results.push({ name, success: false, error: 'Missing required fields' });
        continue;
      }

      try {
        // Encrypt credentials
        const encryptedApiKey = await encryptCredentialPacked(apiKey);
        const encryptedApiSecret = await encryptCredentialPacked(apiSecret);

        console.log(`[update-bot-credentials] Updating credentials for: ${name}`);

        // Check if credential exists
        const { data: existing } = await supabase
          .from('binance_credentials')
          .select('id')
          .eq('name', name)
          .single();

        if (existing) {
          // Update existing
          const { error: updateError } = await supabase
            .from('binance_credentials')
            .update({
              api_key_encrypted: encryptedApiKey,
              api_secret_encrypted: encryptedApiSecret,
              updated_at: new Date().toISOString(),
              is_active: true,
            })
            .eq('name', name);

          if (updateError) throw updateError;
          console.log(`[update-bot-credentials] ✅ Updated: ${name}`);
          results.push({ name, success: true, action: 'updated' });
        } else {
          // Insert new
          const { error: insertError } = await supabase
            .from('binance_credentials')
            .insert({
              name,
              api_key_encrypted: encryptedApiKey,
              api_secret_encrypted: encryptedApiSecret,
              is_active: true,
            });

          if (insertError) throw insertError;
          console.log(`[update-bot-credentials] ✅ Created: ${name}`);
          results.push({ name, success: true, action: 'created' });
        }
      } catch (error) {
        console.error(`[update-bot-credentials] ❌ Failed for ${name}:`, error);
        results.push({
          name,
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    const successCount = results.filter(r => r.success).length;
    console.log(`[update-bot-credentials] Completed: ${successCount}/${credentials.length} successful`);

    return new Response(
      JSON.stringify({
        success: true,
        results,
        summary: {
          total: credentials.length,
          successful: successCount,
          failed: credentials.length - successCount,
        },
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('[update-bot-credentials] Error:', error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});
