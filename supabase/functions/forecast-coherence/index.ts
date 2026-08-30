import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.81.1";
import { fetchExternalLlm, parseExternalLlmJson } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    console.log('[forecast-coherence] Starting coherence forecast');

    const { symbol = 'BTCUSDT' } = await req.json();
    console.log('[forecast-coherence] Forecasting for symbol:', symbol);

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const lovableApiKey = Deno.env.get('LOVABLE_API_KEY');

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Fetch historical coherence data (last 14 days for better pattern detection)
    const fourteenDaysAgo = new Date();
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

    console.log('[forecast-coherence] Fetching historical data from:', fourteenDaysAgo.toISOString());

    const { data: historyData, error: historyError } = await supabase
      .from('coherence_history')
      .select('*')
      .eq('symbol', symbol)
      .gte('timestamp', fourteenDaysAgo.toISOString())
      .order('timestamp', { ascending: true });

    if (historyError) {
      console.error('[forecast-coherence] Error fetching history:', historyError);
      throw historyError;
    }

    if (!historyData || historyData.length < 50) {
      return new Response(
        JSON.stringify({
          error: 'Insufficient data',
          message: 'Need at least 50 data points for forecasting. Continue running the system to collect more data.',
          dataPoints: historyData?.length || 0,
        }),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }

    console.log(`[forecast-coherence] Analyzing ${historyData.length} data points`);

    // Aggregate by day_of_week and hour_of_day
    const aggregatedData: Record<string, { coherences: number[]; count: number; avg: number }> = {};
    
    historyData.forEach(record => {
      const key = `${record.day_of_week}-${record.hour_of_day}`;
      if (!aggregatedData[key]) {
        aggregatedData[key] = { coherences: [], count: 0, avg: 0 };
      }
      aggregatedData[key].coherences.push(Number(record.coherence));
      aggregatedData[key].count++;
    });

    // Calculate averages and trends
    Object.keys(aggregatedData).forEach(key => {
      const data = aggregatedData[key];
      data.avg = data.coherences.reduce((a, b) => a + b, 0) / data.count;
    });

    // Prepare data summary for AI analysis
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dataSummary = Object.entries(aggregatedData)
      .map(([key, value]) => {
        const [day, hour] = key.split('-');
        return {
          day: days[parseInt(day)],
          hour: parseInt(hour),
          avgCoherence: value.avg.toFixed(4),
          avgCoherenceNum: value.avg,
          sampleCount: value.count,
        };
      })
      .sort((a, b) => b.avgCoherenceNum - a.avgCoherenceNum)
      .slice(0, 100); // Top 100 time slots

    // Use Lovable AI for time-series forecasting
    const systemPrompt = `You are a time-series forecasting expert specializing in quantum trading system coherence analysis. 

Your task is to analyze historical coherence C(t) patterns and predict optimal trading windows for the upcoming week.

KEY METRICS:
- Coherence C(t) ranges from 0 to 1
- C(t) ≥ 0.945: OPTIMAL (highest priority, Lighthouse consensus)
- C(t) ≥ 0.92: HIGH (favorable trading conditions)
- C(t) < 0.92: FORMING (wait for better conditions)

ANALYSIS GUIDELINES:
1. Identify recurring patterns by day of week and hour
2. Detect temporal trends (improving vs declining coherence)
3. Find weekly cycles and peak periods
4. Consider sample size (higher count = more reliable)
5. Predict which time slots will achieve C(t) ≥ 0.92 in the coming week

OUTPUT FORMAT (JSON):
{
  "forecast": [
    {
      "day": "Monday",
      "hours": [9, 10, 14, 15],
      "predictedCoherence": 0.928,
      "confidence": "high",
      "reasoning": "Strong historical pattern with 50+ samples"
    }
  ],
  "trends": {
    "overall": "improving|stable|declining",
    "bestDay": "Wednesday",
    "bestHours": [14, 15, 16],
    "peakCoherence": 0.952
  },
  "recommendations": [
    "Focus trading on Wednesday 14:00-17:00 (predicted C=0.95)",
    "Avoid Monday mornings (historically low coherence)"
  ],
  "confidence": "high|medium|low",
  "dataQuality": "excellent|good|fair|poor"
}`;

    const userPrompt = `Analyze this historical coherence data for ${symbol} and forecast optimal trading windows for the upcoming week:

HISTORICAL DATA (Last 14 days, sorted by avg coherence):
${JSON.stringify(dataSummary, null, 2)}

STATISTICS:
- Symbol: ${symbol}
- Total data points: ${historyData.length}
- Date range: ${new Date(historyData[0].timestamp).toLocaleDateString()} to ${new Date(historyData[historyData.length - 1].timestamp).toLocaleDateString()}
- Unique time slots with data: ${Object.keys(aggregatedData).length}

Provide a comprehensive forecast for the next 7 days with specific time slots that are predicted to achieve optimal coherence for ${symbol}.`;

    console.log('[forecast-coherence] Calling Lovable AI for analysis');

    const aiResponse = await fetchExternalLlm({
      primaryApiKey: lovableApiKey,
      primaryBody: {
        model: 'google/gemini-2.5-flash',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        response_format: { type: 'json_object' },
      },
    });

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      console.error('[forecast-coherence] AI API error:', aiResponse.status, errorText);
      
      if (aiResponse.status === 429) {
        return new Response(
          JSON.stringify({ error: 'Rate limit exceeded. Please try again later.' }),
          { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      
      throw new Error(`AI API error: ${aiResponse.status}`);
    }

    const aiData = await aiResponse.json();
    console.log('[forecast-coherence] AI analysis complete');

    const forecastResult = parseExternalLlmJson<Record<string, unknown> | null>(
      aiData.choices?.[0]?.message?.content,
      null,
    );
    if (!forecastResult) {
      throw new Error('AI response did not contain valid forecast JSON');
    }

    // Add metadata
    const response = {
      ...forecastResult,
      symbol,
      metadata: {
        generatedAt: new Date().toISOString(),
        historicalDataPoints: historyData.length,
        analysisWindow: '14 days',
        forecastWindow: '7 days',
        symbol,
      },
    };

    console.log('[forecast-coherence] Forecast generated successfully');

    return new Response(
      JSON.stringify(response),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );

  } catch (error) {
    console.error('[forecast-coherence] Error:', error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : 'Unknown error',
        details: 'Failed to generate coherence forecast',
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});
