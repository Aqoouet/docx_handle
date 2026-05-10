@echo off
setlocal
set ROOT_DIR=%~dp0..
if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
cd /d "%ROOT_DIR%"
call "%ROOT_DIR%\.venv\Scripts\python.exe" "%ROOT_DIR%\scripts\debug_process.py" %* >> "%ROOT_DIR%\logs\debug.log" 2>&1
