import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

function freshSourceTimestamp(value: unknown): string | null {
  const timestamp = String(value || '');
  const age = Date.now() - Date.parse(timestamp);
  return Number.isFinite(age) && age >= 0 && age <= 5 * 60 * 1000 ? timestamp : null;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const anonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace(/^Bearer\s+/i, '');
    if (!token) throw new Error('AUTHENTICATION_REQUIRED');
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error: authError } = await authClient.auth.getUser(token);
    if (authError || !user) throw new Error('INVALID_AUTHENTICATION');

    const { action, huntSessionId, liveExecutionConfirmed } = await req.json();
    
    console.log(`Hunt Loop ${action} request:`, { huntSessionId });

    if (action === 'scan') {
      // === PRIDE SCANNER: Find opportunities across all markets ===
      if (!huntSessionId) throw new Error('huntSessionId required');

      const scanStart = Date.now();

      // Get hunt session
      const { data: huntSession, error: sessionError } = await supabase
        .from('hunt_sessions')
        .select('*, hive_sessions!inner(*)')
        .eq('id', huntSessionId)
        .eq('user_id', user.id)
        .eq('hive_sessions.user_id', user.id)
        .single();

      if (sessionError || !huntSession) {
        throw new Error('Hunt session not found');
      }

      if (huntSession.status !== 'active') {
        return new Response(
          JSON.stringify({ success: false, error: 'Hunt session not active' }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
        );
      }

      // Get active hive and agent
      const { data: hives } = await supabase
        .from('hive_instances')
        .select('id')
        .or(`id.eq.${huntSession.hive_sessions.root_hive_id},parent_hive_id.eq.${huntSession.hive_sessions.root_hive_id}`)
        .eq('status', 'active')
        .limit(1)
        .single();

      if (!hives) {
        throw new Error('No active hive found');
      }

      const { data: agent } = await supabase
        .from('hive_agents')
        .select('id')
        .eq('hive_id', hives.id)
        .limit(1)
        .single();

      if (!agent) {
        throw new Error('No active agent found');
      }

      // Fetch market data from Binance
      const tickerResponse = await fetch('https://api.binance.com/api/v3/ticker/24hr');
      if (!tickerResponse.ok) {
        throw new Error('Failed to fetch Binance market data');
      }

      const tickers = await tickerResponse.json();
      console.log(`Fetched ${tickers.length} market pairs`);

      const signalFreshnessMs = 5 * 60 * 1000;
      const signalCutoff = new Date(Date.now() - signalFreshnessMs).toISOString();
      const { data: qgitaSignals, error: qgitaError } = await supabase
        .from('qgita_signal_states')
        .select('id, signal_type, tier, strength, confidence, lighthouse_l, linear_coherence, nonlinear_coherence, cross_scale_coherence, metadata, created_at, truth_status, source_id, source_timestamp, generated_values')
        .eq('user_id', user.id)
        .eq('truth_status', 'real_derived')
        .eq('generated_values', false)
        .gte('source_timestamp', signalCutoff)
        .order('source_timestamp', { ascending: false })
        .limit(1000);
      if (qgitaError) throw new Error(`QGITA live signal read failed: ${qgitaError.message}`);

      const positionSizeUSD = Number(Deno.env.get('HUNT_POSITION_SIZE_USD'));
      const positionSizingConfigured = Number.isFinite(positionSizeUSD) && positionSizeUSD > 0;
      const twapThresholdUsd = Number(huntSession.twap_threshold_usd);
      const twapDurationSeconds = Number(huntSession.twap_duration_seconds);
      const twapConfigured = Number.isFinite(twapThresholdUsd) && twapThresholdUsd > 0 &&
        Number.isFinite(twapDurationSeconds) && twapDurationSeconds > 0;

      // Filter and score opportunities
      const opportunities = [];
      const validSourceTimestamps: string[] = [];
      for (const ticker of tickers) {
        // Only USDT pairs for simplicity
        if (!ticker.symbol.endsWith('USDT')) continue;

        const price = parseFloat(ticker.lastPrice);
        const volume24h = parseFloat(ticker.quoteVolume);
        const priceChange = parseFloat(ticker.priceChangePercent);
        const providerTimestamp = Number(ticker.closeTime);
        const sourceTimestamp = new Date(providerTimestamp).toISOString();
        const sourceAge = Date.now() - providerTimestamp;
        if (![price, volume24h, priceChange, providerTimestamp].every(Number.isFinite) ||
            price <= 0 || volume24h < 0 || sourceAge < 0 || sourceAge > 5 * 60 * 1000) continue;
        validSourceTimestamps.push(sourceTimestamp);
        
        // Calculate volatility as abs(price change)
        const volatility = Math.abs(priceChange);

        // Filter by minimum thresholds
        if (volatility < huntSession.min_volatility_pct) continue;
        if (volume24h < huntSession.min_volume_usd) continue;

        // Opportunity score = volatility × volume (normalized)
        const opportunityScore = volatility * (volume24h / 1000000);

        opportunities.push({
          symbol: ticker.symbol,
          baseAsset: ticker.symbol.replace('USDT', ''),
          quoteAsset: 'USDT',
          price,
          volume24h,
          volatility24h: volatility,
          opportunityScore,
          priceChange,
          sourceId: 'binance:/api/v3/ticker/24hr',
          sourceTimestamp,
        });
      }
      if (validSourceTimestamps.length === 0) throw new Error('NO_FRESH_BINANCE_TICKER_RECEIPTS');
      const scanSourceTimestamp = validSourceTimestamps.sort()[0];

      // Sort by opportunity score and take top N
      opportunities.sort((a, b) => b.opportunityScore - a.opportunityScore);
      const topTargets = opportunities.slice(0, huntSession.max_targets);

      console.log(`Found ${topTargets.length} targets out of ${opportunities.length} candidates`);

      let signalsGenerated = 0;
      let ordersQueued = 0;

      // Process each target through QGITA → OMS pipeline
      for (const target of topTargets) {
        let savedTargetId: string | null = null;
        
        try {
          // Save target to database
          const { data: savedTarget } = await supabase
            .from('hunt_targets')
            .insert({
              hunt_session_id: huntSessionId,
              symbol: target.symbol,
              base_asset: target.baseAsset,
              quote_asset: target.quoteAsset,
              price: target.price,
              volume_24h: target.volume24h,
              volatility_24h: target.volatility24h,
              opportunity_score: target.opportunityScore,
              status: 'analyzing',
              truth_status: 'real_derived',
              source_id: target.sourceId,
              source_timestamp: target.sourceTimestamp,
              generated_values: false,
            })
            .select()
            .single();

          if (!savedTarget) continue;
          savedTargetId = savedTarget.id;

          const qgitaSignal = (qgitaSignals || []).find((signal: any) =>
            String(signal.metadata?.symbol || '').toUpperCase() === target.symbol.toUpperCase() &&
            ['BUY', 'SELL', 'HOLD'].includes(String(signal.signal_type || '').toUpperCase()) &&
            signal.truth_status === 'real_derived' && signal.generated_values === false &&
            Boolean(signal.source_id) && Boolean(freshSourceTimestamp(signal.source_timestamp))
          );
          if (!qgitaSignal) {
            await supabase.from('hunt_targets').update({
              status: 'rejected',
              rejection_reason: 'NO_FRESH_NATIVE_QGITA_SIGNAL',
              processed_at: new Date().toISOString(),
            }).eq('id', savedTargetId);
            continue;
          }

          const signalType = String(qgitaSignal.signal_type).toUpperCase();
          const confidence = Number(qgitaSignal.confidence);
          const tier = Number(qgitaSignal.tier);
          if (!Number.isFinite(confidence) || !Number.isFinite(tier) || signalType === 'HOLD') {
            await supabase.from('hunt_targets').update({
              status: 'rejected',
              rejection_reason: signalType === 'HOLD' ? 'NATIVE_QGITA_HOLD' : 'INVALID_NATIVE_QGITA_SIGNAL',
              processed_at: new Date().toISOString(),
            }).eq('id', savedTargetId);
            continue;
          }
          
          // Priority = confidence + bonuses
          let priority = Math.floor(confidence);
          if (target.volatility24h > 10) priority = Math.min(100, priority + 10); // High vol bonus
          if (target.volume24h > 10000000) priority = Math.min(100, priority + 5); // High volume bonus

          if (!savedTarget) continue;

          // Update target with signal
          await supabase
            .from('hunt_targets')
            .update({
              status: 'queued',
              signal_generated: true,
              signal_type: signalType,
              signal_confidence: confidence,
              signal_tier: tier,
              processed_at: new Date().toISOString(),
            })
            .eq('id', savedTargetId);

          signalsGenerated++;

          // Only queue Tier 1 and Tier 2 signals
          if (tier <= 2) {
            if (liveExecutionConfirmed !== true) {
              await supabase.from('hunt_targets').update({
                status: 'analyzed',
                rejection_reason: 'LIVE_EXECUTION_NOT_CONFIRMED_ANALYSIS_ONLY',
                processed_at: new Date().toISOString(),
              }).eq('id', savedTargetId);
              continue;
            }
            if (!positionSizingConfigured) {
              await supabase.from('hunt_targets').update({
                status: 'rejected',
                rejection_reason: 'HUNT_POSITION_SIZE_USD_NOT_CONFIGURED',
                processed_at: new Date().toISOString(),
              }).eq('id', savedTargetId);
              continue;
            }
            const tierMultiplier = tier === 1 ? 1.0 : 0.5;
            const positionSize = positionSizeUSD * tierMultiplier;
            const quantity = positionSize / target.price;
            const orderValueUSD = positionSize;

            // Check if order should use TWAP (above threshold)
            if (!twapConfigured) {
              await supabase.from('hunt_targets').update({
                status: 'rejected',
                rejection_reason: 'HUNT_TWAP_CONFIG_NOT_CONFIGURED',
                processed_at: new Date().toISOString(),
              }).eq('id', savedTargetId);
              continue;
            }
            const useTWAP = orderValueUSD >= twapThresholdUsd;

            if (useTWAP) {
              // Place TWAP order directly
              console.log(`📊 ${target.symbol} using TWAP: $${orderValueUSD.toFixed(2)}`);
              
              const { data: twapResult, error: twapError } = await supabase.functions.invoke('binance-algo-twap', {
                headers: { Authorization: authHeader as string },
                body: {
                  action: 'place',
                  symbol: target.symbol,
                  side: signalType,
                  quantity,
                  duration: twapDurationSeconds,
                  limitPrice: target.price,
                  huntSessionId: huntSessionId,
                  liveExecutionConfirmed: true,
                  truthStatus: 'real_derived',
                  sourceId: `qgita_signal:${qgitaSignal.id}:${qgitaSignal.source_id}+${target.sourceId}`,
                  sourceTimestamp: [qgitaSignal.source_timestamp, target.sourceTimestamp].sort()[0],
                  generatedValues: false,
                },
              });

              if (twapResult?.success) {
                await supabase
                  .from('hunt_targets')
                  .update({ 
                    order_queued: true,
                    status: 'twap_placed',
                  })
                  .eq('id', savedTargetId);

                ordersQueued++;
                console.log(`✅ ${target.symbol} TWAP placed: ${signalType} ${quantity.toFixed(8)} over ${huntSession.twap_duration_seconds}s`);
              } else {
                console.error(`❌ ${target.symbol} TWAP failed:`, twapError);
              }
            } else {
              // Enqueue via OMS for regular execution
              const { data: omsResult } = await supabase.functions.invoke('oms-leaky-bucket', {
                headers: { Authorization: authHeader as string },
                body: {
                  action: 'enqueue',
                  sessionId: huntSession.hive_session_id,
                  hiveId: hives.id,
                  agentId: agent.id,
                  symbol: target.symbol,
                  side: signalType,
                  quantity,
                  price: target.price,
                  priority,
                  metadata: {
                    signalStrength: Number(qgitaSignal.strength),
                    coherence: Number(qgitaSignal.cross_scale_coherence),
                    lighthouseValue: Number(qgitaSignal.lighthouse_l),
                    qgitaSignalId: qgitaSignal.id,
                    qgitaSourceId: qgitaSignal.source_id,
                    qgitaSourceTimestamp: qgitaSignal.source_timestamp,
                    marketSourceId: target.sourceId,
                    marketSourceTimestamp: target.sourceTimestamp,
                    sourceId: `qgita_signal:${qgitaSignal.id}:${qgitaSignal.source_id}+${target.sourceId}`,
                    sourceTimestamp: [qgitaSignal.source_timestamp, target.sourceTimestamp].sort()[0],
                    truthStatus: 'real_derived',
                    generatedValues: false,
                    huntOpportunityScore: target.opportunityScore,
                    volatility24h: target.volatility24h,
                    volume24h: target.volume24h,
                  },
                },
              });

              if (omsResult?.success) {
                await supabase
                  .from('hunt_targets')
                  .update({ order_queued: true })
                  .eq('id', savedTargetId);

                ordersQueued++;
                console.log(`✅ ${target.symbol} queued: ${signalType} P${priority} Tier${tier}`);
              }
            }
          } else {
            // Tier 3 signals rejected
            await supabase
              .from('hunt_targets')
              .update({
                status: 'rejected',
                rejection_reason: 'Tier 3 signal (confidence < 60%)',
              })
              .eq('id', savedTargetId);
          }

        } catch (error) {
          console.error(`Failed to process ${target.symbol}:`, error);
          if (savedTargetId) {
            await supabase
              .from('hunt_targets')
              .update({
                status: 'error',
                rejection_reason: error instanceof Error ? error.message : 'Unknown error',
              })
              .eq('id', savedTargetId);
          }
        }
      }

      const scanDuration = Date.now() - scanStart;

      // Record scan history
      await supabase
        .from('hunt_scans')
        .insert({
          hunt_session_id: huntSessionId,
          scan_duration_ms: scanDuration,
          pairs_scanned: validSourceTimestamps.length,
          targets_found: topTargets.length,
          signals_generated: signalsGenerated,
          orders_queued: ordersQueued,
          top_symbol: topTargets[0]?.symbol,
          top_score: topTargets[0]?.opportunityScore,
          truth_status: 'real_derived',
          source_id: 'binance:/api/v3/ticker/24hr',
          source_timestamp: scanSourceTimestamp,
          generated_values: false,
        });

      // Update hunt session stats
      await supabase
        .from('hunt_sessions')
        .update({
          total_scans: huntSession.total_scans + 1,
          total_targets_found: huntSession.total_targets_found + topTargets.length,
          total_signals_generated: huntSession.total_signals_generated + signalsGenerated,
          total_orders_queued: huntSession.total_orders_queued + ordersQueued,
          last_scan_at: new Date().toISOString(),
        })
        .eq('id', huntSessionId);

      console.log(`🦁 Hunt scan complete: ${topTargets.length} targets, ${signalsGenerated} signals, ${ordersQueued} queued (${scanDuration}ms)`);

      return new Response(
        JSON.stringify({
          success: true,
          scanDuration,
          pairsScanned: validSourceTimestamps.length,
          targetsFound: topTargets.length,
          signalsGenerated,
          ordersQueued,
          topTargets: topTargets.slice(0, 3).map(t => ({
            symbol: t.symbol,
            score: t.opportunityScore.toFixed(2),
            volatility: t.volatility24h.toFixed(2),
            volume: `$${(t.volume24h / 1000000).toFixed(2)}M`,
          })),
          truthStatus: 'real_derived',
          sourceId: 'binance:/api/v3/ticker/24hr',
          sourceTimestamp: scanSourceTimestamp,
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    throw new Error(`Unknown action: ${action}`);

  } catch (error) {
    console.error('Hunt loop error:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return new Response(
      JSON.stringify({ success: false, error: message, truthStatus: 'no_data', generatedValues: false }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: /AUTHENTICATION/.test(message) ? 401 : 409 }
    );
  }
});
