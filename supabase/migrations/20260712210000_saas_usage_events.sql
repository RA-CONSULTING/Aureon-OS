-- Aureon SaaS Phase 6C — platform usage metering (record-only, no debits).
-- Written by the Python gateway's metering flusher via PostgREST with the
-- service-role key. Users can read their own events; there are deliberately
-- NO client write policies (service-role bypasses RLS) — unlike the earlier
-- permissive USING(true) patterns.

CREATE TABLE IF NOT EXISTS public.saas_usage_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid,                                   -- auth.users id; NULL = unattributed
  kind text NOT NULL CHECK (kind IN ('api_request', 'llm_tokens', 'fee_charge')),
  route text NOT NULL DEFAULT '',
  method text NOT NULL DEFAULT '',
  status smallint NOT NULL DEFAULT 0,
  quantity numeric NOT NULL DEFAULT 1,
  unit text NOT NULL DEFAULT 'request',             -- 'request' | 'tokens' | 'gbp'
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saas_usage_events_tenant_time
  ON public.saas_usage_events (tenant_id, created_at DESC);

ALTER TABLE public.saas_usage_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage events"
  ON public.saas_usage_events
  FOR SELECT
  USING (auth.uid() = tenant_id);
