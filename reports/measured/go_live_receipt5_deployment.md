# Authenticated deployment — receipt 5

Stage 10 only. This file is a deployment receipt. It is not a claim that a live Aureon instance exists, and it is not a claim that the system is alive.

Outcome: **skip**. Receipt 5 complete: **False**.
Decision: **HOLD**. `go_live_clear`: **False**.
Release boundary: **HOLD**. Orange badge: unchanged.
Badge flip: stage 11 / separate PR.
Public pin: `bb04503119681adcf832f3c3e9b0cbf09fc7a938` (changed: False).
Pin measured at tip `9333bfbbeb8de54a4b42be05f9263e536da643a7`. mcp/aureon_public/guard_loader.py PINNED_COMMIT at started_from; published require-pin. evidence/output/hnc_head_anchor.json public_require_pin stays the receipt 3 value and is not rewritten. This receipt does not move the pin
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
Probe flags: hf_token_present=False hf_upload_opt_in=False gary_yes=False gcloud_on_path=False gcloud_active_account=False gcp_credential_present=False cloud_run_deploy_opt_in=False.

Blocker: Authenticated deploy was not attempted. Missing provider auth: env:HF_TOKEN, env:HUGGING_FACE_HUB_TOKEN, file:~/.cache/huggingface/token, file:~/.huggingface/token, file:~/.config/huggingface/token, command:gcloud, env:GOOGLE_APPLICATION_CREDENTIALS, file:~/.config/gcloud/application_default_credentials.json, file:~/.config/gcloud/credentials.db. Present and unused: none. No provider API was called. No provider read-back was fabricated.

## Scaffold

Eligible upload: `huggingface/hnc-field` files=6 sha256=`e246804c3821bbec73d8e789bf785d3246b4fa0f5ac32eeca984d21126c431a4` source=local-worktree. This hash is a local worktree hash, not a provider read-back.

Spend guard: Upload and provider read-back are off by default. A token is not an opt-in. Both stay off unless AUREON_HF_GARY_YES=1 and AUREON_RECEIPT5_ALLOW_HF_UPLOAD=1. Hardware identifiers and personal data are not sent. The free tier read from the Space must be cpu-basic, and the Space must be private gradio, before any upload. create_repo exist_ok is not that check. A new Space stays private unless AUREON_RECEIPT5_HF_PUBLIC=1 and AUREON_HF_GARY_YES_PUBLIC=1. Cloud Run upload and read-back stay off unless AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1, AUREON_RECEIPT5_GARY_YES_CLOUD_RUN=1, and AUREON_RECEIPT5_CLOUD_RUN_SERVICE, AUREON_RECEIPT5_GCP_PROJECT, AUREON_RECEIPT5_CLOUD_RUN_REGION, and AUREON_RECEIPT5_CLOUD_RUN_IMAGE are set.

Runner: `scripts/validation/go_live_receipt5.py`.

git_head_at_measurement is HEAD when this command ran. The commit that adds this file is not a second measurement. provider_readback_digest is sha256 of the redacted provider payload. A null digest means this run has no provider payload. The UTC stamps are this machine's clock, not receipt 3. The pin value was read at started_from. This command does not move it. Receipts 1-4 were not re-run.
