@echo off
:: Bootstrap script for SSH sessions where U: is not yet mounted.
:: Requires credentials stored in Windows Credential Manager:
::   cmdkey /add:e0-filer03 /user:rymax1e /pass:YOUR_PASSWORD
::
:: Usage (from SSH):
::   ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd"
::   ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd --no-cyr-fix"

setlocal EnableExtensions

set "SHARE=\\e0-filer03\allcreatex\createx\rymax1e\storage"
set "PREFERRED_DRIVE=U"
set "SERVICE_DIR=docx_handle"

:: Pass --no-cyr-fix if given as argument OR env var is set
set "CYR_ARG="
if /i "%~1"=="--no-cyr-fix" set "CYR_ARG=--no-cyr-fix"
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="1" set "CYR_ARG=--no-cyr-fix"
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="true" set "CYR_ARG=--no-cyr-fix"

:: Map U: if not already mapped
if exist "%PREFERRED_DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
    echo [ssh_start] Drive %PREFERRED_DRIVE%: already mapped
) else (
    echo [ssh_start] Mapping %PREFERRED_DRIVE%: from stored credentials ...
    net use %PREFERRED_DRIVE%: "%SHARE%" /persistent:no >nul 2>&1
    if errorlevel 1 (
        echo [ssh_start] ERROR: failed to map %PREFERRED_DRIVE%: - run once interactively:
        echo   cmdkey /add:e0-filer03 /user:rymax1e /pass:YOUR_PASSWORD
        exit /b 1
    )
    echo [ssh_start] Drive %PREFERRED_DRIVE%: mapped OK
)

if defined CYR_ARG echo [ssh_start] Cyrillic fix DISABLED

echo [ssh_start] Starting service ...
set "DOCX_HANDLE_NO_CYR_FIX="
if /i "%CYR_ARG%"=="--no-cyr-fix" set "DOCX_HANDLE_NO_CYR_FIX=1"

call "%PREFERRED_DRIVE%:\%SERVICE_DIR%\scripts\run_service_share.cmd"
