# One-command self-host. Live trading stays off.
# `make up` does not use Docker. `make compose` does.

.PHONY: up down compose smoke plug plug-smoke plug-compose evidence remeasure-go-live-receipts check

up:
	PYTHONPATH=. python3 scripts/selfhost_up.py

down:
	PYTHONPATH=. python3 scripts/selfhost_up.py --stop
	-docker compose -f deploy/selfhost/docker-compose.yml down
	-sudo docker compose -f deploy/selfhost/docker-compose.yml down

compose:
	python3 scripts/stage_selfhost_image.py
	mkdir -p deploy/selfhost/runtime
	chmod 777 deploy/selfhost/runtime
	docker compose -f deploy/selfhost/docker-compose.yml up -d --build --wait || sudo docker compose -f deploy/selfhost/docker-compose.yml up -d --build --wait

smoke:
	PYTHONPATH=. python3 scripts/selfhost_smoke.py

# Local plug-and-play. No Docker, no .env, no external model key.
plug:
	./install.sh

plug-smoke:
	./install.sh --smoke

# Local verification. Does not call GitHub Actions.
# ruff is the files this change owns. The rest of aureon/operator still has
# pre-existing findings on ruff 0.15.21, so a repo-wide ruff is not the gate.
# pytest is the suite in pyproject.toml (live and windows markers excluded).
check:
	@test -x .venv/bin/python || { echo "No .venv yet. Run ./install.sh first." >&2; exit 1; }
	.venv/bin/python -m pip install -r requirements-check.lock
	.venv/bin/python -m ruff check aureon/operator/computer_use_stop.py aureon/operator/local_action_bridge.py aureon/operator/feature_switchboard.py aureon/core/aureon_lattice_simulation.py aureon/core/pursuit.py tests/test_plug_and_play_operational.py tests/test_feature_switchboard.py tests/test_grounded_action.py tests/test_pursuit.py tests/test_soul.py
	.venv/bin/python -m pytest

plug-compose:
	python3 scripts/stage_plug_image.py
	docker compose -f deploy/plug/docker-compose.yml up --build

# Rebuild the HNC, Auris, and QGITA evidence and require the committed bytes.
# The HNC head token is read from refs/notes/aureon-hnc-head. This target does not
# request a new timestamp and does not enable trading.
evidence:
	PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check

# Remeasure go-live receipts 1–4 on a clean worktree. Refuses a dirty tree.
# Does not clear go-live, move the published pin, request a new timestamp,
# or push refs/notes/aureon-hnc-head. See docs/runbooks/GO_LIVE_RECEIPTS_REMEASURE.md.
remeasure-go-live-receipts:
	PYTHONPATH=. python3 scripts/validation/remeasure_go_live_receipts.py
