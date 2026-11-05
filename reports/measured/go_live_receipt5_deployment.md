# Authenticated deployment — receipt 5

Stage 10 only. This file is a deployment receipt. It is not a claim that a live Aureon instance exists, and it is not a claim that the system is alive.

Outcome: **skip**. Receipt 5 complete: **False**.
Decision: **HOLD**. `go_live_clear`: **False**.
Release boundary: **HOLD**. Orange badge: unchanged.
Badge flip: stage 11 / separate PR.
Public pin: `34864ff0547d2cff03e707414743a3b0cc8770b5` (changed: False).
Pin measured at tip `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. evidence/output/hnc_head_anchor.json public_require_pin and docs/runbooks/GO_LIVE_HARDENING.md at started_from; this receipt does not move the pin
Live trading: false. Orders placed: false. Tunnels opened: false. Market data fetched: false.
MCP plan stages 3 and 4 opened: false. Installers switched on: false. Receipts 1-4 re-verified: false.

## Provider

Provider: `None`. Auth method: `None`.
Provider API: `None`. Provider API called: **False**.
Resource id: `None`.
Deploy attempted: **False**. Deploy performed: **False**.
Deploy timestamp: `None` (None).
Healthy: **False**. Provider status: `none`.
Read-back digest: `None`.
Localhost substituted for the provider: **False**.

## Auth probe

Missing provider auth: env:HF_TOKEN, env:HUGGING_FACE_HUB_TOKEN, file:~/.cache/huggingface/token, file:~/.huggingface/token, file:~/.config/huggingface/token, command:gcloud, env:GOOGLE_APPLICATION_CREDENTIALS, file:~/.config/gcloud/application_default_credentials.json, file:~/.config/gcloud/credentials.db.
Present and unused: none.
Probe flags: hf_token_present=False gcloud_on_path=False gcloud_active_account=False gcp_credential_present=False cloud_run_deploy_opt_in=False.

Blocker: Authenticated deploy was not attempted. Missing provider auth: env:HF_TOKEN, env:HUGGING_FACE_HUB_TOKEN, file:~/.cache/huggingface/token, file:~/.huggingface/token, file:~/.config/huggingface/token, command:gcloud, env:GOOGLE_APPLICATION_CREDENTIALS, file:~/.config/gcloud/application_default_credentials.json, file:~/.config/gcloud/credentials.db. Present and unused: none. No provider API was called. No provider read-back was fabricated.

## Scaffold

Eligible upload: `huggingface/hnc-field` files=5 sha256=`66c29e01d07687558d9108f240a8a1f742b53dc838a80b27d5d5ec468a404a4f` source=local-worktree. This hash is a local worktree hash, not a provider read-back.

Spend guard: Hugging Face hardware must stay cpu-basic. A Space stays private unless AUREON_RECEIPT5_HF_PUBLIC=1. Cloud Run is not created unless AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1 and AUREON_RECEIPT5_CLOUD_RUN_SERVICE, AUREON_RECEIPT5_GCP_PROJECT, AUREON_RECEIPT5_CLOUD_RUN_REGION, and AUREON_RECEIPT5_CLOUD_RUN_IMAGE are set.

Runner: `scripts/validation/go_live_receipt5.py`.

git_head_at_measurement is HEAD when this command ran. The commit that adds this file is not a second measurement. provider_readback_digest is sha256 of the redacted provider payload. A null digest means this run has no provider payload. The UTC stamps are this machine's clock, not receipt 3. The pin value was read at started_from. This command does not move it. Receipts 1-4 were not re-run.
