"""
The Payroll Journal — the open pay roster lands on the books, balanced.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

``uk_payroll_reference.payslip_breakdown`` computes a payslip from published
rates; this module posts it as one balanced journal entry on the client's
double-entry books:

    debit  6000 Gross wages          (the cost of the work)
    debit  6100 Employer's NI        (the cost of employing)
    credit 2200 PAYE/NI control      (what is owed to HMRC: tax + both NIs)
    credit 1000 Bank                 (what the employee takes home)

Balanced by construction — gross + employer NI equals HMRC's slice plus net
pay — and the ledger verifies it anyway, because the doctrine is verify,
never assume. The payslip's own source note travels into the entry memo.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict

from aureon.accounting.client_ledger import ClientLedger, Posting

__all__ = ["post_payslip"]


def post_payslip(ledger: ClientLedger, breakdown: Dict[str, Any],
                 employee_ref: str, when: float | None = None) -> str | None:
    """Post one computed payslip as a balanced journal entry.

    ``breakdown`` is the dict from ``payslip_breakdown`` — this function adds
    no numbers of its own; it only arranges the roster's figures on the books.
    """
    gross = int(breakdown["gross_pennies"])
    tax = int(breakdown["income_tax_pennies"])
    employee_ni = int(breakdown["employee_ni_pennies"])
    employer_ni = int(breakdown["employer_ni_pennies"])
    net = int(breakdown["net_pay_pennies"])
    hmrc = tax + employee_ni + employer_ni

    postings = [
        Posting("6000", debit_pennies=gross, memo=f"gross pay {employee_ref}"),
        Posting("6100", debit_pennies=employer_ni, memo=f"employer NI {employee_ref}"),
        Posting("2200", credit_pennies=hmrc,
                memo=f"PAYE+NI due to HMRC ({breakdown.get('tax_year', '?')})"),
        Posting("1000", credit_pennies=net, memo=f"net pay {employee_ref}"),
    ]
    return ledger.post(
        f"payroll: {employee_ref} ({breakdown.get('tax_year', '?')}, "
        f"cat {breakdown.get('ni_category', '?')})",
        postings, reference=f"payslip:{employee_ref}", when=when)
