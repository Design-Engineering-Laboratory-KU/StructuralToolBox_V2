#!/usr/bin/env python3
"""First-time setup for a student install, run by the bundled Python.

Creates the install's own .venv, installs Structural Toolbox and its libraries
from the bundled wheels, and verifies that the result runs on this interpreter.

The launchers keep no logic of their own: cmd.exe mis-tracks file offsets in
batch files that mix non-ASCII text with subroutine calls, so all messages and
steps live here instead.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "install.log"

IS_WINDOWS = os.name == "nt"


class Failure(Exception):
    """Setup cannot continue; the message is shown to the student."""


def out(text: str = "") -> None:
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        print(text.encode(encoding, "replace").decode(encoding), flush=True)


def log(text: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(text.rstrip("\n") + "\n")


def run(cmd: list[str], step: str, silent: bool) -> None:
    log("$ " + " ".join(cmd))
    if silent:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, errors="replace")
        log(result.stdout or "")
        log(result.stderr or "")
    else:
        result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise Failure(step)


def bundled_python() -> Path:
    """The interpreter shipped with this install."""
    if IS_WINDOWS:
        candidates = [ROOT / "python-embed" / "python.exe"]
    else:
        arch = os.uname().machine
        folder = "python-standalone-arm64" if arch == "arm64" else "python-standalone-x64"
        candidates = [ROOT / folder / "bin" / "python3"]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise Failure(
        "同梱の Python が見つかりません。配布ファイルを展開し直すか、教員に連絡してください。"
    )


def venv_python() -> Path:
    if IS_WINDOWS:
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python3"


def pip_source() -> tuple[list[str], bool]:
    """Bundled wheels, so setup needs no internet."""
    wheels = ROOT / "wheels"
    if wheels.is_dir() and any(wheels.glob("*.whl")):
        # Relative path: the working directory is always the install folder.
        return ["--no-index", "--find-links", "wheels"], True
    return [], False


def ensure_pip(python: Path, pip_args: list[str], silent: bool) -> None:
    """The Windows embeddable package ships without pip."""
    probe = subprocess.run(
        [str(python), "-m", "pip", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return

    get_pip = python.parent / "get-pip.py"
    if not get_pip.exists():
        raise Failure("get-pip.py がありません。配布ファイルを展開し直してください。")
    out("pip を同梱 Python に導入しています...")
    run(
        [str(python), str(get_pip), "--no-warn-script-location"] + pip_args,
        "pip の導入に失敗しました。",
        silent,
    )


def create_venv(python: Path, pip_args: list[str], silent: bool) -> None:
    if venv_python().exists():
        out("既存の .venv があります。ライブラリを更新します...")
        return

    out("仮想環境 .venv を作成しています（同梱 Python から）...")
    if IS_WINDOWS:
        # The embeddable package has no venv module, so use virtualenv.
        run(
            [str(python), "-m", "pip", "install"] + pip_args + ["virtualenv"],
            "virtualenv のインストールに失敗しました。",
            silent,
        )
        run(
            [str(python), "-m", "virtualenv", ".venv"],
            ".venv の作成に失敗しました。",
            silent,
        )
    else:
        run([str(python), "-m", "venv", ".venv"], ".venv の作成に失敗しました。", silent)

    if not venv_python().exists():
        raise Failure(".venv の作成に失敗しました。")


def install_libraries(pip_args: list[str], offline: bool, silent: bool) -> None:
    python = venv_python()
    if offline:
        out("必要なライブラリをインストールしています（同梱・インターネット不要・2〜5 分）...")
    else:
        out("必要なライブラリをインストールしています（5〜15 分・インターネットが必要です）...")

    hint = (
        "配布ファイルの wheels フォルダが壊れている可能性があります。教員に連絡してください。"
        if offline
        else "インターネット接続を確認して、もう一度実行してください。"
    )
    run(
        [str(python), "-m", "pip", "install"] + pip_args + ["-U", "pip"],
        "pip の更新に失敗しました。" + hint,
        silent,
    )
    run(
        [str(python), "-m", "pip", "install"] + pip_args + ["-e", ".[gui]"],
        "ライブラリのインストールに失敗しました。" + hint,
        silent,
    )


def verify(silent: bool) -> None:
    out("専用 Python で解析ライブラリを確認しています...")
    run(
        [str(venv_python()), "-m", "stb_cli", "doctor", "--require-bundled"],
        "解析ライブラリの確認に失敗しました。もう一度実行してください。",
        silent,
    )


def grasshopper_libraries() -> Path:
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Grasshopper" / "Libraries"
    return Path.home() / "Library" / "Application Support" / "Grasshopper" / "Libraries"


def install_grasshopper_plugin() -> None:
    plugin = ROOT / "grasshopper" / "StbGrasshopper.gha"
    if not plugin.is_file():
        return

    libraries = grasshopper_libraries()
    if not libraries.is_dir():
        out("Grasshopper が見つかりません。Rhino を使う場合は、あとでもう一度実行してください。")
        log("Grasshopper libraries not found: " + str(libraries))
        return

    try:
        shutil.copyfile(plugin, libraries / "StbGrasshopper.gha")
    except OSError as ex:
        out("[警告] Grasshopper プラグインのコピーに失敗しました。Rhino を終了してから、もう一度実行してください。")
        log("Grasshopper copy failed: " + str(ex))
        return

    out("Grasshopper プラグインを配置しました: " + str(libraries))
    log("Grasshopper plugin installed: " + str(libraries))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silent", action="store_true", help="Keep output in install.log")
    args = parser.parse_args()

    LOG_PATH.write_text("", encoding="utf-8")
    log("install root: " + str(ROOT))

    out("")
    out("========================================")
    out(" Structural Toolbox - 初回セットアップ")
    out("========================================")
    out("")

    try:
        python = bundled_python()
        out("使用する Python（同梱）: " + str(python))
        pip_args, offline = pip_source()
        log("offline install: " + str(offline))

        ensure_pip(python, pip_args, args.silent)
        create_venv(python, pip_args, args.silent)
        install_libraries(pip_args, offline, args.silent)
        verify(args.silent)
        install_grasshopper_plugin()
    except Failure as ex:
        out("")
        out("[エラー] " + str(ex))
        out("詳細ログ: " + str(LOG_PATH))
        log("FAILED: " + str(ex))
        return 1

    log("setup complete")
    out("")
    out("========================================")
    out(" セットアップ完了")
    out("========================================")
    out("")
    out("同梱 Python + このフォルダ専用の .venv で動作します。")
    out("パソコンに入っている別の Python とは混ざりません。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
