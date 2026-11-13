"""HTML report -> PDF with a locally installed Chromium browser (Edge / Chrome).

Edge ships with Windows, so no extra Python package is needed. The HTML is
printed with the browser's own print engine (``--print-to-pdf``), which uses
the report's ``@page`` / ``@media print`` rules, i.e. the same result as
"印刷 / PDF保存" in the browser.

Set ``STB_PDF_BROWSER`` to the browser executable to override the search.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import time

_WINDOWS_CANDIDATES = (
    ("PROGRAMFILES(X86)", r"Microsoft\Edge\Application\msedge.exe"),
    ("PROGRAMFILES", r"Microsoft\Edge\Application\msedge.exe"),
    ("PROGRAMFILES", r"Google\Chrome\Application\chrome.exe"),
    ("PROGRAMFILES(X86)", r"Google\Chrome\Application\chrome.exe"),
    ("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
)
_PATH_NAMES = ("msedge", "microsoft-edge", "google-chrome", "chrome", "chromium", "chromium-browser")
_MAC_CANDIDATES = (
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


class PdfExportError(RuntimeError):
    """The PDF could not be produced (no browser found, or the browser failed)."""


def find_pdf_browser():
    """Path of a Chromium-based browser usable for PDF export, or None."""

    env = os.environ.get("STB_PDF_BROWSER", "").strip().strip('"')
    if env:
        return env if os.path.isfile(env) else None
    for var, rel in _WINDOWS_CANDIDATES:
        base = os.environ.get(var)
        if base:
            path = os.path.join(base, rel)
            if os.path.isfile(path):
                return path
    for path in _MAC_CANDIDATES:
        if os.path.isfile(path):
            return path
    for name in _PATH_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return None


def _wait_for_file(path, deadline, poll_s=0.2):
    """Wait until ``path`` exists with a non-zero size that stopped changing."""

    last = -1
    while time.monotonic() < deadline:
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        if size > 0 and size == last:
            return
        last = size
        time.sleep(poll_s)


def html_to_pdf(html_text, pdf_path, timeout_s=120):
    """Write ``html_text`` as a PDF at ``pdf_path``. Raises PdfExportError."""

    browser = find_pdf_browser()
    if browser is None:
        raise PdfExportError(
            "PDF 出力には Microsoft Edge か Google Chrome が必要です（見つかりませんでした）。"
            " 環境変数 STB_PDF_BROWSER にブラウザの exe を指定することもできます。"
        )
    pdf_path = os.path.abspath(pdf_path)
    out_dir = os.path.dirname(pdf_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    work = tempfile.mkdtemp(prefix="stb_pdf_")
    try:
        src = os.path.join(work, "report.html")
        with open(src, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html_text)
        tmp_pdf = os.path.join(work, "report.pdf")
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--disable-default-apps",
            "--no-pdf-header-footer",
            "--user-data-dir=" + os.path.join(work, "profile"),
            "--print-to-pdf=" + tmp_pdf,
            pathlib.Path(src).as_uri(),
        ]
        if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd.insert(1, "--no-sandbox")
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        deadline = time.monotonic() + timeout_s
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_s, **kwargs
            )
        except subprocess.TimeoutExpired:
            raise PdfExportError("PDF 出力がタイムアウトしました（" + str(timeout_s) + " 秒）。")
        except OSError as ex:
            raise PdfExportError("ブラウザを起動できませんでした: " + browser + " (" + str(ex) + ")")
        # On Windows msedge.exe may hand off to a child process and return
        # before the PDF is written, so wait for the file to appear and settle.
        if proc.returncode == 0:
            _wait_for_file(tmp_pdf, deadline)
        if not os.path.isfile(tmp_pdf) or os.path.getsize(tmp_pdf) == 0:
            detail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-3:]
            raise PdfExportError(
                "PDF を作成できませんでした（" + os.path.basename(browser) + "）。" + " ".join(detail)
            )
        shutil.move(tmp_pdf, pdf_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return pdf_path
