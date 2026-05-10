@echo off
setlocal
set ROOT_DIR=%~dp0..
if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
cd /d "%ROOT_DIR%"
call "%ROOT_DIR%\.venv\Scripts\python.exe" -u -m docx_handle.cli --host 127.0.0.1 --port 8001 >> "%ROOT_DIR%\logs\service_8001.log" 2>&1

