# Update Process

This repository is updated through a local-edit, Git sync, and shared test-data workflow.

Git remote:
`git@github.com:Aqoouet/docx_handle.git`

## Code Sync

1. Make code changes on this local PC checkout first.
2. Commit and push the changes to GitHub.
3. On `ssh stressii-wg`, pull the latest code from GitHub:
 ```bash
 ssh stressii-wg "cd /filer/users/rymax1e/docx_handle && git pull"
 ```
4. **Stop here.** Ask the user to restart the service on `stress11` manually (see **Service Launch** below).
   Service restart requires an interactive session and cannot be done programmatically.

## Shared Test Data

1. `ssh stress11` runs the COM-based preprocessing service and writes the updated DOCX into the shared `test_data` folder.
2. `ssh stressii-wg` uses the same shared `test_data` folder and runs `report_checking` Docling conversion on the updated DOCX to produce the Markdown file.

## Service Launch

The service runs on `stress11` (Windows). Launch it from Linux via SSH.

### One-time setup (done once in an interactive session on `stress11`)

Store the share password so SSH sessions can mount `U:` automatically:
```cmd
echo EzraNehemiah1950-1952>C:\Users\rymax1e\.share_pass
```

### Start service (normal)

```bash
ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd"
```

> **Note:** Service restart on `stress11` only works from an interactive SSH session.
> Do not attempt to restart via a non-interactive shell or background command — it will not work.
> After a code update, stop at the `git pull` step and ask the user to restart the service manually.

### Start service — Cyrillic fix disabled (for testing)

```bash
ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd --no-cyr-fix"
```

The `--no-cyr-fix` flag disables Cyrillic-to-Latin transliteration in formula math nodes.
Use it to verify whether the markdown viewer handles Cyrillic in formulas natively.
Log will print `Cyrillic fix DISABLED` to confirm.

### Check service health

```bash
ssh stressii-wg "curl -s http://stress11:8000/health"
```

See [RUNBOOK.md](RUNBOOK.md) for the full test flow and log locations.

## Rules

- Do not edit the live service tree first.
- Do not assume the local checkout and the remote service tree are already in sync.
- Always verify the pushed commit is present on `stressii-wg` before starting the service on `stress11`.
- For formula regression testing, use the shared `test_data` folder directly instead of copying the file between hosts.
- Treat `/filer/users/rymax1e/...` and `\\e0-filer03\allcreatex\createx\rymax1e\storage` as the same shared storage, expressed in Linux and Windows path form.
- Launch the service from Linux using `scripts/ssh_start_service.cmd` — it maps `U:` automatically using `C:\Users\rymax1e\.share_pass` (not in git).
- Do not store share passwords in git. The password file `.share_pass` lives only on `stress11`.
- Runtime logs are written to `%TEMP%\\docx_handle_share_bootstrap.log` until the share is resolved, then to `%ROOT_DIR%\\logs\\service_share.log`.
- Log files are accessible from Linux at `/filer/users/rymax1e/docx_handle/logs/` (same share, Linux path). Use `ssh stressii-wg "tail -n 100 /filer/users/rymax1e/docx_handle/logs/service_share.log"` to read them.
