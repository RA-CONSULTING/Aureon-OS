# Grant Account Creation Status

Prepared: 2026-07-05T16:17:38+01:00

Purpose: track external grant portal account setup for Gary Anthony Leckey / R&A Consulting and Brokerage Services Ltd / Aureon Institute. This file intentionally does not store passwords, verification codes, tokens, or recovery secrets.

## Aureon Env Persistence

Updated: 2026-07-05T16:17:38+01:00

Grant/account metadata has been persisted for Aureon runtime reuse in:

- `C:\Users\user\aureon-trading\.env`
- `C:\Users\user\aureon-trading\.env1.txt`
- `C:\Users\user\aureon-trading\.env.example`

The live env files now include the `AUREON_GRANT_` key block for applicant data, company data, work hub paths, InterTradeIreland submission confirmation, Invest NI route status, IFS/Next Wave account status, and EIC account status.

Credential policy:

- Plaintext grant portal passwords must not be stored in `.env` or `.env1.txt`.
- `AUREON_GRANT_IFS_PASSWORD_ENV_POLICY=do_not_store_plaintext_passwords_in_env`
- `AUREON_GRANT_IFS_PASSWORD_STORE=C:\Users\user\.aureon_grant_private\credentials`
- The private credential directory has been created, but no password has been generated or stored yet.

## Innovation Funding Service

Official route: https://apply-for-innovation-funding.service.gov.uk/application/create/start-application/2517

Target use: Next Wave: Breakthrough Wave 1 application.

Status: existing account signed in; Next Wave application record created.

Completed in browser:

- Started new Next Wave application account flow.
- Selected organisation as UK-based.
- Selected organisation type: Business.
- Searched Companies House using company number `NI696693`.
- Selected `R&A CONSULTING AND BROKERAGE SERVICES LTD`.
- Confirmed company details shown by the portal:
  - Registration number: NI696693
  - Registered address: 1 Quadrant Place, Belfast, BT12 4HX
- Filled account contact fields:
  - First name: Gary
  - Last name: Leckey
  - Phone: +447547743773
  - Email: gaxlec@gmail.com

Result:

- `gaxlec@gmail.com` already had an Innovation Funding Service account; new-account creation was not possible because the email was already registered.
- Sign-in succeeded using the approved standard grant-portal credential.
- New Next Wave application record created for `R&A CONSULTING AND BROKERAGE SERVICES LTD`.
- Application number: `10209601`.
- Application URL: https://apply-for-innovation-funding.service.gov.uk/application/10209601
- Competition: Next Wave: Breakthrough Wave 1.
- Deadline shown by portal: `11:00am Tuesday 11 August 2026`.
- Status shown by portal: `0% complete`, not submitted.

Credential handling:

- Plaintext grant portal passwords remain excluded from `.env` and `.env1.txt`.
- A Windows user-encrypted credential has been stored under `C:\Users\user\.aureon_grant_private\credentials`.
- Stored files:
  - `grant_portals_gaxlec_standard.xml`
  - `ifs_innovation_funding_service_gaxlec.xml`

## EU Funding & Tenders / EU Login

Target use: EIC Accelerator.

Status: registration created; email verification link opened; final password submit pending user action.

Completed in browser:

- Started EU Login from the EU Funding & Tenders Portal sign-in route.
- EU Login did not find an existing account for `gaxlec@gmail.com` at the email step.
- Created EU Login registration request for Gary Leckey using `gaxlec@gmail.com`.
- Gmail received the EU Login email from `Authentication Service <automated-notifications@nomail.ec.europa.eu>` with subject `Your password`.
- Opened the EU Login password-setup link from that email.
- Reached the `New password` page for EU Login user ID `n00n9i0d`.
- Prefilled the two password fields with the approved standard grant-portal credential.

Current blocker:

- The final EU Login password `Submit` button is visible in Chrome and must be pressed by Gary. The browser policy for this task does not allow me to submit the final password-set/password-change step.

Credential handling:

- Plaintext EU Login passwords remain excluded from `.env` and `.env1.txt`.
- A Windows user-encrypted credential has been stored under `C:\Users\user\.aureon_grant_private\credentials\eu_login_gaxlec.xml`.

## InterTradeIreland

Target use: Innovation Boost follow-up/full application if requested by InterTradeIreland.

Status: account need not yet confirmed. The initial Innovation Boost enquiry has already been submitted without an account.

## Invest NI

Target use: IFAS / client route / R&D support.

Status: pending. IFAS form is still blocked by CAPTCHA/final form completion; an Invest NI client/account route may be needed after advisor response.
