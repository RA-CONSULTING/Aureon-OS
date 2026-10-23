# Artifacts & Large Files

This project generates large results (backtests, hive snapshots, montecarlo outputs). To keep the repository usable we follow this strategy:

- Track working large files with Git LFS (for files collaborators need directly in the repo).
- Keep generated outputs under `artifacts/` and exclude that directory from regular commits.
- Publish stable, large snapshots as GitHub Release assets so they can be downloaded on demand.

Release with large assets:

```bash
# Download the current artifacts release into artifacts/
gh release download v1.0-artifacts --repo RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS- -D artifacts/
```

Set up Git LFS locally (once):

```bash
git lfs install
git lfs track "*.json" "*.csv"
git add .gitattributes
git commit -m "chore: enable git lfs for large artifacts"
```

Recommended workflow:

1. Keep `artifacts/` in `.gitignore` for generated outputs.
2. If a large file needs to be versioned in the repo, add it to Git LFS instead of committing the raw file.
3. For archival runs or public datasets, upload as a GitHub Release asset or to external storage (S3).

If you want, run `scripts/artifacts.sh` to upload or download release assets.
