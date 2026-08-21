# Publish the Aureon website to home.pl

This static website belongs to **R&A Consulting and Brokerage Services Ltd** (company no. **NI696693**), trading as **Aureon Zorza Technologies**. Companies House lists Gary Anthony Leckey as the company's one current director and one active person with significant control, with 75% or more ownership of shares and voting rights. This public record does not establish a more precise ownership percentage. Public correspondence uses the company contact route; do not publish a personal mailbox in the website package.

## Build the package

From the repository root, run the governed builder:

```powershell
python -m scripts.website.build_package --out artifacts/website-releases
```

The builder audits the public surface, fails closed on errors or secret-bearing file types, excludes working archives and unreferenced source artwork, and creates a deterministic ZIP with website files at its top level. The legacy `website/build-homepl-package.ps1` is retired and must not be used.

## Safe publishing sequence

1. Reconfirm the document root for `serwer2636460`. Authenticated WebFTP inspection and verified public read-back most recently reconfirmed `/public_html` as the served root on 26 July 2026; do not upload to `/` or create a nested `public_html` directory by assumption.
2. Create and retain a fresh recursive backup of the current remote root, with a manifest and non-zero file count, before changing anything.
3. Either upload the ZIP to the verified root and use **Unzip** with the target set to exactly that root, or use the internal `publish-homepl-ftps.ps1` tool with an approved temporary FTPS account. The FTPS tool verifies every local file against the release manifest before it can upload anything.
4. The FTPS tool is dry-run by default. It requires `-Deploy`, `HOMEPL_FTPS_HOST`, `HOMEPL_FTPS_USER`, and a process-only `HOMEPL_FTPS_PASSWORD`; it never writes credentials into the website, package, or repository.
5. Wait for the provider to report every nested path copied successfully. A ZIP built on Windows must use forward slashes in its internal paths; the included script enforces this.
6. Remove the temporary ZIP from the verified remote root after public checks succeed.
7. Check `https://aureonzorzatechnologies.pl/`, `/publications/`, `/updates/`, `/live/`, `/funding/`, `/contact/`, `/research/`, and `/projects/` in a private browser window.
8. Delete any temporary FTPS account created specifically for the release and refresh the FTP-account list to verify its removal. Do not change pre-existing FTP accounts by assumption.

Do not change DNS, SSL, or domain assignment as part of a normal website-file update.

## Live publication state before V45

- A V27 package was published on 26 July 2026, followed by an incomplete V28 attempt.
- The latest V28 read-back recorded only 63 of 88 manifest entries exact, 24 manifest failures and 13 site-contract failures; `publication_complete` was false.
- The current public surface must therefore be treated as a mixed V27/V28-era site, not as a fully verified release.
- Before V45 changes any remote file, create a fresh recursive backup of the served root and verify its manifest and non-zero file count.
- V45 is not published until every release file is read back from the public domain and the critical rendered routes pass visual and content checks.

## Safety rules

- Do not place passwords, API keys, FTP credentials, client information, financial records, or other private material in the website source or GitHub.
- Keep public statements evidence-based. Research, concepts, archives, and implemented work have different statuses and must not be represented as equivalent.
- GitHub stores the source history. home.pl serves the live files; a GitHub push does not currently publish this website automatically.
