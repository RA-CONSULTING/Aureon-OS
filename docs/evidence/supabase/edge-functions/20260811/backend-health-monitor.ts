export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

interface HealthMetrics {
  cpu_usage_percent: number;
  memory_usage_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_usage_percent: number;
  load_average_1m: number;
  load_average_5m: number;
  load_average_15m: number;
  active_connections: number;
  requests_per_second: number;
  avg_response_time_ms: number;
  error_rate_percent: number;
  uptime_seconds: number;
  db_connection_pool_size: number;
  db_active_connections: number;
  db_idle_connections: number;
  db_avg_query_time_ms: number;
  db_slow_queries_count: number;
  db_connection_errors: number;
}

interface AlertThresholds {
  cpu_warning: number;
  cpu_critical: number;
  memory_warning: number;
  memory_critical: number;
  disk_warning: number;
  disk_critical: number;
  response_time_warning: number;
  response_time_critical: number;
  db_query_time_warning: number;
  db_query_time_critical: number;
}

const DEFAULT_THRESHOLDS: AlertThresholds = {
  cpu_warning: 70,
  cpu_critical: 90,
  memory_warning: 80,
  memory_critical: 95,
  disk_warning: 85,
  disk_critical: 95,
  response_time_warning: 1000,
  response_time_critical: 3000,
  db_query_time_warning: 500,
  db_query_time_critical: 2000
};

function analyzeMetrics(metrics: HealthMetrics, thresholds: AlertThresholds) {
  const alerts = [];
  let alertLevel = 'normal';
  let scalingRecommendation = '';

  // CPU Analysis
  if (metrics.cpu_usage_percent >= thresholds.cpu_critical) {
    alerts.push({ type: 'cpu', severity: 'critical', value: metrics.cpu_usage_percent });
    alertLevel = 'critical';
    scalingRecommendation += 'Scale up CPU resources immediately. ';
  } else if (metrics.cpu_usage_percent >= thresholds.cpu_warning) {
    alerts.push({ type: 'cpu', severity: 'warning', value: metrics.cpu_usage_percent });
    if (alertLevel !== 'critical') alertLevel = 'warning';
    scalingRecommendation += 'Consider scaling up CPU resources. ';
  }

  // Memory Analysis
  if (metrics.memory_usage_percent >= thresholds.memory_critical) {
    alerts.push({ type: 'memory', severity: 'critical', value: metrics.memory_usage_percent });
    alertLevel = 'critical';
    scalingRecommendation += 'Scale up memory immediately. ';
  } else if (metrics.memory_usage_percent >= thresholds.memory_warning) {
    alerts.push({ type: 'memory', severity: 'warning', value: metrics.memory_usage_percent });
    if (alertLevel !== 'critical') alertLevel = 'warning';
    scalingRecommendation += 'Consider adding more memory. ';
  }

  // Database Performance Analysis
  if (metrics.db_avg_query_time_ms >= thresholds.db_query_time_critical) {
    alerts.push({ type: 'database', severity: 'critical', value: metrics.db_avg_query_time_ms });
    alertLevel = 'critical';
    scalingRecommendation += 'Optimize database queries or scale database resources. ';
  } else if (metrics.db_avg_query_time_ms >= thresholds.db_query_time_warning) {
    alerts.push({ type: 'database', severity: 'warning', value: metrics.db_avg_query_time_ms });
    if (alertLevel !== 'critical') alertLevel = 'warning';
    scalingRecommendation += 'Review slow database queries. ';
  }

  // Connection Pool Analysis
  const poolUtilization = (metrics.db_active_connections / metrics.db_connection_pool_size) * 100;
  if (poolUtilization >= 90) {
    alerts.push({ type: 'connection_pool', severity: 'critical', value: poolUtilization });
    alertLevel = 'critical';
    scalingRecommendation += 'Increase database connection pool size. ';
  } else if (poolUtilization >= 80) {
    alerts.push({ type: 'connection_pool', severity: 'warning', value: poolUtilization });
    if (alertLevel !== 'critical') alertLevel = 'warning';
    scalingRecommendation += 'Monitor connection pool usage. ';
  }

  return {
    alerts,
    alertLevel,
    scalingRecommendation: scalingRecommendation.trim() || 'System operating within normal parameters',
    cpu_alert: metrics.cpu_usage_percent >= thresholds.cpu_warning,
    memory_alert: metrics.memory_usage_percent >= thresholds.memory_warning,
    disk_alert: metrics.disk_usage_percent >= thresholds.disk_warning,
    db_alert: metrics.db_avg_query_time_ms >= thresholds.db_query_time_warning,
    response_time_alert: metrics.avg_response_time_ms >= thresholds.response_time_warning
  };
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { method } = req;
    
    if (method === 'POST') {
      // Store health metrics
      const metrics: HealthMetrics = await req.json();
      const analysis = analyzeMetrics(metrics, DEFAULT_THRESHOLDS);
      
      // Store metrics in database
      const { data, error } = await supabase
        .from('backend_health_metrics')
        .insert({
          ...metrics,
          ...analysis,
          scaling_recommendation: analysis.scalingRecommendation,
          alert_level: analysis.alertLevel
        })
        .select()
        .single();

      if (error) throw error;

      // Store alert events if any
      for (const alert of analysis.alerts) {
        await supabase
          .from('health_alert_events')
          .insert({
            alert_type: alert.type,
            severity: alert.severity,
            message: `${alert.type.toUpperCase()} usage at ${alert.value}%`,
            metric_value: alert.value,
            threshold_value: alert.severity === 'critical' ? 
              DEFAULT_THRESHOLDS[`${alert.type}_critical` as keyof AlertThresholds] :
              DEFAULT_THRESHOLDS[`${alert.type}_warning` as keyof AlertThresholds]
          });
      }

      return new Response(JSON.stringify({ 
        success: true, 
        data,
        alerts: analysis.alerts,
        recommendations: analysis.scalingRecommendation
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
    
    if (method === 'GET') {
      // Get recent health metrics
      const url = new URL(req.url);
      const hours = parseInt(url.searchParams.get('hours') || '24');
      const serverId = url.searchParams.get('server_id') || 'fastapi-main';
      
      const { data: metrics, error: metricsError } = await supabase
        .from('backend_health_metrics')
        .select('*')
        .eq('server_id', serverId)
        .gte('timestamp', new Date(Date.now() - hours * 60 * 60 * 1000).toISOString())
        .order('timestamp', { ascending: false })
        .limit(1000);

      if (metricsError) throw metricsError;

      const { data: alerts, error: alertsError } = await supabase
        .from('health_alert_events')
        .select('*')
        .eq('server_id', serverId)
        .is('resolved_at', null)
        .order('timestamp', { ascending: false })
        .limit(100);

      if (alertsError) throw alertsError;

      return new Response(JSON.stringify({
        success: true,
        metrics: metrics || [],
        activeAlerts: alerts || [],
        summary: metrics?.[0] ? {
          currentCpu: metrics[0].cpu_usage_percent,
          currentMemory: metrics[0].memory_usage_percent,
          currentAlertLevel: metrics[0].alert_level,
          uptime: metrics[0].uptime_seconds,
          lastUpdate: metrics[0].timestamp
        } : null
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });

  } catch (error) {
    console.error('Backend health monitor error:', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      details: error.message 
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});
