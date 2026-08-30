import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.3";
import { fetchExternalLlm, parseExternalLlmJson } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const lovableApiKey = Deno.env.get("LOVABLE_API_KEY");
    
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { temporalId = "02111991", hoursBack = 24, predictionHours = 6 } = await req.json();

    console.log("🔮 Analyzing Stargate Network Patterns");
    console.log("📊 Analysis Window:", hoursBack, "hours");
    console.log("⏰ Prediction Window:", predictionHours, "hours");

    // Fetch historical stargate network data
    const { data: networkStates, error: queryError } = await supabase
      .from("stargate_network_states")
      .select("*")
      .eq("temporal_id", temporalId)
      .gte("event_timestamp", new Date(Date.now() - hoursBack * 60 * 60 * 1000).toISOString())
      .order("event_timestamp", { ascending: true });

    if (queryError) throw queryError;

    if (!networkStates || networkStates.length === 0) {
      return new Response(
        JSON.stringify({
          success: false,
          error: "Insufficient historical data for analysis",
          dataPoints: 0,
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    console.log("📈 Analyzing", networkStates.length, "data points");

    // Prepare data summary for AI analysis
    const dataSummary = {
      totalPoints: networkStates.length,
      timeRange: `${hoursBack} hours`,
      avgNetworkStrength: networkStates.reduce((sum, s) => sum + Number(s.network_strength), 0) / networkStates.length,
      maxNetworkStrength: Math.max(...networkStates.map(s => Number(s.network_strength))),
      minNetworkStrength: Math.min(...networkStates.map(s => Number(s.network_strength))),
      avgCoherence: networkStates.reduce((sum, s) => sum + (Number(s.avg_coherence) || 0), 0) / networkStates.length,
      avgGridEnergy: networkStates.reduce((sum, s) => sum + Number(s.grid_energy), 0) / networkStates.length,
      highCoherencePeriods: networkStates.filter(s => Number(s.network_strength) > 0.9).length,
      samples: networkStates.slice(-20).map(s => ({
        timestamp: s.event_timestamp,
        networkStrength: Number(s.network_strength),
        avgCoherence: Number(s.avg_coherence || 0),
        gridEnergy: Number(s.grid_energy),
        activeNodes: s.active_nodes,
      })),
    };

    // Call Lovable AI for pattern analysis
    const aiResponse = await fetchExternalLlm({
      primaryApiKey: lovableApiKey,
      primaryBody: {
        model: "google/gemini-2.5-flash",
        messages: [
          {
            role: "system",
            content: `You are an expert pattern recognition system for the AUREON Quantum Trading System's Stargate Network.

Your task is to analyze historical stargate network coherence data and predict optimal trading windows.

Key metrics to analyze:
- Network Strength (0-1): Overall network coherence and connectivity
- Avg Coherence (0-1): Average node coherence levels
- Grid Energy (0-1): Planetary energy flow levels
- Active Nodes (1-12): Number of active stargate nodes

High trading opportunity indicators:
- Network Strength > 0.9
- Avg Coherence > 0.9
- Grid Energy > 0.7
- Stable patterns (less volatility)

Analyze temporal patterns:
- Time of day patterns
- Cyclical patterns (daily, hourly)
- Trend direction and momentum
- Volatility patterns

Provide predictions in JSON format with:
{
  "patterns": [
    {
      "type": "daily_peak" | "hourly_cycle" | "energy_surge" | "coherence_wave",
      "description": "Clear description of the pattern",
      "confidence": 0.0-1.0,
      "strength": 0.0-1.0
    }
  ],
  "predictions": [
    {
      "startTime": "ISO timestamp",
      "endTime": "ISO timestamp",
      "expectedNetworkStrength": 0.0-1.0,
      "expectedCoherence": 0.0-1.0,
      "confidence": 0.0-1.0,
      "tradingOpportunity": "excellent" | "good" | "moderate" | "poor",
      "reasoning": "Why this window is predicted to be optimal"
    }
  ],
  "recommendation": "Overall recommendation for next ${predictionHours} hours",
  "riskFactors": ["Any risks or uncertainties to consider"]
}`
          },
          {
            role: "user",
            content: `Analyze this stargate network data and predict optimal trading windows for the next ${predictionHours} hours:

${JSON.stringify(dataSummary, null, 2)}

Focus on identifying patterns in network strength and coherence that correlate with high-quality trading opportunities.`
          }
        ],
        temperature: 0.3,
      },
    });

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      console.error("AI API Error:", aiResponse.status, errorText);
      
      if (aiResponse.status === 429) {
        return new Response(
          JSON.stringify({ error: "Rate limit exceeded. Please try again later." }),
          { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      
      if (aiResponse.status === 402) {
        return new Response(
          JSON.stringify({ error: "AI credits depleted. Please add credits to your workspace." }),
          { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      
      throw new Error(`AI API error: ${aiResponse.status}`);
    }

    const aiResult = await aiResponse.json();
    const analysisContent = aiResult.choices?.[0]?.message?.content;
    
    if (!analysisContent) {
      throw new Error("No analysis returned from AI");
    }

    console.log("🤖 AI Analysis Complete");

    // Parse plain, fenced, or prose-wrapped JSON consistently across providers.
    type StargateAnalysis = {
      patterns?: unknown[];
      predictions?: Array<{
        expectedNetworkStrength?: number;
        expectedCoherence?: number;
        confidence?: number;
      }>;
      recommendation?: string;
      riskFactors?: unknown[];
    };
    const analysis = parseExternalLlmJson<StargateAnalysis | null>(analysisContent, null) || {
      patterns: [],
      predictions: [],
      recommendation: analysisContent.substring(0, 500),
      riskFactors: ["Unable to parse structured predictions"],
    };

    // Store analysis result
    const { error: insertError } = await supabase
      .from("harmonic_nexus_states")
      .insert({
        temporal_id: temporalId,
        sentinel_name: "PATTERN_ANALYZER",
        omega_value: analysis.predictions?.[0]?.expectedNetworkStrength || 0.5,
        substrate_coherence: analysis.predictions?.[0]?.expectedCoherence || 0.5,
        field_integrity: analysis.predictions?.[0]?.confidence || 0.5,
        harmonic_resonance: 528,
        dimensional_alignment: 0.95,
        psi_potential: 1.0,
        love_coherence: 1.0,
        observer_consciousness: 1.0,
        theta_alignment: 0.98,
        unity_probability: 0.95,
        akashic_frequency: 528,
        akashic_convergence: 0.9,
        akashic_stability: 0.95,
        akashic_boost: 0.1,
        sync_status: "pattern_analysis",
        sync_quality: 1.0,
        metadata: {
          analysisType: "stargate_pattern_recognition",
          dataPoints: networkStates.length,
          hoursAnalyzed: hoursBack,
          predictionHours,
          analysis,
        },
      });

    if (insertError) {
      console.error("Failed to store analysis:", insertError);
    }

    return new Response(
      JSON.stringify({
        success: true,
        dataPoints: networkStates.length,
        timeRange: `${hoursBack} hours`,
        currentMetrics: dataSummary,
        analysis,
        timestamp: new Date().toISOString(),
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );

  } catch (error) {
    console.error("❌ Pattern analysis error:", error);
    
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: error instanceof Error ? error.message : "Unknown error" 
      }),
      { 
        status: 500, 
        headers: { ...corsHeaders, "Content-Type": "application/json" } 
      }
    );
  }
});
