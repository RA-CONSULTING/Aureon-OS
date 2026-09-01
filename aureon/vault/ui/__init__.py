"""
Aureon Vault UI — authenticated loopback HOLD-only inspection API.

Usage:
    from aureon.vault.ui import create_app, run_server

    # As a standalone server:
    run_server(host="127.0.0.1", port=5566)

    # Programmatic factory-owned inert app:
    app = create_app()
"""

from aureon.vault.ui.server import create_app, run_server

__all__ = ["create_app", "run_server"]
