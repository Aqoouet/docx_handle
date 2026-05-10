@echo off
setlocal EnableExtensions

set "SHARE=\\e0-filer03\allcreatex\createx\rymax1e\storage"
set "SERVICE_DIR=docx_handle"
set "PREFERRED_DRIVE=%DOCX_HANDLE_DRIVE%"
set "SHARE_USER=%DOCX_HANDLE_USER%"
set "ROOT_DIR="
set "BOOT_LOG=%TEMP%\docx_handle_share_bootstrap.log"
set "LOG_FILE="

if "%PREFERRED_DRIVE%"=="" set "PREFERRED_DRIVE=U"
if "%SHARE_USER%"=="" set "SHARE_USER=rymax1e"
set "PREFERRED_DRIVE=%PREFERRED_DRIVE::=%"

call :log_boot "Launcher started"
call :log_boot "Share=%SHARE%"
call :log_boot "Preferred drive=%PREFERRED_DRIVE%"
call :log_boot "Share user=%SHARE_USER%"

call :try_drive %PREFERRED_DRIVE%
if not defined ROOT_DIR (
  for %%D in (U V W X Y Z) do (
    if not defined ROOT_DIR call :try_drive %%D
  )
)

if not defined ROOT_DIR (
  call :log_boot "Drive mapping failed, trying UNC pushd fallback"
  pushd "%SHARE%\%SERVICE_DIR%" >nul 2>&1
  if not errorlevel 1 (
    set "ROOT_DIR=%CD%"
    popd
    call :log_boot "UNC fallback succeeded"
  ) else (
    call :log_boot "UNC fallback failed"
  )
)

if not defined ROOT_DIR (
  call :log_boot "Failed to map %SHARE% to a usable drive letter"
  echo Failed to map %SHARE% to a usable drive letter.
  exit /b 1
)

if not exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
  call :log_boot "Missing virtual environment: %ROOT_DIR%\.venv\Scripts\python.exe"
  echo Missing virtual environment: %ROOT_DIR%\.venv\Scripts\python.exe
  exit /b 1
)

if not exist "%ROOT_DIR%\logs" mkdir "%ROOT_DIR%\logs"
set "LOG_FILE=%ROOT_DIR%\logs\service_share.log"

call :log "Resolved ROOT_DIR=%ROOT_DIR%"

call :log "Killing any existing docx_handle process on port 8000"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
  call :log "Terminating PID %%P"
  taskkill /PID %%P /F >nul 2>&1
)

call :log "Starting docx_handle on 0.0.0.0:8000"

cd /d "%ROOT_DIR%"
set "CYR_FLAG="
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="1" set "CYR_FLAG=--no-cyr-fix"
if /i "%DOCX_HANDLE_NO_CYR_FIX%"=="true" set "CYR_FLAG=--no-cyr-fix"
if defined CYR_FLAG call :log "Cyrillic fix DISABLED (DOCX_HANDLE_NO_CYR_FIX=%DOCX_HANDLE_NO_CYR_FIX%)"
call "%ROOT_DIR%\.venv\Scripts\python.exe" -u -m docx_handle.cli --host 0.0.0.0 --port 8000 %CYR_FLAG% >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
call :log "Service exited with code %EXIT_CODE%"
exit /b %EXIT_CODE%

:try_drive
set "DRIVE=%~1"
set "DRIVE=%DRIVE::=%"
call :log_boot "Trying drive %DRIVE%"

if exist "%DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
  set "ROOT_DIR=%DRIVE%:\%SERVICE_DIR%"
  call :log_boot "Drive %DRIVE% already mapped"
  exit /b 0
)

call :log_boot "Mapping drive %DRIVE% to %SHARE%"
if defined SHARE_USER (
  call :log_boot "net use %DRIVE%: %SHARE% /user:%SHARE_USER% * /persistent:no"
  net use %DRIVE%: "%SHARE%" /user:%SHARE_USER% * /persistent:no >nul 2>&1
) else (
  call :log_boot "net use %DRIVE%: %SHARE% /persistent:no"
  net use %DRIVE%: "%SHARE%" /persistent:no >nul 2>&1
)
if errorlevel 1 (
  call :log_boot "Drive %DRIVE% mapping failed"
  exit /b 0
)

if exist "%DRIVE%:\%SERVICE_DIR%\docx_handle\cli.py" (
  set "ROOT_DIR=%DRIVE%:\%SERVICE_DIR%"
  call :log_boot "Drive %DRIVE% mapped successfully"
) else (
  call :log_boot "Drive %DRIVE% mapped but repo files were not found"
)
exit /b 0

:log_boot
set "MESSAGE=%~1"
echo [%date% %time%] %MESSAGE%
>> "%BOOT_LOG%" echo [%date% %time%] %MESSAGE%
if defined LOG_FILE >> "%LOG_FILE%" echo [%date% %time%] %MESSAGE%
exit /b 0

:log
set "MESSAGE=%~1"
echo [%date% %time%] %MESSAGE%
>> "%BOOT_LOG%" echo [%date% %time%] %MESSAGE%
if defined LOG_FILE >> "%LOG_FILE%" echo [%date% %time%] %MESSAGE%
exit /b 0
