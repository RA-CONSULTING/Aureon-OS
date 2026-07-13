# Chrome IFS Access Diagnostic

Recorded: 2026-07-09T08:24:00+01:00  
Operator: Aureon  
Affected route: IFS Future Leaders Fellowships Round 11 application `10209992`

## Result

The live IFS application is not currently controllable through the Codex Chrome Extension connection, even though the local grant data and portal handoff are ready.

Update at 2026-07-09T09:10:00+01:00: the in-app browser successfully signed into IFS as `gaxlec@gmail.com` and completed the subsidy basis for application `10209992`. The application overview showed 85% complete. The in-app browser then timed out while attempting finance readback and later timed out before reloading the finance page.

## Checks

- Google Chrome is running.
- The Codex Chrome Extension is installed and enabled in the selected Chrome profile.
- The Chrome native messaging host manifest exists and points to the expected extension origin.
- Browser connection retry still returned: Chrome extension browser unavailable.

## Required Recovery

The Chrome plugin recovery path requires user permission before opening a fresh Chrome window for the selected profile and retrying the connection.

When Chrome control is restored, resume:

https://apply-for-innovation-funding.service.gov.uk/application/10209992

Remaining portal sections:

- Your project finances.
- Finances overview.
- Award terms and conditions.
- Review and submit.
