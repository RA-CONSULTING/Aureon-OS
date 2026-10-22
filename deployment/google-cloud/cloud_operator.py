"""Distinct systemd process identity for the private production operator."""
from cloud_http_runtime import run

if __name__ == "__main__":
    raise SystemExit(run("operator"))
