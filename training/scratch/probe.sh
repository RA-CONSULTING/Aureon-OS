#!/bin/bash
# Report which login node this is and every process here that is writing into
# our shared staging tree.
#
# Both halves matter: the python parent matches 'fetch_zenodo.py', but the curl
# child does not -- its command line is "curl -fL -C - ... zenodo.org/api/...".
# An orphaned curl outlives a killed python and keeps appending to the same
# file, so a check that only greps for the python parent reports zero while
# bytes are still moving.
echo "$(hostname) py_zen=$(pgrep -c -f 'fetch_[z]enodo') py_cor=$(pgrep -c -f 'fetch_[c]orpus') curl_zen=$(pgrep -c -f '[z]enodo\.org/api/records') curl_cor=$(pgrep -c -f '[d]ata\.huggingface\.co')"
