#!/bin/sh
set -eu

# The nginx-only image cannot execute the Python isolated bootstrap.  Until a
# reviewed native/container boundary exists, emit a deterministic explicit HOLD
# and start no listener, child, network request, or filesystem mutation.
printf '%s\n' '{"action_eligible":false,"child_process_started":false,"decision":"HOLD","file_written":false,"network_accessed":false,"production_ready":false,"reason":"native_frontend_container_boundary_required","schema":"aureon.plumber.frontend-container-hold.v05","target_called":false,"target_id":"frontend-static-nginx","target_started":false}'
exit 1
