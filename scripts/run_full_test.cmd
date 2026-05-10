@echo off
setlocal
set ROOT_DIR=%~dp0..
if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
cd /d "%ROOT_DIR%"
call "%ROOT_DIR%\.venv\Scripts\python.exe" -u "%ROOT_DIR%\scripts\run_full_test.py" --skip-docling %* >> "%ROOT_DIR%\logs\full_test.log" 2>&1
