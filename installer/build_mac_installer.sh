#!/usr/bin/env bash
# macOS で実行すると tar.gz に加えて .dmg と .pkg も作る。
# 使い方: ./installer/build_mac_installer.sh --edition simple (または full)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 "$ROOT/installer/build_mac.py" "$@"
