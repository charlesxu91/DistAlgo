from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from distalgo.core.job import JobRunner, load_job
from distalgo.core.runtime import LocalRuntime
from distalgo.algorithms.registry import AlgorithmRegistry
from distalgo.core.server import DistAlgoHTTPApp
from distalgo.core.benchmark import BenchmarkRunner
from distalgo.core.report import ProjectReport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="distalgo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-algorithms", help="list registered algorithms")
    list_parser.add_argument("--status", action="store_true", help="include distributed verification status")
    list_parser.add_argument("--json", action="store_true", help="emit algorithm metadata as JSON")
    subparsers.add_parser("benchmark", help="run the built-in local benchmark")
    subparsers.add_parser("report", help="print project completion report")

    serve_parser = subparsers.add_parser("serve", help="serve a minimal HTTP API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    run_parser = subparsers.add_parser("run", help="run a JSON job file")
    run_parser.add_argument("job", type=Path)
    run_parser.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "run":
        job = load_job(args.job)
        result = JobRunner(LocalRuntime.in_memory()).run(job)
        payload = _jsonable(result)
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    if args.command == "list-algorithms":
        registry = AlgorithmRegistry.default()
        metadata = registry.metadata_all()
        if args.json:
            print(json.dumps([asdict(item) for item in metadata], ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.status:
            print("name\tcategory\tstatus\tverification_level")
            for item in metadata:
                print(f"{item.name}\t{item.category}\t{item.status}\t{item.verification_level}")
            return 0
        for item in metadata:
            print(item.name)
        return 0
    if args.command == "serve":
        app = DistAlgoHTTPApp(JobRunner(LocalRuntime.in_memory()))
        server = _build_server(app, args.host, args.port)
        print(f"distalgo listening on http://{args.host}:{args.port}")
        server.serve_forever()
        return 0
    if args.command == "benchmark":
        print(json.dumps(BenchmarkRunner().run_default(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "report":
        print(ProjectReport().render())
        return 0
    return 2


def _build_server(app: DistAlgoHTTPApp, host: str, port: int) -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib callback name
            response = app.handle("GET", self.path)
            self._send(response)

        def do_POST(self):  # noqa: N802 - stdlib callback name
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            response = app.handle("POST", self.path, body)
            self._send(response)

        def _send(self, response):
            payload = response.body.encode("utf-8")
            self.send_response(response.status)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):  # noqa: A002 - stdlib signature
            return

    return HTTPServer((host, port), Handler)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
