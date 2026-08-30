import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.81.1";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

type SolarFlare = {
  flrID: string;
  beginTime: string;
  peakTime: string;
  endTime: string;
  classType: string;
  sourceLocation: string;
  activeRegionNum: number;
};

function parseSolarFlareClass(classType: string): { class: string; magnitude: number; power: number } {
  const match = classType.match(/^([XMCBA])(\d+\.?\d*)/);
  if (!match) return { class: 'A', magnitude: 0, power: 1.0 };
  
  const [, flareClass, magnitudeStr] = match;
  const magnitude = parseFloat(magnitudeStr);
  
  let basePower = 1.0;
  switch (flareClass) {
    case 'X': basePower = 2.5 + (magnitude * 0.3); break;
    case 'M': basePower = 1.5 + (magnitude * 0.1); break;
    case 'C': basePower = 1.1 + (magnitude * 0.02); break;
    case 'B': basePower = 1.0 + (magnitude * 0.005); break;
  }
  
  return { class: flareClass, magnitude, power: basePower };
}

async function fetchNASASolarFlares(startDate: string, endDate: string): Promise<SolarFlare[]> {
  const apiKey = Deno.env.get('NASA_API_KEY')?.trim();
  if (!apiKey) throw new Error('NASA_API_KEY_NOT_CONFIGURED');
  const url = `https://api.nasa.gov/DONKI/FLR?startDate=${startDate}&endDate=${endDate}&api_key=${apiKey}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`NASA_DONKI_HTTP_${response.status}`);
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error('NASA_DONKI_INVALID_PAYLOAD');
  return payload;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Fetch historical solar flares (last 30 days)
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const solarFlares = await fetchNASASolarFlares(
      thirtyDaysAgo.toISOString().split('T')[0],
      now.toISOString().split('T')[0]
    );

    console.log(`Fetched ${solarFlares.length} solar flares from NASA`);

    // Filter for significant flares (M-class and above)
    const significantFlares = solarFlares.filter(f => {
      const info = parseSolarFlareClass(f.classType);
      return info.class === 'X' || info.class === 'M';
    });

    console.log(`Found ${significantFlares.length} significant flares (M+ class)`);

    const correlations = [];

    // Analyze each significant flare
    for (const flare of significantFlares) {
      const flareTime = new Date(flare.peakTime || flare.beginTime);
      const info = parseSolarFlareClass(flare.classType);
      
      // Define analysis windows
      const before24h = new Date(flareTime.getTime() - 24 * 60 * 60 * 1000);
      const after24h = new Date(flareTime.getTime() + 24 * 60 * 60 * 1000);
      const during6h = new Date(flareTime.getTime() + 6 * 60 * 60 * 1000);

      // Fetch coherence data before, during, and after the flare
      const { data: coherenceBefore } = await supabase
        .from('lighthouse_events')
        .select('coherence')
        .gte('timestamp', before24h.toISOString())
        .lt('timestamp', flareTime.toISOString());

      const { data: coherenceDuring } = await supabase
        .from('lighthouse_events')
        .select('coherence')
        .gte('timestamp', flareTime.toISOString())
        .lt('timestamp', during6h.toISOString());

      const { data: coherenceAfter } = await supabase
        .from('lighthouse_events')
        .select('coherence')
        .gte('timestamp', during6h.toISOString())
        .lte('timestamp', after24h.toISOString());

      // Calculate average coherence
      const avgBefore = coherenceBefore?.length 
        ? coherenceBefore.reduce((sum, d) => sum + d.coherence, 0) / coherenceBefore.length 
        : null;
      const avgDuring = coherenceDuring?.length 
        ? coherenceDuring.reduce((sum, d) => sum + d.coherence, 0) / coherenceDuring.length 
        : null;
      const avgAfter = coherenceAfter?.length 
        ? coherenceAfter.reduce((sum, d) => sum + d.coherence, 0) / coherenceAfter.length 
        : null;

      // Calculate coherence boost
      const coherenceBoost = (avgBefore && avgDuring) 
        ? ((avgDuring - avgBefore) / avgBefore) * 100 
        : null;

      // Fetch trading signals during the flare window
      const { data: signals } = await supabase
        .from('trading_signals')
        .select('signal_type, strength, reason')
        .gte('timestamp', flareTime.toISOString())
        .lte('timestamp', after24h.toISOString());

      const optimalSignals = signals?.filter(s => s.reason.includes('OPTIMAL')) || [];
      const avgStrength = signals?.length 
        ? signals.reduce((sum, s) => sum + s.strength, 0) / signals.length 
        : null;

      // Fetch LHE events during the flare window
      const { data: lheEvents } = await supabase
        .from('lighthouse_events')
        .select('id')
        .eq('is_lhe', true)
        .gte('timestamp', flareTime.toISOString())
        .lte('timestamp', after24h.toISOString());

      // Calculate prediction score (0-100)
      let predictionScore = 50; // Base score
      
      if (info.class === 'X') predictionScore += 30;
      else if (info.class === 'M') predictionScore += 15;
      
      if (coherenceBoost !== null && coherenceBoost > 0) {
        predictionScore += Math.min(coherenceBoost * 2, 20);
      }
      
      if (optimalSignals.length > 0) {
        predictionScore += Math.min(optimalSignals.length * 3, 15);
      }
      
      if (lheEvents && lheEvents.length > 0) {
        predictionScore += Math.min(lheEvents.length * 5, 15);
      }
      
      predictionScore = Math.min(Math.max(predictionScore, 0), 100);

      const correlation = {
        flare_class: flare.classType,
        flare_time: flareTime.toISOString(),
        flare_power: info.power,
        avg_coherence_before: avgBefore,
        avg_coherence_during: avgDuring,
        avg_coherence_after: avgAfter,
        coherence_boost: coherenceBoost,
        trading_signals_count: signals?.length || 0,
        optimal_signals_count: optimalSignals.length,
        lhe_events_count: lheEvents?.length || 0,
        avg_signal_strength: avgStrength,
        prediction_score: predictionScore,
        analysis_window_hours: 24
      };

      correlations.push(correlation);

      // Store in database
      await supabase
        .from('solar_flare_correlations')
        .upsert(correlation, { onConflict: 'flare_time' });
    }

    console.log(`Analyzed ${correlations.length} solar flare correlations`);

    // Calculate overall statistics
    const xClassFlares = correlations.filter(c => c.flare_class.startsWith('X'));
    const mClassFlares = correlations.filter(c => c.flare_class.startsWith('M'));
    
    const avgCoherenceBoostX = xClassFlares.length && xClassFlares.some(c => c.coherence_boost !== null)
      ? xClassFlares.filter(c => c.coherence_boost !== null).reduce((sum, c) => sum + (c.coherence_boost || 0), 0) / xClassFlares.filter(c => c.coherence_boost !== null).length
      : null;
    
    const avgCoherenceBoostM = mClassFlares.length && mClassFlares.some(c => c.coherence_boost !== null)
      ? mClassFlares.filter(c => c.coherence_boost !== null).reduce((sum, c) => sum + (c.coherence_boost || 0), 0) / mClassFlares.filter(c => c.coherence_boost !== null).length
      : null;

    const avgPredictionScoreX = xClassFlares.length
      ? xClassFlares.reduce((sum, c) => sum + (c.prediction_score || 0), 0) / xClassFlares.length
      : null;

    const avgPredictionScoreM = mClassFlares.length
      ? mClassFlares.reduce((sum, c) => sum + (c.prediction_score || 0), 0) / mClassFlares.length
      : null;

    return new Response(JSON.stringify({
      success: true,
      analyzed_flares: correlations.length,
      x_class_count: xClassFlares.length,
      m_class_count: mClassFlares.length,
      avg_coherence_boost_x: avgCoherenceBoostX,
      avg_coherence_boost_m: avgCoherenceBoostM,
      avg_prediction_score_x: avgPredictionScoreX,
      avg_prediction_score_m: avgPredictionScoreM,
      correlations: correlations.sort((a, b) => b.prediction_score - a.prediction_score).slice(0, 10),
      truthStatus: 'real_derived',
      sourceId: 'NASA_DONKI_FLR_AND_AUREON_MARKET_OBSERVATIONS',
      sourceTimestamp: now.toISOString(),
      generatedValues: false,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error in analyze-solar-correlations:', error);
    return new Response(JSON.stringify({ 
      error: error instanceof Error ? error.message : 'Unknown error',
      success: false,
      truthStatus: 'no_data',
      generatedValues: false,
    }), {
      status: 503,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
