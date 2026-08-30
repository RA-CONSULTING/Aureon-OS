# Website and Operator Deployment Boundary

## Current public model

The Aureon public website is a static, read-only information surface. Its
`/live/` page retrieves limited public metadata directly from the GitHub API for
`RA-CONSULTING/Aureon-OS` and may display a dated redacted operator snapshot in
`website/data/operator-evidence.json`; it does not call an Aureon backend.

This is intentional. The website can show an attributable source signal and
public evidence without creating a public route to an operator, model provider,
credential store, grant ledger, trading state, or customer material.

## What may be published on the website host

- Static HTML, CSS, JavaScript, images, and public research/evidence records.
- Links to the public Aureon OS source repository and primary company records.
- Browser-side GitHub metadata with a graceful failure state.
- A timestamped, redacted `healthz` / `readyz` snapshot that states its provider
  mode and real-data-evidence limits. It is a published record, never a public
  proxy or an operator control.

The existing FTPS `public_html` publishing route is suitable for this static
website model. It is not treated as the Aureon Operator runtime.

## What must stay separated

The operator server provides prompt, cognition, provider-management, and
runtime routes. It must not be exposed from the public marketing domain or
embedded as a website widget.

These categories remain private:

- API keys, passwords, one-time codes, sessions, and provider configuration.
- Private company research, grant records, client information, or financial and
  trading data.
- Prompt, agent, action, trading, filing, or administration endpoints.

## Operator production prerequisites

Before the operator is placed on any server, the company owner must approve the
server provider, DNS name, access model, and operating cost. The production
environment must then have all of the following:

1. A separate Linux VM or container host, not the public static site route.
2. Firewall rules that keep port 8790 private; the compose file binds it to
   `127.0.0.1` by default.
3. TLS through an authenticated reverse proxy, with the public origin and
   allowed routes deliberately configured.
4. A non-empty `AUREON_OPERATOR_API_KEY`, a sensible
   `AUREON_OPERATOR_RATE_RPS`, and no secrets committed to the repository. The
   `deploy/docker-compose.operator.yml` production compose file refuses to
   start if the API key is absent.
5. A private health and readiness check, logging/redaction policy, backup plan,
   patching owner, and an incident contact.
6. A review of every route before any reverse proxy exposure. The default
   marketing website must never proxy `/api/` to the operator.

## Safe publication sequence

1. Publish and verify the static website changes through the existing website
   host.
2. Select and approve a separate operator host and a non-public access method.
3. Deploy the operator with protected runtime configuration held only in that
   host's secret manager or runtime environment.
4. Test `/healthz` and `/readyz` from the private network only.
5. Where it is useful for public review, run
   `website/refresh-operator-evidence.ps1` from the secured operator host and
   publish only the generated static snapshot with the website release. Review
   the snapshot's provider and real-data labels before publishing it.
6. If an investor demonstration needs more than a dated snapshot, publish a
   separately designed, read-only, redacted demo endpoint after a security
   review; do not reuse the general operator UI or API.

This boundary lets reviewers see live public evidence while preserving human
control over sensitive workflows.
