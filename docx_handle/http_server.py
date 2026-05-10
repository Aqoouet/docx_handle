from __future__ import annotations

import json
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
from pathlib import Path
from typing import Any

from .errors import BadRequestError, DocumentProcessingError, WordAutomationUnavailableError
from .word_service import SingleWorkerDocxService, build_processor

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
logger = logging.getLogger(__name__)


class DocxHandleHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], processor: SingleWorkerDocxService):
        super().__init__(server_address, DocxHandleRequestHandler)
        self.processor = processor


class DocxHandleRequestHandler(BaseHTTPRequestHandler):
    server_version = "docx-handle/1.0"

    @property
    def processor(self) -> SingleWorkerDocxService:
        return getattr(self.server, "processor")

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return
        self._send_json(HTTPStatus.OK, {"status": "ok"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/convert":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return

        try:
            payload = self._read_upload()
            logger.info("http: convert requested filename=%s bytes=%d", payload["filename"], len(payload["content"]))
            output = self.processor.process_bytes(payload["filename"], payload["content"])
        except BadRequestError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": str(exc)})
            return
        except WordAutomationUnavailableError as exc:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": str(exc)})
            return
        except DocumentProcessingError as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - safety net
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": f"Unexpected failure: {exc}"})
            return

        filename = self._response_filename(payload["filename"])
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", DOCX_MIME_TYPE)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)
        logger.info("http: convert finished filename=%s output_bytes=%d", payload["filename"], len(output))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_upload(self) -> dict[str, bytes | str]:
        content_type = self.headers.get_content_type()
        if content_type != "multipart/form-data":
            raise BadRequestError("Expected multipart/form-data with a file field.")

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise BadRequestError("Invalid Content-Length header.") from exc

        raw_body = self.rfile.read(content_length)
        raw_message = (
            f"Content-Type: {self.headers.get('Content-Type', '')}\r\n"
            "MIME-Version: 1.0\r\n"
            "\r\n"
        ).encode("utf-8") + raw_body
        message = BytesParser(policy=default).parsebytes(raw_message)
        if not message.is_multipart():
            raise BadRequestError("Expected multipart/form-data with a file field.")

        upload = None
        for part in message.iter_parts():
            if part.get_param("name", header="content-disposition") == "file":
                upload = part
                break

        if upload is None:
            raise BadRequestError("Missing file field.")

        filename = Path(upload.get_filename() or "input.docx").name
        content = upload.get_payload(decode=True)
        if not isinstance(content, bytes):
            raise BadRequestError("Uploaded file could not be read as bytes.")
        if not content:
            raise BadRequestError("Uploaded file is empty.")
        return {"filename": filename, "content": content}

    @staticmethod
    def _response_filename(filename: str) -> str:
        stem = Path(filename).stem or "output"
        return f"{stem}_updated.docx"


def serve(host: str, port: int, processor: SingleWorkerDocxService | None = None) -> None:
    processor = processor or build_processor()
    processor.start()
    server = DocxHandleHTTPServer((host, port), processor)
    try:
        server.serve_forever()
    finally:
        server.shutdown()
        processor.close()
