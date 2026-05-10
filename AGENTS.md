# Update Process

This repository is updated through a local-edit, Git sync, and shared test-data workflow.

Git remote:
`git@github.com:Aqoouet/docx_handle.git`

## Code Sync

1. Make code changes on this local PC checkout first.
2. Commit and push the changes to GitHub.
3. On `ssh stressii-wg`, pull the latest code from GitHub when you need the remote checkout updated. Here the working dir is /filer/users/rymax1e/docx_handle
4. On `ssh stress11`, launch the service from the Windows in interactive mode. use `scripts\\run_service_share.cmd`

## Shared Test Data

1. `ssh stress11` runs the COM-based preprocessing service and writes the updated DOCX into the shared `test_data` folder.
2. `ssh stressii-wg` uses the same shared `test_data` folder and runs `report_checking` Docling conversion on the updated DOCX to produce the Markdown file.

See [RUNBOOK.md](RUNBOOK.md) for the exact start commands, full test flow, and log locations.

## Rules

- Do not edit the live service tree first.
- Do not assume the local checkout and the remote service tree are already in sync.
- Always verify the pushed commit is present on `stressii-wg` before starting the service on `stress11`.
- For formula regression testing, use the shared `test_data` folder directly instead of copying the file between hosts.
- Treat `/filer/users/rymax1e/...` and `\\e0-filer03\allcreatex\createx\rymax1e\storage` as the same shared storage, expressed in Linux and Windows path form.
- The SSH start path on `stress11` should use `scripts\\run_service_share.cmd`; it maps a drive letter automatically and falls back across available letters.
- Do not store share passwords in git. If the share prompts for credentials, enter them interactively in the SSH session when `net use` asks.
- Runtime logs are written to `%TEMP%\\docx_handle_share_bootstrap.log` until the share is resolved, then to `%ROOT_DIR%\\logs\\service_share.log`.
