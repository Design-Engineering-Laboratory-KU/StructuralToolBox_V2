#!/bin/bash
# インストール先フォルダで実行。手順とメッセージは setup_runtime.py にある。
# インストーラからは Install_once.command --silent で呼び出す。
set -u

cd "$(dirname "$0")"
ROOT="$(pwd)"

SILENT=0
if [[ "${1:-}" == "--silent" || "${1:-}" == "/silent" ]]; then
  SILENT=1
fi

pause_if_needed() {
  if [[ "$SILENT" == "1" ]]; then
    return 0
  fi
  echo
  read -r -p "Enter キーを押すと閉じます... " _
}

case "$(uname -m)" in
  arm64) EMBED="python-standalone-arm64" ;;
  x86_64) EMBED="python-standalone-x64" ;;
  *)
    echo "[エラー] 未対応の CPU です: $(uname -m)"
    pause_if_needed
    exit 1
    ;;
esac

PY="$ROOT/$EMBED/bin/python3"
if [[ ! -e "$PY" ]]; then
  echo "[エラー] 同梱の Python が見つかりません: $EMBED/"
  echo "配布ファイルを展開し直すか、教員に連絡してください。"
  pause_if_needed
  exit 1
fi

# ダウンロード時に付く検疫属性を外し、実行できる状態にする
xattr -cr "$ROOT/$EMBED" 2>/dev/null || true
chmod +x "$PY" 2>/dev/null || true

if [[ "$SILENT" == "1" ]]; then
  "$PY" "$ROOT/setup_runtime.py" --silent
  exit $?
fi

"$PY" "$ROOT/setup_runtime.py"
RC=$?
echo
echo "次回からは「Start Structural Toolbox.command」"
echo "またはアプリケーションフォルダの「Structural Toolbox」から起動してください。"
pause_if_needed
exit "$RC"
