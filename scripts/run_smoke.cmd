@echo off
setlocal
set ROOT_DIR=%~dp0..
if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
cd /d "%ROOT_DIR%"
call "%ROOT_DIR%\.venv\Scripts\python.exe" "%ROOT_DIR%\scripts\remote_smoke_test.py" %* >> "%ROOT_DIR%\logs\smoke.log" 2>&1
