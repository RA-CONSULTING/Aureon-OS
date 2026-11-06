# Publish to Hugging Face

These commands are the private path. They were not run by the change that added them. This repository does not contain a token. Go-live stays **HOLD**. A finished upload is still not a live Space until a later receipt reads the runtime back.

Do this only from a machine that already has `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` in the environment, and only after Gary's own yes (`AUREON_HF_GARY_YES=1`). Without that yes, run the measurement instead. It does not sign in:

```bash
python huggingface/distribution.py
```

That writes `measured/hf_space_distribution.json`. When the token is missing, when Gary's yes is missing, or when the flavor would need a PRO plan, the decision is HOLD-skip. The file names the missing token and the PRO status. It does not contain the token value.

A public Space, a public dataset, and a `0.0.0.0` listener are not in the commands below. They need Gary's own yes as well. The scaffold flavor is `cpu-basic`. ZeroGPU (`zero-a10g`) and paid hardware need a PRO plan or a paid account, and this file does not select them. If the Hub answers that PRO is required, leave the receipt on HOLD and name PRO.

The organisation id is whatever you create. The examples use `$HF_ORG`.

Licence on every repo: **mit**, matching the Aureon OS `LICENSE`.

Current `huggingface_hub` (1.33 and later) retires the `huggingface-cli` entry point. `huggingface-cli` prints that it is deprecated and does not run the command. The working CLI is `hf`. The library calls are `huggingface_hub.HfApi`. Both read `HF_TOKEN` from the environment. Do not pass the token as an argument. Do not echo it. Do not put it in a Space secret. Do not put an exchange key in a Space secret.

```bash
pip install "huggingface_hub>=1.33"
export HF_ORG="your-org-id"
```

Create the organisation in the Hugging Face website if it does not exist yet. Then, private repos only:

```bash
hf repos create "$HF_ORG/fixed-seed-reproducible-runs" --type dataset --private --exist-ok

hf upload "$HF_ORG/fixed-seed-reproducible-runs" \
  huggingface/fixed-seed-reproducible-runs \
  --repo-type dataset \
  --commit-message "Add fixed-seed reproducible runs"
```

```bash
hf repos create "$HF_ORG/hnc-field" --type space --space-sdk gradio --private --exist-ok
hf upload "$HF_ORG/hnc-field" huggingface/hnc-field \
  --repo-type space \
  --commit-message "Add HNC field Space"

hf repos create "$HF_ORG/auris-coherence" --type space --space-sdk gradio --private --exist-ok
hf upload "$HF_ORG/auris-coherence" huggingface/auris-coherence \
  --repo-type space \
  --commit-message "Add Auris coherence Space"

hf repos create "$HF_ORG/qgita-snr" --type space --space-sdk gradio --private --exist-ok
hf upload "$HF_ORG/qgita-snr" huggingface/qgita-snr \
  --repo-type space \
  --commit-message "Add QGITA adapter Space"

hf repos create "$HF_ORG/organism-replay" --type space --space-sdk gradio --private --exist-ok
hf upload "$HF_ORG/organism-replay" huggingface/organism-replay \
  --repo-type space \
  --commit-message "Add organism replay Space"
```

Omit `--flavor`. The default hardware is `cpu-basic`. Do not pass `zero-a10g`.

The same private uploads through `huggingface_hub`, still using `HF_TOKEN` and never putting the token on the command line:

```python
import os
from huggingface_hub import HfApi

api = HfApi(token=os.environ["HF_TOKEN"])
org = os.environ["HF_ORG"]
ignore = [".env", ".env.*", "**/.env", "**/.env.*", "**/*.pem", "**/*.key", "**/.git/**"]

api.create_repo(
    f"{org}/fixed-seed-reproducible-runs",
    repo_type="dataset",
    private=True,
    exist_ok=True,
)
api.upload_folder(
    repo_id=f"{org}/fixed-seed-reproducible-runs",
    folder_path="huggingface/fixed-seed-reproducible-runs",
    repo_type="dataset",
    ignore_patterns=ignore,
)

for name in ("hnc-field", "auris-coherence", "qgita-snr", "organism-replay"):
    api.create_repo(
        f"{org}/{name}",
        repo_type="space",
        space_sdk="gradio",
        private=True,
        exist_ok=True,
    )
    api.upload_folder(
        repo_id=f"{org}/{name}",
        folder_path=f"huggingface/{name}",
        repo_type="space",
        ignore_patterns=ignore,
    )
```

`huggingface/distribution.py --deploy` is the same private gate in code. It still refuses to start without `HF_TOKEN`, `AUREON_HF_GARY_YES=1`, and `HF_ORG`. It refuses a flavor other than `cpu-basic` and names PRO. It refuses public visibility unless `AUREON_HF_PUBLIC=1` is set as well. A successful return does not set the Space live: the runtime stage is not read, and go-live stays HOLD.

Upload only the `huggingface/` folders. Do not upload `.env`, `.git`, keys, or the rest of the checkout.

Local run, still on localhost:

```bash
python huggingface/hnc-field/app.py
```

The same entry exists for `auris-coherence`, `qgita-snr`, and `organism-replay`. Each one imports `space_bind.py` from its own directory. Edit `huggingface/space_bind.py` and copy that file into the four Space directories so the copies stay identical.

The Space `requirements.txt` installs the package with:

```bash
pip install "aureon @ git+https://github.com/RA-CONSULTING/Aureon-OS.git@bb04503119681adcf832f3c3e9b0cbf09fc7a938"
```

That pin is commit `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. It is the commit the Spaces and the public server install. It is main at the stage-7 containment squash (#238). The published require-pin names that prior tip, the same way #233 named `34864ff0547d2cff03e707414743a3b0cc8770b5`. The recorded brain runs in this bundle were produced at `a00f744d2e686e916e45b81dd4222408c368e305`. The git+ install brings the whole repo, trading modules included, and only the Spaces switch them off.
