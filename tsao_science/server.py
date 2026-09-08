"""Loopback-only planning gateway. No endpoint executes solvers or proxies AI."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .core.jsonio import strict_dumps, strict_loads
from .registry import capabilities
from .engine import plan
from .cli import doctor


class Handler(BaseHTTPRequestHandler):
    def _allowed(self) -> bool:
        host = self.headers.get("Host", "")
        if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{host}", "http://127.0.0.1:3000", "http://localhost:3000"}

    def _reply(self, status: int, payload: dict) -> None:
        body = strict_dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._allowed():
            return self._reply(403, {"error": "origin or host rejected"})
        path = urlparse(self.path).path
        if path == "/api/science/status":
            self._reply(200, doctor())
        elif path == "/api/science/capabilities":
            self._reply(200, {"capabilities": list(capabilities().values())})
        else:
            self._reply(404, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        if not self._allowed() or self.headers.get("X-Tsao-Client") != "workspace":
            return self._reply(403, {"error": "planning client rejected"})
        if self.path != "/api/science/plan" or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._reply(404, {"error": "only JSON planning is available"})
        try:
            size = int(self.headers.get("Content-Length", "-1"))
            if not 0 < size <= 64 * 1024:
                raise ValueError("invalid planning payload size")
            self.connection.settimeout(5)
            request = strict_loads(self.rfile.read(size))
            self._reply(200, plan(request))
        except (ValueError, TypeError, OSError, KeyError) as exc:
            self._reply(400, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        # Do not log potentially sensitive material data or request payloads.
        pass


def serve(port: int = 8765) -> None:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"TsaoScience planning gateway: 127.0.0.1:{port}; execution disabled", flush=True)
        server.serve_forever()
