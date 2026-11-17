"""Native open / save-as file dialogs for the local GUI server.

A browser file input hands over the file's contents but not its location, and
a browser download always lands in the Downloads folder. The GUI therefore asks
the server, which runs on the same computer, to show the operating system's own
dialog instead. Windows uses PowerShell and Windows Forms, macOS uses osascript,
and other systems use zenity, kdialog or tkinter, whichever is present.
"""

import base64
import os
import shutil
import subprocess
import sys
import threading

DIALOG_TIMEOUT_S = 3600

DAT_FILTER = ("STB input", "dat")
PDF_FILTER = ("PDF", "pdf")

_lock = threading.Lock()


class DialogUnavailable(RuntimeError):
    """No native file dialog can be shown on this system."""


class DialogBusy(RuntimeError):
    """A file dialog is already open."""


def choose_dat_file(initial_dir=None, title="Open STB input file"):
    """Show an open-file dialog for .dat files; return the chosen path or None if cancelled."""

    return _run("open", initial_dir, title, DAT_FILTER, None)


def choose_save_path(initial_dir=None, default_name="", title="Save as", file_filter=PDF_FILTER):
    """Show a save-as dialog; return the chosen path (with the extension) or None if cancelled.

    The dialog asks before replacing an existing file.
    """

    path = _run("save", initial_dir, title, file_filter, default_name)
    if path and not path.lower().endswith("." + file_filter[1].lower()):
        path += "." + file_filter[1]
    return path


def _run(mode, initial_dir, title, file_filter, default_name):
    if initial_dir and not os.path.isdir(initial_dir):
        initial_dir = None
    if not _lock.acquire(blocking=False):
        raise DialogBusy("A file dialog is already open")
    try:
        if sys.platform == "win32":
            return _windows(mode, initial_dir, title, file_filter, default_name)
        if sys.platform == "darwin":
            return _mac(mode, initial_dir, title, file_filter, default_name)
        return _other(mode, initial_dir, title, file_filter, default_name)
    finally:
        _lock.release()


def _clean(output):
    path = (output or "").strip()
    return path or None


_WINDOWS_SCRIPT = r"""
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
if ($env:STB_DIALOG_MODE -eq 'save') {
    $dialog = New-Object System.Windows.Forms.SaveFileDialog
    $dialog.OverwritePrompt = $true
    $dialog.AddExtension = $true
    $dialog.DefaultExt = $env:STB_DIALOG_EXT
    $dialog.FileName = $env:STB_DIALOG_NAME
} else {
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
}
$dialog.Filter = $env:STB_DIALOG_FILTER
$dialog.Title = $env:STB_DIALOG_TITLE
if ($env:STB_DIALOG_DIR) { $dialog.InitialDirectory = $env:STB_DIALOG_DIR }
if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Out.Write($dialog.FileName)
}
$owner.Dispose()
"""


def _windows(mode, initial_dir, title, file_filter, default_name):
    exe = shutil.which("powershell") or shutil.which("powershell.exe") or shutil.which("pwsh")
    if not exe:
        raise DialogUnavailable("PowerShell was not found")
    label, ext = file_filter
    encoded = base64.b64encode(_WINDOWS_SCRIPT.encode("utf-16-le")).decode("ascii")
    env = dict(os.environ)
    env["STB_DIALOG_MODE"] = mode
    env["STB_DIALOG_TITLE"] = title
    env["STB_DIALOG_DIR"] = initial_dir or ""
    env["STB_DIALOG_NAME"] = default_name or ""
    env["STB_DIALOG_EXT"] = ext
    env["STB_DIALOG_FILTER"] = "{0} (*.{1})|*.{1}|All files (*.*)|*.*".format(label, ext)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-STA", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        capture_output=True, env=env, timeout=DIALOG_TIMEOUT_S, creationflags=flags,
    )
    if proc.returncode != 0:
        raise DialogUnavailable(proc.stderr.decode("utf-8", "replace").strip() or "PowerShell dialog failed")
    return _clean(proc.stdout.decode("utf-8-sig", "replace"))


def _applescript_text(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _mac(mode, initial_dir, title, file_filter, default_name):
    exe = shutil.which("osascript")
    if not exe:
        raise DialogUnavailable("osascript was not found")
    location = ""
    if initial_dir:
        location = " default location (POSIX file " + _applescript_text(initial_dir) + ")"
    if mode == "save":
        name = " default name " + _applescript_text(default_name or "")
        command = "choose file name with prompt " + _applescript_text(title) + name + location
    else:
        command = "choose file with prompt " + _applescript_text(title) + location
    script = (
        "tell application (path to frontmost application as text)\n"
        "  set chosen to " + command + "\n"
        "end tell\n"
        "POSIX path of chosen"
    )
    proc = subprocess.run([exe, "-e", script], capture_output=True, timeout=DIALOG_TIMEOUT_S)
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace")
        if "-128" in message:  # user cancelled
            return None
        raise DialogUnavailable(message.strip() or "osascript dialog failed")
    return _clean(proc.stdout.decode("utf-8", "replace"))


def _other(mode, initial_dir, title, file_filter, default_name):
    label, ext = file_filter
    start = (initial_dir.rstrip("/") + "/") if initial_dir else ""
    if mode == "save":
        start += default_name or ""
    zenity = shutil.which("zenity")
    if zenity:
        cmd = [zenity, "--file-selection", "--title=" + title,
               "--file-filter={0} | *.{1}".format(label, ext), "--file-filter=All files | *"]
        if mode == "save":
            cmd += ["--save", "--confirm-overwrite"]
        if start:
            cmd.append("--filename=" + start)
        proc = subprocess.run(cmd, capture_output=True, timeout=DIALOG_TIMEOUT_S)
        return _clean(proc.stdout.decode("utf-8", "replace")) if proc.returncode == 0 else None
    kdialog = shutil.which("kdialog")
    if kdialog:
        option = "--getsavefilename" if mode == "save" else "--getopenfilename"
        proc = subprocess.run([kdialog, "--title", title, option, start or ".", "*." + ext],
                              capture_output=True, timeout=DIALOG_TIMEOUT_S)
        return _clean(proc.stdout.decode("utf-8", "replace")) if proc.returncode == 0 else None
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        raise DialogUnavailable("No file dialog (zenity, kdialog or tkinter) is available")
    window = tkinter.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    types = [(label, "*." + ext), ("All files", "*.*")]
    try:
        if mode == "save":
            path = filedialog.asksaveasfilename(
                title=title, initialdir=initial_dir or None, initialfile=default_name or "",
                defaultextension="." + ext, filetypes=types,
            )
        else:
            path = filedialog.askopenfilename(title=title, initialdir=initial_dir or None, filetypes=types)
    finally:
        window.destroy()
    return _clean(path)
