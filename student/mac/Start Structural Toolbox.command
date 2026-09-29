#!/bin/bash
set -u
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/stb" ]]; then
  echo
  echo "[お知らせ] 初回セットアップがまだです。"
  echo "「Install_once.command」を実行してから、もう一度起動してください。"
  echo
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
fi

echo
echo "========================================"
echo " Structural Toolbox"
echo "========================================"
echo
echo "ブラウザが開きます。"
echo "このウィンドウは閉じないでください（ログが表示されます）。"
echo "終了するときはこのウィンドウを閉じてください。"
echo

".venv/bin/stb" gui
RC=$?

echo
if [[ "$RC" -eq 10 ]]; then
  echo "[お知らせ] すでに別の画面でサーバーが動いています。"
  echo "完全に終了するには、そのウィンドウを閉じてから再度起動してください。"
elif [[ "$RC" -ne 0 ]]; then
  echo "[注意] 終了コード $RC"
else
  echo "サーバーを終了しました。"
fi
echo
read -r -p "Enter キーを押すと閉じます... " _
exit "$RC"
