# Resumable Isambard archive transfer

`huggingface/isambard_archive.py` inventories the Isambard trees, applies security and provenance gates, exports path-safe manifests, and transfers only approved files to the three mapped public Hugging Face dataset repositories. It does not delete, rename, edit, or create files in either source tree. There is no local staging copy.

The canonical model publisher remains a separate module. The full-run archive mapping does **not** exempt canonical-model files: if they occur under `hnc-organism`, they are inventoried and mapped like every other file.

## Source mapping

| Isambard source | Public repository | Repository path |
| --- | --- | --- |
| `/projects/u6vs/pretrain/**` | `GaryLeckey/aureon-isambard-data` | `pretrain/**` |
| `/projects/u6vs/hnc-organism/runs/**` | `GaryLeckey/aureon-isambard-runs` | `runs/**` |
| `/projects/u6vs/hnc-organism/training/sft/**` | `GaryLeckey/aureon-isambard-data` | `training/sft/**` |
| `/projects/u6vs/hnc-organism/training/aureon_tokenizer.json` | `GaryLeckey/aureon-isambard-data` | `training/aureon_tokenizer.json` |
| `/projects/u6vs/hnc-organism/training/aureon_tokenizer.report.json` | `GaryLeckey/aureon-isambard-data` | `training/aureon_tokenizer.report.json` |
| Every other regular file under `/projects/u6vs/hnc-organism/**` | `GaryLeckey/aureon-isambard-archive` | `hnc-organism/**` |

The previously handed-off scale is **562GB / 505GB**. These are prior handoff values, not totals measured by this tooling or by a fresh scan. Use the `summary.json` produced by a completed inventory for current measured counts and bytes.

## Safety and resume model

- Inventory uses `lstat`/`scandir` without recursive symlink traversal. Symlinks are preserved as explicit metadata and are never uploaded. Relative link targets appear in the public manifest; absolute targets remain only in the local state and are redacted from that manifest.
- Every selected regular file records its logical source root, relative path, byte size, `mtime_ns`, SHA-256, Git blob SHA-1, destination repository/path, provenance, license status, security status, and verification state. An unchanged size and `mtime_ns` reuses the prior hashes. Each file is committed to SQLite immediately, so an interrupted scan can resume durable work. An interrupted scan remains marked in progress; upload and final verification refuse it until a resumed scan completes.
- A file whose identity, size, or modification time changes while it is open and hashed is marked `changed_during_scan`; its digest is not trusted. A pre-upload fingerprint mismatch also blocks it and requires a rescan.
- SQLite state and export directories must be outside all source roots, including after resolving path symlinks. The database contains absolute paths for local resume only. `manifest.jsonl`, `blocked.jsonl`, and `summary.json` contain no absolute local paths or raw scanner errors.
- Secret findings are stable reason codes, not matched values. The gate covers non-example `.env` variants, private keys, SSH/session/credential material, and high-confidence embedded private-key/token patterns. Only `.env.example`, `.env.template`, `.env.sample`, and their `example.env`/`template.env`/`sample.env` forms are filename-exempt, and their contents are still scanned.
- FineWeb and FineWeb-Edu are marked ODC-BY with attribution and CommonCrawl-term obligations. SmolLM-Corpus `python-edu` is marked ODC-BY with The Stack provenance. CodeParrot raw data/code is blocked for documented review because there is no card-wide license. The Stack gated content is blocked by default. Unknown third-party provenance is blocked rather than assigned redistribution rights.
- Project-original HNC/Aureon paths default to the project MIT license. Path-based provenance classification is not a legal audit; mixed or embedded third-party content still needs review. External model/container caches, `models/`, `containers/`, `venvs/`, `hf*/`, `cache/`, raw `corpus/`, `github/`, `runtime/`, and `tmp/` are review-blocking categories rather than assumed Aureon property.
- Raw `.git` internals and shell/session history are security-blocked. Compressed Git objects cannot be cleared by scanning their compressed bytes; publish reviewed history through the normal GitHub route instead. Security blockers cannot be overridden with a license review.

## Prerequisites and isolated state

Run on Isambard with Python 3.11+, SQLite, and `huggingface_hub>=0.36`. The library import is lazy: inventory and export do not import it and do not need a token. Upload and remote verification read only `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`; tokens are never accepted as CLI arguments or written to SQLite/manifests.

The verified login-node route uses the existing PyTorch container: its Python has SQLite and `huggingface_hub 0.36.2`. The host's `python3` is 3.6 and its minimal `python3.11` lacks SQLite, so an unqualified `python` is not sufficient. This container command performs no GPU allocation or model load:

```bash
export TRANSFER_WORK=/projects/u6vs/aureon-hf-release/transfer
mkdir -p "$TRANSFER_WORK"
export TRANSFER_STATE="$TRANSFER_WORK/state.sqlite3"
export BASE=/projects/u6vs/hnc-organism
export SIF="$BASE/containers/pytorch-25.05-py3.sif"
export VENV="$BASE/venvs/aureon-sft"
transfer_python() {
  apptainer exec --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    "$SIF" "$VENV/bin/python" "$@"
}
cd /projects/u6vs/aureon-hf-release/source
```

`TRANSFER_WORK` must not be inside `/projects/u6vs/pretrain` or `/projects/u6vs/hnc-organism`. Keep long uploads in an explicitly monitored login-node session. Compute nodes have no outbound network, so an upload Slurm job will not work. Neither `tmux` nor `screen` was installed at inspection; do not assume that closing SSH leaves a background process alive. Use a maintained connection or a deliberately configured user service, and rely on the SQLite state for resume after interruption.

For a containerized upload, set `HF_TOKEN` only in the shell and forward it through `APPTAINERENV_HF_TOKEN` without printing it. Do not place either value in a command argument, commit message, manifest, or log.

## 1. Small pilot inventory and export

Filters apply to source-relative POSIX paths. Repeat `--glob` or `--contains` to provide alternatives. `--max-files` and `--max-bytes` bound the initial scan; one first file may exceed the byte limit so a pilot cannot silently become an empty scan.

```bash
transfer_python huggingface/isambard_archive.py inventory \
  --state "$TRANSFER_STATE" \
  --pretrain-root /projects/u6vs/pretrain \
  --hnc-root /projects/u6vs/hnc-organism \
  --glob 'data/fineweb-edu/*' \
  --max-files 20 \
  --max-bytes 10737418240

transfer_python huggingface/isambard_archive.py export \
  --state "$TRANSFER_STATE" \
  --output-dir "$TRANSFER_WORK/public"
```

Review `public/manifest.jsonl`, every entry in `public/blocked.jsonl`, and `public/summary.json` before any upload. A filtered scan adds/updates the selected inventory without marking unselected prior rows inactive.

A one-file login-container pilot completed on 2026-11-22: `data/fineweb-edu/manifest-fineweb-edu.json`, 18,298 bytes, SHA-256 `e9cbd8d1b329cbc0b089199c629ce850996d52d740c2fd82ba3c8e22341e2427`. An independent `sha256sum` returned the same value. This was inventory/export only, not a Hub upload.

## 2. Approved-only pilot upload

Both literal acknowledgements are mandatory. The first acknowledges public visibility; the second explicitly accepts an approved-only, potentially partial release while other files remain blocked or unselected. Repositories are created with `private=False`, and the code refuses destinations outside the three mappings above.

```bash
transfer_python huggingface/isambard_archive.py upload \
  --state "$TRANSFER_STATE" \
  --glob 'data/fineweb-edu/*' \
  --acknowledge-public I_UNDERSTAND_THIS_IS_PUBLIC \
  --acknowledge-partial-release I_APPROVE_A_PARTIAL_RELEASE \
  --batch-files 100 \
  --batch-bytes 1073741824 \
  --large-file-bytes 268435456
```

Each batch uses `CommitOperationAdd` directly against the original file. Batches are bounded by count and bytes; files at or above the large-file threshold are isolated. Before committing, already matching remote files are skipped. After committing, every file is checked through Hub metadata: LFS objects use SHA-256 and ordinary Git blobs use `blob <size>\0` SHA-1. Revision and verification results are persisted. Re-running after a failed batch excludes already verified files and uses remote hashes to avoid duplicating files from a commit whose verification response was interrupted.

A successful approved-only upload is not final release verification.

## 3. Full inventory and upload

A full, unfiltered inventory marks files that disappeared since the prior completed full scan inactive. Do not use the pilot limits for this step.

```bash
transfer_python huggingface/isambard_archive.py inventory \
  --state "$TRANSFER_STATE" \
  --pretrain-root /projects/u6vs/pretrain \
  --hnc-root /projects/u6vs/hnc-organism

transfer_python huggingface/isambard_archive.py export \
  --state "$TRANSFER_STATE" \
  --output-dir "$TRANSFER_WORK/public"

transfer_python huggingface/isambard_archive.py upload \
  --state "$TRANSFER_STATE" \
  --acknowledge-public I_UNDERSTAND_THIS_IS_PUBLIC \
  --acknowledge-partial-release I_APPROVE_A_PARTIAL_RELEASE
```

## 4. Remote and final verification

Verify the current approved selection:

```bash
transfer_python huggingface/isambard_archive.py verify --state "$TRANSFER_STATE"
```

Final verification covers the entire active inventory, fails on every unresolved blocked file, and fails on missing or mismatched remote hashes:

```bash
transfer_python huggingface/isambard_archive.py verify --state "$TRANSFER_STATE" --final
```

A license/provenance blocker can be resolved only by an explicit documented review; this cannot override a security blocker. For example:

```bash
transfer_python - <<'PY'
import os
from huggingface.isambard_archive import ArchiveState

with ArchiveState(os.environ['TRANSFER_STATE']) as state:
    state.record_license_review(
        'hnc-organism',
        'codeparrot/raw.py',
        approve=True,
        reason='Document the per-file redistribution authorization here',
        reviewer='Named accountable reviewer',
    )
PY
```

For a security finding, remove or replace the offending material through a separately authorized source-maintenance process, then rerun the full inventory. This transfer tool itself never performs that removal.

## Tests and operational limits

Run the offline tests from the checkout with an isolated base temp directory:

```bash
python -m pytest tests/test_isambard_archive.py \
  --basetemp=.test-tmp/isambard-archive \
  -p no:cacheprovider -o addopts='' -q
```

Tests use temporary fixture trees and a fake Hub API; they perform no network access. They cover mapping, hash reuse, security/license blocks, symlink handling where supported, mid-scan mutation, batch boundaries, remote skip/mismatch, retry without verified-file duplication, acknowledgement gates, and final blocker/missing-file failure.

The secret scanner is intentionally high-confidence, not a guarantee that every possible credential format is detected. Hub metadata verification confirms the remote object identifiers against locally computed hashes; it is not a second independent download. Only the one-file inventory pilot above has run; no full inventory, Hub upload, or current 562GB/505GB measurement is claimed.
