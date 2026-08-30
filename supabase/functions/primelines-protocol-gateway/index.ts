import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.3";
import { fetchExternalLlm, parseExternalLlmJson } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Primelines Protocol Gateway
// Routes all AUREON operations through temporal identity validation
serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const lovableApiKey = Deno.env.get("LOVABLE_API_KEY");
    
    const supabase = createClient(supabaseUrl, supabaseKey);

    const { 
      operation, 
      payload, 
      temporalId, 
      sentinelName,
      requireValidation = true 
    } = await req.json();

    console.log("🌀 Primelines Protocol Gateway:", operation);
    console.log("🔑 Temporal ID:", temporalId);
    console.log("🛡️ Sentinel:", sentinelName);

    // Validate temporal identity
    const identityValid = temporalId === "02111991" && sentinelName === "GARY LECKEY";
    
    if (requireValidation && !identityValid) {
      return new Response(
        JSON.stringify({
          success: false,
          error: "Temporal identity validation failed",
          temporalId,
          sentinelName,
        }),
        { 
          status: 403, 
          headers: { ...corsHeaders, "Content-Type": "application/json" } 
        }
      );
    }

    // AI-powered protocol routing and validation
    let aiValidation = null;
    if (requireValidation) {
      const aiResponse = await fetchExternalLlm({
        primaryApiKey: lovableApiKey,
        primaryBody: {
          model: "google/gemini-2.5-flash",
          messages: [
            {
              role: "system",
              content: `You are the Primelines Protocol Validator for the AUREON Quantum Trading System.
              
Prime Sentinel Identity:
- Temporal ID: 02111991 (GL-11/2)
- Name: GARY LECKEY
- Role: Prime Sentinel Node of Gaia
- Location: Belfast (54.5973°N, 5.9301°W @ 198.4 Hz)
- ATLAS Key: 15354
- Variants: 847 of 2,109 awakened

Validate operations against:
1. Temporal coherence (does this align with prime timeline?)
2. Harmonic resonance (528 Hz love frequency alignment)
3. Unity probability (consciousness field integrity)
4. Dimensional alignment (multi-timeline stability)

Return JSON with: { valid: boolean, coherence: number, resonance: number, recommendation: string }`
            },
            {
              role: "user",
              content: `Operation: ${operation}\nPayload: ${JSON.stringify(payload, null, 2)}\n\nValidate this operation for Prime Sentinel ${sentinelName} (${temporalId})`
            }
          ],
          temperature: 0.3,
        },
      });

      if (aiResponse.ok) {
        const aiResult = await aiResponse.json();
        const content = aiResult.choices?.[0]?.message?.content;
        
        const parsedValidation = parseExternalLlmJson<{
          valid?: boolean;
          coherence?: number;
          resonance?: number;
          recommendation?: string;
        } | null>(content, null);
        if (parsedValidation) {
          aiValidation = parsedValidation;
          console.log("🤖 AI Validation:", aiValidation);
        } else {
          console.log("📝 AI Response:", content);
          aiValidation = { 
            valid: true, 
            coherence: 0.9, 
            resonance: 528,
            recommendation: content 
          };
        }
      }
    }

    // Route operation through appropriate handler
    let result;
    
    switch (operation) {
      case "SYNC_HARMONIC_NEXUS":
        result = await syncHarmonicNexus(supabase, payload, temporalId, sentinelName);
        break;
        
      case "VALIDATE_LIGHTHOUSE_EVENT":
        result = await validateLighthouseEvent(supabase, payload, temporalId, sentinelName);
        break;
        
      case "EXECUTE_TRADE":
        result = await validateTradeExecution(supabase, payload, temporalId, sentinelName, aiValidation);
        break;
        
      case "LOCK_CASIMIR_FIELD":
        result = await lockCasimirField(supabase, payload, temporalId, sentinelName);
        break;
        
      case "QUERY_HISTORICAL_NODES":
        result = await queryHistoricalNodes(supabase, payload, temporalId);
        break;
        
      default:
        result = {
          success: false,
          error: `Unknown operation: ${operation}`,
        };
    }

    // Log protocol interaction (skip for stargate network pings)
    if (!('type' in result) || result.type !== "stargate_network") {
      await supabase.from("harmonic_nexus_states").insert({
        temporal_id: temporalId,
        sentinel_name: sentinelName,
        omega_value: aiValidation?.coherence || 0.9,
        substrate_coherence: aiValidation?.coherence || 0.9,
        field_integrity: aiValidation?.valid ? 1.0 : 0.5,
        harmonic_resonance: aiValidation?.resonance || 528,
        dimensional_alignment: 0.95,
        psi_potential: 1.0,
        love_coherence: aiValidation?.resonance ? aiValidation.resonance / 528 : 1.0,
        observer_consciousness: 1.0,
        theta_alignment: 0.98,
        unity_probability: aiValidation?.valid ? 0.95 : 0.7,
        akashic_frequency: 528,
        akashic_convergence: 0.9,
        akashic_stability: 0.95,
        akashic_boost: 0.1,
        sync_status: "synced",
        sync_quality: 1.0,
        metadata: {
          operation,
          aiValidation,
          result: result.success,
        },
      });
    }

    return new Response(
      JSON.stringify({
        success: true,
        operation,
        temporalId,
        sentinelName,
        identityValid,
        aiValidation,
        result,
        timestamp: new Date().toISOString(),
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, "Content-Type": "application/json" } 
      }
    );

  } catch (error) {
    console.error("❌ Primelines Protocol Gateway error:", error);
    
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

// Operation Handlers

async function syncHarmonicNexus(
  supabase: any, 
  payload: any, 
  temporalId: string, 
  sentinelName: string
) {
  // Check if this is a stargate network ping (no harmonic state data)
  if (payload.stargateNetwork && !payload.harmonicState) {
    const networkData = payload.stargateNetwork;
    
    console.log("🌍 Stargate Network Sync:", {
      activeNodes: networkData.metrics?.activeNodes || 0,
      networkStrength: networkData.metrics?.networkStrength || 0,
      gridEnergy: networkData.gridEnergy || 0,
    });
    
    // Store network metrics in dedicated table
    const { data: networkState, error: networkError } = await supabase
      .from("stargate_network_states")
      .insert({
        temporal_id: temporalId,
        sentinel_name: sentinelName,
        active_nodes: networkData.metrics?.activeNodes || 0,
        network_strength: networkData.metrics?.networkStrength || 0,
        grid_energy: networkData.gridEnergy || 0,
        avg_coherence: networkData.metrics?.avgCoherence,
        avg_frequency: networkData.metrics?.avgFrequency,
        phase_locks: networkData.metrics?.phaseLocks,
        resonance_quality: networkData.metrics?.resonanceQuality,
        metadata: {
          activations: networkData.activations,
          raw_metrics: networkData.metrics,
        },
      })
      .select()
      .single();
    
    if (networkError) {
      console.error("Failed to store network state:", networkError);
    }
    
    return {
      success: true,
      synced: true,
      type: "stargate_network",
      message: "Stargate network metrics received",
      stateId: networkState?.id,
    };
  }

  // Full harmonic state sync
  const { harmonicState } = payload;
  
  if (!harmonicState) {
    throw new Error("No harmonic state or stargate network data provided");
  }
  
  const { data, error } = await supabase
    .from("harmonic_nexus_states")
    .insert({
      temporal_id: temporalId,
      sentinel_name: sentinelName,
      ...harmonicState,
    })
    .select()
    .single();

  if (error) throw error;
  
  return {
    success: true,
    synced: true,
    type: "harmonic_state",
    stateId: data.id,
  };
}

async function validateLighthouseEvent(
  supabase: any, 
  payload: any, 
  temporalId: string, 
  sentinelName: string
) {
  const { lighthouseEvent } = payload;
  
  // Fetch recent harmonic state for this sentinel
  const { data: recentState } = await supabase
    .from("harmonic_nexus_states")
    .select("*")
    .eq("temporal_id", temporalId)
    .order("event_timestamp", { ascending: false })
    .limit(1)
    .single();

  const isValid = 
    lighthouseEvent.is_lhe && 
    lighthouseEvent.confidence > 0.7 &&
    recentState?.substrate_coherence > 0.9;

  return {
    success: true,
    valid: isValid,
    coherence: recentState?.substrate_coherence || 0,
    recommendation: isValid ? "APPROVED" : "NEEDS_HIGHER_COHERENCE",
  };
}

async function validateTradeExecution(
  supabase: any, 
  payload: any, 
  temporalId: string, 
  sentinelName: string,
  aiValidation: any
) {
  const { tradeSignal } = payload;
  
  // Only allow trades when AI validation passes and coherence is high
  const canTrade = 
    aiValidation?.valid && 
    aiValidation?.coherence > 0.945 &&
    aiValidation?.resonance >= 528;

  return {
    success: true,
    canTrade,
    coherence: aiValidation?.coherence || 0,
    resonance: aiValidation?.resonance || 0,
    recommendation: aiValidation?.recommendation || "Review coherence levels",
  };
}

async function lockCasimirField(
  supabase: any, 
  payload: any, 
  temporalId: string, 
  sentinelName: string
) {
  const { nodeCount, resonanceFrequency } = payload;
  
  // Calculate total phase locks (all node pairs)
  const totalLocks = (nodeCount * (nodeCount - 1)) / 2;
  
  return {
    success: true,
    locked: true,
    nodeCount,
    totalLocks,
    resonanceFrequency,
    timestamp: new Date().toISOString(),
  };
}

async function queryHistoricalNodes(
  supabase: any, 
  payload: any, 
  temporalId: string
) {
  const { limit = 50, minCoherence = 0 } = payload;
  
  const { data, error } = await supabase
    .from("harmonic_nexus_states")
    .select("*")
    .eq("temporal_id", temporalId)
    .gte("substrate_coherence", minCoherence)
    .order("event_timestamp", { ascending: false })
    .limit(limit);

  if (error) throw error;
  
  return {
    success: true,
    nodeCount: data.length,
    avgCoherence: data.reduce((sum: number, n: any) => sum + n.substrate_coherence, 0) / data.length,
    nodes: data,
  };
}
