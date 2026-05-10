from __future__ import annotations

import argparse
import logging

from .http_server import serve


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DOCX cleanup service.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument(
        "--no-cyr-fix",
        action="store_true",
        default=False,
        help="Disable Cyrillic-to-Latin transliteration in formula math nodes.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    serve(args.host, args.port, fix_cyr=not args.no_cyr_fix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
