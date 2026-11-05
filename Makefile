# One-command self-host. Live trading stays off.
# `make up` does not use Docker. `make compose` does.

.PHONY: up down compose smoke plug plug-smoke plug-compose evidence

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

plug-compose:
	python3 scripts/stage_plug_image.py
	docker compose -f deploy/plug/docker-compose.yml up --build

# Rebuild the HNC, Auris, and QGITA evidence and require the committed bytes.
evidence:
	PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check
