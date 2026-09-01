# Continuous runtime status: terminal HOLD

No Aureon process is authorized to run forever or auto-restart. Supervisor,
systemd, Docker Compose, and installer configurations use terminal HOLD routes
with retries disabled. Previous keepalive and restart instructions are
withdrawn.

Native containment and an externally anchored HNC ledger are prerequisites for
a future continuous-runtime design.
