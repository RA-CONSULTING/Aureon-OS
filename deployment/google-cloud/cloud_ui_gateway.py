"""Distinct systemd process identity for the built-asset UI/API gateway."""
from cloud_http_runtime import run

if __name__ == "__main__":
    raise SystemExit(run("ui-gateway"))
