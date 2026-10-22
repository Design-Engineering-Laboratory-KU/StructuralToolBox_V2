#!/bin/bash
# 新しいバージョンをコピーする前に、以前のインストールを削除する。
#
# 使い方: clean_old_install.sh <インストール先> <新しい install_manifest.txt> [以前のインストール先...]
#
# 同梱 Python と .venv を含めてすべて削除する。ただし、ユーザーが追加した
# .dat / .out / .gh / .ghx / .project.json（配布物の一覧に無いもの）は残す。
# インストール先にあるものはそのまま残し、ほかの場所の以前のインストールに
# あるものはインストール先へ移す。Structural Toolbox のインストールに見えない
# フォルダや git のチェックアウトには触れない。
# Windows の installer/clean_old_install.ps1 と同じ規則。macOS 標準の bash 3.2 で動く。
set -u

TARGET="${1:?install folder}"
MANIFEST="${2:?install_manifest.txt}"
shift 2

# 前回の初回セットアップが Grasshopper プラグインの隣に記録したインストール先も見る。
USER_HOME="${STB_USER_HOME:-$HOME}"
for location in \
  "$USER_HOME/Library/Application Support/Grasshopper/Libraries/StbGrasshopper.location.txt" \
  "$USER_HOME/Library/Application Support/McNeel/Rhinoceros/"*/Plug-ins/Grasshopper\ \(*\)/Libraries/StbGrasshopper.location.txt; do
  if [[ -f "$location" ]]; then
    set -- ${1+"$@"} "$(head -n 1 "$location")"
  fi
done

TARGET="${TARGET%/}"
MANIFEST_DIR="$(cd "$(dirname "$MANIFEST")" && pwd)"
MANIFEST="$MANIFEST_DIR/$(basename "$MANIFEST")"
SHIPPED="$(mktemp)"
trap 'rm -f "$SHIPPED"' EXIT

is_install() {
  [[ -d "$1" && ! -e "$1/.git" && -f "$1/Install_once.command" && -f "$1/setup_runtime.py" ]]
}

is_user_file() {
  local rel="$1"
  local name
  name="$(basename "$rel" | tr '[:upper:]' '[:lower:]')"
  case "$rel" in
    */__pycache__/*|__pycache__/*) return 1 ;;
    # Windows のインストーラ（Inno Setup）が置くアンインストール情報。規則をそろえておく。
    unins[0-9][0-9][0-9].dat) return 1 ;;
  esac
  case "$name" in
    *.dat|*.out|*.gh|*.ghx|*.project.json) ;;
    *) return 1 ;;
  esac
  ! grep -Fxq -- "$rel" "$SHIPPED"
}

free_target() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    printf '%s\n' "$path"
    return
  fi
  local dir stem ext i
  dir="$(dirname "$path")"
  stem="$(basename "$path")"
  ext=""
  if [[ "$stem" == *.* ]]; then
    ext=".${stem##*.}"
    stem="${stem%.*}"
  fi
  i=1
  while [[ -e "$dir/$stem (old $i)$ext" ]]; do
    i=$((i + 1))
  done
  printf '%s\n' "$dir/$stem (old $i)$ext"
}

clean_install() {
  local root="${1%/}"
  local kept=0 moved=0 failed=0
  echo "以前のインストールを削除しています: $root"

  # 実行環境は毎回作り直す。中のライブラリには独自の .dat があるので中身は見ない。
  rm -rf "$root/.venv" "$root/python-standalone-arm64" "$root/python-standalone-x64" "$root/wheels"

  cat "$MANIFEST" > "$SHIPPED"
  if [[ -f "$root/install_manifest.txt" ]]; then
    cat "$root/install_manifest.txt" >> "$SHIPPED"
  fi

  local file rel dest
  while IFS= read -r -d '' file; do
    rel="${file#"$root"/}"
    if is_user_file "$rel"; then
      if [[ "$root" == "$TARGET" ]]; then
        kept=$((kept + 1))
        continue
      fi
      dest="$(free_target "$TARGET/$rel")"
      if mkdir -p "$(dirname "$dest")" && mv "$file" "$dest"; then
        echo "  移動: $rel"
        moved=$((moved + 1))
      else
        failed=$((failed + 1))
      fi
      continue
    fi
    rm -f "$file" || failed=$((failed + 1))
  done < <(find "$root" \( -type f -o -type l \) -print0)

  find "$root" -mindepth 1 -depth -type d -empty -delete 2>/dev/null || true
  if [[ "$root" != "$TARGET" ]]; then
    rmdir "$root" 2>/dev/null || true
  fi
  echo "  残したファイル: $kept、移したファイル: $moved、削除できなかったファイル: $failed"
  [[ "$failed" -eq 0 ]]
}

ROOTS=("$TARGET")
for candidate in ${1+"$@"}; do
  candidate="${candidate%/}"
  [[ -z "$candidate" ]] && continue
  duplicate=0
  for root in "${ROOTS[@]}"; do
    [[ "$root" == "$candidate" ]] && duplicate=1
  done
  [[ "$duplicate" -eq 0 ]] && ROOTS+=("$candidate")
done

STATUS=0
FOUND=0
for root in "${ROOTS[@]}"; do
  if is_install "$root"; then
    FOUND=1
    clean_install "$root" || STATUS=1
  fi
done
if [[ "$FOUND" -eq 0 ]]; then
  echo "以前のインストールはありません。"
fi
exit "$STATUS"
