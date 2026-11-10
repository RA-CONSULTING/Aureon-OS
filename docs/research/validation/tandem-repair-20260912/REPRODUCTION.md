# Reproduction and immutable evidence

The three staged source directories contain frozen experiment, full launcher
and audit packages. Original source bytes and two historical NPZ control fixtures
remain in the experiment package. The new computed pilot archive and full result
arrays remain outside Git on Isambard and in the local evidence directory; see
their hash receipts for identity. Read the exact dated report for execution state.

Run only in a separate output directory for a new experiment. The frozen
launchers point to recorded Isambard paths and are not generic rerun commands.
Use the recorded PyTorch 25.05 container and GPU runtime for exact generator
reproduction, including FP64, CUBLAS configuration, batch size and block seeds.
Whitening compilation is serialized and its source/library/compiler are recorded.
The CPU audit uses a separate scalar covariance update and does not import the
experiment generator. Its local tests check calibration separation, pilot overlap,
false-positive gates, paired inference and dense covariance identities.

Submission receipts establish dispatch, not completed experiment findings.
Retain the old detector failures and all later failures. No commit or publication
is part of this staging operation. The connected legacy report is an unchanged
convenience copy; a synthetic echo does not identify a historical timed passage.
