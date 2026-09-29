#!/bin/bash
# 配布フォルダ直下でダブルクリックする Mac 用インストーラ。
set -u

cd "$(dirname "$0")"
HERE="$(pwd)"
PAYLOAD="$HERE/payload"
DEST="$HOME/Library/Application Support/StructuralToolbox"

echo
echo "========================================"
echo " Structural Toolbox インストーラ"
echo "========================================"
echo
echo "インストール先:"
echo "  $DEST"
echo
echo "Python と解析ライブラリは同梱です（インターネット接続は不要・2〜5 分）。"
echo

if ! osascript >/dev/null <<'EOF'
display dialog "Structural Toolbox をこの Mac にインストールします。

Python と解析ライブラリは同梱されています（インターネット接続は不要・2〜5 分）。

続行しますか？" buttons {"キャンセル", "インストール"} default button "インストール" cancel button "キャンセル" with title "Structural Toolbox"
EOF
then
  echo "キャンセルしました。"
  exit 0
fi

if [[ ! -d "$PAYLOAD" ]]; then
  echo "[エラー] payload フォルダがありません: $PAYLOAD"
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) SKIP="python-standalone-x64"; SKIP_WHEELS="*x86_64.whl" ;;
  x86_64) SKIP="python-standalone-arm64"; SKIP_WHEELS="*arm64.whl" ;;
  *)
    echo "[エラー] 未対応の CPU です: $ARCH"
    read -r -p "Enter キーを押すと閉じます... " _
    exit 1
    ;;
esac

mkdir -p "$DEST"
echo "ファイルをコピーしています..."
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude '.venv' --exclude 'install.log' --exclude "$SKIP" "$PAYLOAD/" "$DEST/"
else
  cp -R "$PAYLOAD/." "$DEST/"
  rm -rf "$DEST/$SKIP"
fi

# この Mac で使わない CPU 向けのライブラリは残さない
find "$DEST/wheels" -name "$SKIP_WHEELS" -delete 2>/dev/null || true

xattr -cr "$DEST" 2>/dev/null || true
chmod +x \
  "$DEST/Install_once.command" \
  "$DEST/Start Structural Toolbox.command" \
  "$DEST/Start Structural Toolbox (debug).command" \
  "$DEST/Uninstall.command" \
  "$DEST/create_launchers.sh" \
  2>/dev/null || true

echo
echo "同梱のライブラリをセットアップしています（2〜5 分）..."
if ! /bin/bash "$DEST/Install_once.command" --silent; then
  osascript <<EOF || true
display dialog "セットアップに失敗しました。もう一度「インストール.command」を実行してください。

詳細ログ:
$DEST/install.log" buttons {"OK"} default button 1 with title "Structural Toolbox"
EOF
  echo "[エラー] セットアップに失敗しました。ログ: $DEST/install.log"
  read -r -p "Enter キーを押すと閉じます... " _
  exit 1
fi

/bin/bash "$DEST/create_launchers.sh"

osascript <<'EOF' || true
display dialog "インストールが完了しました。

デスクトップ、またはアプリケーションフォルダの「Structural Toolbox」から起動できます。

終了するときは、開いたターミナルのウィンドウを閉じてください。" buttons {"OK"} default button 1 with title "Structural Toolbox"
EOF

echo
echo "完了しました。"
read -r -p "Enter キーを押すと閉じます... " _
exit 0
