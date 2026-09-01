# DigitalOcean deployment status: terminal HOLD

Push-to-deploy and provider setup instructions are withdrawn. Both `app.yaml`
and `.do/app.yaml` contain zero deployable components, source bindings, secret
references, health endpoints, and databases. Container and shell entrypoints
emit terminal HOLD receipts and start no Aureon target.

No DigitalOcean deployment or provider-side read-back is claimed. See
[`DIGITALOCEAN_DEPLOY.md`](DIGITALOCEAN_DEPLOY.md) for current checks.
