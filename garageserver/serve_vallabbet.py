from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class VallabbetHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        if self.path.startswith("/data/live/") or self.path.startswith("/data/fallback/"):
            self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Vallabbet with CORS headers for live JSON.")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--directory", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    handler = lambda *handler_args, **handler_kwargs: VallabbetHandler(  # noqa: E731
        *handler_args,
        directory=args.directory,
        **handler_kwargs,
    )
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"Serving Vallabbet from {args.directory} on http://{args.bind}:{args.port}/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
