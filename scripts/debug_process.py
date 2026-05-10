from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from docx_handle.word_service import default_engine_factory


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Word engine directly and print full tracebacks.")
    parser.add_argument("--input", required=True, help="Input DOCX path.")
    parser.add_argument("--output", required=True, help="Output DOCX path.")
    args = parser.parse_args()

    engine = default_engine_factory()
    try:
        engine.process(Path(args.input), Path(args.output))
        print(f"Wrote {args.output}")
        return 0
    except Exception:  # noqa: BLE001 - this is a debug helper
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

