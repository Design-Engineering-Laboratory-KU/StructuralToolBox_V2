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

echo.
echo ========================================
echo  Structural Toolbox
echo ========================================
echo.
echo ブラウザが開きます。
echo この黒い画面は閉じないでください（ログが表示されます）。
echo 終了するときはこの画面を閉じてください。
echo デバッグ用: 「Start Structural Toolbox (debug).bat」
echo.

".venv\Scripts\stb.exe" gui
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="10" echo [お知らせ] すでに別の画面でサーバーが動いています。
if "%RC%"=="10" echo 完全に終了するには、その画面を閉じてから再度起動してください。
if "%RC%"=="0" echo サーバーを終了しました。
if not "%RC%"=="0" if not "%RC%"=="10" echo [注意] 終了コード %RC%
echo.
pause
exit /b %RC%
