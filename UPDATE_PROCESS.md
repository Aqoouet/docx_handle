# Update Process

This repository is updated through a local-edit, Git sync, and shared test-data workflow.

Git remote:
`git@github.com:Aqoouet/docx_handle.git`

## Code Sync

1. Make code changes on this local PC checkout first.
2. Commit and push the changes to GitHub.
3. On `stressii-wg`, pull the latest code from GitHub when you need the remote checkout updated.
4. On `stress11`, launch the service from the Windows share path:
   `\\e0-filer03\allcreatex\createx\rymax1e\storage`
   or use `scripts\\run_service_share.cmd` after setting `DOCX_HANDLE_DRIVE` to a preferred letter such as `U`.

## Shared Test Data

1. `stress11` runs the COM-based preprocessing service and writes the updated DOCX into the shared `test_data` folder.
2. `stressii-wg` uses the same shared `test_data` folder and runs `report_checking` Docling conversion on the updated DOCX to produce the Markdown file.

## Rules

- Do not edit the live service tree first.
- Do not assume the local checkout and the remote service tree are already in sync.
- Always verify the pushed commit is present on `stressii-wg` before starting the service on `stress11`.
- For formula regression testing, use the shared `test_data` folder directly instead of copying the file between hosts.
- Treat `/filer/users/rymax1e/...` and `\\e0-filer03\allcreatex\createx\rymax1e\storage` as the same shared storage, expressed in Linux and Windows path form.
- The SSH start path on `stress11` should use `scripts\\run_service_share.cmd`; it maps a drive letter automatically and falls back across available letters.
- Do not store share passwords in git. If the share prompts for credentials, enter them interactively in the SSH session when `net use` asks.
