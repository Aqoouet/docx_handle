from __future__ import annotations

import argparse
import http.client
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from docx_handle.http_server import DocxHandleHTTPServer
from docx_handle.word_service import build_processor


def _multipart_body(filename: str, content: bytes, boundary: str) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + content + tail


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an end-to-end API smoke test against the local service.")
    parser.add_argument("--input", required=True, help="Input DOCX path.")
    parser.add_argument("--output", required=True, help="Output DOCX path.")
    parser.add_argument("--host", default="127.0.0.1", help="Service host.")
    parser.add_argument("--port", type=int, default=8000, help="Service port.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    processor = build_processor()
    processor.start()
    server = DocxHandleHTTPServer(("127.0.0.1", 0), processor)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        boundary = "----docx-handle-smoke-boundary"
        body = _multipart_body(input_path.name, input_path.read_bytes(), boundary)
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        }
        conn = http.client.HTTPConnection(args.host, args.port, timeout=120)
        conn.request("POST", "/convert", body=body, headers=headers)
        response = conn.getresponse()
        response_body = response.read()
        if response.status != 200:
            raise RuntimeError(f"Smoke test failed: HTTP {response.status} {response.reason}: {response_body!r}")
        output_path.write_bytes(response_body)
        print(f"Wrote {output_path}")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        processor.close()


if __name__ == "__main__":
    raise SystemExit(main())
