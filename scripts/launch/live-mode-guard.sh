# Force guarded mode unless the stage 11 gate is clear and AUREON_OPERATOR_ALLOW_LIVE is set.
# Source this from a launcher that has already cd'd to the checkout root.
live_mode_guard() {
  local py="${1:-python3}"
  if ! "$py" -m aureon.launch.live_gate; then
    export AUREON_LIVE_TRADING=0
    export AUREON_AUTONOMY_MODE=guarded
    export AUREON_DISABLE_REAL_ORDERS=1
  fi
}
