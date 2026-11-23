# Public GPU Space publication and acceptance

This path replaces the temporary `aureon-deploy` overlay. The canonical root `Dockerfile` and root `.dockerignore` are unchanged; they still belong to the existing terminal-HOLD image contracts.

## Non-negotiable release order

1. Commit and review the consolidated source. Record that exact source revision in all Isambard and deployment receipts.
2. Run the bounded real-GPU model validator on Isambard. Preserve failed receipts as evidence; never overwrite them.
3. Publish `GaryLeckey/aureon-7b`, then independently download its immutable Hub revision and verify the weight size/hash, tokenizer, EOS metadata, and deterministic generation.
4. Audit the existing `GaryLeckey/aureon-os` Space and publish the maintained configuration. Only then select the approved L40S and disable sleeping for launch.
5. Require the container smoke receipt to pass. Exercise the public API and console through their real URLs, including restart and model-download failure tests.
6. Record source, model, Space, archive revisions, real performance measurements, and explicit blockers in the cross-linked release manifest.

Do not activate paid hardware against a placeholder model revision. Do not upload a model or archive item whose checksum, provenance, license, privacy, or secret gate is unresolved.

## Local source checks

Run from the consolidated repository root. Use a fresh temp path if the system pytest directory is inaccessible.

```powershell
py -3 -m pytest -q -o addopts='' `
  tests/test_validate_aureon_model.py `
  tests/test_download_aureon_hub.py `
  tests/test_aureon_chat_server.py `
  tests/test_hf_model_bootstrap.py `
  tests/test_hf_demo_api.py `
  tests/test_hf_space_config.py `
  tests/test_hnc_llm_gears.py `
  tests/test_hnc_llm_gears_held_reading.py `
  tests/test_hnc_llm_gears_gamma_lambda.py `
  tests/test_hnc_llm_gears_coherence_check.py `
  tests/test_operator_server.py `
  tests/test_selfhost_contract.py
py -3 -m ruff check deploy/huggingface training/aureon_chat_server.py
bash -n deploy/huggingface/entrypoint.sh deploy/huggingface/model_service.sh
```

The local model tests use fakes. They do not prove CUDA, Transformers, or real generation behavior.

## Frontend and image

The Docker build uses a pinned Node 22 builder and runs `npm ci --ignore-scripts --no-audit --no-fund`, typechecking, shell lint, and `npm run build`. Only that build's `dist` is copied into the runtime. Existing `frontend/dist`, `node_modules`, local credentials, runtime state, and approval artifacts are excluded.

Build from the repository root:

```bash
docker build -f deploy/huggingface/Dockerfile -t aureon-os-hf:local .
```

Docker automatically prefers `deploy/huggingface/Dockerfile.dockerignore` for this build. When publishing to a Space root, upload that file as `.dockerignore`, this directory's `Dockerfile` as `Dockerfile`, and this directory's `README.md` as the Space `README.md`.

Required local image checks before publication, when Docker is available:

```bash
docker image inspect aureon-os-hf:local
docker run --rm --entrypoint bash aureon-os-hf:local -n /app/aureon-os/deploy/huggingface/entrypoint.sh
docker run --rm --entrypoint bash aureon-os-hf:local -n /app/aureon-os/deploy/huggingface/model_service.sh
docker run --rm --entrypoint nginx aureon-os-hf:local -t -c /app/aureon-os/deploy/huggingface/nginx.conf
```

`nginx -t` on the source template is expected to fail if a platform treats unresolved bearer placeholders as invalid; render a temporary config with nonsecret test strings first. No real bearer belongs in a build argument, layer, source file, or log.

## Space variables and hardware

Set the nonsecret Space variable `AUREON_MODEL_REVISION` to the verified 40-character model Hub commit. No `HF_TOKEN`, exchange credential, provider key, operator bearer, or Fusion bearer is required or permitted in Space secrets. The entrypoint creates random internal bearer values on every boot.

The approved paid target is **1× Nvidia L40S**, listed at **$1.80/hour while running** when the plan was approved. Confirm the current Hugging Face price before activation. Keep it always-on for launch only after the immutable model is publicly downloadable and the source image passes its build.

## Container acceptance

`deploy/huggingface/smoke.py` is a one-shot supervisor process. It waits for strict readiness, then requires:

- exact own-model attribution, immutable revision, weight size/hash, parameter/vocabulary/EOS identity, CUDA, and startup generation;
- one real bounded completion with its pre-inference HNC organism snapshot;
- public console, operator reads, Fusion status, HNC status/replays, and evidence HTML;
- denial of sensitive reads and POST/PUT/PATCH/DELETE mutations, including requests carrying the real internal bearer values;
- observed generation rate limiting;
- Redis, local Postgres schema, error sink, and every required supervisor process.

Every required failure exits nonzero. The receipt is `runtime/smoke-receipt.json`; it contains statuses and check labels, never prompts, completions, or credentials. A running container with a failed smoke receipt is not a passed release.

## Public verification

Exercise both `https://huggingface.co/spaces/GaryLeckey/aureon-os` and `https://garyleckey-aureon-os.hf.space` in a real browser. Verify console navigation, HNC evidence, generation failures and successes, refresh, restart behavior, and accessibility. Use API clients to verify liveness versus readiness, exact model attribution, rate limits, and all denied routes.

Measure cold start, first-token latency, throughput, GPU/RAM use, bounded concurrency, and a sustained soak on the actual L40S. Record first-call and worst-case results, not only averages. Model-download refusal, CPU fallback, wrong hash, wrong revision, missing readiness, and stale approval artifacts must remain failing cases.

## Archive boundary

Archive publication remains a separate Isambard-login-path workflow in `huggingface/ISAMBARD_TRANSFER.md`. Compute nodes have no outbound network. Do not stage the archive on the 13 GB-local PC. Raw Git internals, unknown provenance, private material, third-party corpus without redistribution permission, and blocked batches remain unpublished and explicitly listed in the final manifest.
