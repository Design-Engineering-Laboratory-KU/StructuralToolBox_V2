"""Server log file for GUI launches that have no console window.

The launchers start the GUI without a terminal (``pythonw.exe`` on Windows, an
app bundle on macOS). ``pythonw.exe`` leaves ``sys.stdout`` / ``sys.stderr`` as
``None``, which breaks uvicorn's log formatter (it calls ``sys.stdout.isatty()``)
and hides every error. :func:`ensure_log_streams` points both streams at a log
file instead, so prints, uvicorn logs and tracebacks all end up there.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Optional

LOG_NAME = "stb_gui.log"
# Rotate once at start-up so the file cannot grow without bound.
_MAX_LOG_BYTES = 5 * 1024 * 1024

_log_path: Optional[str] = None


def default_log_dir() -> str:
    override = os.environ.get("STB_GUI_LOG_DIR", "").strip()
    if override:
        return override
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "StructuralToolbox", "logs")
    if system == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Logs", "StructuralToolbox")
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "structural-toolbox")


def default_log_path() -> str:
    return os.path.join(default_log_dir(), LOG_NAME)


def has_console() -> bool:
    return sys.stdout is not None and sys.stderr is not None


def log_path() -> Optional[str]:
    """Path of the log file the std streams were redirected to, if any."""
    return _log_path


def _rotate(path: str) -> None:
    try:
        if os.path.getsize(path) > _MAX_LOG_BYTES:
            os.replace(path, path + ".1")
    except OSError:
        pass


def ensure_log_streams() -> Optional[str]:
    """Redirect missing stdout/stderr to the GUI log file.

    Does nothing when both streams exist (started from a terminal). Returns the
    log path when a redirection was made.
    """
    global _log_path
    if has_console():
        return None
    path = default_log_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _rotate(path)
        stream = open(path, "a", encoding="utf-8", errors="replace", buffering=1)
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
        path = None
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    _log_path = path
    if path:
        import time

        stream.write("\n===== {0} Structural Toolbox GUI (pid {1}) =====\n".format(
            time.strftime("%Y-%m-%d %H:%M:%S"), os.getpid()))
    return path


def show_error_dialog(message: str) -> None:
    """Tell the user about a fatal start-up error when there is no console."""
    if _log_path:
        message = message.rstrip() + "\n\nLog: " + _log_path
    try:
        if platform.system() == "Windows":
            import ctypes

            mb_iconerror = 0x10
            ctypes.windll.user32.MessageBoxW(None, message, "Structural Toolbox", mb_iconerror)
    except Exception:
        pass
