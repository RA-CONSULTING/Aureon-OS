"""
The King's Court — the HNC accounting body, generalized for any business.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"The King counts every coin" — and now he counts them for any client, from a
micro-business file-drop to a corporation's ledger, on the same double-entry
doctrine the trading organism already trusts (``aureon/bots/king_ledger.py``).

Three organs, each honest to the bone:

* ``client_ledger``       — multi-client double-entry ledger on a UK SME chart;
                            every posting proves its own balance and records an
                            HNC coordination row (canonical Γ attached when the
                            field is live, ``None`` when dark — never invented).
* ``file_drop``           — the ingestion front door: real files in, normalized
                            transactions out; unrecognized rows land in suspense
                            (the accountant's honest bucket), malformed rows are
                            NAMED blockers, never guessed values.
* ``uk_payroll_reference``— the open pay-type roster: published UK PAYE and
                            National Insurance figures, every constant carrying
                            its source; a reference snapshot, not a filing
                            authority.

Gary Leckey · Aureon Institute · R&A Consulting (the benchmark client)
"""

from aureon.accounting.client_ledger import UK_SME_CHART, ClientLedger  # noqa: F401
from aureon.accounting.file_drop import ingest_file, registered_ingestors  # noqa: F401
from aureon.accounting.hmrc_mutation_boundary import (  # noqa: F401
    HMRCMutationHold,
    HMRCMutationRegistry,
    bind_hmrc_mutation_registry,
)
from aureon.accounting.uk_payroll_reference import payslip_breakdown  # noqa: F401
