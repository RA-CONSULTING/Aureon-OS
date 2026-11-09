# Force guarded mode unless the stage 11 gate is clear and AUREON_OPERATOR_ALLOW_LIVE
# is set, or a valid operator test session is active. A session does not set
# go_live_clear. Source this from a launcher that has already cd'd to the checkout.
live_mode_guard() {
  local py="${1:-python3}"
  local output status stamp
  set +e
  output="$("$py" -m aureon.launch.live_gate 2>&1)"
  status=$?
  set -e
  printf '%s\n' "$output"
  if [ "$status" -ne 0 ]; then
    export AUREON_LIVE_TRADING=0
    export AUREON_AUTONOMY_MODE=guarded
    export AUREON_DISABLE_REAL_ORDERS=1
    unset AUREON_OPERATOR_TEST_SESSION_STAMP
    return 0
  fi
  stamp="$(printf '%s\n' "$output" | sed -n 's/.*\(operator_test_session=[A-Za-z0-9._-]*, go_live_clear=false\).*/\1/p')"
  if [ -n "$stamp" ]; then
    export AUREON_OPERATOR_TEST_SESSION_STAMP="$stamp"
  fi
}
