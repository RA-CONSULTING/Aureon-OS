# Maeshowe repair and evidence bundle, 12 September 2026

This package contains a repaired candidate-transliteration reader, the explicitly labelled legacy frequency model, the full conditional-control results, tests, source review and receipts. Read `Maeshowe-repaired-experiment-results-2026-09-12.md` first.

Control job 6501577 and integration job 6501655 both completed with exit 0. The latter verified 16 tests against the three staged repository files. The patch is based on commit f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d in the isolated expansion worktree. No commit or publication is claimed. Original code is preserved under `code/originals`; native manuscripts remain in the recovered original corpus.

`code/PROTOCOL.md` is the pre-run protocol. `maeshowe-controls-6501577/results/conditional-controls.csv.gz` contains every one of 120,960 configurations; `configuration-index.json` resolves the indices. The local verification independently re-counted all five rank summaries from these rows. These comparisons do not establish a physical decipherment or historical probability.

To reproduce the CPU comparison in a modern Python environment: `python code/run_controls.py --output fresh-results`. To run the integrated patch checks: `python -m unittest discover -s repository-patch/tests/research -p test_maeshowe_epigraphy.py -v`.

The source patch files correspond to paths beneath the repository root. Their SHA-256 values are in `maeshowe-repository-checks-6501655/verification.json`. The pending observation record contains no branch counts. Source uncertainty must not be filled from desired meanings or gamma values.

The prior isambard-20260912 package v6 is preserved separately. The broader compute goal remains active; this bundle does not represent all-family completion.
