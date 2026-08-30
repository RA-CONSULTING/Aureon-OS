from __future__ import annotations

from datetime import date
from pathlib import Path

from Kings_Accounting_Suite.tools.company_house_tax_audit import (
    build_assessments,
    companies_house_late_penalty,
    inventory_statement_coverage,
    parse_companies_house_profile,
    parse_statement_span,
)


def test_parse_companies_house_profile_marks_overdue_and_strike_off() -> None:
    html = """
    <h1>EXAMPLE TRADING LTD</h1>
    Company number 00000000
    Registered office address 123 Test Street
    Company status Active -- Active proposal to strike off
    Company type Private limited Company
    Incorporated on 25 April 2023
    Accounts overdue
    Next accounts made up to 30 April 2025 due by 31 January 2026
    Last accounts made up to 30 April 2024
    Next statement date 25 April 2026 due by 9 May 2026
    Last statement dated 25 April 2025
    """

    profile = parse_companies_house_profile(html, source_url="https://example.test")

    assert profile.company_name == "EXAMPLE TRADING LTD"
    assert profile.company_number == "00000000"
    assert profile.accounts_overdue is True
    assert profile.active_proposal_to_strike_off is True
    assert profile.next_accounts_made_up_to == "30 April 2025"
    assert profile.accounts_due_by == "31 January 2026"
    assert profile.confirmation_statement_due_by == "9 May 2026"


def test_statement_span_parses_monthly_and_range_names() -> None:
    assert parse_statement_span("Statement__GBP_20240501-20240531 (1).pdf") == (
        date(2024, 5, 1),
        date(2024, 5, 31),
    )
    assert parse_statement_span("account-statement_12-Sep-2024_31-Dec-2024.pdf") == (
        date(2024, 9, 12),
        date(2024, 12, 31),
    )


def test_statement_coverage_detects_complete_period(tmp_path: Path) -> None:
    for month in range(5, 13):
        (tmp_path / f"Statement__GBP_2024{month:02d}01-2024{month:02d}28.pdf").write_text("x")
    for month in range(1, 5):
        (tmp_path / f"Statement__GBP_2025{month:02d}01-2025{month:02d}28.pdf").write_text("x")

    coverage = inventory_statement_coverage(tmp_path, "2024-05-01", "2025-04-30")

    assert coverage.complete is True
    assert coverage.missing_months == []
    assert coverage.covered_months[0] == "2024-05"
    assert coverage.covered_months[-1] == "2025-04"


def test_deadline_assessments_show_overdue_on_2026_05_08() -> None:
    assessments = build_assessments("2025-04-30", date(2026, 5, 8))
    by_name = {item.name: item for item in assessments}

    assert by_name["Companies House annual accounts"].status == "overdue"
    assert by_name["Companies House annual accounts"].days_overdue == 97
    assert by_name["HMRC Corporation Tax payment"].due_date == "2026-02-01"
    assert by_name["HMRC Corporation Tax payment"].days_overdue == 96
    assert by_name["HMRC Company Tax Return / CT600"].days_overdue == 8


def test_companies_house_penalty_tiers() -> None:
    assert companies_house_late_penalty(0) == "none estimated"
    assert companies_house_late_penalty(1) == "private company tier: GBP 150"
    assert companies_house_late_penalty(40) == "private company tier: GBP 375"
    assert companies_house_late_penalty(100) == "private company tier: GBP 750"
    assert companies_house_late_penalty(200) == "private company tier: GBP 1,500"
