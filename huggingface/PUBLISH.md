# Publish to Hugging Face

Do this from a machine that has `HF_TOKEN` set. This repository does not contain a token, and these commands are not run by the change that added the files.

The organisation id is whatever you create. The examples use `$HF_ORG`.

Licence on every repo: **mit**, matching the Aureon OS `LICENSE`.

Current `huggingface_hub` (1.33 and later) retires the `huggingface-cli` entry point. `huggingface-cli` prints that it is deprecated and does not run the command. The working CLI is `hf`. The library calls are `huggingface_hub.HfApi`. Both read `HF_TOKEN` from the environment. Do not pass the token as an argument.

```bash
pip install "huggingface_hub>=1.33"
export HF_TOKEN="$HF_TOKEN"
export HF_ORG="your-org-id"
```

Create the organisation in the Hugging Face website if it does not exist yet. Then:

```bash
hf repos create "$HF_ORG/fixed-seed-reproducible-runs" --type dataset --exist-ok

hf upload "$HF_ORG/fixed-seed-reproducible-runs" \
  huggingface/fixed-seed-reproducible-runs \
  --repo-type dataset \
  --commit-message "Add fixed-seed reproducible runs"
```

```bash
hf repos create "$HF_ORG/hnc-field" --type space --sdk gradio --exist-ok
hf upload "$HF_ORG/hnc-field" huggingface/hnc-field \
  --repo-type space \
  --commit-message "Add HNC field Space"

hf repos create "$HF_ORG/auris-coherence" --type space --sdk gradio --exist-ok
hf upload "$HF_ORG/auris-coherence" huggingface/auris-coherence \
  --repo-type space \
  --commit-message "Add Auris coherence Space"

hf repos create "$HF_ORG/qgita-snr" --type space --sdk gradio --exist-ok
hf upload "$HF_ORG/qgita-snr" huggingface/qgita-snr \
  --repo-type space \
  --commit-message "Add QGITA adapter Space"

hf repos create "$HF_ORG/organism-replay" --type space --sdk gradio --exist-ok
hf upload "$HF_ORG/organism-replay" huggingface/organism-replay \
  --repo-type space \
  --commit-message "Add organism replay Space"
```

The same uploads through `huggingface_hub`, still using `HF_TOKEN` and never putting the token on the command line:

```python
import os
from huggingface_hub import HfApi

api = HfApi(token=os.environ["HF_TOKEN"])
org = os.environ["HF_ORG"]

api.create_repo(f"{org}/fixed-seed-reproducible-runs", repo_type="dataset", exist_ok=True)
api.upload_folder(
    repo_id=f"{org}/fixed-seed-reproducible-runs",
    folder_path="huggingface/fixed-seed-reproducible-runs",
    repo_type="dataset",
)

for name in ("hnc-field", "auris-coherence", "qgita-snr", "organism-replay"):
    api.create_repo(
        f"{org}/{name}",
        repo_type="space",
        space_sdk="gradio",
        exist_ok=True,
    )
    api.upload_folder(
        repo_id=f"{org}/{name}",
        folder_path=f"huggingface/{name}",
        repo_type="space",
    )
```

Upload only the `huggingface/` folders. Do not upload `.env`, `.git`, keys, or the rest of the checkout.

The Space `requirements.txt` installs the package with:

```bash
pip install "git+https://github.com/RA-CONSULTING/Aureon-OS.git"
```

Merge this change to the default branch before expecting that install to include the packaging note from this branch. The field, evaluator, and adapter modules are already on the default branch.
