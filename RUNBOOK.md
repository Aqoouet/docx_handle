# Runbook

## One-time setup on `stress11`

Store the share password (run once in an interactive CMD on `stress11`):
```cmd
echo EzraNehemiah1950-1952>C:\Users\rymax1e\.share_pass
```

## Full test flow

### 1. Push code changes (local PC)

```bash
git add . && git commit -m "..." && git push
```

### 2. Pull on `stressii-wg`

```bash
ssh stressii-wg "cd /filer/users/rymax1e/docx_handle && git pull"
```

### 3. Start the service on `stress11`

Normal (Cyrillic fix enabled):
```bash
ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd"
```

Without Cyrillic fix (for testing):
```bash
ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd --no-cyr-fix"
```

### 4. Check service is healthy

```bash
ssh stressii-wg "curl -s http://stress11:8000/health"
```

Expected: `{"status": "ok"}`

### 5. Run preprocessing (sends DOCX to service, writes result to shared test_data)

```bash
ssh stressii-wg "cd /filer/users/rymax1e/docx_handle && python scripts/remote_smoke_test.py"
```

### 6. Run Docling conversion (shared test_data → Markdown)

```bash
ssh stressii-wg "cd /filer/users/rymax1e/docx_handle && ./scripts/remote_docling_convert.sh"
```

Output: `/filer/users/rymax1e/docx_handle/test_data/test_preprocessed.md`

## Log locations

| Log | Path |
|-----|------|
| Service bootstrap | `%TEMP%\docx_handle_share_bootstrap.log` on `stress11` |
| Service runtime | `U:\docx_handle\logs\service_share.log` on `stress11` |

## Feature flags

| Variable / flag | Effect |
|-----------------|--------|
| `--no-cyr-fix` arg to `ssh_start_service.cmd` | Disable Cyrillic transliteration in formula math nodes |
| `DOCX_HANDLE_NO_CYR_FIX=1` env var before `run_service_share.cmd` | Same effect |
