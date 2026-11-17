"""Native file selection for the locally running GUI server."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Optional, Sequence


def _run_dialog(command: Sequence[str]) -> Optional[str]:
    kwargs = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(list(command), **kwargs)
    path = result.stdout.strip()
    if result.returncode == 0 and path:
        return os.path.abspath(os.path.expanduser(path))
    if result.returncode in (0, 1):
        return None
    message = result.stderr.strip() or "File selection dialog failed"
    raise RuntimeError(message)


def choose_dat_file() -> Optional[str]:
    """Open the host OS file picker and return the selected .dat path."""

    system = platform.system()
    if system == "Windows":
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell:
            script = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$d=New-Object System.Windows.Forms.OpenFileDialog;"
                "$d.Title='Open Structural Toolbox model';"
                "$d.Filter='Structural Toolbox model (*.dat)|*.dat|All files (*.*)|*.*';"
                "if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK)"
                "{[Console]::OutputEncoding=[Text.Encoding]::UTF8;$d.FileName}"
            )
            return _run_dialog([powershell, "-NoProfile", "-STA", "-Command", script])

    if system == "Darwin":
        osascript = shutil.which("osascript")
        if osascript:
            script = (
                'POSIX path of (choose file with prompt "Open Structural Toolbox model" '
                'of type {"dat"})'
            )
            return _run_dialog([osascript, "-e", script])

    zenity = shutil.which("zenity")
    if zenity:
        return _run_dialog([
            zenity,
            "--file-selection",
            "--title=Open Structural Toolbox model",
            "--file-filter=Structural Toolbox model (*.dat) | *.dat",
            "--file-filter=All files | *",
        ])

    kdialog = shutil.which("kdialog")
    if kdialog:
        return _run_dialog([
            kdialog,
            "--getopenfilename",
            os.path.expanduser("~"),
            "*.dat|Structural Toolbox model (*.dat)",
            "--title",
            "Open Structural Toolbox model",
        ])

    raise RuntimeError(
        "No native file picker is available. Install zenity or kdialog."
    )
