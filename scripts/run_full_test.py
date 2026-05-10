from __future__ import annotations

import argparse
import http.client
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _multipart_body(filename: str, content: bytes, boundary: str) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + content + tail


def _request_convert(host: str, port: int, input_path: Path, output_path: Path) -> None:
    print(f"[local] preprocessing {input_path}")
    boundary = "----docx-handle-full-test-boundary"
    body = _multipart_body(input_path.name, input_path.read_bytes(), boundary)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    conn = http.client.HTTPConnection(host, port, timeout=600)
    conn.request("POST", "/convert", body=body, headers=headers)
    response = conn.getresponse()
    response_body = response.read()
    if response.status != 200:
        raise RuntimeError(f"docx_handle returned HTTP {response.status} {response.reason}: {response_body!r}")
    output_path.write_bytes(response_body)
    print(f"[local] wrote preprocessed DOCX: {output_path}")


def _ssh_capture(host: str, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", host, command],
        check=False,
        text=True,
        capture_output=True,
    )


def _remote_docling_convert(
    report_checking_root: str,
    linux_input_path: Path,
    linux_output_path: Path,
    docling_container_name: str,
    ) -> None:
    print("[remote] resolving docling container IP")
    ip_proc = _ssh_capture(
        "stressii-wg",
        f"docker inspect {shlex.quote(docling_container_name)} --format '{{{{range.NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}'",
    )
    if ip_proc.returncode != 0:
        if ip_proc.stdout.strip():
            print(ip_proc.stdout.rstrip())
        if ip_proc.stderr.strip():
            print(ip_proc.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError(
            f"Failed to resolve Docling container IP on stressii-wg (exit {ip_proc.returncode})."
        )
    docling_ip = ip_proc.stdout.strip()
    if not docling_ip:
        raise RuntimeError("Could not resolve the Docling container IP on stressii-wg.")

    python_code = (
        "from pathlib import Path\n"
        "from backend.app.docling_client import convert_file_to_md\n"
        f"src = Path({linux_input_path.as_posix()!r})\n"
        f"out = Path({linux_output_path.as_posix()!r})\n"
        "md = convert_file_to_md(str(src))\n"
        "out.write_text(md, encoding='utf-8')\n"
        "print(f'Wrote {out}')\n"
        "print(f'MD bytes: {len(md.encode(\"utf-8\"))}')\n"
    )
    remote_command = (
        f"cd {shlex.quote(report_checking_root)} && "
        "if [ -x backend/.venv/bin/python ]; then PYTHON=backend/.venv/bin/python; "
        "else PYTHON=python3; fi && "
        f"DOCLING_URL=http://{docling_ip}:5001 \"$PYTHON\" -c {shlex.quote(python_code)}"
    )

    print(f"[remote] converting via docling at {docling_ip}:5001")
    proc = _ssh_capture("stressii-wg", remote_command)
    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"Docling conversion failed on stressii-wg (exit {proc.returncode}).")
    print(f"[remote] wrote markdown: {linux_output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full DOCX preprocessing + Docling conversion test.")
    parser.add_argument(
        "--input",
        default=str(REPO_ROOT / "test_data" / "A320_ESG-855_01-SR_Part14_MSN05031_TH-003999231_template_v2_1.docx"),
        help="Input DOCX path for the local preprocessing service.",
    )
    parser.add_argument("--service-host", default="127.0.0.1", help="docx_handle service host.")
    parser.add_argument("--service-port", type=int, default=8000, help="docx_handle service port.")
    parser.add_argument(
        "--linux-shared-root",
        default="/filer/users/rymax1e/docx_handle/test_data",
        help="Shared Linux path where the updated DOCX and Markdown should be written on stressii-wg.",
    )
    parser.add_argument(
        "--report-checking-root",
        default="/home/rymax1e/report_checking",
        help="report_checking checkout root on stressii-wg.",
    )
    parser.add_argument(
        "--docling-container-name",
        default="report-checker-docling",
        help="Docling container name on stressii-wg.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input DOCX not found: {input_path}")

    preprocessed_path = input_path.with_name(f"{input_path.stem}_preprocessed.docx")
    markdown_path = input_path.with_name(f"{input_path.stem}_preprocessed.md")

    _request_convert(args.service_host, args.service_port, input_path, preprocessed_path)

    linux_root = Path(args.linux_shared_root)
    linux_input = linux_root / preprocessed_path.name
    linux_output = linux_root / markdown_path.name
    if not linux_input.exists():
        raise FileNotFoundError(f"Preprocessed DOCX is not visible from stressii-wg shared path: {linux_input}")

    _remote_docling_convert(
        args.report_checking_root,
        linux_input,
        linux_output,
        args.docling_container_name,
    )

    print("[done] full test complete")
    print(f"[done] preprocessed DOCX: {preprocessed_path}")
    print(f"[done] markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
