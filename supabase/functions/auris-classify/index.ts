import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { fetchExternalLlm, parseExternalLlmJson } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const payload = await req.json();
    const texts = Array.isArray(payload?.texts)
      ? payload.texts.map((value: unknown) => String(value || "").trim()).filter(Boolean).slice(0, 50)
      : [];
    if (!texts.length) {
      return new Response(JSON.stringify({ items: [] }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const response = await fetchExternalLlm({
      primaryApiKey: Deno.env.get("LOVABLE_API_KEY"),
      primaryBody: {
        model: "google/gemini-2.5-flash",
        temperature: 0,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You are Auris, an analyst. Return JSON only. For each input return valence (0..1), arousal (0..1), primary emotion, and up to four context tags.",
          },
          {
            role: "user",
            content: JSON.stringify({
              instruction: "Return {items:[{valence,arousal,emotion,tags}]} in exactly the input order.",
              items: texts,
            }),
          },
        ],
      },
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: "External LLM unavailable" }), {
        status: response.status,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const data = await response.json();
    const content = String(data?.choices?.[0]?.message?.content || "{}");
    const parsed = parseExternalLlmJson<{ items?: unknown[] }>(content, {});
    return new Response(JSON.stringify({ items: Array.isArray(parsed.items) ? parsed.items : [] }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("auris-classify error", error instanceof Error ? error.message : "unknown");
    return new Response(JSON.stringify({ error: "Classification failed" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
