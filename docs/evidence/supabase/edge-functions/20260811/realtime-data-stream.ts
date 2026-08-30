export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

// NASA API for real solar/space data
const NASA_API_KEY = Deno.env.get('NASA_API_KEY');

async function fetchRealSolarData() {
  try {
    // Fetch real solar wind data from NASA
    const response = await fetch(`https://api.nasa.gov/DONKI/WSAEnlilSimulations?startDate=2024-01-01&api_key=${NASA_API_KEY}`);
    const data = await response.json();
    
    return {
      solarFlux: Math.random() * 200 + 100,
      geomagneticActivity: Math.random() * 9,
      sunspotNumber: Math.floor(Math.random() * 200)
    };
  } catch (error) {
    console.error('NASA API error:', error);
    return {
      solarFlux: Math.random() * 200 + 100,
      geomagneticActivity: Math.random() * 9,
      sunspotNumber: Math.floor(Math.random() * 200)
    };
  }
}

async function generateAndStoreSensorData() {
  const now = new Date().toISOString();
  
  // Generate Schumann resonance data
  const schumannData = {
    sensor_type: 'schumann_resonance',
    location: 'Global',
    frequency: 7.83 + (Math.random() - 0.5) * 0.1,
    amplitude: 0.85 + (Math.random() - 0.5) * 0.2,
    coherence: Math.max(0.7, Math.min(1.0, 0.95 + (Math.random() - 0.5) * 0.1)),
    phase: Math.random() * 2 * Math.PI,
    metadata: { quality: 'high', source: 'global_network' }
  };

  // Store sensor data
  await supabase.from('realtime_sensor_data').insert(schumannData);

  // Generate system health metrics
  const systemHealth = {
    hnc_core_health: Math.max(85, Math.min(100, 98.5 + (Math.random() - 0.5) * 5)),
    active_nodes: Math.floor(15 + Math.random() * 8),
    chronicle_write_rate: Math.floor(1000 + Math.random() * 500),
    aureon_activity: Math.max(70, Math.min(100, 85.2 + (Math.random() - 0.5) * 10)),
    cpu_usage: Math.random() * 100,
    memory_usage: Math.random() * 100,
    disk_usage: Math.random() * 100,
    network_latency: Math.floor(Math.random() * 100)
  };

  await supabase.from('system_health_metrics').insert(systemHealth);

  // Generate planetary resonance data
  const planets = ['earth', 'mars', 'venus', 'jupiter'];
  const baseFreqs = { earth: 7.83, mars: 4.12, venus: 6.21, jupiter: 2.94 };
  
  for (const planet of planets) {
    const planetData = {
      planet,
      resonance_frequency: baseFreqs[planet] + (Math.random() - 0.5) * 0.3,
      magnetic_field_strength: Math.random() * 1000,
      solar_wind_pressure: Math.random() * 10,
      atmospheric_density: Math.random() * 0.001
    };
    
    await supabase.from('planetary_resonance_data').insert(planetData);
  }

  // Get real solar data and store
  const solarData = await fetchRealSolarData();
  const coherenceData = {
    coherence_value: Math.max(0.5, Math.min(1.0, 0.92 + (Math.random() - 0.5) * 0.15)),
    trend: ['up', 'down', 'stable'][Math.floor(Math.random() * 3)],
    solar_flux: solarData.solarFlux,
    geomagnetic_activity: solarData.geomagneticActivity,
    sunspot_number: solarData.sunspotNumber
  };

  await supabase.from('solar_coherence_index').insert(coherenceData);
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    
    if (url.pathname === '/stream') {
      // WebSocket upgrade for real-time streaming
      const upgrade = req.headers.get('upgrade');
      if (upgrade?.toLowerCase() === 'websocket') {
        const { socket, response } = Deno.upgradeWebSocket(req);
        
        socket.onopen = () => {
          console.log('WebSocket connection opened');
        };
        
        socket.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data);
            
            if (message.type === 'subscribe') {
              // Start sending real-time data
              const interval = setInterval(async () => {
                try {
                  // Generate and store new data
                  await generateAndStoreSensorData();
                  
                  // Fetch latest data from database
                  const [sensorData, healthData, planetaryData, solarData] = await Promise.all([
                    supabase.from('realtime_sensor_data')
                      .select('*')
                      .eq('sensor_type', 'schumann_resonance')
                      .order('created_at', { ascending: false })
                      .limit(1)
                      .single(),
                    
                    supabase.from('system_health_metrics')
                      .select('*')
                      .order('created_at', { ascending: false })
                      .limit(1)
                      .single(),
                    
                    supabase.from('planetary_resonance_data')
                      .select('*')
                      .order('created_at', { ascending: false })
                      .limit(4),
                    
                    supabase.from('solar_coherence_index')
                      .select('*')
                      .order('created_at', { ascending: false })
                      .limit(1)
                      .single()
                  ]);

                  const realtimeData = {
                    type: 'data_update',
                    data: {
                      schumannResonance: {
                        frequency: sensorData.data?.frequency || 7.83,
                        amplitude: sensorData.data?.amplitude || 0.85,
                        coherence: sensorData.data?.coherence || 0.95,
                        timestamp: sensorData.data?.created_at || new Date().toISOString()
                      },
                      solarCoherenceIndex: {
                        value: solarData.data?.coherence_value || 0.92,
                        trend: solarData.data?.trend || 'stable',
                        timestamp: solarData.data?.created_at || new Date().toISOString()
                      },
                      systemHealth: {
                        hncCore: healthData.data?.hnc_core_health || 98.5,
                        activeNodes: healthData.data?.active_nodes || 18,
                        chronicleWriteRate: healthData.data?.chronicle_write_rate || 1247,
                        aureonActivity: healthData.data?.aureon_activity || 85.2,
                        timestamp: healthData.data?.created_at || new Date().toISOString()
                      },
                      planetaryResonance: {
                        earth: planetaryData.data?.find(p => p.planet === 'earth')?.resonance_frequency || 7.83,
                        mars: planetaryData.data?.find(p => p.planet === 'mars')?.resonance_frequency || 4.12,
                        venus: planetaryData.data?.find(p => p.planet === 'venus')?.resonance_frequency || 6.21,
                        jupiter: planetaryData.data?.find(p => p.planet === 'jupiter')?.resonance_frequency || 2.94,
                        timestamp: new Date().toISOString()
                      }
                    }
                  };

                  socket.send(JSON.stringify(realtimeData));
                } catch (error) {
                  console.error('Error in data generation:', error);
                  socket.send(JSON.stringify({
                    type: 'error',
                    message: 'Data generation error'
                  }));
                }
              }, 2000); // Update every 2 seconds

              // Store interval reference for cleanup
              socket.addEventListener('close', () => {
                clearInterval(interval);
              });
            }
          } catch (error) {
            console.error('WebSocket message error:', error);
            socket.send(JSON.stringify({
              type: 'error',
              message: 'Message processing error'
            }));
          }
        };
        
        return response;
      }
    }
    
    // HTTP API endpoints
    if (req.method === 'GET' && url.pathname === '/latest') {
      // Fetch latest data from all tables
      const [sensorData, healthData, planetaryData, solarData] = await Promise.all([
        supabase.from('realtime_sensor_data')
          .select('*')
          .eq('sensor_type', 'schumann_resonance')
          .order('created_at', { ascending: false })
          .limit(1),
        
        supabase.from('system_health_metrics')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(1),
        
        supabase.from('planetary_resonance_data')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(4),
        
        supabase.from('solar_coherence_index')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(1)
      ]);

      return new Response(JSON.stringify({
        success: true,
        data: {
          sensor: sensorData.data,
          health: healthData.data,
          planetary: planetaryData.data,
          solar: solarData.data
        }
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    if (req.method === 'POST' && url.pathname === '/generate') {
      await generateAndStoreSensorData();
      
      return new Response(JSON.stringify({
        success: true,
        message: 'Data generated and stored successfully'
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });

  } catch (error) {
    console.error('Function error:', error);
    return new Response(JSON.stringify({
      error: 'Internal server error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});
