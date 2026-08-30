export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  public: {
    Tables: {
      adaptive_learning_states: {
        Row: {
          band_performance: Json | null
          calibration_profit_factor: number | null
          calibration_win_rate: number | null
          confidence_score: number
          created_at: string
          hourly_performance: Json | null
          id: string
          kelly_multiplier: number
          learning_rate: number
          max_position_pct: number
          metadata: Json | null
          min_coherence: number
          min_confidence: number
          regime_adjustments: Json | null
          symbol_adjustments: Json | null
          temporal_id: string
          tier_performance: Json | null
          total_trades_learned: number
        }
        Insert: {
          band_performance?: Json | null
          calibration_profit_factor?: number | null
          calibration_win_rate?: number | null
          confidence_score?: number
          created_at?: string
          hourly_performance?: Json | null
          id?: string
          kelly_multiplier?: number
          learning_rate?: number
          max_position_pct?: number
          metadata?: Json | null
          min_coherence?: number
          min_confidence?: number
          regime_adjustments?: Json | null
          symbol_adjustments?: Json | null
          temporal_id: string
          tier_performance?: Json | null
          total_trades_learned?: number
        }
        Update: {
          band_performance?: Json | null
          calibration_profit_factor?: number | null
          calibration_win_rate?: number | null
          confidence_score?: number
          created_at?: string
          hourly_performance?: Json | null
          id?: string
          kelly_multiplier?: number
          learning_rate?: number
          max_position_pct?: number
          metadata?: Json | null
          min_coherence?: number
          min_confidence?: number
          regime_adjustments?: Json | null
          symbol_adjustments?: Json | null
          temporal_id?: string
          tier_performance?: Json | null
          total_trades_learned?: number
        }
        Relationships: []
      }
      akashic_attunement_states: {
        Row: {
          attunement_quality: string
          convergence_rate: number
          created_at: string | null
          cycles_performed: number
          final_frequency: number
          id: string
          metadata: Json | null
          stability_index: number
          temporal_id: string
          timestamp: string | null
        }
        Insert: {
          attunement_quality?: string
          convergence_rate?: number
          created_at?: string | null
          cycles_performed?: number
          final_frequency?: number
          id?: string
          metadata?: Json | null
          stability_index?: number
          temporal_id: string
          timestamp?: string | null
        }
        Update: {
          attunement_quality?: string
          convergence_rate?: number
          created_at?: string | null
          cycles_performed?: number
          final_frequency?: number
          id?: string
          metadata?: Json | null
          stability_index?: number
          temporal_id?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      aureon_user_sessions: {
        Row: {
          alpaca_api_key_encrypted: string | null
          alpaca_iv: string | null
          alpaca_secret_key_encrypted: string | null
          available_balance_usdt: number | null
          binance_api_key_encrypted: string | null
          binance_api_secret_encrypted: string | null
          binance_iv: string | null
          capital_api_key_encrypted: string | null
          capital_identifier_encrypted: string | null
          capital_iv: string | null
          capital_password_encrypted: string | null
          created_at: string | null
          current_coherence: number | null
          current_lambda: number | null
          current_lighthouse_signal: number | null
          dominant_node: string | null
          gas_tank_balance: number | null
          id: string
          is_trading_active: boolean | null
          kraken_api_key_encrypted: string | null
          kraken_api_secret_encrypted: string | null
          kraken_iv: string | null
          last_quantum_update_at: string | null
          last_trade_at: string | null
          measurement_collected_at: string | null
          measurement_generated_values: boolean
          measurement_source_id: string | null
          measurement_source_timestamp: string | null
          measurement_truth_status: string
          payment_completed: boolean | null
          payment_completed_at: string | null
          prism_level: number | null
          prism_state: string | null
          recent_trades: Json | null
          total_equity_usdt: number | null
          total_equity_usd: number | null
          total_pnl_usdt: number | null
          total_trades: number | null
          trading_mode: string | null
          updated_at: string | null
          user_id: string
          winning_trades: number | null
        }
        Insert: {
          alpaca_api_key_encrypted?: string | null
          alpaca_iv?: string | null
          alpaca_secret_key_encrypted?: string | null
          available_balance_usdt?: number | null
          binance_api_key_encrypted?: string | null
          binance_api_secret_encrypted?: string | null
          binance_iv?: string | null
          capital_api_key_encrypted?: string | null
          capital_identifier_encrypted?: string | null
          capital_iv?: string | null
          capital_password_encrypted?: string | null
          created_at?: string | null
          current_coherence?: number | null
          current_lambda?: number | null
          current_lighthouse_signal?: number | null
          dominant_node?: string | null
          gas_tank_balance?: number | null
          id?: string
          is_trading_active?: boolean | null
          kraken_api_key_encrypted?: string | null
          kraken_api_secret_encrypted?: string | null
          kraken_iv?: string | null
          last_quantum_update_at?: string | null
          last_trade_at?: string | null
          measurement_collected_at?: string | null
          measurement_generated_values?: boolean
          measurement_source_id?: string | null
          measurement_source_timestamp?: string | null
          measurement_truth_status?: string
          payment_completed?: boolean | null
          payment_completed_at?: string | null
          prism_level?: number | null
          prism_state?: string | null
          recent_trades?: Json | null
          total_equity_usdt?: number | null
          total_equity_usd?: number | null
          total_pnl_usdt?: number | null
          total_trades?: number | null
          trading_mode?: string | null
          updated_at?: string | null
          user_id: string
          winning_trades?: number | null
        }
        Update: {
          alpaca_api_key_encrypted?: string | null
          alpaca_iv?: string | null
          alpaca_secret_key_encrypted?: string | null
          available_balance_usdt?: number | null
          binance_api_key_encrypted?: string | null
          binance_api_secret_encrypted?: string | null
          binance_iv?: string | null
          capital_api_key_encrypted?: string | null
          capital_identifier_encrypted?: string | null
          capital_iv?: string | null
          capital_password_encrypted?: string | null
          created_at?: string | null
          current_coherence?: number | null
          current_lambda?: number | null
          current_lighthouse_signal?: number | null
          dominant_node?: string | null
          gas_tank_balance?: number | null
          id?: string
          is_trading_active?: boolean | null
          kraken_api_key_encrypted?: string | null
          kraken_api_secret_encrypted?: string | null
          kraken_iv?: string | null
          last_quantum_update_at?: string | null
          last_trade_at?: string | null
          measurement_collected_at?: string | null
          measurement_generated_values?: boolean
          measurement_source_id?: string | null
          measurement_source_timestamp?: string | null
          measurement_truth_status?: string
          payment_completed?: boolean | null
          payment_completed_at?: string | null
          prism_level?: number | null
          prism_state?: string | null
          recent_trades?: Json | null
          total_equity_usdt?: number | null
          total_equity_usd?: number | null
          total_pnl_usdt?: number | null
          total_trades?: number | null
          trading_mode?: string | null
          updated_at?: string | null
          user_id?: string
          winning_trades?: number | null
        }
        Relationships: []
      }
      auris_node_states: {
        Row: {
          active_nodes: number
          cargoship_frequency: number
          cargoship_value: number
          clownfish_frequency: number
          clownfish_value: number
          created_at: string | null
          deer_frequency: number
          deer_value: number
          dolphin_frequency: number
          dolphin_value: number
          dominant_node: string
          falcon_frequency: number
          falcon_value: number
          harmonic_resonance: number
          hummingbird_frequency: number
          hummingbird_value: number
          id: string
          metadata: Json | null
          owl_frequency: number
          owl_value: number
          panda_frequency: number
          panda_value: number
          temporal_id: string
          tiger_frequency: number
          tiger_value: number
          timestamp: string | null
          total_coherence: number
        }
        Insert: {
          active_nodes?: number
          cargoship_frequency?: number
          cargoship_value?: number
          clownfish_frequency?: number
          clownfish_value?: number
          created_at?: string | null
          deer_frequency?: number
          deer_value?: number
          dolphin_frequency?: number
          dolphin_value?: number
          dominant_node?: string
          falcon_frequency?: number
          falcon_value?: number
          harmonic_resonance?: number
          hummingbird_frequency?: number
          hummingbird_value?: number
          id?: string
          metadata?: Json | null
          owl_frequency?: number
          owl_value?: number
          panda_frequency?: number
          panda_value?: number
          temporal_id: string
          tiger_frequency?: number
          tiger_value?: number
          timestamp?: string | null
          total_coherence?: number
        }
        Update: {
          active_nodes?: number
          cargoship_frequency?: number
          cargoship_value?: number
          clownfish_frequency?: number
          clownfish_value?: number
          created_at?: string | null
          deer_frequency?: number
          deer_value?: number
          dolphin_frequency?: number
          dolphin_value?: number
          dominant_node?: string
          falcon_frequency?: number
          falcon_value?: number
          harmonic_resonance?: number
          hummingbird_frequency?: number
          hummingbird_value?: number
          id?: string
          metadata?: Json | null
          owl_frequency?: number
          owl_value?: number
          panda_frequency?: number
          panda_value?: number
          temporal_id?: string
          tiger_frequency?: number
          tiger_value?: number
          timestamp?: string | null
          total_coherence?: number
        }
        Relationships: []
      }
      backtest_results: {
        Row: {
          avg_trade_duration: number | null
          config: Json
          created_at: string
          end_date: string
          equity_curve: Json
          final_capital: number
          id: string
          initial_capital: number
          losing_trades: number
          max_drawdown: number
          profit_factor: number
          sharpe_ratio: number | null
          start_date: string
          status: string
          symbol: string
          total_return: number
          total_trades: number
          trades: Json
          win_rate: number
          winning_trades: number
        }
        Insert: {
          avg_trade_duration?: number | null
          config: Json
          created_at?: string
          end_date: string
          equity_curve: Json
          final_capital: number
          id?: string
          initial_capital: number
          losing_trades: number
          max_drawdown: number
          profit_factor: number
          sharpe_ratio?: number | null
          start_date: string
          status?: string
          symbol: string
          total_return: number
          total_trades: number
          trades: Json
          win_rate: number
          winning_trades: number
        }
        Update: {
          avg_trade_duration?: number | null
          config?: Json
          created_at?: string
          end_date?: string
          equity_curve?: Json
          final_capital?: number
          id?: string
          initial_capital?: number
          losing_trades?: number
          max_drawdown?: number
          profit_factor?: number
          sharpe_ratio?: number | null
          start_date?: string
          status?: string
          symbol?: string
          total_return?: number
          total_trades?: number
          trades?: Json
          win_rate?: number
          winning_trades?: number
        }
        Relationships: []
      }
      binance_credentials: {
        Row: {
          api_key_encrypted: string
          api_secret_encrypted: string
          created_at: string | null
          id: string
          is_active: boolean | null
          last_used_at: string | null
          name: string
          rate_limit_reset_at: string | null
          requests_count: number | null
          updated_at: string | null
        }
        Insert: {
          api_key_encrypted: string
          api_secret_encrypted: string
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          last_used_at?: string | null
          name: string
          rate_limit_reset_at?: string | null
          requests_count?: number | null
          updated_at?: string | null
        }
        Update: {
          api_key_encrypted?: string
          api_secret_encrypted?: string
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          last_used_at?: string | null
          name?: string
          rate_limit_reset_at?: string | null
          requests_count?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      brain_states: {
        Row: {
          bearish_accuracy: number | null
          brain_directive: string | null
          btc_change_24h: number | null
          btc_dominance: number | null
          btc_price: number | null
          bullish_accuracy: number | null
          cascade_multiplier: number | null
          civilization_actions: Json | null
          council_action: string | null
          council_arguments: string[] | null
          council_consensus: string | null
          created_at: string | null
          diamond_coherence: number | null
          diamond_phi_alignment: number | null
          dreams: Json | null
          entry_filter_reason: string | null
          evolved_generation: number | null
          evolved_win_rate: number | null
          exit_targets: Json | null
          fear_greed: number | null
          fear_greed_class: string | null
          full_state: Json | null
          green_flags: string[] | null
          harmonic_signal: number | null
          hnc_probability: number | null
          id: string
          is_lighthouse: boolean | null
          lambda_field: number | null
          learning_directive: string | null
          live_pulse: Json | null
          manipulation_probability: number | null
          overall_accuracy: number | null
          piano_coherence: number | null
          piano_lambda: number | null
          planetary_gamma: number | null
          position_size_pct: number | null
          prediction_confidence: number | null
          prediction_direction: string | null
          probability_edge: number | null
          quantum_coherence: number | null
          rainbow_state: string | null
          red_flags: string[] | null
          reflection: Json | null
          sandbox_generation: number | null
          sandbox_win_rate: number | null
          self_critique: string[] | null
          should_trade: boolean | null
          speculations: string[] | null
          spoof_score: number | null
          timestamp: string | null
          total_predictions: number | null
          truth_score: number | null
          user_id: string
          wisdom_consensus: Json | null
        }
        Insert: {
          bearish_accuracy?: number | null
          brain_directive?: string | null
          btc_change_24h?: number | null
          btc_dominance?: number | null
          btc_price?: number | null
          bullish_accuracy?: number | null
          cascade_multiplier?: number | null
          civilization_actions?: Json | null
          council_action?: string | null
          council_arguments?: string[] | null
          council_consensus?: string | null
          created_at?: string | null
          diamond_coherence?: number | null
          diamond_phi_alignment?: number | null
          dreams?: Json | null
          entry_filter_reason?: string | null
          evolved_generation?: number | null
          evolved_win_rate?: number | null
          exit_targets?: Json | null
          fear_greed?: number | null
          fear_greed_class?: string | null
          full_state?: Json | null
          green_flags?: string[] | null
          harmonic_signal?: number | null
          hnc_probability?: number | null
          id?: string
          is_lighthouse?: boolean | null
          lambda_field?: number | null
          learning_directive?: string | null
          live_pulse?: Json | null
          manipulation_probability?: number | null
          overall_accuracy?: number | null
          piano_coherence?: number | null
          piano_lambda?: number | null
          planetary_gamma?: number | null
          position_size_pct?: number | null
          prediction_confidence?: number | null
          prediction_direction?: string | null
          probability_edge?: number | null
          quantum_coherence?: number | null
          rainbow_state?: string | null
          red_flags?: string[] | null
          reflection?: Json | null
          sandbox_generation?: number | null
          sandbox_win_rate?: number | null
          self_critique?: string[] | null
          should_trade?: boolean | null
          speculations?: string[] | null
          spoof_score?: number | null
          timestamp?: string | null
          total_predictions?: number | null
          truth_score?: number | null
          user_id: string
          wisdom_consensus?: Json | null
        }
        Update: {
          bearish_accuracy?: number | null
          brain_directive?: string | null
          btc_change_24h?: number | null
          btc_dominance?: number | null
          btc_price?: number | null
          bullish_accuracy?: number | null
          cascade_multiplier?: number | null
          civilization_actions?: Json | null
          council_action?: string | null
          council_arguments?: string[] | null
          council_consensus?: string | null
          created_at?: string | null
          diamond_coherence?: number | null
          diamond_phi_alignment?: number | null
          dreams?: Json | null
          entry_filter_reason?: string | null
          evolved_generation?: number | null
          evolved_win_rate?: number | null
          exit_targets?: Json | null
          fear_greed?: number | null
          fear_greed_class?: string | null
          full_state?: Json | null
          green_flags?: string[] | null
          harmonic_signal?: number | null
          hnc_probability?: number | null
          id?: string
          is_lighthouse?: boolean | null
          lambda_field?: number | null
          learning_directive?: string | null
          live_pulse?: Json | null
          manipulation_probability?: number | null
          overall_accuracy?: number | null
          piano_coherence?: number | null
          piano_lambda?: number | null
          planetary_gamma?: number | null
          position_size_pct?: number | null
          prediction_confidence?: number | null
          prediction_direction?: string | null
          probability_edge?: number | null
          quantum_coherence?: number | null
          rainbow_state?: string | null
          red_flags?: string[] | null
          reflection?: Json | null
          sandbox_generation?: number | null
          sandbox_win_rate?: number | null
          self_critique?: string[] | null
          should_trade?: boolean | null
          speculations?: string[] | null
          spoof_score?: number | null
          timestamp?: string | null
          total_predictions?: number | null
          truth_score?: number | null
          user_id?: string
          wisdom_consensus?: Json | null
        }
        Relationships: []
      }
      calibration_trades: {
        Row: {
          coherence_at_entry: number
          cosmic_phase: string | null
          created_at: string
          entry_price: number
          entry_time: string
          exchange: string
          exit_price: number | null
          exit_time: string | null
          frequency_band: string
          hnc_probability: number
          id: string
          is_forced: boolean | null
          is_win: boolean | null
          lambda_at_entry: number
          lighthouse_confidence: number
          metadata: Json | null
          order_id: string | null
          pnl: number | null
          pnl_percent: number | null
          position_size_usd: number
          prism_frequency: number
          qgita_tier: number
          quantity: number
          regime: string
          side: string
          symbol: string
          temporal_id: string
        }
        Insert: {
          coherence_at_entry: number
          cosmic_phase?: string | null
          created_at?: string
          entry_price: number
          entry_time?: string
          exchange?: string
          exit_price?: number | null
          exit_time?: string | null
          frequency_band: string
          hnc_probability: number
          id?: string
          is_forced?: boolean | null
          is_win?: boolean | null
          lambda_at_entry: number
          lighthouse_confidence: number
          metadata?: Json | null
          order_id?: string | null
          pnl?: number | null
          pnl_percent?: number | null
          position_size_usd: number
          prism_frequency: number
          qgita_tier?: number
          quantity: number
          regime?: string
          side: string
          symbol: string
          temporal_id: string
        }
        Update: {
          coherence_at_entry?: number
          cosmic_phase?: string | null
          created_at?: string
          entry_price?: number
          entry_time?: string
          exchange?: string
          exit_price?: number | null
          exit_time?: string | null
          frequency_band?: string
          hnc_probability?: number
          id?: string
          is_forced?: boolean | null
          is_win?: boolean | null
          lambda_at_entry?: number
          lighthouse_confidence?: number
          metadata?: Json | null
          order_id?: string | null
          pnl?: number | null
          pnl_percent?: number | null
          position_size_usd?: number
          prism_frequency?: number
          qgita_tier?: number
          quantity?: number
          regime?: string
          side?: string
          symbol?: string
          temporal_id?: string
        }
        Relationships: []
      }
      coherence_history: {
        Row: {
          coherence: number
          created_at: string
          day_of_week: number
          hour_of_day: number
          id: string
          lambda_value: number
          symbol: string
          timestamp: string
        }
        Insert: {
          coherence: number
          created_at?: string
          day_of_week: number
          hour_of_day: number
          id?: string
          lambda_value: number
          symbol?: string
          timestamp?: string
        }
        Update: {
          coherence?: number
          created_at?: string
          day_of_week?: number
          hour_of_day?: number
          id?: string
          lambda_value?: number
          symbol?: string
          timestamp?: string
        }
        Relationships: []
      }
      consciousness_field_history: {
        Row: {
          alpha_waves: number | null
          beta_waves: number | null
          biometric_coherence_index: number | null
          celestial_boost: number
          created_at: string
          delta_waves: number | null
          heart_rate: number | null
          hrv: number | null
          id: string
          schumann_amplitude: number
          schumann_coherence_boost: number
          schumann_frequency: number
          schumann_phase: string
          schumann_quality: number
          theta_waves: number | null
          timestamp: string
          total_coherence: number
        }
        Insert: {
          alpha_waves?: number | null
          beta_waves?: number | null
          biometric_coherence_index?: number | null
          celestial_boost?: number
          created_at?: string
          delta_waves?: number | null
          heart_rate?: number | null
          hrv?: number | null
          id?: string
          schumann_amplitude: number
          schumann_coherence_boost: number
          schumann_frequency: number
          schumann_phase: string
          schumann_quality: number
          theta_waves?: number | null
          timestamp?: string
          total_coherence: number
        }
        Update: {
          alpha_waves?: number | null
          beta_waves?: number | null
          biometric_coherence_index?: number | null
          celestial_boost?: number
          created_at?: string
          delta_waves?: number | null
          heart_rate?: number | null
          hrv?: number | null
          id?: string
          schumann_amplitude?: number
          schumann_coherence_boost?: number
          schumann_frequency?: number
          schumann_phase?: string
          schumann_quality?: number
          theta_waves?: number | null
          timestamp?: string
          total_coherence?: number
        }
        Relationships: []
      }
      crypto_assets_registry: {
        Row: {
          base_asset: string
          created_at: string
          exchange: string
          id: string
          is_active: boolean | null
          is_spot_trading_allowed: boolean | null
          last_synced_at: string | null
          max_qty: number | null
          min_notional: number | null
          min_qty: number | null
          price_precision: number | null
          quantity_precision: number | null
          quote_asset: string
          status: string | null
          step_size: number | null
          symbol: string
          tick_size: number | null
          updated_at: string
        }
        Insert: {
          base_asset: string
          created_at?: string
          exchange?: string
          id?: string
          is_active?: boolean | null
          is_spot_trading_allowed?: boolean | null
          last_synced_at?: string | null
          max_qty?: number | null
          min_notional?: number | null
          min_qty?: number | null
          price_precision?: number | null
          quantity_precision?: number | null
          quote_asset: string
          status?: string | null
          step_size?: number | null
          symbol: string
          tick_size?: number | null
          updated_at?: string
        }
        Update: {
          base_asset?: string
          created_at?: string
          exchange?: string
          id?: string
          is_active?: boolean | null
          is_spot_trading_allowed?: boolean | null
          last_synced_at?: string | null
          max_qty?: number | null
          min_notional?: number | null
          min_qty?: number | null
          price_precision?: number | null
          quantity_precision?: number | null
          quote_asset?: string
          status?: string | null
          step_size?: number | null
          symbol?: string
          tick_size?: number | null
          updated_at?: string
        }
        Relationships: []
      }
      data_access_audit: {
        Row: {
          access_type: string
          accessed_by: string | null
          id: string
          ip_address: string | null
          metadata: Json | null
          resource_type: string
          timestamp: string
          user_id: string
        }
        Insert: {
          access_type: string
          accessed_by?: string | null
          id?: string
          ip_address?: string | null
          metadata?: Json | null
          resource_type: string
          timestamp?: string
          user_id: string
        }
        Update: {
          access_type?: string
          accessed_by?: string | null
          id?: string
          ip_address?: string | null
          metadata?: Json | null
          resource_type?: string
          timestamp?: string
          user_id?: string
        }
        Relationships: []
      }
      data_validation_log: {
        Row: {
          error_message: string | null
          exchange: string
          id: string
          is_valid: boolean
          metadata: Json | null
          packet_timestamp: string | null
          temporal_id: string
          validation_timestamp: string
          validation_type: string
        }
        Insert: {
          error_message?: string | null
          exchange: string
          id?: string
          is_valid: boolean
          metadata?: Json | null
          packet_timestamp?: string | null
          temporal_id: string
          validation_timestamp?: string
          validation_type: string
        }
        Update: {
          error_message?: string | null
          exchange?: string
          id?: string
          is_valid?: boolean
          metadata?: Json | null
          packet_timestamp?: string | null
          temporal_id?: string
          validation_timestamp?: string
          validation_type?: string
        }
        Relationships: []
      }
      decision_audit_log: {
        Row: {
          accuracy_15m: boolean | null
          accuracy_1m: boolean | null
          accuracy_5m: boolean | null
          actual_direction_15m: string | null
          actual_direction_1m: string | null
          actual_direction_5m: string | null
          coherence: number
          confidence: number
          created_at: string
          decision_action: string
          decision_timestamp: string
          factors: Json | null
          geometric_alignment: number | null
          harmonic_lock: boolean | null
          id: string
          lambda: number
          lighthouse_l: number | null
          price_after_15m: number | null
          price_after_1m: number | null
          price_after_5m: number | null
          price_at_decision: number | null
          prism_frequency: number | null
          prism_level: number | null
          probability_fused: number | null
          qgita_confidence: number | null
          qgita_tier: number | null
          reasoning: Json | null
          sentiment_score: number | null
          summary: string | null
          symbol: string
          user_id: string
          verified_at: string | null
          wave_state: string | null
        }
        Insert: {
          accuracy_15m?: boolean | null
          accuracy_1m?: boolean | null
          accuracy_5m?: boolean | null
          actual_direction_15m?: string | null
          actual_direction_1m?: string | null
          actual_direction_5m?: string | null
          coherence: number
          confidence: number
          created_at?: string
          decision_action: string
          decision_timestamp?: string
          factors?: Json | null
          geometric_alignment?: number | null
          harmonic_lock?: boolean | null
          id?: string
          lambda: number
          lighthouse_l?: number | null
          price_after_15m?: number | null
          price_after_1m?: number | null
          price_after_5m?: number | null
          price_at_decision?: number | null
          prism_frequency?: number | null
          prism_level?: number | null
          probability_fused?: number | null
          qgita_confidence?: number | null
          qgita_tier?: number | null
          reasoning?: Json | null
          sentiment_score?: number | null
          summary?: string | null
          symbol?: string
          user_id: string
          verified_at?: string | null
          wave_state?: string | null
        }
        Update: {
          accuracy_15m?: boolean | null
          accuracy_1m?: boolean | null
          accuracy_5m?: boolean | null
          actual_direction_15m?: string | null
          actual_direction_1m?: string | null
          actual_direction_5m?: string | null
          coherence?: number
          confidence?: number
          created_at?: string
          decision_action?: string
          decision_timestamp?: string
          factors?: Json | null
          geometric_alignment?: number | null
          harmonic_lock?: boolean | null
          id?: string
          lambda?: number
          lighthouse_l?: number | null
          price_after_15m?: number | null
          price_after_1m?: number | null
          price_after_5m?: number | null
          price_at_decision?: number | null
          prism_frequency?: number | null
          prism_level?: number | null
          probability_fused?: number | null
          qgita_confidence?: number | null
          qgita_tier?: number | null
          reasoning?: Json | null
          sentiment_score?: number | null
          summary?: string | null
          symbol?: string
          user_id?: string
          verified_at?: string | null
          wave_state?: string | null
        }
        Relationships: []
      }
      decision_fusion_states: {
        Row: {
          confidence: number
          created_at: string | null
          ensemble_score: number
          final_action: string
          harmonic_6d_score: number
          harmonic_lock: boolean | null
          id: string
          metadata: Json | null
          position_size: number
          qgita_boost: number
          sentiment_score: number
          temporal_id: string
          timestamp: string | null
          wave_state: string | null
        }
        Insert: {
          confidence?: number
          created_at?: string | null
          ensemble_score?: number
          final_action?: string
          harmonic_6d_score?: number
          harmonic_lock?: boolean | null
          id?: string
          metadata?: Json | null
          position_size?: number
          qgita_boost?: number
          sentiment_score?: number
          temporal_id: string
          timestamp?: string | null
          wave_state?: string | null
        }
        Update: {
          confidence?: number
          created_at?: string | null
          ensemble_score?: number
          final_action?: string
          harmonic_6d_score?: number
          harmonic_lock?: boolean | null
          id?: string
          metadata?: Json | null
          position_size?: number
          qgita_boost?: number
          sentiment_score?: number
          temporal_id?: string
          timestamp?: string | null
          wave_state?: string | null
        }
        Relationships: []
      }
      eckoushic_cascade_states: {
        Row: {
          akashic: number
          cascade_level: number
          created_at: string | null
          eckoushic: number
          frequency: number
          harmonic_nexus: number
          heart_wave: number
          id: string
          metadata: Json | null
          temporal_id: string
          timestamp: string | null
        }
        Insert: {
          akashic?: number
          cascade_level?: number
          created_at?: string | null
          eckoushic?: number
          frequency?: number
          harmonic_nexus?: number
          heart_wave?: number
          id?: string
          metadata?: Json | null
          temporal_id: string
          timestamp?: string | null
        }
        Update: {
          akashic?: number
          cascade_level?: number
          created_at?: string | null
          eckoushic?: number
          frequency?: number
          harmonic_nexus?: number
          heart_wave?: number
          id?: string
          metadata?: Json | null
          temporal_id?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      ecosystem_snapshots: {
        Row: {
          bus_confidence: number
          bus_consensus: string
          created_at: string | null
          hive_mind_coherence: number
          id: string
          json_enhancements_loaded: boolean | null
          metadata: Json | null
          system_states: Json
          systems_online: number
          temporal_id: string
          timestamp: string | null
          total_systems: number
        }
        Insert: {
          bus_confidence?: number
          bus_consensus?: string
          created_at?: string | null
          hive_mind_coherence?: number
          id?: string
          json_enhancements_loaded?: boolean | null
          metadata?: Json | null
          system_states?: Json
          systems_online?: number
          temporal_id: string
          timestamp?: string | null
          total_systems?: number
        }
        Update: {
          bus_confidence?: number
          bus_consensus?: string
          created_at?: string | null
          hive_mind_coherence?: number
          id?: string
          json_enhancements_loaded?: boolean | null
          metadata?: Json | null
          system_states?: Json
          systems_online?: number
          temporal_id?: string
          timestamp?: string | null
          total_systems?: number
        }
        Relationships: []
      }
      elephant_memory: {
        Row: {
          blacklisted: boolean | null
          cooldown_until: string | null
          created_at: string | null
          id: string
          last_trade: string | null
          loss_streak: number | null
          losses: number | null
          profit: number | null
          symbol: string
          trades: number | null
          updated_at: string | null
          wins: number | null
        }
        Insert: {
          blacklisted?: boolean | null
          cooldown_until?: string | null
          created_at?: string | null
          id?: string
          last_trade?: string | null
          loss_streak?: number | null
          losses?: number | null
          profit?: number | null
          symbol: string
          trades?: number | null
          updated_at?: string | null
          wins?: number | null
        }
        Update: {
          blacklisted?: boolean | null
          cooldown_until?: string | null
          created_at?: string | null
          id?: string
          last_trade?: string | null
          loss_streak?: number | null
          losses?: number | null
          profit?: number | null
          symbol?: string
          trades?: number | null
          updated_at?: string | null
          wins?: number | null
        }
        Relationships: []
      }
      exchange_balance_cache: {
        Row: {
          balance_data: Json
          cached_at: string
          created_at: string
          exchange: string
          id: string
          user_id: string
        }
        Insert: {
          balance_data: Json
          cached_at?: string
          created_at?: string
          exchange: string
          id?: string
          user_id: string
        }
        Update: {
          balance_data?: Json
          cached_at?: string
          created_at?: string
          exchange?: string
          id?: string
          user_id?: string
        }
        Relationships: []
      }
      exchange_learning_states: {
        Row: {
          avg_latency_ms: number | null
          avg_pnl: number | null
          created_at: string
          exchange: string
          id: string
          last_trade_at: string | null
          losses: number
          metadata: Json | null
          symbol: string
          temporal_id: string
          total_profit: number
          total_trades: number
          win_rate: number | null
          wins: number
        }
        Insert: {
          avg_latency_ms?: number | null
          avg_pnl?: number | null
          created_at?: string
          exchange: string
          id?: string
          last_trade_at?: string | null
          losses?: number
          metadata?: Json | null
          symbol: string
          temporal_id: string
          total_profit?: number
          total_trades?: number
          win_rate?: number | null
          wins?: number
        }
        Update: {
          avg_latency_ms?: number | null
          avg_pnl?: number | null
          created_at?: string
          exchange?: string
          id?: string
          last_trade_at?: string | null
          losses?: number
          metadata?: Json | null
          symbol?: string
          temporal_id?: string
          total_profit?: number
          total_trades?: number
          win_rate?: number | null
          wins?: number
        }
        Relationships: []
      }
      ftcp_detector_states: {
        Row: {
          created_at: string | null
          curvature: number
          curvature_direction: string
          divergence_from_fib: number | null
          id: string
          is_fibonacci_level: boolean | null
          metadata: Json | null
          nearest_fib_ratio: number | null
          phase: string
          temporal_id: string
          timestamp: string | null
          trend_strength: number
        }
        Insert: {
          created_at?: string | null
          curvature?: number
          curvature_direction?: string
          divergence_from_fib?: number | null
          id?: string
          is_fibonacci_level?: boolean | null
          metadata?: Json | null
          nearest_fib_ratio?: number | null
          phase?: string
          temporal_id: string
          timestamp?: string | null
          trend_strength?: number
        }
        Update: {
          created_at?: string | null
          curvature?: number
          curvature_direction?: string
          divergence_from_fib?: number | null
          id?: string
          is_fibonacci_level?: boolean | null
          metadata?: Json | null
          nearest_fib_ratio?: number | null
          phase?: string
          temporal_id?: string
          timestamp?: string | null
          trend_strength?: number
        }
        Relationships: []
      }
      gas_tank_accounts: {
        Row: {
          balance: number
          created_at: string
          fee_rate: number
          fees_paid_today: number
          high_water_mark: number
          id: string
          initial_balance: number
          last_fee_deducted_at: string | null
          last_top_up_at: string | null
          membership_type: string
          status: string
          total_fees_paid: number
          updated_at: string
          user_id: string
        }
        Insert: {
          balance?: number
          created_at?: string
          fee_rate?: number
          fees_paid_today?: number
          high_water_mark?: number
          id?: string
          initial_balance?: number
          last_fee_deducted_at?: string | null
          last_top_up_at?: string | null
          membership_type?: string
          status?: string
          total_fees_paid?: number
          updated_at?: string
          user_id: string
        }
        Update: {
          balance?: number
          created_at?: string
          fee_rate?: number
          fees_paid_today?: number
          high_water_mark?: number
          id?: string
          initial_balance?: number
          last_fee_deducted_at?: string | null
          last_top_up_at?: string | null
          membership_type?: string
          status?: string
          total_fees_paid?: number
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      gas_tank_transactions: {
        Row: {
          account_id: string
          amount: number
          balance_after: number
          balance_before: number
          created_at: string
          description: string | null
          id: string
          metadata: Json | null
          trade_execution_id: string | null
          type: string
        }
        Insert: {
          account_id: string
          amount: number
          balance_after: number
          balance_before: number
          created_at?: string
          description?: string | null
          id?: string
          metadata?: Json | null
          trade_execution_id?: string | null
          type: string
        }
        Update: {
          account_id?: string
          amount?: number
          balance_after?: number
          balance_before?: number
          created_at?: string
          description?: string | null
          id?: string
          metadata?: Json | null
          trade_execution_id?: string | null
          type?: string
        }
        Relationships: [
          {
            foreignKeyName: "gas_tank_transactions_account_id_fkey"
            columns: ["account_id"]
            isOneToOne: false
            referencedRelation: "gas_tank_accounts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "gas_tank_transactions_trade_execution_id_fkey"
            columns: ["trade_execution_id"]
            isOneToOne: false
            referencedRelation: "trading_executions"
            referencedColumns: ["id"]
          },
        ]
      }
      harmonic_6d_states: {
        Row: {
          created_at: string | null
          d1_price: Json
          d2_volume: Json
          d3_time: Json
          d4_correlation: Json
          d5_momentum: Json
          d6_frequency: Json
          dimensional_coherence: number
          energy_density: number
          harmonic_lock: boolean | null
          id: string
          market_phase: string
          metadata: Json | null
          phase_alignment: number
          probability_field: number
          resonance_score: number
          temporal_id: string
          timestamp: string | null
          wave_state: string
        }
        Insert: {
          created_at?: string | null
          d1_price?: Json
          d2_volume?: Json
          d3_time?: Json
          d4_correlation?: Json
          d5_momentum?: Json
          d6_frequency?: Json
          dimensional_coherence?: number
          energy_density?: number
          harmonic_lock?: boolean | null
          id?: string
          market_phase?: string
          metadata?: Json | null
          phase_alignment?: number
          probability_field?: number
          resonance_score?: number
          temporal_id: string
          timestamp?: string | null
          wave_state?: string
        }
        Update: {
          created_at?: string | null
          d1_price?: Json
          d2_volume?: Json
          d3_time?: Json
          d4_correlation?: Json
          d5_momentum?: Json
          d6_frequency?: Json
          dimensional_coherence?: number
          energy_density?: number
          harmonic_lock?: boolean | null
          id?: string
          market_phase?: string
          metadata?: Json | null
          phase_alignment?: number
          probability_field?: number
          resonance_score?: number
          temporal_id?: string
          timestamp?: string | null
          wave_state?: string
        }
        Relationships: []
      }
      harmonic_nexus_states: {
        Row: {
          akashic_boost: number
          akashic_convergence: number
          akashic_frequency: number
          akashic_stability: number
          created_at: string
          dimensional_alignment: number
          event_timestamp: string
          field_integrity: number
          harmonic_resonance: number
          id: string
          lighthouse_signal: number | null
          love_coherence: number
          metadata: Json | null
          observer_consciousness: number
          omega_value: number
          prism_level: number | null
          psi_potential: number
          sentinel_name: string | null
          substrate_coherence: number
          sync_quality: number
          sync_status: string
          temporal_id: string
          theta_alignment: number
          timeline_divergence: number
          unity_probability: number
        }
        Insert: {
          akashic_boost: number
          akashic_convergence: number
          akashic_frequency: number
          akashic_stability: number
          created_at?: string
          dimensional_alignment: number
          event_timestamp?: string
          field_integrity: number
          harmonic_resonance: number
          id?: string
          lighthouse_signal?: number | null
          love_coherence: number
          metadata?: Json | null
          observer_consciousness: number
          omega_value: number
          prism_level?: number | null
          psi_potential: number
          sentinel_name?: string | null
          substrate_coherence: number
          sync_quality?: number
          sync_status?: string
          temporal_id: string
          theta_alignment: number
          timeline_divergence?: number
          unity_probability: number
        }
        Update: {
          akashic_boost?: number
          akashic_convergence?: number
          akashic_frequency?: number
          akashic_stability?: number
          created_at?: string
          dimensional_alignment?: number
          event_timestamp?: string
          field_integrity?: number
          harmonic_resonance?: number
          id?: string
          lighthouse_signal?: number | null
          love_coherence?: number
          metadata?: Json | null
          observer_consciousness?: number
          omega_value?: number
          prism_level?: number | null
          psi_potential?: number
          sentinel_name?: string | null
          substrate_coherence?: number
          sync_quality?: number
          sync_status?: string
          temporal_id?: string
          theta_alignment?: number
          timeline_divergence?: number
          unity_probability?: number
        }
        Relationships: []
      }
      hive_agents: {
        Row: {
          agent_index: number
          created_at: string
          current_symbol: string
          hive_id: string
          id: string
          last_trade_at: string | null
          position_entry_price: number | null
          position_open: boolean
          position_quantity: number | null
          position_side: string | null
          total_pnl: number
          trades_count: number
        }
        Insert: {
          agent_index: number
          created_at?: string
          current_symbol: string
          hive_id: string
          id?: string
          last_trade_at?: string | null
          position_entry_price?: number | null
          position_open?: boolean
          position_quantity?: number | null
          position_side?: string | null
          total_pnl?: number
          trades_count?: number
        }
        Update: {
          agent_index?: number
          created_at?: string
          current_symbol?: string
          hive_id?: string
          id?: string
          last_trade_at?: string | null
          position_entry_price?: number | null
          position_open?: boolean
          position_quantity?: number | null
          position_side?: string | null
          total_pnl?: number
          trades_count?: number
        }
        Relationships: [
          {
            foreignKeyName: "hive_agents_hive_id_fkey"
            columns: ["hive_id"]
            isOneToOne: false
            referencedRelation: "hive_instances"
            referencedColumns: ["id"]
          },
        ]
      }
      hive_instances: {
        Row: {
          created_at: string
          current_balance: number
          generation: number
          id: string
          initial_balance: number
          num_agents: number
          parent_hive_id: string | null
          status: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          current_balance: number
          generation?: number
          id?: string
          initial_balance: number
          num_agents?: number
          parent_hive_id?: string | null
          status?: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          current_balance?: number
          generation?: number
          id?: string
          initial_balance?: number
          num_agents?: number
          parent_hive_id?: string | null
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "hive_instances_parent_hive_id_fkey"
            columns: ["parent_hive_id"]
            isOneToOne: false
            referencedRelation: "hive_instances"
            referencedColumns: ["id"]
          },
        ]
      }
      hive_sessions: {
        Row: {
          created_at: string
          current_equity: number
          id: string
          initial_capital: number
          root_hive_id: string
          started_at: string
          status: string
          steps_executed: number
          stopped_at: string | null
          total_agents: number
          total_hives_spawned: number
          total_trades: number
          user_id: string
        }
        Insert: {
          created_at?: string
          current_equity: number
          id?: string
          initial_capital: number
          root_hive_id: string
          started_at?: string
          status?: string
          steps_executed?: number
          stopped_at?: string | null
          total_agents?: number
          total_hives_spawned?: number
          total_trades?: number
          user_id: string
        }
        Update: {
          created_at?: string
          current_equity?: number
          id?: string
          initial_capital?: number
          root_hive_id?: string
          started_at?: string
          status?: string
          steps_executed?: number
          stopped_at?: string | null
          total_agents?: number
          total_hives_spawned?: number
          total_trades?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "hive_sessions_root_hive_id_fkey"
            columns: ["root_hive_id"]
            isOneToOne: false
            referencedRelation: "hive_instances"
            referencedColumns: ["id"]
          },
        ]
      }
      hive_trades: {
        Row: {
          agent_id: string
          closed_at: string | null
          created_at: string
          entry_price: number
          exit_price: number | null
          hive_id: string
          id: string
          opened_at: string
          pnl: number | null
          quantity: number
          session_id: string
          side: string
          status: string
          symbol: string
        }
        Insert: {
          agent_id: string
          closed_at?: string | null
          created_at?: string
          entry_price: number
          exit_price?: number | null
          hive_id: string
          id?: string
          opened_at?: string
          pnl?: number | null
          quantity: number
          session_id: string
          side: string
          status?: string
          symbol: string
        }
        Update: {
          agent_id?: string
          closed_at?: string | null
          created_at?: string
          entry_price?: number
          exit_price?: number | null
          hive_id?: string
          id?: string
          opened_at?: string
          pnl?: number | null
          quantity?: number
          session_id?: string
          side?: string
          status?: string
          symbol?: string
        }
        Relationships: [
          {
            foreignKeyName: "hive_trades_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "hive_agents"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "hive_trades_hive_id_fkey"
            columns: ["hive_id"]
            isOneToOne: false
            referencedRelation: "hive_instances"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "hive_trades_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "hive_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      hnc_detection_states: {
        Row: {
          anchor_power: number | null
          bridge_status: string
          created_at: string | null
          distortion_power: number | null
          harmonic_fidelity: number
          id: string
          imperial_yield: number
          is_lighthouse_detected: boolean | null
          love_power: number | null
          metadata: Json | null
          schumann_power: number | null
          temporal_id: string
          timestamp: string | null
          unity_power: number | null
        }
        Insert: {
          anchor_power?: number | null
          bridge_status?: string
          created_at?: string | null
          distortion_power?: number | null
          harmonic_fidelity?: number
          id?: string
          imperial_yield?: number
          is_lighthouse_detected?: boolean | null
          love_power?: number | null
          metadata?: Json | null
          schumann_power?: number | null
          temporal_id: string
          timestamp?: string | null
          unity_power?: number | null
        }
        Update: {
          anchor_power?: number | null
          bridge_status?: string
          created_at?: string | null
          distortion_power?: number | null
          harmonic_fidelity?: number
          id?: string
          imperial_yield?: number
          is_lighthouse_detected?: boolean | null
          love_power?: number | null
          metadata?: Json | null
          schumann_power?: number | null
          temporal_id?: string
          timestamp?: string | null
          unity_power?: number | null
        }
        Relationships: []
      }
      hunt_scans: {
        Row: {
          created_at: string
          hunt_session_id: string
          id: string
          orders_queued: number
          pairs_scanned: number
          scan_duration_ms: number
          scan_timestamp: string
          signals_generated: number
          targets_found: number
          top_score: number | null
          top_symbol: string | null
        }
        Insert: {
          created_at?: string
          hunt_session_id: string
          id?: string
          orders_queued: number
          pairs_scanned: number
          scan_duration_ms: number
          scan_timestamp?: string
          signals_generated: number
          targets_found: number
          top_score?: number | null
          top_symbol?: string | null
        }
        Update: {
          created_at?: string
          hunt_session_id?: string
          id?: string
          orders_queued?: number
          pairs_scanned?: number
          scan_duration_ms?: number
          scan_timestamp?: string
          signals_generated?: number
          targets_found?: number
          top_score?: number | null
          top_symbol?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "hunt_scans_hunt_session_id_fkey"
            columns: ["hunt_session_id"]
            isOneToOne: false
            referencedRelation: "hunt_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      hunt_sessions: {
        Row: {
          created_at: string
          hive_session_id: string | null
          id: string
          last_scan_at: string | null
          max_targets: number
          min_volatility_pct: number
          min_volume_usd: number
          scan_interval_seconds: number
          started_at: string
          status: string
          stopped_at: string | null
          total_orders_queued: number
          total_scans: number
          total_signals_generated: number
          total_targets_found: number
          twap_duration_seconds: number | null
          twap_threshold_usd: number | null
          user_id: string
        }
        Insert: {
          created_at?: string
          hive_session_id?: string | null
          id?: string
          last_scan_at?: string | null
          max_targets?: number
          min_volatility_pct?: number
          min_volume_usd?: number
          scan_interval_seconds?: number
          started_at?: string
          status?: string
          stopped_at?: string | null
          total_orders_queued?: number
          total_scans?: number
          total_signals_generated?: number
          total_targets_found?: number
          twap_duration_seconds?: number | null
          twap_threshold_usd?: number | null
          user_id: string
        }
        Update: {
          created_at?: string
          hive_session_id?: string | null
          id?: string
          last_scan_at?: string | null
          max_targets?: number
          min_volatility_pct?: number
          min_volume_usd?: number
          scan_interval_seconds?: number
          started_at?: string
          status?: string
          stopped_at?: string | null
          total_orders_queued?: number
          total_scans?: number
          total_signals_generated?: number
          total_targets_found?: number
          twap_duration_seconds?: number | null
          twap_threshold_usd?: number | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "hunt_sessions_hive_session_id_fkey"
            columns: ["hive_session_id"]
            isOneToOne: false
            referencedRelation: "hive_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      hunt_targets: {
        Row: {
          base_asset: string
          created_at: string
          discovered_at: string
          hunt_session_id: string
          id: string
          opportunity_score: number
          order_queued: boolean | null
          price: number
          processed_at: string | null
          quote_asset: string
          rejection_reason: string | null
          signal_confidence: number | null
          signal_generated: boolean | null
          signal_tier: number | null
          signal_type: string | null
          status: string
          symbol: string
          volatility_24h: number
          volume_24h: number
        }
        Insert: {
          base_asset: string
          created_at?: string
          discovered_at?: string
          hunt_session_id: string
          id?: string
          opportunity_score: number
          order_queued?: boolean | null
          price: number
          processed_at?: string | null
          quote_asset: string
          rejection_reason?: string | null
          signal_confidence?: number | null
          signal_generated?: boolean | null
          signal_tier?: number | null
          signal_type?: string | null
          status?: string
          symbol: string
          volatility_24h: number
          volume_24h: number
        }
        Update: {
          base_asset?: string
          created_at?: string
          discovered_at?: string
          hunt_session_id?: string
          id?: string
          opportunity_score?: number
          order_queued?: boolean | null
          price?: number
          processed_at?: string | null
          quote_asset?: string
          rejection_reason?: string | null
          signal_confidence?: number | null
          signal_generated?: boolean | null
          signal_tier?: number | null
          signal_type?: string | null
          status?: string
          symbol?: string
          volatility_24h?: number
          volume_24h?: number
        }
        Relationships: [
          {
            foreignKeyName: "hunt_targets_hunt_session_id_fkey"
            columns: ["hunt_session_id"]
            isOneToOne: false
            referencedRelation: "hunt_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      integral_aqal_states: {
        Row: {
          created_at: string | null
          dominant_quadrant: string
          id: string
          integration_level: number
          lower_left: number
          lower_right: number
          metadata: Json | null
          quadrant_balance: number
          spiral_stage: string
          temporal_id: string
          timestamp: string | null
          upper_left: number
          upper_right: number
        }
        Insert: {
          created_at?: string | null
          dominant_quadrant?: string
          id?: string
          integration_level?: number
          lower_left?: number
          lower_right?: number
          metadata?: Json | null
          quadrant_balance?: number
          spiral_stage?: string
          temporal_id: string
          timestamp?: string | null
          upper_left?: number
          upper_right?: number
        }
        Update: {
          created_at?: string | null
          dominant_quadrant?: string
          id?: string
          integration_level?: number
          lower_left?: number
          lower_right?: number
          metadata?: Json | null
          quadrant_balance?: number
          spiral_stage?: string
          temporal_id?: string
          timestamp?: string | null
          upper_left?: number
          upper_right?: number
        }
        Relationships: []
      }
      kelly_computation_states: {
        Row: {
          avg_loss: number
          avg_win: number
          created_at: string | null
          id: string
          kelly_fraction: number
          kelly_half: number
          kelly_quarter: number
          losing_trades: number
          max_position_pct: number
          metadata: Json | null
          min_position_pct: number
          recommended_position_pct: number
          temporal_id: string
          timestamp: string | null
          total_trades: number
          win_loss_ratio: number
          win_rate: number
          winning_trades: number
        }
        Insert: {
          avg_loss?: number
          avg_win?: number
          created_at?: string | null
          id?: string
          kelly_fraction?: number
          kelly_half?: number
          kelly_quarter?: number
          losing_trades?: number
          max_position_pct?: number
          metadata?: Json | null
          min_position_pct?: number
          recommended_position_pct?: number
          temporal_id: string
          timestamp?: string | null
          total_trades?: number
          win_loss_ratio?: number
          win_rate?: number
          winning_trades?: number
        }
        Update: {
          avg_loss?: number
          avg_win?: number
          created_at?: string | null
          id?: string
          kelly_fraction?: number
          kelly_half?: number
          kelly_quarter?: number
          losing_trades?: number
          max_position_pct?: number
          metadata?: Json | null
          min_position_pct?: number
          recommended_position_pct?: number
          temporal_id?: string
          timestamp?: string | null
          total_trades?: number
          win_loss_ratio?: number
          win_rate?: number
          winning_trades?: number
        }
        Relationships: []
      }
      lighthouse_events: {
        Row: {
          coherence: number
          confidence: number
          created_at: string
          dominant_node: string | null
          id: string
          is_lhe: boolean
          lambda_value: number
          lighthouse_signal: number
          metric_clin: number
          metric_cnonlin: number
          metric_geff: number
          metric_q: number
          prism_level: number | null
          prism_state: string | null
          threshold: number
          timestamp: string
        }
        Insert: {
          coherence: number
          confidence: number
          created_at?: string
          dominant_node?: string | null
          id?: string
          is_lhe: boolean
          lambda_value: number
          lighthouse_signal: number
          metric_clin: number
          metric_cnonlin: number
          metric_geff: number
          metric_q: number
          prism_level?: number | null
          prism_state?: string | null
          threshold: number
          timestamp?: string
        }
        Update: {
          coherence?: number
          confidence?: number
          created_at?: string
          dominant_node?: string | null
          id?: string
          is_lhe?: boolean
          lambda_value?: number
          lighthouse_signal?: number
          metric_clin?: number
          metric_cnonlin?: number
          metric_geff?: number
          metric_q?: number
          prism_level?: number | null
          prism_state?: string | null
          threshold?: number
          timestamp?: string
        }
        Relationships: []
      }
      local_system_logs: {
        Row: {
          batch_id: string | null
          created_at: string
          id: string
          level: string
          log_type: string
          message: string
          module: string
          parsed_data: Json | null
          timestamp: string
        }
        Insert: {
          batch_id?: string | null
          created_at?: string
          id?: string
          level?: string
          log_type?: string
          message: string
          module?: string
          parsed_data?: Json | null
          timestamp?: string
        }
        Update: {
          batch_id?: string | null
          created_at?: string
          id?: string
          level?: string
          log_type?: string
          message?: string
          module?: string
          parsed_data?: Json | null
          timestamp?: string
        }
        Relationships: []
      }
      master_equation_field_history: {
        Row: {
          coherence: number
          coherence_linear: number
          coherence_nonlinear: number
          coherence_phi: number
          created_at: string
          dominant_node: string
          echo: number
          effective_gain: number
          id: string
          lambda: number
          metadata: Json | null
          momentum: number | null
          node_weights: Json
          observer: number
          price: number | null
          quality_factor: number
          sentinel_name: string | null
          substrate: number
          symbol: string | null
          temporal_id: string
          timestamp: string
          volatility: number | null
          volume: number | null
        }
        Insert: {
          coherence: number
          coherence_linear?: number
          coherence_nonlinear: number
          coherence_phi: number
          created_at?: string
          dominant_node: string
          echo: number
          effective_gain: number
          id?: string
          lambda: number
          metadata?: Json | null
          momentum?: number | null
          node_weights?: Json
          observer: number
          price?: number | null
          quality_factor: number
          sentinel_name?: string | null
          substrate: number
          symbol?: string | null
          temporal_id: string
          timestamp?: string
          volatility?: number | null
          volume?: number | null
        }
        Update: {
          coherence?: number
          coherence_linear?: number
          coherence_nonlinear?: number
          coherence_phi?: number
          created_at?: string
          dominant_node?: string
          echo?: number
          effective_gain?: number
          id?: string
          lambda?: number
          metadata?: Json | null
          momentum?: number | null
          node_weights?: Json
          observer?: number
          price?: number | null
          quality_factor?: number
          sentinel_name?: string | null
          substrate?: number
          symbol?: string | null
          temporal_id?: string
          timestamp?: string
          volatility?: number | null
          volume?: number | null
        }
        Relationships: []
      }
      monte_carlo_simulations: {
        Row: {
          base_config: Json
          confidence_intervals: Json
          created_at: string
          distribution_stats: Json
          end_date: string
          id: string
          num_simulations: number
          randomization_method: string
          results: Json
          start_date: string
          status: string
          symbol: string
        }
        Insert: {
          base_config: Json
          confidence_intervals: Json
          created_at?: string
          distribution_stats: Json
          end_date: string
          id?: string
          num_simulations: number
          randomization_method: string
          results: Json
          start_date: string
          status?: string
          symbol: string
        }
        Update: {
          base_config?: Json
          confidence_intervals?: Json
          created_at?: string
          distribution_stats?: Json
          end_date?: string
          id?: string
          num_simulations?: number
          randomization_method?: string
          results?: Json
          start_date?: string
          status?: string
          symbol?: string
        }
        Relationships: []
      }
      omega_equation_states: {
        Row: {
          celestial_boost: number | null
          coherence: number
          created_at: string | null
          dominant_node: string
          echo: number
          fibonacci_level: number
          id: string
          lambda: number
          love: number
          metadata: Json | null
          observer: number
          omega: number
          psi: number
          schumann_boost: number | null
          spiral_phase: number
          substrate: number
          temporal_id: string
          theta: number
          timestamp: string | null
          unity: number
        }
        Insert: {
          celestial_boost?: number | null
          coherence?: number
          created_at?: string | null
          dominant_node?: string
          echo?: number
          fibonacci_level?: number
          id?: string
          lambda?: number
          love?: number
          metadata?: Json | null
          observer?: number
          omega?: number
          psi?: number
          schumann_boost?: number | null
          spiral_phase?: number
          substrate?: number
          temporal_id: string
          theta?: number
          timestamp?: string | null
          unity?: number
        }
        Update: {
          celestial_boost?: number | null
          coherence?: number
          created_at?: string | null
          dominant_node?: string
          echo?: number
          fibonacci_level?: number
          id?: string
          lambda?: number
          love?: number
          metadata?: Json | null
          observer?: number
          omega?: number
          psi?: number
          schumann_boost?: number | null
          spiral_phase?: number
          substrate?: number
          temporal_id?: string
          theta?: number
          timestamp?: string | null
          unity?: number
        }
        Relationships: []
      }
      oms_execution_metrics: {
        Row: {
          avg_execution_latency_ms: number | null
          avg_wait_time_ms: number | null
          created_at: string
          current_window_orders: number
          id: string
          orders_executed_last_minute: number
          orders_failed_last_minute: number
          queue_depth: number
          rate_limit_utilization: number
          timestamp: string
        }
        Insert: {
          avg_execution_latency_ms?: number | null
          avg_wait_time_ms?: number | null
          created_at?: string
          current_window_orders: number
          id?: string
          orders_executed_last_minute: number
          orders_failed_last_minute: number
          queue_depth: number
          rate_limit_utilization: number
          timestamp?: string
        }
        Update: {
          avg_execution_latency_ms?: number | null
          avg_wait_time_ms?: number | null
          created_at?: string
          current_window_orders?: number
          id?: string
          orders_executed_last_minute?: number
          orders_failed_last_minute?: number
          queue_depth?: number
          rate_limit_utilization?: number
          timestamp?: string
        }
        Relationships: []
      }
      oms_order_queue: {
        Row: {
          agent_id: string
          cancelled_at: string | null
          coherence: number | null
          created_at: string
          error_message: string | null
          exchange_order_id: string | null
          executed_at: string | null
          executed_price: number | null
          executed_quantity: number | null
          hive_id: string
          id: string
          lighthouse_value: number | null
          order_type: string
          price: number
          priority: number
          quantity: number
          queued_at: string
          session_id: string
          side: string
          signal_strength: number | null
          status: string
          symbol: string
        }
        Insert: {
          agent_id: string
          cancelled_at?: string | null
          coherence?: number | null
          created_at?: string
          error_message?: string | null
          exchange_order_id?: string | null
          executed_at?: string | null
          executed_price?: number | null
          executed_quantity?: number | null
          hive_id: string
          id?: string
          lighthouse_value?: number | null
          order_type?: string
          price: number
          priority?: number
          quantity: number
          queued_at?: string
          session_id: string
          side: string
          signal_strength?: number | null
          status?: string
          symbol: string
        }
        Update: {
          agent_id?: string
          cancelled_at?: string | null
          coherence?: number | null
          created_at?: string
          error_message?: string | null
          exchange_order_id?: string | null
          executed_at?: string | null
          executed_price?: number | null
          executed_quantity?: number | null
          hive_id?: string
          id?: string
          lighthouse_value?: number | null
          order_type?: string
          price?: number
          priority?: number
          quantity?: number
          queued_at?: string
          session_id?: string
          side?: string
          signal_strength?: number | null
          status?: string
          symbol?: string
        }
        Relationships: [
          {
            foreignKeyName: "oms_order_queue_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "hive_agents"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "oms_order_queue_hive_id_fkey"
            columns: ["hive_id"]
            isOneToOne: false
            referencedRelation: "hive_instances"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "oms_order_queue_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "hive_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      oms_rate_limit_windows: {
        Row: {
          created_at: string
          id: string
          orders_executed: number
          window_end: string
          window_start: string
        }
        Insert: {
          created_at?: string
          id?: string
          orders_executed?: number
          window_end: string
          window_start: string
        }
        Update: {
          created_at?: string
          id?: string
          orders_executed?: number
          window_end?: string
          window_start?: string
        }
        Relationships: []
      }
      payment_transactions: {
        Row: {
          amount: number
          created_at: string
          currency: string
          id: string
          metadata: Json | null
          paid_at: string | null
          payment_provider: string
          payment_status: string
          payment_url: string | null
          transaction_reference: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          amount: number
          created_at?: string
          currency?: string
          id?: string
          metadata?: Json | null
          paid_at?: string | null
          payment_provider?: string
          payment_status?: string
          payment_url?: string | null
          transaction_reference?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          amount?: number
          created_at?: string
          currency?: string
          id?: string
          metadata?: Json | null
          paid_at?: string | null
          payment_provider?: string
          payment_status?: string
          payment_url?: string | null
          transaction_reference?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      performance_tracker_states: {
        Row: {
          created_at: string | null
          id: string
          max_drawdown: number
          metadata: Json | null
          realized_pnl: number
          sharpe: number
          temporal_id: string
          timestamp: string | null
          total_trades: number
          unrealized_pnl: number
          wins: number
        }
        Insert: {
          created_at?: string | null
          id?: string
          max_drawdown?: number
          metadata?: Json | null
          realized_pnl?: number
          sharpe?: number
          temporal_id: string
          timestamp?: string | null
          total_trades?: number
          unrealized_pnl?: number
          wins?: number
        }
        Update: {
          created_at?: string | null
          id?: string
          max_drawdown?: number
          metadata?: Json | null
          realized_pnl?: number
          sharpe?: number
          temporal_id?: string
          timestamp?: string | null
          total_trades?: number
          unrealized_pnl?: number
          wins?: number
        }
        Relationships: []
      }
      planetary_modulation_states: {
        Row: {
          coherence_nudge: number
          color_palette_shift: number
          created_at: string | null
          harmonic_weight_modulation: Json
          id: string
          metadata: Json | null
          phase_bias: Json
          planetary_states: Json
          temporal_id: string
          timestamp: string | null
        }
        Insert: {
          coherence_nudge?: number
          color_palette_shift?: number
          created_at?: string | null
          harmonic_weight_modulation?: Json
          id?: string
          metadata?: Json | null
          phase_bias?: Json
          planetary_states?: Json
          temporal_id: string
          timestamp?: string | null
        }
        Update: {
          coherence_nudge?: number
          color_palette_shift?: number
          created_at?: string | null
          harmonic_weight_modulation?: Json
          id?: string
          metadata?: Json | null
          phase_bias?: Json
          planetary_states?: Json
          temporal_id?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      price_alerts: {
        Row: {
          alert_type: string
          created_at: string
          current_value: number | null
          id: string
          is_active: boolean
          is_triggered: boolean
          notes: string | null
          symbol: string
          target_value: number
          triggered_at: string | null
        }
        Insert: {
          alert_type: string
          created_at?: string
          current_value?: number | null
          id?: string
          is_active?: boolean
          is_triggered?: boolean
          notes?: string | null
          symbol: string
          target_value: number
          triggered_at?: string | null
        }
        Update: {
          alert_type?: string
          created_at?: string
          current_value?: number | null
          id?: string
          is_active?: boolean
          is_triggered?: boolean
          notes?: string | null
          symbol?: string
          target_value?: number
          triggered_at?: string | null
        }
        Relationships: []
      }
      prime_seal_packets: {
        Row: {
          amplitude_gain: number
          created_at: string
          id: string
          intent_text: string | null
          lattice_phase: number
          metadata: Json | null
          packet_value: number
          prime_coherence: number
          seal_lock: boolean
          systems_contributing: Json | null
          temporal_id: string
          timestamp: string
          w_anchor_1: number
          w_flow_9: number
          w_unity_10: number
        }
        Insert: {
          amplitude_gain?: number
          created_at?: string
          id?: string
          intent_text?: string | null
          lattice_phase?: number
          metadata?: Json | null
          packet_value?: number
          prime_coherence?: number
          seal_lock?: boolean
          systems_contributing?: Json | null
          temporal_id: string
          timestamp?: string
          w_anchor_1?: number
          w_flow_9?: number
          w_unity_10?: number
        }
        Update: {
          amplitude_gain?: number
          created_at?: string
          id?: string
          intent_text?: string | null
          lattice_phase?: number
          metadata?: Json | null
          packet_value?: number
          prime_coherence?: number
          seal_lock?: boolean
          systems_contributing?: Json | null
          temporal_id?: string
          timestamp?: string
          w_anchor_1?: number
          w_flow_9?: number
          w_unity_10?: number
        }
        Relationships: []
      }
      prism_transformation_states: {
        Row: {
          coherence: number
          created_at: string
          frequency: number
          harmonic_purity: number
          id: string
          input_frequency: number
          is_lhe_correlated: boolean | null
          is_love_locked: boolean | null
          lambda_value: number
          level: number
          lighthouse_event_id: string | null
          lighthouse_signal: number | null
          metadata: Json | null
          resonance_strength: number
          sentinel_name: string | null
          state: string
          temporal_id: string
          timestamp: string
          transformation_quality: number
        }
        Insert: {
          coherence: number
          created_at?: string
          frequency: number
          harmonic_purity: number
          id?: string
          input_frequency: number
          is_lhe_correlated?: boolean | null
          is_love_locked?: boolean | null
          lambda_value: number
          level: number
          lighthouse_event_id?: string | null
          lighthouse_signal?: number | null
          metadata?: Json | null
          resonance_strength: number
          sentinel_name?: string | null
          state: string
          temporal_id: string
          timestamp?: string
          transformation_quality: number
        }
        Update: {
          coherence?: number
          created_at?: string
          frequency?: number
          harmonic_purity?: number
          id?: string
          input_frequency?: number
          is_lhe_correlated?: boolean | null
          is_love_locked?: boolean | null
          lambda_value?: number
          level?: number
          lighthouse_event_id?: string | null
          lighthouse_signal?: number | null
          metadata?: Json | null
          resonance_strength?: number
          sentinel_name?: string | null
          state?: string
          temporal_id?: string
          timestamp?: string
          transformation_quality?: number
        }
        Relationships: [
          {
            foreignKeyName: "prism_transformation_states_lighthouse_event_id_fkey"
            columns: ["lighthouse_event_id"]
            isOneToOne: false
            referencedRelation: "lighthouse_events"
            referencedColumns: ["id"]
          },
        ]
      }
      probability_matrix_states: {
        Row: {
          confidence: number
          created_at: string | null
          dynamic_weight: number
          fused_probability: number
          harmonic_lock: boolean | null
          hnc_probability: number
          id: string
          metadata: Json | null
          six_d_probability: number
          temporal_id: string
          timestamp: string | null
          trading_action: string
          wave_state: string | null
        }
        Insert: {
          confidence?: number
          created_at?: string | null
          dynamic_weight?: number
          fused_probability?: number
          harmonic_lock?: boolean | null
          hnc_probability?: number
          id?: string
          metadata?: Json | null
          six_d_probability?: number
          temporal_id: string
          timestamp?: string | null
          trading_action?: string
          wave_state?: string | null
        }
        Update: {
          confidence?: number
          created_at?: string | null
          dynamic_weight?: number
          fused_probability?: number
          harmonic_lock?: boolean | null
          hnc_probability?: number
          id?: string
          metadata?: Json | null
          six_d_probability?: number
          temporal_id?: string
          timestamp?: string | null
          trading_action?: string
          wave_state?: string | null
        }
        Relationships: []
      }
      profiles: {
        Row: {
          created_at: string
          data_consent_date: string | null
          data_consent_given: boolean | null
          date_of_birth: string | null
          email: string | null
          full_name: string | null
          id: string
          id_document_path: string | null
          kyc_status: string | null
          kyc_verified_at: string | null
          location: string | null
          payment_completed: boolean | null
          payment_completed_at: string | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          data_consent_date?: string | null
          data_consent_given?: boolean | null
          date_of_birth?: string | null
          email?: string | null
          full_name?: string | null
          id: string
          id_document_path?: string | null
          kyc_status?: string | null
          kyc_verified_at?: string | null
          location?: string | null
          payment_completed?: boolean | null
          payment_completed_at?: string | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          data_consent_date?: string | null
          data_consent_given?: boolean | null
          date_of_birth?: string | null
          email?: string | null
          full_name?: string | null
          id?: string
          id_document_path?: string | null
          kyc_status?: string | null
          kyc_verified_at?: string | null
          location?: string | null
          payment_completed?: boolean | null
          payment_completed_at?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      qgita_signal_states: {
        Row: {
          anomaly_pointer: number | null
          coherence_boost: number
          confidence: number
          created_at: string | null
          cross_scale_coherence: number | null
          curvature: number | null
          curvature_direction: string | null
          frequency: number
          ftcp_detected: boolean | null
          golden_ratio_score: number | null
          id: string
          is_lhe: boolean | null
          lighthouse_l: number | null
          lighthouse_threshold: number | null
          linear_coherence: number | null
          metadata: Json | null
          nonlinear_coherence: number | null
          phase: string
          reasoning: string | null
          signal_type: string
          strength: number
          temporal_id: string
          tier: number | null
          timestamp: string | null
        }
        Insert: {
          anomaly_pointer?: number | null
          coherence_boost?: number
          confidence?: number
          created_at?: string | null
          cross_scale_coherence?: number | null
          curvature?: number | null
          curvature_direction?: string | null
          frequency?: number
          ftcp_detected?: boolean | null
          golden_ratio_score?: number | null
          id?: string
          is_lhe?: boolean | null
          lighthouse_l?: number | null
          lighthouse_threshold?: number | null
          linear_coherence?: number | null
          metadata?: Json | null
          nonlinear_coherence?: number | null
          phase?: string
          reasoning?: string | null
          signal_type?: string
          strength?: number
          temporal_id: string
          tier?: number | null
          timestamp?: string | null
        }
        Update: {
          anomaly_pointer?: number | null
          coherence_boost?: number
          confidence?: number
          created_at?: string | null
          cross_scale_coherence?: number | null
          curvature?: number | null
          curvature_direction?: string | null
          frequency?: number
          ftcp_detected?: boolean | null
          golden_ratio_score?: number | null
          id?: string
          is_lhe?: boolean | null
          lighthouse_l?: number | null
          lighthouse_threshold?: number | null
          linear_coherence?: number | null
          metadata?: Json | null
          nonlinear_coherence?: number | null
          phase?: string
          reasoning?: string | null
          signal_type?: string
          strength?: number
          temporal_id?: string
          tier?: number | null
          timestamp?: string | null
        }
        Relationships: []
      }
      rainbow_bridge_states: {
        Row: {
          arousal: number
          base_frequency: number
          coherence: number
          color: string
          created_at: string
          dominant_emotion: string
          emotional_tags: string[] | null
          frequency: number
          harmonic_index: number
          id: string
          intensity: number
          lambda_value: number
          metadata: Json | null
          phase: string
          phase_transition: boolean | null
          previous_phase: string | null
          sentinel_name: string | null
          temporal_id: string
          timestamp: string
          valence: number
        }
        Insert: {
          arousal: number
          base_frequency: number
          coherence: number
          color: string
          created_at?: string
          dominant_emotion: string
          emotional_tags?: string[] | null
          frequency: number
          harmonic_index: number
          id?: string
          intensity: number
          lambda_value: number
          metadata?: Json | null
          phase: string
          phase_transition?: boolean | null
          previous_phase?: string | null
          sentinel_name?: string | null
          temporal_id: string
          timestamp?: string
          valence: number
        }
        Update: {
          arousal?: number
          base_frequency?: number
          coherence?: number
          color?: string
          created_at?: string
          dominant_emotion?: string
          emotional_tags?: string[] | null
          frequency?: number
          harmonic_index?: number
          id?: string
          intensity?: number
          lambda_value?: number
          metadata?: Json | null
          phase?: string
          phase_transition?: boolean | null
          previous_phase?: string | null
          sentinel_name?: string | null
          temporal_id?: string
          timestamp?: string
          valence?: number
        }
        Relationships: []
      }
      risk_manager_states: {
        Row: {
          created_at: string | null
          equity: number
          id: string
          max_drawdown: number
          metadata: Json | null
          open_positions: Json | null
          open_positions_count: number
          temporal_id: string
          timestamp: string | null
        }
        Insert: {
          created_at?: string | null
          equity?: number
          id?: string
          max_drawdown?: number
          metadata?: Json | null
          open_positions?: Json | null
          open_positions_count?: number
          temporal_id: string
          timestamp?: string | null
        }
        Update: {
          created_at?: string | null
          equity?: number
          id?: string
          max_drawdown?: number
          metadata?: Json | null
          open_positions?: Json | null
          open_positions_count?: number
          temporal_id?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      scheduler_history: {
        Row: {
          action: string
          coherence_at_action: number
          created_at: string
          daily_activations: number
          id: string
          lighthouse_events_count: number
          metadata: Json | null
          reason: string
          timestamp: string
          trading_enabled_after: boolean
          trading_enabled_before: boolean
        }
        Insert: {
          action: string
          coherence_at_action: number
          created_at?: string
          daily_activations?: number
          id?: string
          lighthouse_events_count?: number
          metadata?: Json | null
          reason: string
          timestamp?: string
          trading_enabled_after: boolean
          trading_enabled_before: boolean
        }
        Update: {
          action?: string
          coherence_at_action?: number
          created_at?: string
          daily_activations?: number
          id?: string
          lighthouse_events_count?: number
          metadata?: Json | null
          reason?: string
          timestamp?: string
          trading_enabled_after?: boolean
          trading_enabled_before?: boolean
        }
        Relationships: []
      }
      sentinel_config: {
        Row: {
          auto_initialize: boolean | null
          created_at: string | null
          id: string
          sentinel_birthdate: string
          sentinel_name: string
          sentinel_title: string
          stargate_latitude: number
          stargate_location: string
          stargate_longitude: number
          updated_at: string | null
        }
        Insert: {
          auto_initialize?: boolean | null
          created_at?: string | null
          id?: string
          sentinel_birthdate: string
          sentinel_name: string
          sentinel_title: string
          stargate_latitude: number
          stargate_location: string
          stargate_longitude: number
          updated_at?: string | null
        }
        Update: {
          auto_initialize?: boolean | null
          created_at?: string | null
          id?: string
          sentinel_birthdate?: string
          sentinel_name?: string
          sentinel_title?: string
          stargate_latitude?: number
          stargate_location?: string
          stargate_longitude?: number
          updated_at?: string | null
        }
        Relationships: []
      }
      smart_router_states: {
        Row: {
          binance_fee: number | null
          created_at: string | null
          fee_savings: number | null
          id: string
          kraken_fee: number | null
          metadata: Json | null
          routing_reason: string
          selected_exchange: string
          temporal_id: string
          timestamp: string | null
        }
        Insert: {
          binance_fee?: number | null
          created_at?: string | null
          fee_savings?: number | null
          id?: string
          kraken_fee?: number | null
          metadata?: Json | null
          routing_reason?: string
          selected_exchange?: string
          temporal_id: string
          timestamp?: string | null
        }
        Update: {
          binance_fee?: number | null
          created_at?: string | null
          fee_savings?: number | null
          id?: string
          kraken_fee?: number | null
          metadata?: Json | null
          routing_reason?: string
          selected_exchange?: string
          temporal_id?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      solar_flare_correlations: {
        Row: {
          analysis_window_hours: number | null
          avg_coherence_after: number | null
          avg_coherence_before: number | null
          avg_coherence_during: number | null
          avg_return: number | null
          avg_signal_strength: number | null
          coherence_boost: number | null
          created_at: string | null
          flare_class: string
          flare_power: number
          flare_time: string
          id: string
          lhe_events_count: number | null
          optimal_signals_count: number | null
          prediction_score: number | null
          trading_signals_count: number | null
          updated_at: string | null
          win_rate: number | null
        }
        Insert: {
          analysis_window_hours?: number | null
          avg_coherence_after?: number | null
          avg_coherence_before?: number | null
          avg_coherence_during?: number | null
          avg_return?: number | null
          avg_signal_strength?: number | null
          coherence_boost?: number | null
          created_at?: string | null
          flare_class: string
          flare_power: number
          flare_time: string
          id?: string
          lhe_events_count?: number | null
          optimal_signals_count?: number | null
          prediction_score?: number | null
          trading_signals_count?: number | null
          updated_at?: string | null
          win_rate?: number | null
        }
        Update: {
          analysis_window_hours?: number | null
          avg_coherence_after?: number | null
          avg_coherence_before?: number | null
          avg_coherence_during?: number | null
          avg_return?: number | null
          avg_signal_strength?: number | null
          coherence_boost?: number | null
          created_at?: string | null
          flare_class?: string
          flare_power?: number
          flare_time?: string
          id?: string
          lhe_events_count?: number | null
          optimal_signals_count?: number | null
          prediction_score?: number | null
          trading_signals_count?: number | null
          updated_at?: string | null
          win_rate?: number | null
        }
        Relationships: []
      }
      stargate_harmonizer_states: {
        Row: {
          coherence_boost: number
          confidence_modifier: number
          created_at: string | null
          dominant_frequency: number
          harmonics: Json | null
          id: string
          metadata: Json | null
          optimal_entry_window: boolean | null
          resonance_quality: number
          signal_amplification: number
          temporal_id: string
          timestamp: string | null
          trading_bias: string
        }
        Insert: {
          coherence_boost?: number
          confidence_modifier?: number
          created_at?: string | null
          dominant_frequency?: number
          harmonics?: Json | null
          id?: string
          metadata?: Json | null
          optimal_entry_window?: boolean | null
          resonance_quality?: number
          signal_amplification?: number
          temporal_id: string
          timestamp?: string | null
          trading_bias?: string
        }
        Update: {
          coherence_boost?: number
          confidence_modifier?: number
          created_at?: string | null
          dominant_frequency?: number
          harmonics?: Json | null
          id?: string
          metadata?: Json | null
          optimal_entry_window?: boolean | null
          resonance_quality?: number
          signal_amplification?: number
          temporal_id?: string
          timestamp?: string | null
          trading_bias?: string
        }
        Relationships: []
      }
      stargate_network_states: {
        Row: {
          active_nodes: number
          avg_coherence: number | null
          avg_frequency: number | null
          created_at: string
          event_timestamp: string
          grid_energy: number
          id: string
          metadata: Json | null
          network_strength: number
          phase_locks: number | null
          resonance_quality: number | null
          sentinel_name: string | null
          temporal_id: string
        }
        Insert: {
          active_nodes: number
          avg_coherence?: number | null
          avg_frequency?: number | null
          created_at?: string
          event_timestamp?: string
          grid_energy: number
          id?: string
          metadata?: Json | null
          network_strength: number
          phase_locks?: number | null
          resonance_quality?: number | null
          sentinel_name?: string | null
          temporal_id: string
        }
        Update: {
          active_nodes?: number
          avg_coherence?: number | null
          avg_frequency?: number | null
          created_at?: string
          event_timestamp?: string
          grid_energy?: number
          id?: string
          metadata?: Json | null
          network_strength?: number
          phase_locks?: number | null
          resonance_quality?: number | null
          sentinel_name?: string | null
          temporal_id?: string
        }
        Relationships: []
      }
      system_runtime_stats: {
        Row: {
          avg_hold_time_minutes: number | null
          carrier_wave_phi: number | null
          compounded_capital: number | null
          created_at: string | null
          current_drawdown_percent: number | null
          cycle_pnl: number | null
          entry_coherence_threshold: number | null
          exit_coherence_threshold: number | null
          gaia_frequency: number | null
          gaia_lattice_state: string | null
          harmonic_lock_432: number | null
          harvested_capital: number | null
          hnc_coherence_percent: number | null
          hnc_frequency: number | null
          hnc_market_state: string | null
          hnc_modifier: number | null
          id: string
          max_drawdown_percent: number | null
          max_generation: number | null
          mycelium_agents: number | null
          mycelium_generation: number | null
          mycelium_hives: number | null
          peak_equity: number | null
          pool_available: number | null
          pool_total: number | null
          purity_percent: number | null
          queen_pnl: number | null
          queen_state: string | null
          risk_multiplier: number | null
          scout_count: number | null
          session_start_time: string
          split_count: number | null
          take_profit_multiplier: number | null
          trading_mode: string | null
          updated_at: string | null
          user_id: string
          ws_message_count: number | null
        }
        Insert: {
          avg_hold_time_minutes?: number | null
          carrier_wave_phi?: number | null
          compounded_capital?: number | null
          created_at?: string | null
          current_drawdown_percent?: number | null
          cycle_pnl?: number | null
          entry_coherence_threshold?: number | null
          exit_coherence_threshold?: number | null
          gaia_frequency?: number | null
          gaia_lattice_state?: string | null
          harmonic_lock_432?: number | null
          harvested_capital?: number | null
          hnc_coherence_percent?: number | null
          hnc_frequency?: number | null
          hnc_market_state?: string | null
          hnc_modifier?: number | null
          id?: string
          max_drawdown_percent?: number | null
          max_generation?: number | null
          mycelium_agents?: number | null
          mycelium_generation?: number | null
          mycelium_hives?: number | null
          peak_equity?: number | null
          pool_available?: number | null
          pool_total?: number | null
          purity_percent?: number | null
          queen_pnl?: number | null
          queen_state?: string | null
          risk_multiplier?: number | null
          scout_count?: number | null
          session_start_time?: string
          split_count?: number | null
          take_profit_multiplier?: number | null
          trading_mode?: string | null
          updated_at?: string | null
          user_id: string
          ws_message_count?: number | null
        }
        Update: {
          avg_hold_time_minutes?: number | null
          carrier_wave_phi?: number | null
          compounded_capital?: number | null
          created_at?: string | null
          current_drawdown_percent?: number | null
          cycle_pnl?: number | null
          entry_coherence_threshold?: number | null
          exit_coherence_threshold?: number | null
          gaia_frequency?: number | null
          gaia_lattice_state?: string | null
          harmonic_lock_432?: number | null
          harvested_capital?: number | null
          hnc_coherence_percent?: number | null
          hnc_frequency?: number | null
          hnc_market_state?: string | null
          hnc_modifier?: number | null
          id?: string
          max_drawdown_percent?: number | null
          max_generation?: number | null
          mycelium_agents?: number | null
          mycelium_generation?: number | null
          mycelium_hives?: number | null
          peak_equity?: number | null
          pool_available?: number | null
          pool_total?: number | null
          purity_percent?: number | null
          queen_pnl?: number | null
          queen_state?: string | null
          risk_multiplier?: number | null
          scout_count?: number | null
          session_start_time?: string
          split_count?: number | null
          take_profit_multiplier?: number | null
          trading_mode?: string | null
          updated_at?: string | null
          user_id?: string
          ws_message_count?: number | null
        }
        Relationships: []
      }
      telescope_observations: {
        Row: {
          beam_angle: number
          beam_intensity: number
          beam_polarization: number
          beam_velocity: number
          beam_wavelength: number
          created_at: string
          dodecahedron_resonance: number
          dominant_solid: string
          focal_coherence: number
          geometric_alignment: number
          hexahedron_resonance: number
          holographic_projection: Json | null
          icosahedron_resonance: number
          id: string
          metadata: Json | null
          octahedron_resonance: number
          prism_boost_factor: number
          probability_spectrum: Json | null
          symbol: string
          temporal_id: string
          tetrahedron_resonance: number
          timestamp: string
        }
        Insert: {
          beam_angle?: number
          beam_intensity?: number
          beam_polarization?: number
          beam_velocity?: number
          beam_wavelength?: number
          created_at?: string
          dodecahedron_resonance?: number
          dominant_solid?: string
          focal_coherence?: number
          geometric_alignment?: number
          hexahedron_resonance?: number
          holographic_projection?: Json | null
          icosahedron_resonance?: number
          id?: string
          metadata?: Json | null
          octahedron_resonance?: number
          prism_boost_factor?: number
          probability_spectrum?: Json | null
          symbol?: string
          temporal_id: string
          tetrahedron_resonance?: number
          timestamp?: string
        }
        Update: {
          beam_angle?: number
          beam_intensity?: number
          beam_polarization?: number
          beam_velocity?: number
          beam_wavelength?: number
          created_at?: string
          dodecahedron_resonance?: number
          dominant_solid?: string
          focal_coherence?: number
          geometric_alignment?: number
          hexahedron_resonance?: number
          holographic_projection?: Json | null
          icosahedron_resonance?: number
          id?: string
          metadata?: Json | null
          octahedron_resonance?: number
          prism_boost_factor?: number
          probability_spectrum?: Json | null
          symbol?: string
          temporal_id?: string
          tetrahedron_resonance?: number
          timestamp?: string
        }
        Relationships: []
      }
      temporal_anchor_states: {
        Row: {
          anchor_strength: number
          created_at: string | null
          drift_amount_ms: number | null
          drift_detected: boolean | null
          id: string
          is_valid: boolean | null
          metadata: Json | null
          registered_systems: number
          temporal_id: string
          timestamp: string | null
          verified_systems: number
        }
        Insert: {
          anchor_strength?: number
          created_at?: string | null
          drift_amount_ms?: number | null
          drift_detected?: boolean | null
          id?: string
          is_valid?: boolean | null
          metadata?: Json | null
          registered_systems?: number
          temporal_id: string
          timestamp?: string | null
          verified_systems?: number
        }
        Update: {
          anchor_strength?: number
          created_at?: string | null
          drift_amount_ms?: number | null
          drift_detected?: boolean | null
          id?: string
          is_valid?: boolean | null
          metadata?: Json | null
          registered_systems?: number
          temporal_id?: string
          timestamp?: string | null
          verified_systems?: number
        }
        Relationships: []
      }
      ticker_snapshots: {
        Row: {
          ask_price: number | null
          bid_price: number | null
          created_at: string
          data_source: string | null
          exchange: string
          fetched_at: string
          high_24h: number | null
          id: string
          is_validated: boolean | null
          low_24h: number | null
          momentum: number | null
          price: number
          price_change_24h: number | null
          spread: number | null
          symbol: string
          temporal_id: string
          validation_status: string | null
          volatility: number | null
          volume: number | null
          volume_usd: number | null
        }
        Insert: {
          ask_price?: number | null
          bid_price?: number | null
          created_at?: string
          data_source?: string | null
          exchange?: string
          fetched_at?: string
          high_24h?: number | null
          id?: string
          is_validated?: boolean | null
          low_24h?: number | null
          momentum?: number | null
          price: number
          price_change_24h?: number | null
          spread?: number | null
          symbol: string
          temporal_id: string
          validation_status?: string | null
          volatility?: number | null
          volume?: number | null
          volume_usd?: number | null
        }
        Update: {
          ask_price?: number | null
          bid_price?: number | null
          created_at?: string
          data_source?: string | null
          exchange?: string
          fetched_at?: string
          high_24h?: number | null
          id?: string
          is_validated?: boolean | null
          low_24h?: number | null
          momentum?: number | null
          price?: number
          price_change_24h?: number | null
          spread?: number | null
          symbol?: string
          temporal_id?: string
          validation_status?: string | null
          volatility?: number | null
          volume?: number | null
          volume_usd?: number | null
        }
        Relationships: []
      }
      trade_audit_log: {
        Row: {
          client_order_id: string | null
          commission: number | null
          commission_asset: string | null
          created_at: string
          error_code: string | null
          error_message: string | null
          exchange: string
          exchange_response: Json | null
          executed_price: number | null
          executed_qty: number | null
          external_order_id: string | null
          id: string
          order_type: string | null
          price: number | null
          quantity: number
          side: string
          stage: string
          symbol: string
          trade_id: string
          updated_at: string
          validation_message: string | null
          validation_status: string | null
        }
        Insert: {
          client_order_id?: string | null
          commission?: number | null
          commission_asset?: string | null
          created_at?: string
          error_code?: string | null
          error_message?: string | null
          exchange: string
          exchange_response?: Json | null
          executed_price?: number | null
          executed_qty?: number | null
          external_order_id?: string | null
          id?: string
          order_type?: string | null
          price?: number | null
          quantity: number
          side: string
          stage?: string
          symbol: string
          trade_id: string
          updated_at?: string
          validation_message?: string | null
          validation_status?: string | null
        }
        Update: {
          client_order_id?: string | null
          commission?: number | null
          commission_asset?: string | null
          created_at?: string
          error_code?: string | null
          error_message?: string | null
          exchange?: string
          exchange_response?: Json | null
          executed_price?: number | null
          executed_qty?: number | null
          external_order_id?: string | null
          id?: string
          order_type?: string | null
          price?: number | null
          quantity?: number
          side?: string
          stage?: string
          symbol?: string
          trade_id?: string
          updated_at?: string
          validation_message?: string | null
          validation_status?: string | null
        }
        Relationships: []
      }
      trade_records: {
        Row: {
          created_at: string
          exchange: string
          fee: number | null
          fee_asset: string | null
          id: string
          is_win: boolean | null
          pnl: number | null
          price: number
          quantity: number
          quote_qty: number | null
          side: string
          symbol: string
          timestamp: string
          transaction_id: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          exchange: string
          fee?: number | null
          fee_asset?: string | null
          id?: string
          is_win?: boolean | null
          pnl?: number | null
          price: number
          quantity: number
          quote_qty?: number | null
          side: string
          symbol: string
          timestamp: string
          transaction_id: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          exchange?: string
          fee?: number | null
          fee_asset?: string | null
          id?: string
          is_win?: boolean | null
          pnl?: number | null
          price?: number
          quantity?: number
          quote_qty?: number | null
          side?: string
          symbol?: string
          timestamp?: string
          transaction_id?: string
          user_id?: string | null
        }
        Relationships: []
      }
      trading_config: {
        Row: {
          allowed_symbols: string[]
          base_position_size_usdt: number
          created_at: string
          id: string
          is_enabled: boolean
          max_daily_loss_usdt: number
          max_daily_trades: number
          max_position_size_usdt: number
          min_coherence: number
          min_lighthouse_confidence: number
          min_prism_level: number
          position_size_mode: string
          require_lhe: boolean
          stop_loss_percentage: number
          take_profit_percentage: number
          trading_mode: string
          updated_at: string
        }
        Insert: {
          allowed_symbols?: string[]
          base_position_size_usdt?: number
          created_at?: string
          id?: string
          is_enabled?: boolean
          max_daily_loss_usdt?: number
          max_daily_trades?: number
          max_position_size_usdt?: number
          min_coherence?: number
          min_lighthouse_confidence?: number
          min_prism_level?: number
          position_size_mode?: string
          require_lhe?: boolean
          stop_loss_percentage?: number
          take_profit_percentage?: number
          trading_mode?: string
          updated_at?: string
        }
        Update: {
          allowed_symbols?: string[]
          base_position_size_usdt?: number
          created_at?: string
          id?: string
          is_enabled?: boolean
          max_daily_loss_usdt?: number
          max_daily_trades?: number
          max_position_size_usdt?: number
          min_coherence?: number
          min_lighthouse_confidence?: number
          min_prism_level?: number
          position_size_mode?: string
          require_lhe?: boolean
          stop_loss_percentage?: number
          take_profit_percentage?: number
          trading_mode?: string
          updated_at?: string
        }
        Relationships: []
      }
      trading_executions: {
        Row: {
          coherence: number
          created_at: string
          error_message: string | null
          exchange_order_id: string | null
          executed_at: string | null
          executed_price: number | null
          id: string
          is_forced_validation: boolean | null
          lighthouse_confidence: number
          lighthouse_event_id: string | null
          lighthouse_value: number
          order_type: string
          position_size_usdt: number
          price: number | null
          prism_level: number
          quantity: number
          side: string
          signal_id: string | null
          signal_type: string
          status: string
          stop_loss_price: number | null
          symbol: string
          take_profit_price: number | null
          validation_trace: Json | null
        }
        Insert: {
          coherence: number
          created_at?: string
          error_message?: string | null
          exchange_order_id?: string | null
          executed_at?: string | null
          executed_price?: number | null
          id?: string
          is_forced_validation?: boolean | null
          lighthouse_confidence: number
          lighthouse_event_id?: string | null
          lighthouse_value: number
          order_type?: string
          position_size_usdt: number
          price?: number | null
          prism_level: number
          quantity: number
          side: string
          signal_id?: string | null
          signal_type: string
          status?: string
          stop_loss_price?: number | null
          symbol: string
          take_profit_price?: number | null
          validation_trace?: Json | null
        }
        Update: {
          coherence?: number
          created_at?: string
          error_message?: string | null
          exchange_order_id?: string | null
          executed_at?: string | null
          executed_price?: number | null
          id?: string
          is_forced_validation?: boolean | null
          lighthouse_confidence?: number
          lighthouse_event_id?: string | null
          lighthouse_value?: number
          order_type?: string
          position_size_usdt?: number
          price?: number | null
          prism_level?: number
          quantity?: number
          side?: string
          signal_id?: string | null
          signal_type?: string
          status?: string
          stop_loss_price?: number | null
          symbol?: string
          take_profit_price?: number | null
          validation_trace?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_executions_lighthouse_event_id_fkey"
            columns: ["lighthouse_event_id"]
            isOneToOne: false
            referencedRelation: "lighthouse_events"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_executions_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "recent_optimal_signals"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_executions_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_positions: {
        Row: {
          close_reason: string | null
          closed_at: string | null
          current_price: number | null
          entry_price: number
          exchange: string
          execution_id: string | null
          exit_price: number | null
          id: string
          opened_at: string
          position_value_usdt: number
          quantity: number
          realized_pnl: number | null
          realized_pnl_pct: number | null
          side: string
          status: string
          stop_loss_price: number | null
          symbol: string
          source_id: string
          source_timestamp: string
          take_profit_price: number | null
          truth_status: string
          unrealized_pnl: number | null
          updated_at: string
          user_id: string
          generated_values: boolean
        }
        Insert: {
          close_reason?: string | null
          closed_at?: string | null
          current_price?: number | null
          entry_price: number
          exchange: string
          execution_id?: string | null
          exit_price?: number | null
          id?: string
          opened_at?: string
          position_value_usdt: number
          quantity: number
          realized_pnl?: number | null
          realized_pnl_pct?: number | null
          side: string
          status?: string
          stop_loss_price?: number | null
          symbol: string
          source_id: string
          source_timestamp: string
          take_profit_price?: number | null
          truth_status: string
          unrealized_pnl?: number | null
          updated_at?: string
          user_id: string
          generated_values?: boolean
        }
        Update: {
          close_reason?: string | null
          closed_at?: string | null
          current_price?: number | null
          entry_price?: number
          exchange?: string
          execution_id?: string | null
          exit_price?: number | null
          id?: string
          opened_at?: string
          position_value_usdt?: number
          quantity?: number
          realized_pnl?: number | null
          realized_pnl_pct?: number | null
          side?: string
          status?: string
          stop_loss_price?: number | null
          symbol?: string
          source_id?: string
          source_timestamp?: string
          take_profit_price?: number | null
          truth_status?: string
          unrealized_pnl?: number | null
          updated_at?: string
          user_id?: string
          generated_values?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "trading_positions_execution_id_fkey"
            columns: ["execution_id"]
            isOneToOne: false
            referencedRelation: "trading_executions"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_signals: {
        Row: {
          coherence: number
          created_at: string
          id: string
          lighthouse_event_id: string | null
          lighthouse_value: number
          prism_level: number
          reason: string
          signal_type: string
          strength: number
          timestamp: string
        }
        Insert: {
          coherence: number
          created_at?: string
          id?: string
          lighthouse_event_id?: string | null
          lighthouse_value: number
          prism_level: number
          reason: string
          signal_type: string
          strength: number
          timestamp?: string
        }
        Update: {
          coherence?: number
          created_at?: string
          id?: string
          lighthouse_event_id?: string | null
          lighthouse_value?: number
          prism_level?: number
          reason?: string
          signal_type?: string
          strength?: number
          timestamp?: string
        }
        Relationships: [
          {
            foreignKeyName: "trading_signals_lighthouse_event_id_fkey"
            columns: ["lighthouse_event_id"]
            isOneToOne: false
            referencedRelation: "lighthouse_events"
            referencedColumns: ["id"]
          },
        ]
      }
      twap_orders: {
        Row: {
          algo_id: number | null
          algo_status: string | null
          avg_price: number | null
          book_time: string | null
          client_algo_id: string
          created_at: string
          duration_seconds: number
          end_time: string | null
          error_code: number | null
          error_message: string | null
          executed_amount: number | null
          executed_quantity: number | null
          hunt_session_id: string | null
          id: string
          limit_price: number | null
          metadata: Json | null
          oms_order_id: string | null
          side: string
          symbol: string
          total_quantity: number
          updated_at: string
          urgency: string | null
        }
        Insert: {
          algo_id?: number | null
          algo_status?: string | null
          avg_price?: number | null
          book_time?: string | null
          client_algo_id: string
          created_at?: string
          duration_seconds: number
          end_time?: string | null
          error_code?: number | null
          error_message?: string | null
          executed_amount?: number | null
          executed_quantity?: number | null
          hunt_session_id?: string | null
          id?: string
          limit_price?: number | null
          metadata?: Json | null
          oms_order_id?: string | null
          side: string
          symbol: string
          total_quantity: number
          updated_at?: string
          urgency?: string | null
        }
        Update: {
          algo_id?: number | null
          algo_status?: string | null
          avg_price?: number | null
          book_time?: string | null
          client_algo_id?: string
          created_at?: string
          duration_seconds?: number
          end_time?: string | null
          error_code?: number | null
          error_message?: string | null
          executed_amount?: number | null
          executed_quantity?: number | null
          hunt_session_id?: string | null
          id?: string
          limit_price?: number | null
          metadata?: Json | null
          oms_order_id?: string | null
          side?: string
          symbol?: string
          total_quantity?: number
          updated_at?: string
          urgency?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "twap_orders_hunt_session_id_fkey"
            columns: ["hunt_session_id"]
            isOneToOne: false
            referencedRelation: "hunt_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "twap_orders_oms_order_id_fkey"
            columns: ["oms_order_id"]
            isOneToOne: false
            referencedRelation: "oms_order_queue"
            referencedColumns: ["id"]
          },
        ]
      }
      twap_sub_orders: {
        Row: {
          avg_price: number | null
          book_time: string
          created_at: string
          executed_amount: number
          executed_quantity: number
          fee_amount: number | null
          fee_asset: string | null
          id: string
          order_id: number
          order_status: string
          orig_quantity: number
          side: string
          sub_id: number
          symbol: string
          time_in_force: string | null
          twap_order_id: string
        }
        Insert: {
          avg_price?: number | null
          book_time: string
          created_at?: string
          executed_amount?: number
          executed_quantity?: number
          fee_amount?: number | null
          fee_asset?: string | null
          id?: string
          order_id: number
          order_status: string
          orig_quantity: number
          side: string
          sub_id: number
          symbol: string
          time_in_force?: string | null
          twap_order_id: string
        }
        Update: {
          avg_price?: number | null
          book_time?: string
          created_at?: string
          executed_amount?: number
          executed_quantity?: number
          fee_amount?: number | null
          fee_asset?: string | null
          id?: string
          order_id?: number
          order_status?: string
          orig_quantity?: number
          side?: string
          sub_id?: number
          symbol?: string
          time_in_force?: string | null
          twap_order_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "twap_sub_orders_twap_order_id_fkey"
            columns: ["twap_order_id"]
            isOneToOne: false
            referencedRelation: "twap_orders"
            referencedColumns: ["id"]
          },
        ]
      }
      unified_bus_snapshots: {
        Row: {
          consensus_confidence: number | null
          consensus_signal: string | null
          created_at: string | null
          id: string
          snapshot: Json
          systems_ready: number | null
          total_systems: number | null
        }
        Insert: {
          consensus_confidence?: number | null
          consensus_signal?: string | null
          created_at?: string | null
          id?: string
          snapshot: Json
          systems_ready?: number | null
          total_systems?: number | null
        }
        Update: {
          consensus_confidence?: number | null
          consensus_signal?: string | null
          created_at?: string | null
          id?: string
          snapshot?: Json
          systems_ready?: number | null
          total_systems?: number | null
        }
        Relationships: []
      }
      unity_event_states: {
        Row: {
          coherence: number
          created_at: string | null
          duration_ms: number
          event_type: string
          id: string
          is_peak: boolean | null
          metadata: Json | null
          omega: number
          temporal_id: string
          theta: number
          timestamp: string | null
          unity: number
        }
        Insert: {
          coherence?: number
          created_at?: string | null
          duration_ms?: number
          event_type?: string
          id?: string
          is_peak?: boolean | null
          metadata?: Json | null
          omega?: number
          temporal_id: string
          theta?: number
          timestamp?: string | null
          unity?: number
        }
        Update: {
          coherence?: number
          created_at?: string | null
          duration_ms?: number
          event_type?: string
          id?: string
          is_peak?: boolean | null
          metadata?: Json | null
          omega?: number
          temporal_id?: string
          theta?: number
          timestamp?: string | null
          unity?: number
        }
        Relationships: []
      }
      user_binance_credentials: {
        Row: {
          api_key_encrypted: string
          api_secret_encrypted: string
          created_at: string
          id: string
          iv: string | null
          last_used_at: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          api_key_encrypted: string
          api_secret_encrypted: string
          created_at?: string
          id?: string
          iv?: string | null
          last_used_at?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          api_key_encrypted?: string
          api_secret_encrypted?: string
          created_at?: string
          id?: string
          iv?: string | null
          last_used_at?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      recent_optimal_signals: {
        Row: {
          coherence: number | null
          id: string | null
          is_lhe: boolean | null
          lhe_confidence: number | null
          lighthouse_signal: number | null
          lighthouse_value: number | null
          reason: string | null
          signal_type: string | null
          strength: number | null
          timestamp: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      cleanup_old_logs: { Args: never; Returns: undefined }
      get_latest_harmonic_state: {
        Args: { p_temporal_id: string }
        Returns: {
          event_timestamp: string
          omega_value: number
          substrate_coherence: number
          sync_quality: number
        }[]
      }
      get_signal_statistics: {
        Args: { time_range?: unknown }
        Returns: {
          avg_strength: number
          hold_signals: number
          lhe_count: number
          long_signals: number
          optimal_signals: number
          short_signals: number
          total_signals: number
        }[]
      }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "admin" | "user"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "user"],
    },
  },
} as const
