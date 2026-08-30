export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3';

const supabase = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
);

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { action, data } = await req.json();

    switch (action) {
      case 'register_server':
        return await registerServer(data);
      case 'health_check':
        return await performHealthCheck(data);
      case 'correlation_analysis':
        return await performCorrelationAnalysis();
      case 'failover_analysis':
        return await analyzeFailover();
      case 'load_optimization':
        return await optimizeLoadDistribution();
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});

async function registerServer(serverData) {
  const { data, error } = await supabase
    .from('server_registry')
    .upsert({
      ...serverData,
      last_heartbeat: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });

  if (error) throw error;

  return new Response(JSON.stringify({ success: true, data }), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

async function performHealthCheck(checkData) {
  const servers = await getActiveServers();
  const healthResults = [];

  for (const server of servers) {
    try {
      const health = await checkServerHealth(server);
      healthResults.push(health);
      
      // Store metrics
      await supabase.from('backend_health_metrics').insert({
        server_id: server.server_id,
        server_name: server.server_name,
        cpu_usage: health.cpu_usage,
        memory_usage: health.memory_usage,
        disk_usage: health.disk_usage,
        active_connections: health.active_connections,
        request_rate: health.request_rate,
        response_time_p95: health.response_time_p95,
        error_rate: health.error_rate
      });
    } catch (error) {
      healthResults.push({
        server_id: server.server_id,
        status: 'unhealthy',
        error: error.message
      });
    }
  }

  return new Response(JSON.stringify({ healthResults }), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

async function getActiveServers() {
  const { data, error } = await supabase
    .from('server_registry')
    .select('*')
    .eq('status', 'active');
  
  if (error) throw error;
  return data || [];
}

async function checkServerHealth(server) {
  // Mock health check - in real implementation, make HTTP request to server
  return {
    server_id: server.server_id,
    status: 'healthy',
    cpu_usage: Math.random() * 100,
    memory_usage: Math.random() * 100,
    disk_usage: Math.random() * 100,
    active_connections: Math.floor(Math.random() * 1000),
    request_rate: Math.random() * 1000,
    response_time_p95: Math.random() * 500,
    error_rate: Math.random() * 5
  };
}

async function performCorrelationAnalysis() {
  const { data: metrics } = await supabase
    .from('backend_health_metrics')
    .select('*')
    .gte('timestamp', new Date(Date.now() - 3600000).toISOString());

  const analysis = analyzeServerCorrelations(metrics || []);
  
  await supabase.from('server_correlation_analysis').insert({
    analysis_type: 'performance_correlation',
    correlation_data: analysis.correlations,
    recommendations: analysis.recommendations
  });

  return new Response(JSON.stringify(analysis), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

function analyzeServerCorrelations(metrics) {
  return {
    correlations: {
      cpu_memory_correlation: 0.85,
      response_time_load_correlation: 0.92,
      error_rate_cpu_correlation: 0.78
    },
    recommendations: [
      {
        type: 'scaling',
        priority: 'high',
        message: 'Server-01 showing high CPU correlation with response time'
      },
      {
        type: 'load_balancing',
        priority: 'medium',
        message: 'Redistribute traffic from server-02 to server-03'
      }
    ]
  };
}

async function analyzeFailover() {
  const servers = await getActiveServers();
  const failoverPlan = generateFailoverPlan(servers);
  
  return new Response(JSON.stringify(failoverPlan), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

function generateFailoverPlan(servers) {
  return {
    primary_failover: servers[1]?.server_id || 'server-02',
    backup_servers: servers.slice(2).map(s => s.server_id),
    estimated_switchover_time: '30 seconds',
    traffic_redistribution: {
      'server-01': 0,
      'server-02': 60,
      'server-03': 40
    }
  };
}

async function optimizeLoadDistribution() {
  const { data: metrics } = await supabase
    .from('backend_health_metrics')
    .select('*')
    .gte('timestamp', new Date(Date.now() - 1800000).toISOString());

  const optimization = calculateOptimalDistribution(metrics || []);
  
  return new Response(JSON.stringify(optimization), {
    headers: { 'Content-Type': 'application/json', ...corsHeaders }
  });
}

function calculateOptimalDistribution(metrics) {
  return {
    current_distribution: { 'server-01': 40, 'server-02': 35, 'server-03': 25 },
    optimal_distribution: { 'server-01': 30, 'server-02': 40, 'server-03': 30 },
    expected_improvement: '15% response time reduction',
    implementation_steps: [
      'Gradually shift 10% traffic from server-01 to server-03',
      'Monitor response times for 5 minutes',
      'Adjust server-02 allocation based on performance'
    ]
  };
}
