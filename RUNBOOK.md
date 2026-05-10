# Runbook

This repo has two distinct workflows:

1. Start the DOCX preprocessing service on `stress11`.
2. Run the full test flow that produces a Markdown file through `report_checking` Docling.

## 1. Start the DOCX preprocessing service

Use the interactive `stress11` shell.

```bat
cd /d C:\Users\rymax1e\docx_handle
set DOCX_HANDLE_DRIVE=U
call scripts\run_service_share.cmd
```

What the launcher does:

- tries to map the shared storage to `U:` first
- falls back to `V:`, `W:`, `X:`, `Y:`, `Z:`
- if needed, prompts for the share password interactively through `net use`
- starts `docx_handle` from the share-backed repo once the mapping is ready

## 2. Run the full preprocess + Docling test

Source DOCX:

`U:\docx_handle\test_data\A320_ESG-855_01-SR_Part14_MSN05031_TH-003999231_template_v2_1.docx`

1. Start `docx_handle` on `stress11` using the command above.

Then run the automated full test from the same interactive shell:

```bat
call scripts\run_full_test.cmd
```

What it does:

1. Sends the DOCX to `http://127.0.0.1:8000/convert`.
2. Saves the returned updated DOCX into the shared `test_data` folder.
3. SSHes to `stressii-wg`.
4. Resolves the Docling container IP.
5. Runs the `report_checking` Docling conversion.
6. Writes the resulting Markdown into the same shared `test_data` folder.

The output Markdown file should live next to the DOCX, for example:

`U:\docx_handle\test_data\A320_ESG-855_01-SR_Part14_MSN05031_TH-003999231_preprocessed.md`

## 3. Where to see logs

Launcher/bootstrap log:

`%TEMP%\docx_handle_share_bootstrap.log`

Service log:

`C:\Users\rymax1e\docx_handle\logs\service_share.log`

Full test log:

`C:\Users\rymax1e\docx_handle\logs\full_test.log`

If the service is started from another repo root, the log is still written under that root's `logs` folder.

Useful runtime log messages:

- `http: convert requested ...`
- `queue: accepted ...`
- `worker: starting ...`
- `word: opening ...`
- `word: cleanup complete ...`
- `word: normalizing math text ...`
- `queue: finished ...`

## 4. Where to see the converted MD

The Docling Markdown output is written in the shared `test_data` folder on the `report_checking` side.

If you are using the sample file, expect the Markdown artifact to be adjacent to the DOCX in `test_data`.

## 5. Important notes

- Do not store share passwords in git.
- `stress11` COM preprocessing is required before Docling conversion.
- `stressii-wg` is only for the Docling conversion and Markdown verification step.
