-- Tables the row-level-security migration hardens. No measured rows are invented.
CREATE TABLE IF NOT EXISTS public.schumann_resonance_data (
  id bigserial PRIMARY KEY,
  observed_at timestamptz NOT NULL DEFAULT now(),
  owner_id text NOT NULL,
  frequency_hz double precision,
  source text NOT NULL
);
