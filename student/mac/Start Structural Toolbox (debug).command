#!/bin/bash
set -u
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python3" && ! -x ".venv/bin/python" ]]; then
  echo "先に Install_once.command を実行してください。"
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
fi

VENV_PY=".venv/bin/python3"
if [[ ! -x "$VENV_PY" ]]; then
  VENV_PY=".venv/bin/python"
fi

LOG="$(pwd)/stb_gui.log"
echo "========================================"
echo " Structural Toolbox - debug mode"
echo "========================================"
echo " Log file: $LOG"
echo " URL: http://127.0.0.1:8765/"
echo " このウィンドウを閉じるとサーバーが止まります。"
echo "========================================"
echo

"$VENV_PY" -u -m stb_cli gui --log-file "$LOG"
RC=$?
echo
read -r -p "Enter キーを押すと閉じます... " _
exit "$RC"
