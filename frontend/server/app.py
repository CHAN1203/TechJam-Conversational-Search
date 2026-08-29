from __future__ import annotations

import argparse
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

from frontend.server.transcript import (
    DEFAULT_CATALOG,
    DEFAULT_DATASET,
    DEFAULT_GAZETTEER,
    SessionRunner,
)


MAX_BODY_BYTES = 4096


class ViewerHandler(BaseHTTPRequestHandler):
    runner: SessionRunner

    def do_OPTIONS(self) -> None:
        self._send(204, None)

    def do_GET(self) -> None:
        if self.path.startswith("/api/health"):
            self._send(200, {
                "ok": True,
                "sample_count": self.runner.sample_count,
                "agent": self.runner.agent_config(),
            })
        elif self.path.startswith("/api/samples"):
            self._send(200, {"samples": self.runner.listing()})
        else:
            self._send(404, {"error": f"no route for {self.path}"})

    def do_POST(self) -> None:
        if not self.path.startswith("/api/run"):
            self._send(404, {"error": f"no route for {self.path}"})
            return
        try:
            body = json.loads(self._read_body() or "{}")
            number = body.get("sample")
        except ValueError as error:
            self._send(400, {"error": f"invalid JSON body: {error}"})
            return
        try:
            self._send(200, self.runner.run(number))
        except ValueError as error:
            self._send(400, {"error": str(error)})
        except Exception as error:  # noqa: BLE001 - surface the failure in the UI
            traceback.print_exc()
            self._send(500, {"error": f"{type(error).__name__}: {error}"})

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        return self.rfile.read(length).decode("utf-8")

    def _send(self, status: int, payload: object) -> None:
        encoded = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if encoded:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        # Loopback-only development server; permissive CORS so the page also
        # works when opened outside the Vite proxy.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if encoded:
            self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        print(f"  {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local evaluation session viewer API")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--gazetteer", default=DEFAULT_GAZETTEER)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"indexing {args.catalog} ...")
    ViewerHandler.runner = SessionRunner(args.catalog, args.dataset, args.gazetteer)
    config = ViewerHandler.runner.agent_config()
    print(
        f"ready: {ViewerHandler.runner.sample_count} samples, "
        f"{config['catalog_size']} products, "
        f"policy={config['clarification_policy']}, pool={config['candidate_pool_size']}"
    )

    # Single-threaded on purpose: the agent's SQLite connection is created with
    # check_same_thread=True, so a threading server would raise on the second
    # request. One user, one request at a time is the right model here.
    server = HTTPServer(("127.0.0.1", args.port), ViewerHandler)
    print(f"listening on http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
