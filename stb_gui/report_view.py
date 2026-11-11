"""確認申請補助計算書 (``stb report``) for the GUI.

The project JSON is given as a full path, so models kept outside the
Structural Toolbox folder (for example in Dropbox) can be reported without
copying them into data/. The report is written next to the input by default,
the same file ``stb report`` would write.
"""

from __future__ import annotations

import os
import threading
import uuid

from stb_gui.model_json import resolve_model_path
from stb_project import project_path_for_dat
from stb_reports import default_report_output_path, generate_confirmation_report, report_format_for_path

# token -> absolute path of a report generated in this GUI session. Only these
# files are served back by /api/report/view.
_GENERATED = {}
_GENERATED_LOCK = threading.Lock()


def report_defaults_for_model(rel_path=None):
    """Suggested input/output paths for the model open in the viewer (may be empty)."""

    if not rel_path:
        return {"input": "", "output": "", "input_exists": False}
    full = resolve_model_path(rel_path)
    project_path = project_path_for_dat(full)
    exists = os.path.isfile(project_path)
    return {
        "input": project_path if exists else full,
        "output": default_report_output_path(project_path if exists else full),
        "input_exists": exists,
    }


def _clean_path(value):
    text = str(value or "").strip()
    # Explorer "Copy as path" wraps the path in double quotes.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return os.path.expanduser(text)


def run_confirmation_report(input_path, output_path=None, output_format=None):
    """Generate the report. Returns a JSON-serializable dict; raises ValueError/IOError on bad input."""

    from stb_engine.version import __version__ as stb_version

    input_path = _clean_path(input_path)
    if not input_path:
        raise ValueError("project.json のパスを入力してください。")
    if not os.path.isabs(input_path):
        raise ValueError("project.json はフルパスで指定してください: " + input_path)
    input_path = os.path.normpath(input_path)
    lower = input_path.lower()
    if not (lower.endswith(".json") or lower.endswith(".dat")):
        raise ValueError("入力は .project.json か .dat を指定してください: " + input_path)
    if not os.path.isfile(input_path):
        raise ValueError("ファイルが見つかりません: " + input_path)

    output_path = _clean_path(output_path) or default_report_output_path(input_path)
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.path.dirname(input_path), output_path)
    output_path = os.path.normpath(output_path)
    implied = report_format_for_path(output_path)
    if implied is None:
        raise ValueError("出力ファイルの拡張子は .html か .md にしてください: " + output_path)
    fmt = output_format or implied
    if fmt not in ("html", "markdown"):
        raise ValueError("Unsupported report format: " + str(fmt))
    if fmt != implied:
        raise ValueError("出力形式と拡張子が一致しません（html は .html、markdown は .md）。")
    if os.path.normcase(output_path) == os.path.normcase(input_path):
        raise ValueError("出力先が入力ファイルと同じです。")

    draft, _project, dat_path = generate_confirmation_report(
        input_path,
        output_path,
        output_format=fmt,
        program_version=stb_version,
        quiet=True,
    )

    token = uuid.uuid4().hex
    with _GENERATED_LOCK:
        _GENERATED[token] = output_path
    return {
        "ok": True,
        "input": input_path,
        "dat": dat_path,
        "output": output_path,
        "format": fmt,
        "warnings": list(draft.warnings),
        "token": token,
    }


def generated_report_file(token):
    """Absolute path of a report generated in this session, or None."""

    with _GENERATED_LOCK:
        return _GENERATED.get(str(token or ""))
