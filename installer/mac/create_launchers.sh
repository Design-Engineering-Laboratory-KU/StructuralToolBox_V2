#!/bin/bash
# ~/Applications に起動用アプリとデスクトップのショートカットを作る。
set -u

DEST="$HOME/Library/Application Support/StructuralToolbox"
APP_VERSION="$(tr -d '[:space:]' 2>/dev/null < "$DEST/VERSION" || true)"
APP_VERSION="${APP_VERSION:-0.0.0}"
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
  <string>${APP_VERSION}</string>
  <key>CFBundleShortVersionString</key>
  <string>${APP_VERSION}</string>
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

LOG_DIR="$HOME/Library/Logs/StructuralToolbox"
LOG="$LOG_DIR/stb_gui.log"

alert() {
  osascript - "$1" <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run argv
  display dialog (item 1 of argv) buttons {"OK"} default button 1 with icon caution with title "Structural Toolbox"
end run
APPLESCRIPT
}

if [[ "$MODE" == "gui" ]]; then
  # ターミナルを開かずに起動する。ログは ~/Library/Logs/StructuralToolbox/stb_gui.log。
  # 終了はアプリのウィンドウを閉じるだけ（サーバーも止まる）。
  cd "$DEST" || { alert "インストール先が見つかりません: $DEST"; exit 1; }
  if [[ ! -x ".venv/bin/stb" ]]; then
    alert "初回セットアップがまだです。ターミナルで次を実行してください:
bash \"$DEST/Install_once.command\""
    exit 1
  fi
  mkdir -p "$LOG_DIR"
  if [[ -f "$LOG" && $(stat -f %z "$LOG" 2>/dev/null || echo 0) -gt 5242880 ]]; then
    mv -f "$LOG" "$LOG.1"
  fi
  printf '\n===== %s Structural Toolbox GUI =====\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  nohup ".venv/bin/stb" gui >> "$LOG" 2>&1 < /dev/null &
  PID=$!
  # 起動に失敗したときだけ知らせる（ポートが開けば成功とみなしてすぐ終わる）。
  for _ in $(seq 1 60); do
    if ! kill -0 "$PID" 2>/dev/null; then
      wait "$PID"
      RC=$?
      if [[ "$RC" -ne 0 && "$RC" -ne 10 ]]; then
        alert "Structural Toolbox を起動できませんでした（終了コード $RC）。
ログ: $LOG"
      fi
      exit "$RC"
    fi
    if /usr/bin/nc -z 127.0.0.1 8765 >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  disown "$PID" 2>/dev/null || true
  exit 0
fi

# debug: ログを見られるようにターミナルで動かす。
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

VENV_PY=".venv/bin/python3"
if [[ ! -x "$VENV_PY" ]]; then
  VENV_PY=".venv/bin/python"
fi
if [[ ! -x "$VENV_PY" ]]; then
  echo
  echo "[お知らせ] 初回セットアップがまだです。"
  echo "次をターミナルで実行してください:"
  echo "  bash \"$DEST/Install_once.command\""
  echo
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
fi

DEBUG_LOG="$DEST/stb_gui.log"
echo "========================================"
echo " Structural Toolbox - debug mode"
echo "========================================"
echo " Log file: $DEBUG_LOG"
echo " URL: http://127.0.0.1:8765/"
echo " アプリのウィンドウか、このウィンドウを閉じるとサーバーが止まります。"
echo "========================================"
echo
"$VENV_PY" -u -m stb_cli gui --log-file "$DEBUG_LOG"
RC=$?
echo
if [[ "$RC" -eq 10 ]]; then
  echo "[お知らせ] すでに別の画面でサーバーが動いています。"
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
