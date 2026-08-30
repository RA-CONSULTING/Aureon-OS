import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { decryptCredential } from "../_shared/credential_crypto.ts";
import { fetchLiveJson, requireFiniteNumber, requireFreshTimestamp } from "../_shared/real_data.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!;

    // === SECURITY FIX: Verify the user is authenticated ===
    const authHeader = req.headers.get('Authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      console.error('[execute-trade] Missing authorization token');
      return new Response(
        JSON.stringify({ success: false, error: 'Unauthorized' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 401 }
      );
    }

    // Verify user token
    const anonSupabase = createClient(supabaseUrl, supabaseAnonKey);
    const { data: { user }, error: authError } = await anonSupabase.auth.getUser(token);

    if (authError || !user) {
      console.error('[execute-trade] Invalid token:', authError?.message);
      return new Response(
        JSON.stringify({ success: false, error: 'Unauthorized' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 401 }
      );
    }

    console.log('[execute-trade] User verified:', user.id);

    const supabase = createClient(supabaseUrl, supabaseKey);

    // === SECURITY FIX: Verify user has an active trading session ===
    const { data: userSession, error: sessionError } = await supabase
      .from('aureon_user_sessions')
      .select('*')
      .eq('user_id', user.id)
      .single();

    if (sessionError || !userSession) {
      console.error('[execute-trade] No session found for user:', user.id);
      return new Response(
        JSON.stringify({ success: false, error: 'No trading session found. Please complete setup first.' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 403 }
      );
    }

    if (!userSession.is_trading_active) {
      return new Response(
        JSON.stringify({ success: false, error: 'Trading is not active for your account.' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 403 }
      );
    }

    const {
      signalId,
      lighthouseEventId,
      symbol,
      signalType,
      coherence,
      lighthouseValue,
      lighthouseConfidence,
      prismLevel,
      currentPrice,
      price, // Alias for currentPrice
      liveExecutionConfirmed,
      truthStatus,
      sourceId,
      sourceTimestamp: requestedSourceTimestamp,
      generatedValues,
    } = await req.json();

    if (liveExecutionConfirmed !== true) {
      return new Response(
        JSON.stringify({ success: false, error: 'LIVE_EXECUTION_CONFIRMATION_REQUIRED' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 },
      );
    }
    const requestedPrice = Number(currentPrice ?? price);
    if (!/^[A-Z0-9]{5,20}$/.test(String(symbol || '')) ||
        truthStatus !== 'real_derived' || !String(sourceId || '').trim() ||
        generatedValues !== false) {
      return new Response(
        JSON.stringify({ success: false, error: 'FRESH_REAL_MARKET_PROVENANCE_REQUIRED' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 },
      );
    }
    try {
      requireFreshTimestamp(String(requestedSourceTimestamp || ''), 5 * 60 * 1000, 'sourceTimestamp');
    } catch (error) {
      return new Response(
        JSON.stringify({ success: false, error: error instanceof Error ? error.message : String(error) }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 },
      );
    }

    const maxDeviationBps = Number(Deno.env.get('EXECUTION_MAX_PRICE_DEVIATION_BPS'));
    if (!Number.isFinite(maxDeviationBps) || maxDeviationBps <= 0 || maxDeviationBps > 1000) {
      return new Response(
        JSON.stringify({ success: false, error: 'EXECUTION_MAX_PRICE_DEVIATION_BPS_NOT_CONFIGURED' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 503 },
      );
    }
    let validatedPrice: number;
    try {
      const ticker = await fetchLiveJson<any>(
        `https://api.binance.com/api/v3/ticker/24hr?symbol=${encodeURIComponent(symbol)}`,
      );
      validatedPrice = requireFiniteNumber(Number(ticker.lastPrice), 'binance.lastPrice');
      const providerTimestamp = new Date(requireFiniteNumber(Number(ticker.closeTime), 'binance.closeTime')).toISOString();
      requireFreshTimestamp(providerTimestamp, 5 * 60 * 1000, 'binance.closeTime');
      if (validatedPrice <= 0 || !Number.isFinite(requestedPrice) || requestedPrice <= 0 ||
          Math.abs(requestedPrice - validatedPrice) / validatedPrice * 10_000 > maxDeviationBps) {
        throw new Error('REQUEST_PRICE_DOES_NOT_MATCH_LIVE_BINANCE_PRICE');
      }
    } catch (error) {
      return new Response(
        JSON.stringify({ success: false, error: error instanceof Error ? error.message : String(error) }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 },
      );
    }

    // === CRITICAL FAIL-SAFES (Strategic Plan Requirements) ===
    
    // 1. PRICE VALIDATION: Reject invalid or stale prices
    if (!Number.isFinite(validatedPrice) || validatedPrice <= 0) {
      console.error('🛑 FAIL-SAFE: Invalid price', validatedPrice);
      return new Response(
        JSON.stringify({ success: false, error: 'Invalid price provided' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    console.log('Execute trade request:', { symbol, signalType, coherence, price: validatedPrice, userId: user.id });

    // Get trading config
    const { data: configData, error: configError } = await supabase
      .from('trading_config')
      .select('*')
      .single();

    if (configError || !configData) {
      console.error('[execute-trade] Trading config not found:', configError);
      return new Response(
        JSON.stringify({ success: false, error: 'Trading configuration not found' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
      );
    }

    // Safety checks
    if (!configData.is_enabled) {
      return new Response(
        JSON.stringify({ success: false, error: 'Trading is currently disabled' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Check signal filters
    if (coherence < configData.min_coherence) {
      return new Response(
        JSON.stringify({ success: false, error: 'Coherence below minimum threshold' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    if (lighthouseConfidence < configData.min_lighthouse_confidence) {
      return new Response(
        JSON.stringify({ success: false, error: 'Lighthouse confidence below minimum' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    if (prismLevel < configData.min_prism_level) {
      return new Response(
        JSON.stringify({ success: false, error: 'Prism level below minimum' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    if (!configData.allowed_symbols.includes(symbol)) {
      return new Response(
        JSON.stringify({ success: false, error: 'Symbol not allowed for trading' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Check daily limits
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const { data: todayExecutions, error: todayExecutionsError } = await supabase
      .from('trading_executions')
      .select('*')
      .eq('user_id', user.id)
      .gte('executed_at', today.toISOString());
    if (todayExecutionsError) {
      return new Response(
        JSON.stringify({ success: false, error: `DAILY_EXECUTION_READ_FAILED:${todayExecutionsError.message}` }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 503 },
      );
    }

    const tradeCount = todayExecutions.length;
    if (tradeCount >= configData.max_daily_trades) {
      return new Response(
        JSON.stringify({ success: false, error: 'Daily trade limit reached' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Calculate daily P&L
    const realizedPnLRows = todayExecutions
      .filter((execution) => execution.realized_pnl != null)
      .map((execution) => Number(execution.realized_pnl));
    if (realizedPnLRows.some((value) => !Number.isFinite(value))) {
      return new Response(
        JSON.stringify({ success: false, error: 'INVALID_REALIZED_PNL_HISTORY' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 503 },
      );
    }
    const dailyPnL = realizedPnLRows.reduce((sum, value) => sum + value, 0);

    if (dailyPnL < -Math.abs(configData.max_daily_loss_usdt)) {
      return new Response(
        JSON.stringify({ success: false, error: 'Daily loss limit reached' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Calculate position size
    const positionSizeUsdt = parseFloat(configData.base_position_size_usdt as any);
    const quantity = positionSizeUsdt / validatedPrice;

    // === SANITY CHECK: Validate calculated quantity ===
    if (!quantity || isNaN(quantity) || quantity <= 0) {
      console.error('🛑 FAIL-SAFE: Invalid quantity calculation', { positionSizeUsdt, price: validatedPrice, quantity });
      return new Response(
        JSON.stringify({ success: false, error: 'Invalid quantity calculation' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    // Calculate stop loss and take profit
    const stopLossPrice = signalType === 'LONG'
      ? validatedPrice * (1 - parseFloat(configData.stop_loss_percentage as any) / 100)
      : validatedPrice * (1 + parseFloat(configData.stop_loss_percentage as any) / 100);

    const takeProfitPrice = signalType === 'LONG'
      ? validatedPrice * (1 + parseFloat(configData.take_profit_percentage as any) / 100)
      : validatedPrice * (1 - parseFloat(configData.take_profit_percentage as any) / 100);

    const side = signalType === 'LONG' ? 'BUY' : 'SELL';

    if (configData.trading_mode !== 'live') {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'PRODUCTION_LIVE_MODE_REQUIRED',
          truthStatus: 'no_data',
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 }
      );
    }

    let executionResult: any;
    {
      // Live trading - use user's credentials from their session
      console.log('🔄 Using user credentials for live trading...');
      
      // === SECURITY FIX: Use user's own credentials, not from shared pool ===
      if (!userSession.binance_api_key_encrypted || !userSession.binance_api_secret_encrypted) {
        return new Response(
          JSON.stringify({ success: false, error: 'No Binance credentials configured. Please add your API keys.' }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
        );
      }

      const binanceApiKey = await decryptCredential(userSession.binance_api_key_encrypted, userSession.binance_iv || '');
      const binanceApiSecret = await decryptCredential(userSession.binance_api_secret_encrypted, userSession.binance_iv || '');

      if (!binanceApiKey || !binanceApiSecret) {
        console.error('[execute-trade] Failed to decrypt credentials for user:', user.id);
        return new Response(
          JSON.stringify({ success: false, error: 'Failed to access trading credentials' }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
        );
      }

      console.log(`✅ Using credentials for user: ${user.id}`);

      // Create order on Binance
      const timestamp = Date.now();
      const queryString = `symbol=${symbol}&side=${side}&type=MARKET&quantity=${quantity.toFixed(8)}&timestamp=${timestamp}`;
      
      // Sign the request
      const crypto = await import("https://deno.land/std@0.177.0/crypto/mod.ts");
      const encoder = new TextEncoder();
      const key = await crypto.crypto.subtle.importKey(
        "raw",
        encoder.encode(binanceApiSecret),
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
      );
      const signatureBuffer = await crypto.crypto.subtle.sign(
        "HMAC",
        key,
        encoder.encode(queryString)
      );
      const signature = Array.from(new Uint8Array(signatureBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

      // === NETWORK FAIL-SAFE: Timeout and retry logic ===
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout for exchange APIs during high load

      try {
        const binanceResponse = await fetch(
          `https://api.binance.com/api/v3/order?${queryString}&signature=${signature}`,
          {
            method: 'POST',
            headers: {
              'X-MBX-APIKEY': binanceApiKey,
            },
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        if (!binanceResponse.ok) {
          const errorText = await binanceResponse.text();
          console.error('Binance API error:', errorText);
          
          // Check for rate limit error (429)
          if (binanceResponse.status === 429) {
            return new Response(
              JSON.stringify({ success: false, error: 'Rate limit exceeded. Please try again later.' }),
              { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 429 }
            );
          }
          
          return new Response(
            JSON.stringify({ success: false, error: 'Exchange order failed. Please check your API keys and balance.' }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
          );
        }

        executionResult = await binanceResponse.json();
        console.log('Live trade executed:', executionResult);

      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        
        if (fetchError?.name === 'AbortError') {
          console.error('🛑 TIMEOUT: Binance API request timed out');
          return new Response(
            JSON.stringify({ success: false, error: 'Exchange request timed out. Please try again.' }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 504 }
          );
        }
        
        console.error('[execute-trade] Fetch error:', fetchError);
        return new Response(
          JSON.stringify({ success: false, error: 'Failed to connect to exchange' }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
        );
      }
    }

    const executedQuantity = Number(executionResult.executedQty);
    const cumulativeQuote = Number(executionResult.cummulativeQuoteQty);
    const fillRows = Array.isArray(executionResult.fills) ? executionResult.fills : [];
    const fillQuote = fillRows.reduce(
      (sum: number, fill: any) => sum + Number(fill.price) * Number(fill.qty),
      0,
    );
    const fillQuantity = fillRows.reduce((sum: number, fill: any) => sum + Number(fill.qty), 0);
    const executedPrice = fillQuantity > 0
      ? fillQuote / fillQuantity
      : executedQuantity > 0 && cumulativeQuote > 0
        ? cumulativeQuote / executedQuantity
        : Number.NaN;
    const providerTimestampMs = Number(executionResult.transactTime);
    const sourceTimestamp = Number.isFinite(providerTimestampMs)
      ? new Date(providerTimestampMs).toISOString()
      : '';

    if (executionResult.status !== 'FILLED' || !Number.isFinite(executedQuantity) || executedQuantity <= 0 ||
        !Number.isFinite(executedPrice) || executedPrice <= 0 || !sourceTimestamp) {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'EXCHANGE_EXECUTION_NOT_FILLED',
          exchangeOrderId: executionResult.orderId ?? null,
          exchangeStatus: executionResult.status ?? null,
          truthStatus: 'live',
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 409 }
      );
    }

    // Save execution to database with user_id
    const { data: execution, error: execError } = await supabase
      .from('trading_executions')
      .insert({
        signal_id: signalId,
        lighthouse_event_id: lighthouseEventId,
        symbol,
        side,
        signal_type: signalType,
        order_type: 'MARKET',
        quantity: executedQuantity,
        price: validatedPrice,
        executed_price: executedPrice,
        position_size_usdt: executedQuantity * executedPrice,
        stop_loss_price: stopLossPrice,
        take_profit_price: takeProfitPrice,
        status: String(executionResult.status).toLowerCase(),
        exchange_order_id: executionResult.orderId,
        coherence,
        lighthouse_value: lighthouseValue,
        lighthouse_confidence: lighthouseConfidence,
        prism_level: prismLevel,
        user_id: user.id,
        exchange: 'binance',
        truth_status: 'live',
        source_id: 'binance:/api/v3/order',
        source_timestamp: sourceTimestamp,
        generated_values: false,
      })
      .select()
      .single();

    if (execError) {
      console.error('Error saving execution:', execError);
      return new Response(
        JSON.stringify({ success: false, error: 'Failed to save trade execution' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
      );
    }

    // Create position
    const { error: positionError } = await supabase
      .from('trading_positions')
      .insert({
        user_id: user.id,
        execution_id: execution.id,
        symbol,
        side: signalType,
        entry_price: executedPrice,
        quantity: executedQuantity,
        position_value_usdt: executedQuantity * executedPrice,
        stop_loss_price: stopLossPrice,
        take_profit_price: takeProfitPrice,
        current_price: executedPrice,
        status: 'open',
        exchange: 'binance',
        truth_status: 'live',
        source_id: 'binance:/api/v3/order',
        source_timestamp: sourceTimestamp,
        generated_values: false,
      });
    if (positionError) {
      return new Response(
        JSON.stringify({
          success: false,
          error: `LIVE_ORDER_RECORDED_POSITION_WRITE_FAILED:${positionError.message}`,
          exchangeOrderId: String(executionResult.orderId),
          truthStatus: 'live',
          sourceId: 'binance:/api/v3/order',
          sourceTimestamp,
          generatedValues: false,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 },
      );
    }

    console.log('Trade executed successfully:', execution.id, 'for user:', user.id);

    return new Response(
      JSON.stringify({
        success: true,
        execution: execution,
        message: `Live trade executed: ${side} ${executedQuantity.toFixed(8)} ${symbol} @ $${executedPrice.toFixed(2)}`,
        truthStatus: 'live',
        sourceId: 'binance:/api/v3/order',
        sourceTimestamp,
        generatedValues: false,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Execute trade error:', error);
    // SECURITY FIX: Return generic error, don't leak internal details
    return new Response(
      JSON.stringify({ success: false, error: 'Trade execution failed. Please try again.' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});
