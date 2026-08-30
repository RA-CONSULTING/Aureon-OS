-- A session row is an identity/control record, not evidence that a measurement
-- was observed.  Do not manufacture zero balances, neutral HNC values, paper
-- mode, or a funded gas tank when a user first stores credentials.
ALTER TABLE public.aureon_user_sessions
  ALTER COLUMN payment_completed DROP DEFAULT,
  ALTER COLUMN trading_mode DROP DEFAULT,
  ALTER COLUMN current_coherence DROP DEFAULT,
  ALTER COLUMN current_lambda DROP DEFAULT,
  ALTER COLUMN current_lighthouse_signal DROP DEFAULT,
  ALTER COLUMN prism_level DROP DEFAULT,
  ALTER COLUMN prism_state DROP DEFAULT,
  ALTER COLUMN total_equity_usdt DROP DEFAULT,
  ALTER COLUMN available_balance_usdt DROP DEFAULT,
  ALTER COLUMN total_trades DROP DEFAULT,
  ALTER COLUMN winning_trades DROP DEFAULT,
  ALTER COLUMN total_pnl_usdt DROP DEFAULT,
  ALTER COLUMN gas_tank_balance DROP DEFAULT,
  ALTER COLUMN recent_trades DROP DEFAULT;

ALTER TABLE public.aureon_user_sessions
  ADD COLUMN total_equity_usd numeric,
  ADD COLUMN measurement_truth_status text NOT NULL DEFAULT 'no_data',
  ADD COLUMN measurement_source_id text,
  ADD COLUMN measurement_source_timestamp timestamptz,
  ADD COLUMN measurement_collected_at timestamptz,
  ADD COLUMN measurement_generated_values boolean NOT NULL DEFAULT false;

ALTER TABLE public.aureon_user_sessions
  ADD CONSTRAINT aureon_user_sessions_measurement_truth_status_check
    CHECK (measurement_truth_status IN ('live', 'real_derived', 'no_data')),
  ADD CONSTRAINT aureon_user_sessions_no_generated_measurements_check
    CHECK (measurement_generated_values = false),
  ADD CONSTRAINT aureon_user_sessions_live_measurement_provenance_check
    CHECK (
      measurement_truth_status = 'no_data'
      OR (
        measurement_source_id IS NOT NULL
        AND measurement_source_timestamp IS NOT NULL
        AND measurement_collected_at IS NOT NULL
      )
    );

COMMENT ON COLUMN public.aureon_user_sessions.measurement_truth_status IS
  'live for direct provider observations, real_derived for documented calculations, no_data when not yet observed';
COMMENT ON COLUMN public.aureon_user_sessions.measurement_generated_values IS
  'Must remain false: production session measurements cannot contain mock, demo, synthetic, or fallback values';

ALTER TABLE public.trade_records
  ALTER COLUMN fee DROP DEFAULT,
  ALTER COLUMN fee SET NOT NULL,
  ALTER COLUMN fee_asset SET NOT NULL,
  ALTER COLUMN user_id SET NOT NULL,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT trade_records_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT trade_records_no_generated_values_check
    CHECK (generated_values = false);

COMMENT ON COLUMN public.trade_records.source_id IS
  'Provider and endpoint that issued the immutable transaction_id';

ALTER TABLE public.trading_positions
  ALTER COLUMN unrealized_pnl DROP DEFAULT,
  ALTER COLUMN user_id SET NOT NULL,
  ADD COLUMN exchange text NOT NULL,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT trading_positions_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT trading_positions_no_generated_values_check
    CHECK (generated_values = false);

ALTER TABLE public.hnc_detection_states
  ALTER COLUMN timestamp DROP DEFAULT,
  ALTER COLUMN is_lighthouse_detected DROP DEFAULT,
  ALTER COLUMN schumann_power DROP DEFAULT,
  ALTER COLUMN anchor_power DROP DEFAULT,
  ALTER COLUMN love_power DROP DEFAULT,
  ALTER COLUMN unity_power DROP DEFAULT,
  ALTER COLUMN distortion_power DROP DEFAULT,
  ALTER COLUMN imperial_yield DROP DEFAULT,
  ALTER COLUMN harmonic_fidelity DROP DEFAULT,
  ALTER COLUMN bridge_status DROP DEFAULT,
  ALTER COLUMN metadata DROP DEFAULT,
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT hnc_detection_states_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT hnc_detection_states_no_generated_values_check
    CHECK (generated_values = false);

CREATE INDEX hnc_detection_states_user_source_time_idx
  ON public.hnc_detection_states (user_id, source_timestamp DESC);

DROP POLICY "Authenticated users can read hnc_detection_states"
  ON public.hnc_detection_states;
CREATE POLICY "Users can read own HNC detection states"
  ON public.hnc_detection_states FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

ALTER TABLE public.trading_executions
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN exchange text NOT NULL,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT trading_executions_truth_status_check
    CHECK (truth_status = 'live'),
  ADD CONSTRAINT trading_executions_no_generated_values_check
    CHECK (generated_values = false);

DROP POLICY "Authenticated users can read executions"
  ON public.trading_executions;
CREATE POLICY "Users can read own trading executions"
  ON public.trading_executions FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

CREATE TABLE public.aureon_runtime_observations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  payload jsonb NOT NULL,
  truth_status text NOT NULL CHECK (truth_status IN ('live', 'real_derived')),
  source_id text NOT NULL,
  source_timestamp timestamptz NOT NULL,
  collected_at timestamptz NOT NULL DEFAULT now(),
  generated_values boolean NOT NULL DEFAULT false CHECK (generated_values = false)
);

ALTER TABLE public.aureon_runtime_observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own runtime observations"
  ON public.aureon_runtime_observations FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE INDEX aureon_runtime_observations_user_source_time_idx
  ON public.aureon_runtime_observations (user_id, source_timestamp DESC);

ALTER TABLE public.oms_order_queue
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT oms_order_queue_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT oms_order_queue_no_generated_values_check
    CHECK (generated_values = false);

ALTER TABLE public.hive_trades
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT hive_trades_truth_status_check
    CHECK (truth_status = 'live'),
  ADD CONSTRAINT hive_trades_no_generated_values_check
    CHECK (generated_values = false);

CREATE UNIQUE INDEX oms_order_queue_native_signal_agent_unique
  ON public.oms_order_queue (source_id, source_timestamp, agent_id);

-- Brain-state fields are observations or derived conclusions.  Null means a
-- subsystem supplied no evidence; database defaults must not invent a neutral
-- market, confidence, accuracy, action, or empty analysis.
ALTER TABLE public.brain_states
  ALTER COLUMN timestamp DROP DEFAULT,
  ALTER COLUMN fear_greed DROP DEFAULT,
  ALTER COLUMN fear_greed_class DROP DEFAULT,
  ALTER COLUMN btc_price DROP DEFAULT,
  ALTER COLUMN btc_dominance DROP DEFAULT,
  ALTER COLUMN btc_change_24h DROP DEFAULT,
  ALTER COLUMN manipulation_probability DROP DEFAULT,
  ALTER COLUMN red_flags DROP DEFAULT,
  ALTER COLUMN green_flags DROP DEFAULT,
  ALTER COLUMN council_consensus DROP DEFAULT,
  ALTER COLUMN council_action DROP DEFAULT,
  ALTER COLUMN truth_score DROP DEFAULT,
  ALTER COLUMN spoof_score DROP DEFAULT,
  ALTER COLUMN council_arguments DROP DEFAULT,
  ALTER COLUMN learning_directive DROP DEFAULT,
  ALTER COLUMN prediction_direction DROP DEFAULT,
  ALTER COLUMN prediction_confidence DROP DEFAULT,
  ALTER COLUMN overall_accuracy DROP DEFAULT,
  ALTER COLUMN total_predictions DROP DEFAULT,
  ALTER COLUMN bullish_accuracy DROP DEFAULT,
  ALTER COLUMN bearish_accuracy DROP DEFAULT,
  ALTER COLUMN self_critique DROP DEFAULT,
  ALTER COLUMN speculations DROP DEFAULT,
  ALTER COLUMN wisdom_consensus DROP DEFAULT,
  ALTER COLUMN evolved_generation DROP DEFAULT,
  ALTER COLUMN evolved_win_rate DROP DEFAULT,
  ALTER COLUMN full_state DROP DEFAULT,
  ALTER COLUMN live_pulse DROP DEFAULT,
  ALTER COLUMN is_lighthouse DROP DEFAULT,
  ALTER COLUMN dreams DROP DEFAULT,
  ALTER COLUMN exit_targets DROP DEFAULT,
  ALTER COLUMN reflection DROP DEFAULT,
  ALTER COLUMN civilization_actions DROP DEFAULT,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT brain_states_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT brain_states_no_generated_values_check
    CHECK (generated_values = false);

DROP POLICY "Anyone can read brain states" ON public.brain_states;
CREATE POLICY "Users can read own brain states"
  ON public.brain_states FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE INDEX brain_states_user_source_time_idx
  ON public.brain_states (user_id, source_timestamp DESC);

ALTER TABLE public.calibration_trades
  ALTER COLUMN entry_time DROP DEFAULT,
  ALTER COLUMN qgita_tier DROP DEFAULT,
  ALTER COLUMN exchange DROP DEFAULT,
  ALTER COLUMN regime DROP DEFAULT,
  ALTER COLUMN is_forced DROP DEFAULT,
  ALTER COLUMN metadata DROP DEFAULT,
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN exit_source_id text,
  ADD COLUMN exit_source_timestamp timestamptz,
  ADD COLUMN exit_order_id text,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT calibration_trades_truth_status_check CHECK (truth_status = 'live'),
  ADD CONSTRAINT calibration_trades_no_generated_values_check CHECK (generated_values = false),
  ADD CONSTRAINT calibration_trades_exit_provenance_check CHECK (
    exit_time IS NULL OR (
      exit_source_id IS NOT NULL AND exit_source_timestamp IS NOT NULL AND exit_order_id IS NOT NULL
    )
  );

DROP POLICY "Authenticated users can read calibration_trades" ON public.calibration_trades;
CREATE POLICY "Users can read own calibration trades"
  ON public.calibration_trades FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE INDEX calibration_trades_user_exit_time_idx
  ON public.calibration_trades (user_id, exit_time DESC);

ALTER TABLE public.kelly_computation_states
  ALTER COLUMN timestamp DROP DEFAULT,
  ALTER COLUMN total_trades DROP DEFAULT,
  ALTER COLUMN winning_trades DROP DEFAULT,
  ALTER COLUMN losing_trades DROP DEFAULT,
  ALTER COLUMN win_rate DROP DEFAULT,
  ALTER COLUMN avg_win DROP DEFAULT,
  ALTER COLUMN avg_loss DROP DEFAULT,
  ALTER COLUMN win_loss_ratio DROP DEFAULT,
  ALTER COLUMN kelly_fraction DROP DEFAULT,
  ALTER COLUMN kelly_half DROP DEFAULT,
  ALTER COLUMN kelly_quarter DROP DEFAULT,
  ALTER COLUMN recommended_position_pct DROP DEFAULT,
  ALTER COLUMN max_position_pct DROP DEFAULT,
  ALTER COLUMN min_position_pct DROP DEFAULT,
  ALTER COLUMN metadata DROP DEFAULT,
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT kelly_states_truth_status_check CHECK (truth_status = 'real_derived'),
  ADD CONSTRAINT kelly_states_no_generated_values_check CHECK (generated_values = false),
  ADD CONSTRAINT kelly_states_observed_sample_check CHECK (
    total_trades > 0 AND winning_trades > 0 AND losing_trades > 0
    AND avg_win > 0 AND avg_loss > 0
  );

DROP POLICY "Authenticated users can read kelly_computation_states"
  ON public.kelly_computation_states;
CREATE POLICY "Users can read own Kelly states"
  ON public.kelly_computation_states FOR SELECT TO authenticated
  USING (auth.uid() = user_id);
CREATE INDEX kelly_states_user_source_time_idx
  ON public.kelly_computation_states (user_id, source_timestamp DESC);

-- QGITA is a real-derived market calculation. Physical frequency and a
-- coherence boost are not inputs to that calculation and must stay NULL rather
-- than being invented as 528 Hz / zero. Every row remains attributable to the
-- authenticated owner and the provider observation from which it was derived.
ALTER TABLE public.qgita_signal_states
  ALTER COLUMN timestamp DROP DEFAULT,
  ALTER COLUMN signal_type DROP DEFAULT,
  ALTER COLUMN strength DROP DEFAULT,
  ALTER COLUMN confidence DROP DEFAULT,
  ALTER COLUMN coherence_boost DROP DEFAULT,
  ALTER COLUMN coherence_boost DROP NOT NULL,
  ALTER COLUMN phase DROP DEFAULT,
  ALTER COLUMN frequency DROP DEFAULT,
  ALTER COLUMN frequency DROP NOT NULL,
  ALTER COLUMN metadata DROP DEFAULT,
  ALTER COLUMN tier DROP DEFAULT,
  ALTER COLUMN curvature DROP DEFAULT,
  ALTER COLUMN curvature_direction DROP DEFAULT,
  ALTER COLUMN ftcp_detected DROP DEFAULT,
  ALTER COLUMN golden_ratio_score DROP DEFAULT,
  ALTER COLUMN lighthouse_l DROP DEFAULT,
  ALTER COLUMN is_lhe DROP DEFAULT,
  ALTER COLUMN lighthouse_threshold DROP DEFAULT,
  ALTER COLUMN linear_coherence DROP DEFAULT,
  ALTER COLUMN nonlinear_coherence DROP DEFAULT,
  ALTER COLUMN cross_scale_coherence DROP DEFAULT,
  ALTER COLUMN anomaly_pointer DROP DEFAULT,
  ALTER COLUMN reasoning DROP DEFAULT,
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT qgita_states_truth_status_check CHECK (truth_status = 'real_derived'),
  ADD CONSTRAINT qgita_states_no_generated_values_check CHECK (generated_values = false),
  ADD CONSTRAINT qgita_states_metadata_provenance_check CHECK (
    metadata->>'truth_status' = truth_status
    AND metadata->>'source_id' = source_id
    AND (metadata->>'source_timestamp')::timestamptz = source_timestamp
    AND metadata->>'generated_values' = 'false'
  );

DROP POLICY "Authenticated users can read qgita_signal_states"
  ON public.qgita_signal_states;
CREATE POLICY "Users can read own QGITA states"
  ON public.qgita_signal_states FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

-- Hunt observations are provider-derived market evidence. These tables are
-- currently empty, so require provenance before the first production row.
ALTER TABLE public.hunt_targets
  ADD COLUMN truth_status text NOT NULL CHECK (truth_status = 'real_derived'),
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false CHECK (generated_values = false);

ALTER TABLE public.hunt_scans
  ADD COLUMN truth_status text NOT NULL CHECK (truth_status = 'real_derived'),
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false CHECK (generated_values = false);

DROP POLICY "Service manages hunt targets" ON public.hunt_targets;
CREATE POLICY "Service role manages hunt targets"
  ON public.hunt_targets FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY "Service manages hunt scans" ON public.hunt_scans;
CREATE POLICY "Service role manages hunt scans"
  ON public.hunt_scans FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE public.twap_orders
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL CHECK (truth_status = 'live'),
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false CHECK (generated_values = false);

ALTER TABLE public.twap_sub_orders
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL CHECK (truth_status = 'live'),
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL DEFAULT false CHECK (generated_values = false);

DROP POLICY "Users view own TWAP orders" ON public.twap_orders;
CREATE POLICY "Users view own TWAP orders"
  ON public.twap_orders FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY "Users view own TWAP sub-orders" ON public.twap_sub_orders;
CREATE POLICY "Users view own TWAP sub-orders"
  ON public.twap_sub_orders FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE UNIQUE INDEX qgita_states_user_temporal_id_idx
  ON public.qgita_signal_states (user_id, temporal_id);

-- Ecosystem snapshots are measurements, not a place to synthesize a healthy
-- dashboard through database defaults. Production preflight found zero rows.
ALTER TABLE public.ecosystem_snapshots
  ALTER COLUMN timestamp DROP DEFAULT,
  ALTER COLUMN systems_online DROP DEFAULT,
  ALTER COLUMN total_systems DROP DEFAULT,
  ALTER COLUMN hive_mind_coherence DROP DEFAULT,
  ALTER COLUMN bus_consensus DROP DEFAULT,
  ALTER COLUMN bus_confidence DROP DEFAULT,
  ALTER COLUMN json_enhancements_loaded DROP DEFAULT,
  ALTER COLUMN system_states DROP DEFAULT,
  ADD COLUMN user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN truth_status text NOT NULL,
  ADD COLUMN source_id text NOT NULL,
  ADD COLUMN source_event_id text NOT NULL,
  ADD COLUMN source_timestamp timestamptz NOT NULL,
  ADD COLUMN generated_values boolean NOT NULL,
  ADD CONSTRAINT ecosystem_snapshots_truth_status_check
    CHECK (truth_status IN ('live', 'real_derived')),
  ADD CONSTRAINT ecosystem_snapshots_generated_values_check
    CHECK (generated_values = false),
  ADD CONSTRAINT ecosystem_snapshots_system_count_check
    CHECK (systems_online >= 0 AND total_systems > 0 AND systems_online <= total_systems),
  ADD CONSTRAINT ecosystem_snapshots_coherence_check
    CHECK (hive_mind_coherence >= 0 AND hive_mind_coherence <= 1),
  ADD CONSTRAINT ecosystem_snapshots_confidence_check
    CHECK (bus_confidence >= 0 AND bus_confidence <= 1);

CREATE UNIQUE INDEX ecosystem_snapshots_source_event_idx
  ON public.ecosystem_snapshots (user_id, source_id, source_event_id);

CREATE INDEX ecosystem_snapshots_user_source_timestamp_idx
  ON public.ecosystem_snapshots (user_id, source_timestamp DESC);

DROP POLICY "Service can insert ecosystem_snapshots" ON public.ecosystem_snapshots;
CREATE POLICY "Service role inserts ecosystem snapshots"
  ON public.ecosystem_snapshots FOR INSERT TO service_role WITH CHECK (true);
DROP POLICY "Authenticated users can read ecosystem_snapshots" ON public.ecosystem_snapshots;
CREATE POLICY "Users read own ecosystem snapshots"
  ON public.ecosystem_snapshots FOR SELECT TO authenticated USING (auth.uid() = user_id);
