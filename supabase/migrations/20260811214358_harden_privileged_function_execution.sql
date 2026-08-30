-- Tighten privileged and trigger functions without changing their bodies.
-- Provider migration ledger version: 20260811214358.
-- Fresh environments may not contain every live-only legacy function, so each
-- exact signature is hardened only when it exists.

do $$
declare
  function_signature text;
begin
  foreach function_signature in array array[
    'public.handle_new_user()',
    'public.handle_updated_at()',
    'public.log_performance_metric(text,text,numeric,integer,text)',
    'public.update_payment_updated_at()',
    'public.update_sentinel_updated_at()',
    'public.update_spiritual_user_stats()',
    'public.update_updated_at_column()'
  ]
  loop
    if to_regprocedure(function_signature) is null then
      continue;
    end if;

    execute format(
      'alter function %s set search_path to pg_catalog, public',
      function_signature
    );
    execute format(
      'revoke execute on function %s from public, anon, authenticated',
      function_signature
    );
    execute format(
      'grant execute on function %s to service_role',
      function_signature
    );
  end loop;

  foreach function_signature in array array[
    'public.has_role(uuid,public.app_role)',
    'public.session_belongs_to_current_user(uuid)'
  ]
  loop
    if to_regprocedure(function_signature) is null then
      continue;
    end if;

    execute format(
      'alter function %s set search_path to pg_catalog, public',
      function_signature
    );
    execute format(
      'revoke execute on function %s from public, anon',
      function_signature
    );
    execute format(
      'grant execute on function %s to authenticated, service_role',
      function_signature
    );
  end loop;
end
$$;
