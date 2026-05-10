@echo off
setlocal EnableExtensions

set "SHARE=\\e0-filer03\allcreatex\createx\rymax1e\storage"
set "SERVICE_DIR=docx_handle"
set "PREFERRED_DRIVE=%DOCX_HANDLE_DRIVE%"
set "SHARE_USER=%DOCX_HANDLE_USER%"
set "ROOT_DIR="

if "%PREFERRED_DRIVE%"=="" set "PREFERRED_DRIVE=U"
if "%SHARE_USER%"=="" set "SHARE_USER=rymax1e"
set "PREFERRED_DRIVE=%PREFERRED_DRIVE::=%"

call :try_drive %PREFERRED_DRIVE%
if not defined ROOT_DIR (
  for %%D in (U V W X Y Z) do (
    if not defined ROOT_DIR call :try_drive %%D
  )
)

if not defined ROOT_DIR (
  pushd "%SHARE%\%SERVICE_DIR%" >nul 2>&1
  if not errorlevel 1 (
    set "ROOT_DIR=%CD%"
    popd
  )
)

if not defined ROOT_DIR (
  echo Failed to map %SHARE% to a usable drive letter.
  exit /b 1
)

if not exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
  echo Missing virtual environment: %ROOT_DIR%\.venv\Scripts\python.exe
  exit /b 1
)

if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
cd /d "%ROOT_DIR%"
call "%ROOT_DIR%\.venv\Scripts\python.exe" -u -m docx_handle.cli --host 0.0.0.0 --port 8000 >> "%ROOT_DIR%\logs\service_share.log" 2>&1
exit /b %errorlevel%

:try_drive
set "DRIVE=%~1"
set "DRIVE=%DRIVE::=%"
if exist "%DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
  set "ROOT_DIR=%DRIVE%:\%SERVICE_DIR%"
  exit /b 0
)

if defined SHARE_USER (
  net use %DRIVE%: "%SHARE%" /user:%SHARE_USER% * /persistent:no >nul 2>&1
)
if not defined SHARE_USER (
  net use %DRIVE%: "%SHARE%" /persistent:no >nul 2>&1
)
if errorlevel 1 exit /b 0

if exist "%DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
  set "ROOT_DIR=%DRIVE%:\%SERVICE_DIR%"
)
exit /b 0
