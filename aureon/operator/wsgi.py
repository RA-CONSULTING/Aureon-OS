"""
WSGI entrypoint for the Aureon Operator / Cognition service.

Exposes a module-level ``app`` so any production WSGI server can serve it:

    waitress-serve --port=8790 aureon.operator.wsgi:app
    gunicorn aureon.operator.wsgi:app -b 0.0.0.0:8790

The app is fully wired (config validated, cognition eagerly built and joined to
the mycelium mesh + Queen hive) via ``operator_server.build_boot_app()``.
"""

from __future__ import annotations

from aureon.operator.operator_server import build_boot_app

app = build_boot_app()

__all__ = ["app"]
