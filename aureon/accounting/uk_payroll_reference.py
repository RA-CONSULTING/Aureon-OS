"""
The Open Pay Roster — published UK pay-type figures, every constant sourced.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The accounting body needs the UK's pay machinery as DATA: income-tax bands
(rUK and Scotland), National Insurance classes and category letters, the
employment allowance, auto-enrolment bounds. This module is that roster —
registry-as-data, each figure a published GOV.UK rate for the 2025/26 tax
year, computed deterministically in integer pennies.

HONESTY BOUNDARY: this is a reference SNAPSHOT of published rates, suitable
for draft calculations and benchmarks. It is not a filing authority — verify
against the current GOV.UK tables before anything is submitted to HMRC.

Sources (published rates, 2025/26 tax year):
* Income tax rates and Personal Allowance — gov.uk/income-tax-rates
* Scottish income tax — gov.uk/scottish-income-tax
* NI rates and categories — gov.uk/national-insurance-rates-letters
* Employer NI / employment allowance — gov.uk/employer-national-insurance-rates
* Auto-enrolment qualifying earnings — thepensionsregulator.gov.uk

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

__all__ = [
    "TAX_YEAR", "SOURCE_NOTE", "PERSONAL_ALLOWANCE_P",
    "RUK_BANDS", "SCOTTISH_BANDS", "NI_EMPLOYEE", "NI_EMPLOYER",
    "NI_CATEGORY_LETTERS", "AUTO_ENROLMENT", "payslip_breakdown",
]

TAX_YEAR = "2025/26"
SOURCE_NOTE = (
    "Published GOV.UK rates for the 2025/26 UK tax year — a reference snapshot "
    "for draft calculations and benchmarks, NOT a filing authority. Verify "
    "against current GOV.UK tables before submitting anything to HMRC."
)

#: Standard Personal Allowance, pennies/year. Tapers £1 per £2 above £100,000.
PERSONAL_ALLOWANCE_P = 12_570_00
_PA_TAPER_START_P = 100_000_00

#: rUK (England/Wales/NI) bands over TAXABLE income (above the allowance):
#: (upper bound of band in pennies or None for no ceiling, rate).
RUK_BANDS: List[Tuple[Any, float]] = [
    (37_700_00, 0.20),   # basic
    (112_570_00, 0.40),  # higher (to £125,140 gross)
    (None, 0.45),        # additional
]

#: Scottish bands over TAXABLE income (above the allowance), 2025/26.
SCOTTISH_BANDS: List[Tuple[Any, float]] = [
    (2_827_00, 0.19),    # starter   (to £15,397 gross)
    (14_921_00, 0.20),   # basic     (to £27,491 gross)
    (31_092_00, 0.21),   # intermediate (to £43,662 gross)
    (62_430_00, 0.42),   # higher    (to £75,000 gross)
    (112_570_00, 0.45),  # advanced  (to £125,140 gross)
    (None, 0.48),        # top
]

#: Class 1 employee NI, annual thresholds in pennies.
NI_EMPLOYEE: Dict[str, Any] = {
    "primary_threshold_p": 12_570_00,
    "upper_earnings_limit_p": 50_270_00,
    "main_rate": 0.08,
    "upper_rate": 0.02,
    "married_reduced_rate": 0.0185,  # category B below UEL
}

#: Class 1 employer (secondary) NI, 2025/26 — secondary threshold £5,000,
#: rate 15%, employment allowance £10,500 for eligible employers.
NI_EMPLOYER: Dict[str, Any] = {
    "secondary_threshold_p": 5_000_00,
    "rate": 0.15,
    "employment_allowance_p": 10_500_00,
    # relief categories pay 0% employer NI up to this limit (then 15%)
    "relief_upper_limit_p": 50_270_00,
}

#: NI category letters — the roster the pay engine dispatches on.
NI_CATEGORY_LETTERS: Dict[str, str] = {
    "A": "standard employee",
    "B": "married women/widows with a valid reduced-rate election",
    "C": "employee over State Pension age (no employee NI; employer still pays)",
    "H": "apprentice under 25 (employer relief to the upper limit)",
    "J": "employee deferring NI (pays 2% throughout)",
    "M": "employee under 21 (employer relief to the upper limit)",
    "V": "veteran in first year of civilian employment (employer relief)",
    "Z": "under 21 who is also deferring (2%; employer relief)",
}
_EMPLOYER_RELIEF_CATEGORIES = {"H", "M", "V", "Z"}
_EMPLOYEE_NIL_CATEGORIES = {"C"}
_EMPLOYEE_DEFERRED_CATEGORIES = {"J", "Z"}

#: Auto-enrolment qualifying earnings band and statutory minimums, 2025/26.
AUTO_ENROLMENT: Dict[str, Any] = {
    "lower_p": 6_240_00,
    "upper_p": 50_270_00,
    "minimum_total": 0.08,
    "minimum_employer": 0.03,
}


def _personal_allowance(gross_p: int) -> int:
    """Standard allowance with the published £1-per-£2 taper above £100k."""
    if gross_p <= _PA_TAPER_START_P:
        return PERSONAL_ALLOWANCE_P
    reduction = (gross_p - _PA_TAPER_START_P) // 2
    return max(0, PERSONAL_ALLOWANCE_P - int(reduction))


def _banded_tax(taxable_p: int, bands: List[Tuple[Any, float]]) -> int:
    tax = 0.0
    lower = 0
    for upper, rate in bands:
        if upper is None or taxable_p < upper:
            tax += max(0, taxable_p - lower) * rate
            break
        tax += (upper - lower) * rate
        lower = upper
    return int(round(tax))


def payslip_breakdown(gross_annual_pennies: int, *, scotland: bool = False,
                      ni_category: str = "A") -> Dict[str, Any]:
    """Deterministic annual payslip on the published roster, integer pennies.

    Returns income tax, employee NI, employer NI, net pay, and the employer's
    total cost — plus the source note, because a draft is a draft.
    """
    gross = int(gross_annual_pennies)
    if gross < 0:
        raise ValueError("gross pay cannot be negative")
    cat = str(ni_category).upper()
    if cat not in NI_CATEGORY_LETTERS:
        raise ValueError(
            f"unknown NI category {ni_category!r} — roster: {sorted(NI_CATEGORY_LETTERS)}")

    allowance = _personal_allowance(gross)
    taxable = max(0, gross - allowance)
    income_tax = _banded_tax(taxable, SCOTTISH_BANDS if scotland else RUK_BANDS)

    # employee NI
    pt = NI_EMPLOYEE["primary_threshold_p"]
    uel = NI_EMPLOYEE["upper_earnings_limit_p"]
    if cat in _EMPLOYEE_NIL_CATEGORIES:
        employee_ni = 0
    elif cat in _EMPLOYEE_DEFERRED_CATEGORIES:
        employee_ni = int(round(max(0, gross - pt) * NI_EMPLOYEE["upper_rate"]))
    else:
        main = NI_EMPLOYEE["married_reduced_rate"] if cat == "B" else NI_EMPLOYEE["main_rate"]
        band = max(0, min(gross, uel) - pt)
        above = max(0, gross - uel)
        employee_ni = int(round(band * main + above * NI_EMPLOYEE["upper_rate"]))

    # employer NI (before any employment allowance the employer may claim)
    st = NI_EMPLOYER["secondary_threshold_p"]
    if cat in _EMPLOYER_RELIEF_CATEGORIES:
        employer_base = max(0, gross - NI_EMPLOYER["relief_upper_limit_p"])
    else:
        employer_base = max(0, gross - st)
    employer_ni = int(round(employer_base * NI_EMPLOYER["rate"]))

    return {
        "tax_year": TAX_YEAR,
        "scotland": bool(scotland),
        "ni_category": cat,
        "gross_pennies": gross,
        "personal_allowance_pennies": allowance,
        "income_tax_pennies": income_tax,
        "employee_ni_pennies": employee_ni,
        "employer_ni_pennies": employer_ni,
        "net_pay_pennies": gross - income_tax - employee_ni,
        "employer_total_cost_pennies": gross + employer_ni,
        "source_note": SOURCE_NOTE,
    }
