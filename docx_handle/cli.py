from __future__ import annotations

import argparse

from .http_server import serve


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DOCX cleanup service.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    args = parser.parse_args()
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

