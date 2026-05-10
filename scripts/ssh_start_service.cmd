@echo off
:: Bootstrap script for SSH sessions where U: is not yet mounted.
:: Requires C:\Users\rymax1e\.share_pass containing the share password on one line.
:: Create it once in an interactive session:
::   echo YOUR_PASSWORD>C:\Users\rymax1e\.share_pass
::
:: Usage from Linux:
::   ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd"
::   ssh stress11 "C:\Users\rymax1e\docx_handle\scripts\ssh_start_service.cmd --no-cyr-fix"

set "SHARE=\\e0-filer03\allcreatex\createx\rymax1e\storage"
set "PREFERRED_DRIVE=U"
set "SERVICE_DIR=docx_handle"
set "PASS_FILE=%USERPROFILE%\.share_pass"

set "CYR_FLAG="
if /i "%~1"=="--no-cyr-fix" set "CYR_FLAG=1"
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="1" set "CYR_FLAG=1"
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="true" set "CYR_FLAG=1"

if exist "%PREFERRED_DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
    echo [ssh_start] Drive %PREFERRED_DRIVE%: already mapped
    goto :launch
)

echo [ssh_start] Mapping %PREFERRED_DRIVE%: ...
if not exist "%PASS_FILE%" (
    echo [ssh_start] ERROR: %PASS_FILE% not found
    echo   Create it once: echo YOUR_PASSWORD^>%PASS_FILE%
    exit /b 1
)

for /f "usebackq delims=" %%P in ("%PASS_FILE%") do (
    net use %PREFERRED_DRIVE%: "%SHARE%" /user:rymax1e "%%P" /persistent:no >nul 2>&1
    if errorlevel 1 (
        echo [ssh_start] ERROR: net use failed - check password in %PASS_FILE%
        exit /b 1
    )
)

if not exist "%PREFERRED_DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
    echo [ssh_start] ERROR: mapped %PREFERRED_DRIVE%: but repo files not found
    exit /b 1
)
echo [ssh_start] Drive %PREFERRED_DRIVE%: mapped OK

:launch
if defined CYR_FLAG (
    echo [ssh_start] Cyrillic fix DISABLED
    set "DOCX_HANDLE_NO_CYR_FIX=1"
) else (
    set "DOCX_HANDLE_NO_CYR_FIX="
)
echo [ssh_start] Starting service ...
call "%PREFERRED_DRIVE%:\%SERVICE_DIR%\scripts\run_service_share.cmd"
