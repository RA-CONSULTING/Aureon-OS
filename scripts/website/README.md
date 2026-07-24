# `scripts/website/` — audit → build → FTP-deploy for the static `website/` site

Pure-standard-library tooling (no third-party dependency, no network at import time) for the
hand-written static site in [`website/`](../../website/) — the Aureon Zorza / Project Envision
site served from the home.pl document root. It gives you a repeatable **audit → build → deploy**
path while leaving the existing manual home.pl file-manager route
([`website/HOMEPL_UPLOAD_README.md`](../../website/HOMEPL_UPLOAD_README.md)) fully intact.

> **Back up the current live site before your first upload.** The deployer only creates/overwrites
> remote files; it never deletes anything unless you pass `--prune`.

## 1. Audit — correctness · SEO · a11y · perf

```bash
python -m scripts.website.audit_site          # human report; exits non-zero on any ERROR
python -m scripts.website.audit_site --json    # machine-readable findings
```

Checks (ERROR fails the run, WARN is advisory):

- **Correctness** — every internal link/asset/`srcset`/CSS `url(...)` resolves to a file on disk;
  every `data/*.json` and JSON-LD block parses; required root files present.
- **SEO** — each indexable page has `<title>`, `<meta description>`, and a `<link rel=canonical>`
  on `aureonzorzatechnologies.pl`; `og:url` matches canonical; `sitemap.xml` lists exactly the
  indexable pages (absolute HTTPS, `noindex` pages excluded); `robots.txt` `Sitemap:` matches.
- **a11y** — `<html lang>`; every `<img>` has `alt`; external `target="_blank"` links carry
  `rel="noopener"`; a skip link that targets `#main-content` must have that landmark. (JS-rendered
  project detail pages inject their `<h1>` at runtime and are recognised as such.)
- **perf** — raster images carry loading hints; oversized non-WebP rasters are flagged (advisory).

## 2. Build the home.pl package (deterministic)

```bash
python -m scripts.website.build_package --out dist
# reproducible artifact for verification:
python -m scripts.website.build_package --out dist --created-at 2026-07-19T00:00:00Z
```

Runs the audit first (**aborts on any ERROR**), assembles a clean tree into
`dist/website_package/` (with `index.html` at its root), regenerates
`HOMEPL_PACKAGE_MANIFEST.txt` with real file counts, and writes:

- `dist/aureon-zorza-website.zip` — the upload archive.
- `dist/aureon-zorza-website.zip.sha256.txt` — the **companion** manifest with the ZIP's size and
  SHA-256 (the checksum can't live inside the archive it checksums).

Two builds at the same `--created-at` are **byte-identical** (sorted entries, fixed timestamps).

## 3. Deploy over FTP(S) — credentials only from the environment

Credentials are read **only** from environment variables — never passed on the command line, never
committed, and never printed. The script refuses to run if any required variable is unset. FTPS
(explicit TLS) is the default.

| Variable | Required | Meaning |
|---|---|---|
| `AUREON_FTP_HOST` | yes | FTP server hostname |
| `AUREON_FTP_USER` | yes | username |
| `AUREON_FTP_PASS` | yes | password |
| `AUREON_FTP_DIR`  | yes | remote document root to mirror into (e.g. `/` or `/domains/…/public_html`) |
| `AUREON_FTP_PORT` | no  | default `21` |
| `AUREON_FTP_TLS`  | no  | `1` (default, FTPS) or `0` (plain FTP) |

```bash
# Always safe — prints the exact upload plan, touches no network:
python -m scripts.website.ftp_deploy --package dist/website_package --dry-run

# Real upload (set the vars in your shell first; do not commit them):
export AUREON_FTP_HOST=... AUREON_FTP_USER=... AUREON_FTP_PASS=... AUREON_FTP_DIR=...
python -m scripts.website.ftp_deploy --package dist/website_package
```

`--prune` (off by default) would allow removing remote files absent locally — leave it off to
protect the live site unless you specifically intend a mirror-delete.

## Security notes

- **No credentials live in the repo.** Set them in your shell (or a local, git-ignored `.env` you
  `source`), never in a committed file. The tools mask the password in all output.
- Assign the domain, DNS, and SSL in the home.pl panel — uploading files does not configure them
  (see the manual guide).

## Tests

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 pytest tests/test_website_tooling.py -q
```
