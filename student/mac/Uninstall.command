#!/bin/bash
# インストール先の外から実行する（実行中に自分のフォルダを消すため）
set -u

if [[ "${STB_UNINSTALL_FROM:-}" != "tmp" ]]; then
  cp "$0" /tmp/stb-uninstall.command
  export STB_UNINSTALL_FROM=tmp
  exec /bin/bash /tmp/stb-uninstall.command
fi

if ! osascript >/dev/null <<'EOF'
display dialog "Structural Toolbox を削除します。インストール先に保存したモデルも消えます。よろしいですか？" buttons {"キャンセル", "削除"} default button "キャンセル" cancel button "キャンセル" with title "Structural Toolbox"
EOF
then
  echo "キャンセルしました。"
  exit 0
fi

DEST="$HOME/Library/Application Support/StructuralToolbox"
rm -rf "$DEST"
rm -rf "$HOME/Applications/Structural Toolbox.app"
rm -rf "$HOME/Applications/Structural Toolbox (debug).app"
rm -f "$HOME/Applications/Structural Toolbox をアンインストール.command"
rm -f "$HOME/Desktop/Structural Toolbox"
rm -f "$HOME/Library/Application Support/Grasshopper/Libraries/StbGrasshopper.gha"

osascript <<'EOF' || true
display dialog "Structural Toolbox を削除しました。" buttons {"OK"} default button 1 with title "Structural Toolbox"
EOF
echo "削除しました。"
exit 0
