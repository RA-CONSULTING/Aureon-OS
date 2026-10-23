"""Master launcher UI — Dashboard and Command Center are tabs of one page.

The shell binds the launcher port (default 8080). The pro dashboard and the
command center keep serving their own pages on internal ports and appear here
as tabs. Live trading is not armed from this page.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_HOST = "127.0.0.1"
_SERVER: ThreadingHTTPServer | None = None
_THREAD: threading.Thread | None = None
_LOCK = threading.Lock()


def page_html(dashboard_url: str, command_center_url: str) -> str:
    dash = json.dumps(dashboard_url)
    command = json.dumps(command_center_url)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Aureon Master Launcher</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; font-family: Georgia, "Iowan Old Style", serif; background: #0c1110; color: #e7efe9; }}
  header {{ display: flex; align-items: center; gap: 16px; padding: 12px 18px; background: #14211c; border-bottom: 1px solid #2c463a; }}
  h1 {{ font-size: 18px; margin: 0; letter-spacing: 0.04em; }}
  .note {{ color: #b7c9bf; font-size: 13px; }}
  nav {{ display: flex; gap: 8px; padding: 10px 18px; background: #101816; }}
  button[data-tab] {{ background: #1c2e26; color: #e7efe9; border: 1px solid #3d5c4c; padding: 8px 14px; cursor: pointer; }}
  button[data-tab].active {{ background: #d8b15a; color: #1a1408; border-color: #d8b15a; }}
  iframe {{ width: 100%; height: calc(100vh - 108px); border: 0; background: #070b0a; }}
</style>
</head>
<body>
<header>
  <h1>Aureon</h1>
  <p class="note">Live trading is off. Dashboard and Command Center are tabs of this launcher.</p>
</header>
<nav>
  <button type="button" data-tab="dashboard" class="active">Dashboard</button>
  <button type="button" data-tab="command-center">Command Center</button>
</nav>
<iframe id="seat" title="Dashboard" src={dash}></iframe>
<script>
const seats = {{
  dashboard: {{ url: {dash}, title: "Dashboard" }},
  "command-center": {{ url: {command}, title: "Command Center" }}
}};
const frame = document.getElementById("seat");
document.querySelectorAll("button[data-tab]").forEach((button) => {{
  button.addEventListener("click", () => {{
    document.querySelectorAll("button[data-tab]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const seat = seats[button.dataset.tab];
    frame.title = seat.title;
    frame.src = seat.url;
  }});
}});
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    dashboard_url = "http://127.0.0.1:18080/"
    command_center_url = "http://127.0.0.1:18800/"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            body = page_html(self.dashboard_url, self.command_center_url).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            raw = b'{"ok":true,"ui":"master-launcher","live_trading":false}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_response(404)
        self.end_headers()


def start_master_ui(
    port: int | None = None,
    *,
    dashboard_url: str = "http://127.0.0.1:18080/",
    command_center_url: str = "http://127.0.0.1:18800/",
) -> dict[str, Any]:
    global _SERVER, _THREAD
    chosen = int(os.environ.get("AUREON_UI_PORT", "8080") if port is None else port)
    with _LOCK:
        if _SERVER is not None and _THREAD is not None and _THREAD.is_alive():
            bound = int(_SERVER.server_address[1])
            return {"ok": True, "port": bound, "url": f"http://{_HOST}:{bound}/"}
        handler = type(
            "MasterLauncherHandler",
            (_Handler,),
            {"dashboard_url": dashboard_url, "command_center_url": command_center_url},
        )
        server = ThreadingHTTPServer((_HOST, chosen), handler)
        thread = threading.Thread(target=server.serve_forever, name="master-launcher-ui", daemon=True)
        thread.start()
        _SERVER = server
        _THREAD = thread
        bound = int(server.server_address[1])
    return {"ok": True, "port": bound, "url": f"http://{_HOST}:{bound}/"}


def stop_master_ui() -> None:
    global _SERVER, _THREAD
    with _LOCK:
        server, thread = _SERVER, _THREAD
        _SERVER = None
        _THREAD = None
    if server is not None:
        server.shutdown()
        server.server_close()
    if thread is not None:
        thread.join(timeout=2.0)
