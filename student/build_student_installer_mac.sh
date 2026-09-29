#!/usr/bin/env bash
# macOS で実行すると tar.gz に加えて .dmg と .pkg も作る。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 "$ROOT/student/build_student_mac.py"
