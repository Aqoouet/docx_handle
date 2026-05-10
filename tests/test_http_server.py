from __future__ import annotations

from email.message import Message
from io import BytesIO
from types import SimpleNamespace

from docx_handle.http_server import DOCX_MIME_TYPE, DocxHandleRequestHandler


class FakeProcessor:
    def __init__(self):
        self.calls = []

    def start(self) -> None:
        return

    def close(self) -> None:
        return

    def process_bytes(self, filename: str, content: bytes) -> bytes:
        self.calls.append((filename, content))
        return b"updated-docx"


def test_health_and_convert_endpoints():
    processor = FakeProcessor()
    boundary = "----docx-handle-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="sample.docx"\r\n'
        f"Content-Type: {DOCX_MIME_TYPE}\r\n\r\n"
        "payload"
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    headers = Message()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    headers["Content-Length"] = str(len(body))

    handler = object.__new__(DocxHandleRequestHandler)
    handler.server = SimpleNamespace(processor=processor)
    handler.path = "/health"
    handler.headers = headers
    handler.rfile = BytesIO(b"")
    handler.wfile = BytesIO()
    handler._status = None
    handler._headers = []

    def send_response(status):
        handler._status = status

    def send_header(name, value):
        handler._headers.append((name, value))

    def end_headers():
        return None

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers

    handler.do_GET()
    assert handler._status == 200
    assert handler.wfile.getvalue() == b'{"status": "ok"}'

    handler.path = "/convert"
    handler.headers = headers
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    handler._status = None
    handler._headers = []
    handler.do_POST()

    assert handler._status == 200
    assert handler.wfile.getvalue() == b"updated-docx"
    assert processor.calls == [("sample.docx", b"payload")]
    assert ("Content-Type", DOCX_MIME_TYPE) in handler._headers
