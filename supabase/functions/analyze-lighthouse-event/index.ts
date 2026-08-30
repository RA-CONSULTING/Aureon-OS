import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { fetchExternalLlm } from "../_shared/external_llm_fallback.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface AnalysisRequest {
  lighthouseEvent: {
    lambda: number;
    coherence: number;
    lighthouseSignal: number;
    confidence: number;
    isLHE: boolean;
    dominantNode: string;
    prismLevel: number;
    prismState: string;
  };
  tradingSignal: {
    type: string;
    strength: number;
    reason: string;
  };
  marketData: {
    symbol: string;
    price: number;
    volume: number;
    volatility: number;
  };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { lighthouseEvent, tradingSignal, marketData }: AnalysisRequest = await req.json();
    
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');

    console.log('🤖 Generating AI analysis for Lighthouse Event...');

    const prompt = `You are an expert financial analyst explaining AUREON Quantum Trading System signals to traders.

MARKET CONTEXT:
- Symbol: ${marketData.symbol}
- Current Price: $${marketData.price.toFixed(2)}
- Volume: ${marketData.volume.toFixed(2)}
- Volatility: ${(marketData.volatility * 100).toFixed(2)}%

LIGHTHOUSE EVENT DETECTED:
- Lambda (Λ): ${lighthouseEvent.lambda.toFixed(3)} (field state)
- Coherence (Γ): ${lighthouseEvent.coherence.toFixed(3)} (alignment quality)
- Lighthouse Signal (L): ${lighthouseEvent.lighthouseSignal.toFixed(3)}
- Confidence: ${(lighthouseEvent.confidence * 100).toFixed(1)}%
- LHE Detected: ${lighthouseEvent.isLHE ? 'YES ✅' : 'NO'}
- Dominant Node: ${lighthouseEvent.dominantNode}
- Prism Level: ${lighthouseEvent.prismLevel}/5
- Prism State: ${lighthouseEvent.prismState}

TRADING SIGNAL GENERATED:
- Type: ${tradingSignal.type}
- Strength: ${(tradingSignal.strength * 100).toFixed(1)}%
- Reason: ${tradingSignal.reason}

Provide a concise 2-3 paragraph analysis that:
1. Explains what this Lighthouse Event means in plain language
2. Interprets the significance of the coherence and dominant node
3. Evaluates the trading signal strength and viability
4. Provides actionable insight (consider or wait)

Keep it professional, clear, and actionable. Avoid jargon unless necessary.`;

    const response = await fetchExternalLlm({
      primaryApiKey: LOVABLE_API_KEY,
      primaryBody: {
        model: 'google/gemini-2.5-flash',
        messages: [
          {
            role: 'system',
            content: 'You are a professional financial analyst providing clear, actionable insights about quantum trading signals.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 500,
      },
    });

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(
          JSON.stringify({ 
            error: 'Rate limit exceeded. Please try again in a moment.',
            analysis: 'AI analysis temporarily unavailable due to rate limits.'
          }),
          { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      if (response.status === 402) {
        return new Response(
          JSON.stringify({ 
            error: 'Payment required. Please add credits to your Lovable workspace.',
            analysis: 'AI analysis requires credits. Please add credits in Settings → Usage.'
          }),
          { status: 402, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      throw new Error(`AI API error: ${response.status}`);
    }

    const data = await response.json();
    const analysis = data.choices?.[0]?.message?.content || 'Analysis generation failed';

    console.log('✅ AI analysis generated successfully');

    return new Response(
      JSON.stringify({ 
        success: true, 
        analysis,
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Analysis error:', error);
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error',
        analysis: 'Unable to generate AI analysis at this time.'
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
