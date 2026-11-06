@echo off
chcp 65001 >nul
title Structural Toolbox
cd /d "%~dp0"
REM Ignore the PC's own Python settings; they crash the bundled interpreter.
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "VIRTUAL_ENV="
set "PYTHONNOUSERSITE=1"

REM 単行の if だけを使う（かっこ付きブロックや goto は、日本語を含む .bat で
REM cmd.exe が行の途中から実行してしまうため使わない）。
if not exist ".venv\Scripts\stb.exe" echo [お知らせ] 初回セットアップを実行します（数分かかります）。
if not exist ".venv\Scripts\stb.exe" "%~dp0python-embed\python.exe" "%~dp0setup_runtime.py"
if not exist ".venv\Scripts\stb.exe" echo.
if not exist ".venv\Scripts\stb.exe" echo [エラー] セットアップが完了していません。Install_once.bat を実行してください。
if not exist ".venv\Scripts\stb.exe" pause
if not exist ".venv\Scripts\stb.exe" exit /b 1

REM コンソールなしで起動する（pythonw.exe）。この画面はすぐ閉じます。
REM 終了するときはアプリのウィンドウを閉じるだけでよい（サーバーも止まる）。
REM ログ: %LOCALAPPDATA%\StructuralToolbox\logs\stb_gui.log
REM ログをコンソールで見たいときは「Start Structural Toolbox (debug).bat」を使う。
if exist ".venv\Scripts\pythonw.exe" start "" ".venv\Scripts\pythonw.exe" -E -s -m stb_cli gui
if exist ".venv\Scripts\pythonw.exe" exit /b 0

REM pythonw.exe がない古い .venv 向け: 従来どおりコンソールで動かす。
echo 終了するときはこの画面を閉じてください。
".venv\Scripts\stb.exe" gui
pause
