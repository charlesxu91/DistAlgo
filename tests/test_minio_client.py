import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from distalgo.core.minio_client import MinIOCheckpointClient, MinIOClientConfig
from distalgo.core.object_checkpoint import ObjectCheckpointStore


class InMemoryS3Handler(BaseHTTPRequestHandler):
    buckets = set()
    objects = {}

    def do_HEAD(self):  # noqa: N802
        parts = self.path.strip("/").split("/", 1)
        if len(parts) == 1 and parts[0] in self.buckets:
            self.send_response(200)
        elif len(parts) == 2 and (parts[0], parts[1]) in self.objects:
            self.send_response(200)
        else:
            self.send_response(404)
        self.end_headers()

    def do_PUT(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        parts = self.path.strip("/").split("/", 1)
        if len(parts) == 1:
            self.buckets.add(parts[0])
        else:
            self.objects[(parts[0], parts[1])] = body
        self.send_response(200)
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parts = self.path.strip("/").split("/", 1)
        body = self.objects[(parts[0], parts[1])]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        return


class MinIOClientTest(unittest.TestCase):
    def test_minio_checkpoint_client_round_trips_against_s3_compatible_http_service(self):
        InMemoryS3Handler.buckets = set()
        InMemoryS3Handler.objects = {}
        try:
            server = HTTPServer(("127.0.0.1", 0), InMemoryS3Handler)
        except PermissionError as exc:
            self.skipTest(f"socket bind is not permitted in this sandbox: {exc}")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_address[1]}"
            client = MinIOCheckpointClient(
                MinIOClientConfig(endpoint=endpoint, access_key="distalgo", secret_key="distalgo-password")
            )
            client.ensure_bucket("distalgo-checkpoints")
            store = ObjectCheckpointStore(client, bucket="distalgo-checkpoints", prefix="jobs")

            store.save("pagerank", 4, {"scores": {1: 0.25, 2: 0.75}})

            self.assertTrue(store.exists("pagerank", 4))
            self.assertEqual(store.load("pagerank", 4)["scores"][2], 0.75)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
