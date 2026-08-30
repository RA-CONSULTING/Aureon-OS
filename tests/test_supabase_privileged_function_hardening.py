'''Static contract for the privileged-function grant/search-path migration.'''

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / 'supabase' / 'migrations'
PRODUCTION_RECEIPT = (
    ROOT / 'docs' / 'SUPABASE_PRODUCTION_FUNCTION_HARDENING_20260811.json'
)

SERVICE_ONLY = {
    'public.handle_new_user()',
    'public.handle_updated_at()',
    'public.log_performance_metric(text,text,numeric,integer,text)',
    'public.update_payment_updated_at()',
    'public.update_sentinel_updated_at()',
    'public.update_spiritual_user_stats()',
    'public.update_updated_at_column()',
}
AUTH_POLICY_HELPERS = {
    'public.has_role(uuid,public.app_role)',
    'public.session_belongs_to_current_user(uuid)',
}


def _sql() -> str:
    matches = list(
        MIGRATIONS.glob('*_harden_privileged_function_execution.sql')
    )
    assert len(matches) == 1
    return matches[0].read_text(encoding='utf-8').lower()


def _signature_groups(sql: str) -> list[set[str]]:
    arrays = re.findall(
        r'foreach\s+function_signature\s+in\s+array\s+array\[(.*?)\]'
        r'\s+loop',
        sql,
        flags=re.DOTALL,
    )
    return [set(re.findall(r"'([^']+)'", block)) for block in arrays]


def test_exact_function_groups_are_pinned_and_missing_functions_are_skipped() -> None:
    sql = _sql()

    assert _signature_groups(sql) == [SERVICE_ONLY, AUTH_POLICY_HELPERS]
    assert sql.count('to_regprocedure(function_signature)') == 2
    assert sql.count('continue;') == 2


def test_every_existing_function_gets_a_fixed_search_path() -> None:
    sql = _sql()

    assert sql.count(
        "'alter function %s set search_path to pg_catalog, public'"
    ) == 2


def test_service_only_and_policy_helper_grants_are_fail_closed() -> None:
    sql = _sql()

    assert (
        "'revoke execute on function %s from public, anon, authenticated'"
        in sql
    )
    assert "'grant execute on function %s to service_role'" in sql
    assert "'revoke execute on function %s from public, anon'" in sql
    assert (
        "'grant execute on function %s to authenticated, service_role'"
        in sql
    )


def test_migration_changes_metadata_only_and_cannot_replace_function_bodies() -> None:
    sql = _sql()

    assert 'create function' not in sql
    assert 'create or replace function' not in sql
    assert 'drop function' not in sql
    assert 'security definer' not in sql
    assert 'grant execute' in sql
    assert 'revoke execute' in sql


def test_production_provider_readback_is_exact_and_content_free() -> None:
    receipt = json.loads(PRODUCTION_RECEIPT.read_text(encoding='utf-8'))

    assert receipt['schema'] == (
        'aureon.supabase.production_function_hardening.v1'
    )
    assert receipt['project_id'] == 'siihxcwetdjdsrfdexmb'
    assert receipt['provider_migration'] == {
        'name': 'harden_privileged_function_execution',
        'version': '20260811214358',
    }
    assert receipt['source_migration'] == (
        'supabase/migrations/'
        '20260811214358_harden_privileged_function_execution.sql'
    )
    assert set(receipt['target_functions']) == SERVICE_ONLY | AUTH_POLICY_HELPERS
    assert receipt['sandbox_validation'] == {
        'matching_function_count': 0,
        'migration_applied': True,
        'project_id': 'bswwejakhfojgalhefjy',
        'security_advisor_finding_count': 0,
    }
    readback = receipt['readback']
    assert readback['function_count'] == 9
    assert readback['fixed_search_path_count'] == 9
    assert readback['anon_execute_false_count'] == 9
    assert readback['authenticated_execute_false_count'] == 7
    assert readback['service_role_execute_true_count'] == 9
    assert set(readback['authenticated_execute_true_functions']) == (
        AUTH_POLICY_HELPERS
    )
    assert readback['anonymous_security_definer_advisor_finding_count'] == 0
    assert set(
        readback['intentional_authenticated_security_definer_advisor_findings']
    ) == AUTH_POLICY_HELPERS
    assert receipt['row_content_read'] is False
    assert receipt['row_content_changed'] is False
    assert receipt['provider_applied_and_read_back'] is True
