# docx_handle

Small DOCX cleanup service for Microsoft Word automation on Windows.

The service:

- accepts a `.docx` upload over HTTP
- converts Word cross-reference fields into plain text
- removes text marked as hidden in Word
- returns the updated `.docx`

The service is designed to run from a user home directory on `stress11` using a local virtual environment. No system-wide Python installation changes are required.

## API

### `GET /health`

Returns:

```json
{"status":"ok"}
```

### `POST /convert`

Accepts `multipart/form-data` with a single field named `file`.

The response is the transformed `.docx` with:

- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment`

## Local run

```bash
python3 scripts/bootstrap_venv.py
./.venv/bin/python -m docx_handle.cli --host 0.0.0.0 --port 8000
```

On Windows:

```powershell
python scripts\bootstrap_venv.py
.\.venv\Scripts\python.exe -m docx_handle.cli --host 0.0.0.0 --port 8000
```

## Stress11 deployment model

Copy the source tree into the home directory of `rymax1e` on `stress11`, then create a local `.venv` there and install requirements into that environment.

Recommended layout on the host:

```text
~/docx_handle/
  .venv/
  docx_handle/
  scripts/
  requirements.txt
  README.md
```

The service should be started from that directory with the local venv Python:

```powershell
.\.venv\Scripts\python.exe -m docx_handle.cli --host 0.0.0.0 --port 8000
```

If you are starting from the shared Windows storage over SSH, use the share launcher:

```bat
set DOCX_HANDLE_DRIVE=U
scripts\run_service_share.cmd
```

The launcher will try the preferred drive letter first and then fall back to other free letters.
If the share needs a password, `net use` will prompt for it interactively.
Startup details are written to:
- `%TEMP%\docx_handle_share_bootstrap.log` before the share is resolved
- `%ROOT_DIR%\logs\service_share.log` after the repo and venv are found

To run the full preprocess + Docling test after the service is already up:

```bat
scripts\run_full_test.cmd
```

That writes its console log to `%ROOT_DIR%\logs\full_test.log`.

See [RUNBOOK.md](RUNBOOK.md) for the full start + test flow and log locations.

## Notes

- The Word automation worker is single-threaded and processes one document at a time.
- Cross-reference detection is intentionally conservative and targets Word field codes such as `REF`, `PAGEREF`, and `NOTEREF`.
- Hidden text removal uses Word's formatting search and replace, so the transformation depends on Word being available on the host.
