export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-api-key',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

interface ApiResponse {
  success: boolean;
  data?: any;
  error?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
  };
}

async function validateApiKey(apiKey: string): Promise<any> {
  if (!apiKey) return null;
  
  const { data } = await supabase
    .from('api_keys')
    .select('*')
    .eq('key_hash', apiKey)
    .eq('is_active', true)
    .single();
    
  if (!data) return null;
  
  // Check expiration
  if (data.expires_at && new Date(data.expires_at) < new Date()) {
    return null;
  }
  
  return data;
}

async function checkRateLimit(apiKeyId: string, limit: number, window: number): Promise<boolean> {
  const windowStart = new Date();
  windowStart.setSeconds(0, 0);
  
  const { data, error } = await supabase
    .from('api_rate_limits')
    .select('request_count')
    .eq('api_key_id', apiKeyId)
    .eq('window_start', windowStart.toISOString())
    .single();
    
  if (error && error.code !== 'PGRST116') return false;
  
  const currentCount = data?.request_count || 0;
  
  if (currentCount >= limit) return false;
  
  // Update or insert rate limit record
  await supabase
    .from('api_rate_limits')
    .upsert({
      api_key_id: apiKeyId,
      window_start: windowStart.toISOString(),
      request_count: currentCount + 1
    });
    
  return true;
}

async function logApiUsage(apiKeyId: string, endpoint: string, method: string, statusCode: number, responseTime: number, req: Request) {
  await supabase
    .from('api_usage_logs')
    .insert({
      api_key_id: apiKeyId,
      endpoint,
      method,
      status_code: statusCode,
      response_time_ms: responseTime,
      ip_address: req.headers.get('x-forwarded-for') || 'unknown',
      user_agent: req.headers.get('user-agent') || 'unknown'
    });
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  const startTime = Date.now();
  const url = new URL(req.url);
  const path = url.pathname;
  const method = req.method;
  
  try {
    // Extract API key
    const apiKey = req.headers.get('x-api-key') || url.searchParams.get('api_key');
    
    if (!apiKey) {
      return new Response(JSON.stringify({
        success: false,
        error: 'API key required'
      }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Validate API key
    const keyData = await validateApiKey(apiKey);
    if (!keyData) {
      return new Response(JSON.stringify({
        success: false,
        error: 'Invalid or expired API key'
      }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Check rate limit
    const rateLimitOk = await checkRateLimit(keyData.id, keyData.rate_limit, keyData.rate_window);
    if (!rateLimitOk) {
      await logApiUsage(keyData.id, path, method, 429, Date.now() - startTime, req);
      return new Response(JSON.stringify({
        success: false,
        error: 'Rate limit exceeded'
      }), {
        status: 429,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }

    // Route requests
    let response: ApiResponse;
    
    if (path.startsWith('/api/v1/sensor-data')) {
      response = await handleSensorData(url, method, keyData);
    } else if (path.startsWith('/api/v1/analytics')) {
      response = await handleAnalytics(url, method, keyData);
    } else if (path.startsWith('/api/v1/metrics')) {
      response = await handleMetrics(url, method, keyData);
    } else if (path.startsWith('/api/v1/backups')) {
      response = await handleBackups(url, method, keyData);
    } else {
      response = { success: false, error: 'Endpoint not found' };
    }

    const statusCode = response.success ? 200 : 400;
    await logApiUsage(keyData.id, path, method, statusCode, Date.now() - startTime, req);

    return new Response(JSON.stringify(response), {
      status: statusCode,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error'
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});

async function handleSensorData(url: URL, method: string, keyData: any): Promise<ApiResponse> {
  const params = url.searchParams;
  const limit = Math.min(parseInt(params.get('limit') || '100'), 1000);
  const offset = parseInt(params.get('offset') || '0');
  const startDate = params.get('start_date');
  const endDate = params.get('end_date');
  
  let query = supabase
    .from('sensor_readings')
    .select('*', { count: 'exact' })
    .range(offset, offset + limit - 1);
    
  if (startDate) query = query.gte('timestamp', startDate);
  if (endDate) query = query.lte('timestamp', endDate);
  
  const { data, error, count } = await query;
  
  if (error) {
    return { success: false, error: error.message };
  }
  
  return {
    success: true,
    data,
    pagination: {
      page: Math.floor(offset / limit) + 1,
      limit,
      total: count || 0
    }
  };
}

async function handleAnalytics(url: URL, method: string, keyData: any): Promise<ApiResponse> {
  const params = url.searchParams;
  const limit = Math.min(parseInt(params.get('limit') || '100'), 1000);
  const offset = parseInt(params.get('offset') || '0');
  
  const { data, error, count } = await supabase
    .from('analysis_results')
    .select('*', { count: 'exact' })
    .range(offset, offset + limit - 1)
    .order('created_at', { ascending: false });
    
  if (error) {
    return { success: false, error: error.message };
  }
  
  return {
    success: true,
    data,
    pagination: {
      page: Math.floor(offset / limit) + 1,
      limit,
      total: count || 0
    }
  };
}

async function handleMetrics(url: URL, method: string, keyData: any): Promise<ApiResponse> {
  const params = url.searchParams;
  const limit = Math.min(parseInt(params.get('limit') || '100'), 1000);
  const offset = parseInt(params.get('offset') || '0');
  
  const { data, error, count } = await supabase
    .from('system_metrics')
    .select('*', { count: 'exact' })
    .range(offset, offset + limit - 1)
    .order('timestamp', { ascending: false });
    
  if (error) {
    return { success: false, error: error.message };
  }
  
  return {
    success: true,
    data,
    pagination: {
      page: Math.floor(offset / limit) + 1,
      limit,
      total: count || 0
    }
  };
}

async function handleBackups(url: URL, method: string, keyData: any): Promise<ApiResponse> {
  const params = url.searchParams;
  const limit = Math.min(parseInt(params.get('limit') || '50'), 500);
  const offset = parseInt(params.get('offset') || '0');
  
  const { data, error, count } = await supabase
    .from('backup_jobs')
    .select('*', { count: 'exact' })
    .range(offset, offset + limit - 1)
    .order('created_at', { ascending: false });
    
  if (error) {
    return { success: false, error: error.message };
  }
  
  return {
    success: true,
    data,
    pagination: {
      page: Math.floor(offset / limit) + 1,
      limit,
      total: count || 0
    }
  };
}
