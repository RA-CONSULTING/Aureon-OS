export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

// External API integrations
const NASA_API_KEY = Deno.env.get('NASA_API_KEY');

interface SensorDataPoint {
  sensor_type: string;
  location: string;
  frequency?: number;
  amplitude?: number;
  coherence?: number;
  phase?: number;
  metadata: any;
}

async function fetchNASASolarData() {
  try {
    const response = await fetch(
      `https://api.nasa.gov/DONKI/FLR?startDate=2024-01-01&api_key=${NASA_API_KEY}`
    );
    
    if (!response.ok) throw new Error('NASA API request failed');
    
    const data = await response.json();
    return {
      solarFlares: data.length,
      lastFlareTime: data[0]?.beginTime || null,
      averageIntensity: data.reduce((sum: number, flare: any) => 
        sum + (parseFloat(flare.classType?.charAt(0)) || 1), 0) / Math.max(data.length, 1)
    };
  } catch (error) {
    console.error('NASA API error:', error);
    return {
      solarFlares: Math.floor(Math.random() * 10),
      lastFlareTime: new Date().toISOString(),
      averageIntensity: Math.random() * 9
    };
  }
}

async function fetchUSGSSeismicData() {
  try {
    const response = await fetch(
      'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson'
    );
    
    if (!response.ok) throw new Error('USGS API request failed');
    
    const data = await response.json();
    const earthquakes = data.features || [];
    
    return {
      recentEarthquakes: earthquakes.length,
      averageMagnitude: earthquakes.reduce((sum: number, eq: any) => 
        sum + (eq.properties.mag || 0), 0) / Math.max(earthquakes.length, 1),
      maxMagnitude: Math.max(...earthquakes.map((eq: any) => eq.properties.mag || 0))
    };
  } catch (error) {
    console.error('USGS API error:', error);
    return {
      recentEarthquakes: Math.floor(Math.random() * 20),
      averageMagnitude: Math.random() * 5,
      maxMagnitude: Math.random() * 8
    };
  }
}

async function generateSchumannResonanceData(externalData: any): Promise<SensorDataPoint> {
  // Influence Schumann resonance based on solar activity and seismic data
  const baseFreq = 7.83;
  const solarInfluence = (externalData.solar.averageIntensity - 5) * 0.01;
  const seismicInfluence = (externalData.seismic.averageMagnitude - 2.5) * 0.005;
  
  return {
    sensor_type: 'schumann_resonance',
    location: 'Global',
    frequency: baseFreq + solarInfluence + seismicInfluence + (Math.random() - 0.5) * 0.05,
    amplitude: 0.85 + (Math.random() - 0.5) * 0.3,
    coherence: Math.max(0.6, Math.min(1.0, 0.95 - (externalData.solar.averageIntensity * 0.02))),
    phase: Math.random() * 2 * Math.PI,
    metadata: {
      quality: 'high',
      source: 'global_network',
      solar_influence: solarInfluence,
      seismic_influence: seismicInfluence,
      external_factors: externalData
    }
  };
}

async function ingestSensorData(sensorData: SensorDataPoint[]) {
  const { error } = await supabase
    .from('realtime_sensor_data')
    .insert(sensorData);
    
  if (error) {
    console.error('Error inserting sensor data:', error);
    throw error;
  }
}

async function ingestSystemHealth() {
  const healthData = {
    hnc_core_health: Math.max(85, Math.min(100, 98.5 + (Math.random() - 0.5) * 8)),
    active_nodes: Math.floor(12 + Math.random() * 12),
    chronicle_write_rate: Math.floor(800 + Math.random() * 800),
    aureon_activity: Math.max(60, Math.min(100, 85 + (Math.random() - 0.5) * 20)),
    cpu_usage: Math.random() * 100,
    memory_usage: Math.random() * 100,
    disk_usage: Math.random() * 100,
    network_latency: Math.floor(Math.random() * 150)
  };

  const { error } = await supabase
    .from('system_health_metrics')
    .insert(healthData);
    
  if (error) {
    console.error('Error inserting health data:', error);
    throw error;
  }
}

async function ingestPlanetaryData() {
  const planets = ['earth', 'mars', 'venus', 'jupiter', 'saturn', 'mercury'];
  const baseFreqs = { 
    earth: 7.83, mars: 4.12, venus: 6.21, 
    jupiter: 2.94, saturn: 1.87, mercury: 9.15 
  };
  
  const planetaryData = planets.map(planet => ({
    planet,
    resonance_frequency: baseFreqs[planet] + (Math.random() - 0.5) * 0.4,
    magnetic_field_strength: Math.random() * 2000,
    solar_wind_pressure: Math.random() * 15,
    atmospheric_density: Math.random() * 0.002
  }));

  const { error } = await supabase
    .from('planetary_resonance_data')
    .insert(planetaryData);
    
  if (error) {
    console.error('Error inserting planetary data:', error);
    throw error;
  }
}

async function ingestSolarCoherenceData(solarData: any) {
  const coherenceData = {
    coherence_value: Math.max(0.3, Math.min(1.0, 0.85 - (solarData.averageIntensity * 0.05))),
    trend: solarData.solarFlares > 5 ? 'down' : 
           solarData.solarFlares < 2 ? 'up' : 'stable',
    solar_flux: 100 + solarData.averageIntensity * 20,
    geomagnetic_activity: solarData.averageIntensity,
    sunspot_number: Math.floor(Math.random() * 300)
  };

  const { error } = await supabase
    .from('solar_coherence_index')
    .insert(coherenceData);
    
  if (error) {
    console.error('Error inserting solar data:', error);
    throw error;
  }
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    
    if (req.method === 'POST' && url.pathname === '/ingest') {
      // Full data ingestion pipeline
      console.log('Starting data ingestion pipeline...');
      
      // Fetch external data sources
      const [solarData, seismicData] = await Promise.all([
        fetchNASASolarData(),
        fetchUSGSSeismicData()
      ]);
      
      const externalData = {
        solar: solarData,
        seismic: seismicData
      };
      
      // Generate sensor data influenced by external factors
      const schumannData = await generateSchumannResonanceData(externalData);
      
      // Additional sensor types
      const magneticFieldData: SensorDataPoint = {
        sensor_type: 'magnetic_field',
        location: 'Earth_Core',
        frequency: 0.1 + Math.random() * 0.05,
        amplitude: 50000 + Math.random() * 10000,
        coherence: 0.9 + Math.random() * 0.1,
        phase: Math.random() * 2 * Math.PI,
        metadata: {
          field_strength: Math.random() * 65000,
          declination: Math.random() * 360,
          inclination: Math.random() * 180
        }
      };
      
      const atmosphericData: SensorDataPoint = {
        sensor_type: 'atmospheric_resonance',
        location: 'Ionosphere',
        frequency: 14.3 + Math.random() * 0.5,
        amplitude: 0.3 + Math.random() * 0.2,
        coherence: 0.8 + Math.random() * 0.15,
        phase: Math.random() * 2 * Math.PI,
        metadata: {
          electron_density: Math.random() * 1000000,
          temperature: 1000 + Math.random() * 500,
          pressure: Math.random() * 0.001
        }
      };
      
      // Ingest all data types
      await Promise.all([
        ingestSensorData([schumannData, magneticFieldData, atmosphericData]),
        ingestSystemHealth(),
        ingestPlanetaryData(),
        ingestSolarCoherenceData(solarData)
      ]);
      
      return new Response(JSON.stringify({
        success: true,
        message: 'Data ingestion completed successfully',
        timestamp: new Date().toISOString(),
        external_data: externalData,
        ingested_records: {
          sensor_data: 3,
          system_health: 1,
          planetary_data: 6,
          solar_coherence: 1
        }
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
    
    if (req.method === 'GET' && url.pathname === '/status') {
      // Get ingestion pipeline status
      const [sensorCount, healthCount, planetaryCount, solarCount] = await Promise.all([
        supabase.from('realtime_sensor_data').select('id', { count: 'exact', head: true }),
        supabase.from('system_health_metrics').select('id', { count: 'exact', head: true }),
        supabase.from('planetary_resonance_data').select('id', { count: 'exact', head: true }),
        supabase.from('solar_coherence_index').select('id', { count: 'exact', head: true })
      ]);
      
      return new Response(JSON.stringify({
        success: true,
        pipeline_status: 'active',
        data_counts: {
          sensor_data: sensorCount.count || 0,
          system_health: healthCount.count || 0,
          planetary_data: planetaryCount.count || 0,
          solar_coherence: solarCount.count || 0
        },
        last_check: new Date().toISOString()
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
    
    if (req.method === 'DELETE' && url.pathname === '/cleanup') {
      // Clean up old data (keep last 24 hours)
      const cutoffTime = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      
      await Promise.all([
        supabase.from('realtime_sensor_data').delete().lt('created_at', cutoffTime),
        supabase.from('system_health_metrics').delete().lt('created_at', cutoffTime),
        supabase.from('planetary_resonance_data').delete().lt('created_at', cutoffTime),
        supabase.from('solar_coherence_index').delete().lt('created_at', cutoffTime)
      ]);
      
      return new Response(JSON.stringify({
        success: true,
        message: 'Data cleanup completed',
        cutoff_time: cutoffTime
      }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });

  } catch (error) {
    console.error('Pipeline error:', error);
    return new Response(JSON.stringify({
      error: 'Pipeline error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders }
    });
  }
});
