-- Fail closed for legacy tables that were created in the exposed public schema
-- Provider migration ledger version: 20260811210525.
-- with broad default grants and no row-level security. These tables are consumed
-- by service-role Edge Functions; direct anon/authenticated access is not part of
-- the audited repository contract.
--
-- Some fresh/local environments do not contain these live-only legacy tables.
-- The migration therefore hardens every table that exists without inventing a
-- replacement schema. The accompanying contract test pins the complete target
-- list so drift cannot silently remove a production table from this boundary.

do $$
declare
  target_table text;
begin
  foreach target_table in array array[
    'backend_health_metrics',
    'backup_jobs',
    'backup_records',
    'backup_restore_logs',
    'celestial_data',
    'chart_annotations',
    'chart_data',
    'chat_messages',
    'dashboard_comments',
    'dashboard_configurations',
    'data_backups',
    'electromagnetic_data',
    'health_alert_events',
    'load_balancer_metrics',
    'optimization_recommendations',
    'performance_optimization_analysis',
    'predictive_scaling_models',
    'resource_allocation_history',
    'schumann_resonance_data',
    'server_correlation_analysis',
    'server_registry',
    'system_alerts'
  ]
  loop
    if to_regclass(format('public.%I', target_table)) is null then
      continue;
    end if;

    execute format(
      'alter table public.%I enable row level security',
      target_table
    );
    execute format(
      'revoke all privileges on table public.%I from public, anon, authenticated',
      target_table
    );
    execute format(
      'grant select, insert, update, delete on table public.%I to service_role',
      target_table
    );
    execute format(
      'drop policy if exists deny_direct_client_access on public.%I',
      target_table
    );
    execute format(
      'create policy deny_direct_client_access on public.%I '
      'for all to anon, authenticated using (false) with check (false)',
      target_table
    );
  end loop;
end
$$;
