import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { fetchExternalLlm } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { trades } = await req.json();
    
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');

    // Build context from trades
    const tradesSummary = trades.slice(0, 10).map((t: any) => 
      `${t.side} ${t.quantity} ${t.symbol} @ $${t.price} (ID: ${t.transaction_id})`
    ).join('\n');

    const totalBuys = trades.filter((t: any) => t.side === 'BUY').length;
    const totalSells = trades.filter((t: any) => t.side === 'SELL').length;
    const symbols = [...new Set(trades.map((t: any) => t.symbol))];

    const systemPrompt = `You are an expert crypto trading analyst providing live commentary on trading activity. Be concise, insightful, and highlight:
- Trade execution patterns (clustering, timing)
- Market context (what the trades might indicate about market sentiment)
- Performance patterns (win streaks, volume concentration)
- Risk observations (position sizing, diversification)

Keep responses under 150 words. Be engaging and use trading terminology.`;

    const userPrompt = `Analyze these recent trades and provide live commentary:

Recent Trades:
${tradesSummary}

Summary: ${trades.length} total trades, ${totalBuys} buys, ${totalSells} sells
Symbols traded: ${symbols.join(', ')}

What's happening?`;

    const response = await fetchExternalLlm({
      primaryApiKey: LOVABLE_API_KEY,
      primaryBody: {
        model: 'google/gemini-2.5-flash',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('AI API error:', response.status, errorText);
      return new Response(JSON.stringify({ error: 'AI service error', details: errorText }), {
        status: response.status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const data = await response.json();
    const commentary = data.choices?.[0]?.message?.content || 'Unable to generate commentary';

    return new Response(JSON.stringify({ commentary }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    console.error('Error generating commentary:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
