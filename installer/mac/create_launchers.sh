#!/bin/bash
# ~/Applications に起動用アプリとデスクトップのショートカットを作る。
set -u

DEST="$HOME/Library/Application Support/StructuralToolbox"
APPS="$HOME/Applications"
mkdir -p "$APPS"

write_app() {
  local app="$1"
  local exe="$2"
  local bundle_id="$3"
  local display_name="$4"
  local mode="$5"
  local macos="$app/Contents/MacOS"

  rm -rf "$app"
  mkdir -p "$macos" "$app/Contents/Resources"
  printf '%s\n' "$mode" > "$app/Contents/Resources/mode"

  cat > "$app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>${display_name}</string>
  <key>CFBundleDisplayName</key>
  <string>${display_name}</string>
  <key>CFBundleIdentifier</key>
  <string>${bundle_id}</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleExecutable</key>
  <string>${exe}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

  cat > "$macos/$exe" <<'LAUNCH'
#!/bin/bash
set -u
unset PYTHONHOME PYTHONPATH PYTHONSTARTUP PYTHONUSERBASE VIRTUAL_ENV
export PYTHONNOUSERSITE=1
MODE="$(cat "$(dirname "$0")/../Resources/mode" 2>/dev/null || echo gui)"
DEST="$HOME/Library/Application Support/StructuralToolbox"

if [[ "${STB_IN_TERMINAL:-}" != "1" ]]; then
  osascript - "$0" <<'APPLESCRIPT'
on run argv
  set cmd to item 1 of argv
  tell application "Terminal"
    activate
    do script "export STB_IN_TERMINAL=1; /bin/bash " & quoted form of cmd
  end tell
end run
APPLESCRIPT
  exit 0
fi

cd "$DEST" || {
  echo "[エラー] インストール先が見つかりません: $DEST"
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
}

if [[ ! -x ".venv/bin/stb" ]]; then
  echo
  echo "[お知らせ] 初回セットアップがまだです。"
  echo "次をターミナルで実行してください:"
  echo "  bash \"$DEST/Install_once.command\""
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

if [[ "$MODE" == "debug" ]]; then
  LOG="$DEST/stb_gui.log"
  echo "Log file: $LOG"
  echo "URL: http://127.0.0.1:8765/"
  VENV_PY=".venv/bin/python3"
  if [[ ! -x "$VENV_PY" ]]; then
    VENV_PY=".venv/bin/python"
  fi
  "$VENV_PY" -u -m stb_cli gui --log-file "$LOG"
  RC=$?
else
  ".venv/bin/stb" gui
  RC=$?
fi

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
LAUNCH
  chmod +x "$macos/$exe"
}

write_app \
  "$APPS/Structural Toolbox.app" \
  "launch" \
  "org.structuraltoolbox.app" \
  "Structural Toolbox" \
  "gui"

write_app \
  "$APPS/Structural Toolbox (debug).app" \
  "launch-debug" \
  "org.structuraltoolbox.app.debug" \
  "Structural Toolbox (debug)" \
  "debug"

cp "$DEST/Uninstall.command" "$APPS/Structural Toolbox をアンインストール.command"
chmod +x "$APPS/Structural Toolbox をアンインストール.command"

ln -sfn "$APPS/Structural Toolbox.app" "$HOME/Desktop/Structural Toolbox"

echo "起動用アプリを作成しました:"
echo "  $APPS/Structural Toolbox.app"
echo "  $HOME/Desktop/Structural Toolbox"
