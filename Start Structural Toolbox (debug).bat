@echo off
chcp 65001 >nul
title Structural Toolbox (debug)
cd /d "%~dp0"

REM 単行の if だけを使う（理由は Start Structural Toolbox.bat のコメント参照）。
if not exist ".venv\Scripts\python.exe" echo [エラー] 先に Install_once.bat を実行してください。
if not exist ".venv\Scripts\python.exe" pause
if not exist ".venv\Scripts\python.exe" exit /b 1

set "LOG=%~dp0stb_gui.log"
echo ========================================
echo  Structural Toolbox - debug mode
echo ========================================
echo  Console: this window
echo  Log file: %LOG%
echo  URL: http://127.0.0.1:8765/
echo  Close this window to stop the server.
echo ========================================
echo.

REM -u = unbuffered stdout; window stays open via cmd /k
cmd /k ""%CD%\.venv\Scripts\python.exe" -u -m stb_cli gui --log-file "%LOG%""
