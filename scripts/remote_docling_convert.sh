#!/usr/bin/env bash
set -euo pipefail

SHARED_ROOT="${1:-/filer/users/rymax1e/docx_handle/test_data}"
INPUT_NAME="${2:-test_preprocessed.docx}"
REPORT_CHECKING_ROOT="${3:-/home/rymax1e/report_checking}"
CONTAINER="${4:-report-checker-docling}"

INPUT_PATH="$SHARED_ROOT/$INPUT_NAME"
OUTPUT_PATH="${INPUT_PATH%.docx}.md"

echo "[remote] resolving docling container IP"
DOCLING_IP=$(docker inspect "$CONTAINER" --format '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
if [ -z "$DOCLING_IP" ]; then
    echo "[remote] ERROR: could not resolve IP for container $CONTAINER" >&2
    exit 1
fi
echo "[remote] container $CONTAINER at $DOCLING_IP"

if [ -x "$REPORT_CHECKING_ROOT/backend/.venv/bin/python" ]; then
    PYTHON="$REPORT_CHECKING_ROOT/backend/.venv/bin/python"
else
    PYTHON=python3
fi

echo "[remote] converting $INPUT_PATH -> $OUTPUT_PATH"
cd "$REPORT_CHECKING_ROOT"
DOCLING_URL="http://$DOCLING_IP:5001" "$PYTHON" - <<EOF
from pathlib import Path
from backend.app.docling_client import convert_file_to_md
src = Path("$INPUT_PATH")
out = Path("$OUTPUT_PATH")
md = convert_file_to_md(str(src))
out.write_text(md, encoding="utf-8")
print(f"Wrote {out}")
print(f"MD bytes: {len(md.encode('utf-8'))}")
EOF

echo "[remote] done"
