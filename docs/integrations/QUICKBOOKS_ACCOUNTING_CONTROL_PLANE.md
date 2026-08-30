# Aureon QuickBooks Accounting Control Plane

## Outcome

`Kings_Accounting_Suite/tools/quickbooks_accounting_integration.py` makes
QuickBooks Online a downstream projection and read-back adapter for Aureon.
Aureon OS is always the canonical accounting/evidence authority. The first live
pass is read-only: company identity, chart of accounts, customers, vendors,
balance sheet, profit and loss, trial balance, and cash flow. Each API response
produces a payload-free SHA-256 audit receipt.

The invariant is:

`Aureon canonical event + evidence -> approved QBO projection -> QBO read-back -> Aureon reconciliation`

QuickBooks imports, suggestions, balances, and webhook events are observations.
They can open a reconciliation task but cannot overwrite an Aureon decision.

`Kings_Accounting_Suite/tools/aureon_accounting_control_plane.py` is the
authoritative journal layer behind the adapter. It provides:

- evidence-bound GBP double-entry postings;
- an append-only JSONL hash chain with full-chain verification;
- a separate owner/accountant approval record;
- deterministic, payload-digest-bound QuickBooks projection intents;
- provider-object and SyncToken verification on API read-back; and
- digest-only QuickBooks observation tasks that can never create or mutate a
  canonical posting; and
- source-allowlisted, digest-only Aureon grant-ledger, Companies House, Gmail,
  Drive, bank, HMRC, Intuit Developer, and Xero evidence observations that
  cannot create a posting, queue a projection, or change a compliance state.

The runtime journal and status live under
`Kings_Accounting_Suite/output/accounting_control/`, which remains private and
git-ignored. Aureon's accounting context reads the secret-free status and makes
it available through `/accounts status`, `/accounts quickbooks`, ThoughtBus,
and the accounting vault.

QuickBooks is not an HMRC or Companies House filing substitute. Company Tax
Returns now require suitable commercial filing software, and filing/payment
actions stay behind the existing manual review and provider-receipt boundaries.

## Security and authority

- OAuth uses the Accounting scope and a signed, ten-minute state value.
- Access and refresh tokens stay in memory or a Windows DPAPI vault under the
  current Windows user. `.aureon/` is git-ignored.
- Logs and audit receipts redact secrets and do not persist accounting payloads.
- QuickBooks writes are off by default.
- A write requires an immutable Aureon canonical accounting event with source
  evidence SHA-256 digests, an explicit runtime switch, and an expiring HMAC
  approval bound to that event, company realm, operation, entity, exact payload
  digest, and idempotency key.
- There is no CLI command for an accounting write.
- HMRC submissions, Companies House filings, payments, payroll, billing, and
  bank changes remain manual-only.

## Intuit developer setup

Intuit developer enrolment presents a binding Terms of Service agreement.
Automation must not tick or submit it. On 31 July 2026 the owner independently
accepted the terms, created the development app, and saved the exact localhost
redirect URI. Aureon records this as owner action, not an automation action.

The development credentials are now secured with Windows DPAPI. OAuth is still
pending: Intuit reported no sandbox companies, then its sandbox creator returned
the same provider error for two UK attempts and one US attempt. This is a test
infrastructure gate; it is not a live-company connection and no accounting
mutation was attempted.

The live QuickBooks company is a separate production route. Provider emails now
evidence a QuickBooks Online Advanced/Payroll Elite subscription with payment
scheduled (not settlement) and Zempler bank-sharing consent with transaction
import read-back still pending. These observations prove neither reconciled
transactions nor an API connection. Intuit requires production credentials for
live companies; production credentials are available only after the production
app details and assessment are approved. Production also requires a public HTTPS
redirect URI plus public policy, launch, connect/reconnect, and disconnect URLs.

Aureon binds client credentials and OAuth tokens to their environment. A sandbox
vault cannot be used with a production configuration, and production localhost
redirects are rejected. Existing sandbox vault filenames remain compatible;
production defaults use distinct `quickbooks_production_*` DPAPI vaults.

1. Create an Intuit Developer app and enable the QuickBooks Online Accounting
   scope.
2. Register the exact OAuth redirect URI for the environment.
3. Test with an Intuit sandbox before production.
4. Put the values in a local `.env` or approved secret manager:

   - `QUICKBOOKS_CLIENT_ID`
   - `QUICKBOOKS_CLIENT_SECRET`
   - `QUICKBOOKS_CLIENT_CREDENTIAL_VAULT=.aureon/quickbooks_client_credentials.dpapi.json`
   - `QUICKBOOKS_REDIRECT_URI=http://localhost:8765/callback`
   - `QUICKBOOKS_ENVIRONMENT=sandbox`
   - `QUICKBOOKS_REALM_ID` optionally after the company connection

For the live company, set `QUICKBOOKS_ENVIRONMENT=production`, use the distinct
production credential/token vault paths in `.env.example`, and register an HTTPS
callback. The loopback `oauth-connect-local` command is sandbox-only. The hosted
callback must pass its short-lived values to `oauth-exchange` without logging or
persisting the authorization code.

For `sync-read-only`, the secured token vault is authoritative for the realm ID.
An explicitly configured realm is accepted only when it matches that vault.

Never commit `.env`, an OAuth callback code, a token, a DPAPI vault, or a live
accounting response.

The client ID and secret can be loaded once from the current process environment
and immediately encrypted under the current Windows user:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration credentials-save
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration credentials-status
```

With the exact development redirect URI registered in Intuit, the local flow
opens authorization, receives the callback without logging the code, validates
the signed state, exchanges the code, and writes tokens only to DPAPI:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration oauth-connect-local
```

For a controlled Chrome session, Aureon can keep the short-lived URL local and
avoid the Windows default browser. The URL file is removed when the callback
finishes or times out:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration oauth-connect-local `
  --no-open-browser `
  --authorization-url-path .aureon/quickbooks_oauth_authorization.url
```

## Commands

From the repository root:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration preflight `
  --active-grant-ledger "C:\Users\user\Aureon-OS\data\research\grants"
```

Generate the authorization URL:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration oauth-url
```

After the browser callback, place the short-lived callback values only in the
current process environment and exchange them:

```powershell
$env:QUICKBOOKS_AUTH_CODE = "<short-lived callback code>"
$env:QUICKBOOKS_RETURNED_STATE = "<returned state>"
$env:QUICKBOOKS_EXPECTED_STATE = "<state emitted by oauth-url>"
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration oauth-exchange `
  --realm-id "<returned realmId>"
Remove-Item Env:QUICKBOOKS_AUTH_CODE, Env:QUICKBOOKS_RETURNED_STATE, Env:QUICKBOOKS_EXPECTED_STATE
```

Run the controlled snapshot:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration sync-read-only `
  --start-date 2025-05-01 --end-date 2026-04-30
```

The command prints only the snapshot digest, section names, and audit location.
It does not print the accounting payload or tokens.

Verify Aureon's canonical journal hash chain and import the current secret-free
QuickBooks control-plane status as a non-authoritative reconciliation task:

```powershell
python -m Kings_Accounting_Suite.tools.aureon_accounting_control_plane verify
python -m Kings_Accounting_Suite.tools.aureon_accounting_control_plane observe-quickbooks-status
```

The observation command is idempotent for an unchanged QuickBooks status
receipt. It stores only digests in the canonical journal and creates no ledger
posting.

Other external evidence uses a private JSON receipt with schema
`aureon-evidence-observation-v1` and the same digest-only boundary:

```powershell
python -m Kings_Accounting_Suite.tools.aureon_accounting_control_plane `
  observe-evidence-file `
  --evidence-payload Kings_Accounting_Suite/output/accounting_control/evidence_observations/receipt.json
```

The source allowlist is closed. The journal stores the source classification,
observation type, external-reference digest, and payload digest—not the provider
message, bank transactions, tax identifiers, or Xero ledger data.

Record the current live-company production gate from a private, secret-free
evidence file:

```powershell
python -m Kings_Accounting_Suite.tools.quickbooks_accounting_integration `
  production-readiness `
  --evidence Kings_Accounting_Suite/output/quickbooks/production_readiness_evidence_20260802.json
python -m Kings_Accounting_Suite.tools.aureon_accounting_control_plane `
  observe-quickbooks-status
```

This readiness command cannot request production credentials, complete the
Intuit assessment, authorize OAuth, import transactions, or enable mutations. It
records which public URL, provider, OAuth, and CompanyInfo gates remain open.

Generate the privacy-minimised work queue after evidence changes:

```powershell
python -m Kings_Accounting_Suite.tools.aureon_accounting_reconciliation generate
```

The report maps the current evidence into fourteen accounting/compliance
workstreams. Every workstream defaults to no posting, no QuickBooks projection,
and no external compliance action. Aureon's runtime exposes the same read-only
view through `/accounts reconciliation`, ThoughtBus topic
`accounting.reconciliation.status`, and the accounting vault.

## Reconciliation order

1. Read back QBO `CompanyInfo` and match the legal entity/company number.
2. Preserve the Xero chart, trial balance, journals, open invoices/bills,
   contacts, and tax settings.
3. Agree the migration cut-off and opening balances with the accountant.
4. Reconcile Zempler, entity-owned Revolut records, SumUp reports, and every
   other confirmed company account or processor.
5. Reconcile VAT, PAYE, CIS, and Corporation Tax to live HMRC evidence. Historic
   letters or email summaries are evidence leads, not current balances.
6. Add grant/project tracking only from award/provider evidence. An application
   or unreceipted submission is not a grant asset or receivable.
7. Build R&D project evidence from eligible cost records; any tax claim remains
   accountant-reviewed and externally filed through suitable commercial
   software.

## Official references

- Intuit OAuth 2.0:
  <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0>
- Intuit Accounting API:
  <https://developer.intuit.com/app/developer/qbo/docs/get-started>
- Intuit production credentials and assessment:
  <https://developer.intuit.com/app/developer/qbo/docs/go-live/publish-app>
- Intuit production platform requirements:
  <https://developer.intuit.com/app/developer/qbo/docs/go-live/publish-app/platform-requirements>
- Intuit redirect URI requirements:
  <https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/set-redirect-uri>
- GOV.UK Company Tax Returns:
  <https://www.gov.uk/company-tax-returns>
- Companies House filing:
  <https://www.gov.uk/file-your-company-annual-accounts>
