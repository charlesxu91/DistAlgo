from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

from distalgo.core.metrics import MetricsRegistry


class MetricsHTTPServer:
    def __init__(self, metrics: MetricsRegistry, host: str = "127.0.0.1", port: int = 0):
        self.metrics = metrics
        self.host = host
        self.port = port
        self._server = None

    def render(self) -> str:
        return self.metrics.to_prometheus_text()

    def start(self) -> HTTPServer:
        metrics = self.metrics

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib callback name
                if self.path != "/metrics":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = metrics.to_prometheus_text().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A002 - stdlib signature
                return

        self._server = HTTPServer((self.host, self.port), Handler)
        return self._server
