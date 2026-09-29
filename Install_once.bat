@echo off
REM ASCII only. All setup steps and Japanese messages live in setup_runtime.py,
REM because cmd.exe mis-reads batch files that mix non-ASCII text with calls.
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%~dp0python-embed\python.exe"
if not exist "%PY%" (
    echo [ERROR] Bundled Python was not found: python-embed\python.exe
    echo Unzip the distributed file again, or ask your instructor.
    if /i not "%~1"=="/silent" pause
    exit /b 1
)

if /i "%~1"=="/silent" (
    "%PY%" "%~dp0setup_runtime.py" --silent
    exit /b %ERRORLEVEL%
)

"%PY%" "%~dp0setup_runtime.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
