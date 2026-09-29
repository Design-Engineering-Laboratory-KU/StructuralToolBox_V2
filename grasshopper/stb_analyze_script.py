"""Grasshopper Python Script sample for running STB.

Inputs expected in Grasshopper:
    datPath: str
    pythonExe: str, optional (empty auto-detects the bundled Python)
    repoRoot: str, optional (empty auto-detects the install folder)
    run: bool
    outPath: str, optional
    loadCase: int, optional

Outputs produced by this script:
    success: bool
    exitCode: int
    outPath: str
    stdout: str
    stderr: str
    summary: str
    nodeIds: list[int]
    loadCases: list[int]
    translations: list[tuple[float, float, float]]
    rotations: list[tuple[float, float, float]]

The module also runs as a normal Python script for testing without Rhino.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

try:
    from grasshopper.stb_out_parser import parse_stb_out_file
except ImportError:
    from stb_out_parser import parse_stb_out_file


@dataclass
class AnalyzeResult:
    success: bool
    exit_code: int
    out_path: str
    stdout: str
    stderr: str
    summary: str
    node_ids: List[int]
    load_cases: List[int]
    translations: List[Tuple[float, float, float]]
    rotations: List[Tuple[float, float, float]]


def default_output_path(dat_path: str) -> str:
    base = os.path.splitext(os.path.basename(dat_path))[0]
    out_dir = os.path.join(tempfile.gettempdir(), "stb_gh")
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, base + ".out")


def candidate_roots(repo_root: Optional[str]) -> List[str]:
    roots = []
    if repo_root:
        roots.append(os.path.abspath(repo_root))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(os.path.join(local, "StructuralToolbox"))
    home = os.path.expanduser("~")
    roots.append(os.path.join(home, "Library", "Application Support", "StructuralToolbox"))
    roots.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    unique = []
    for root in roots:
        if root and root not in unique:
            unique.append(root)
    return unique


def venv_python(root: str) -> Optional[str]:
    for rel in (
        os.path.join(".venv", "Scripts", "python.exe"),
        os.path.join(".venv", "bin", "python3"),
        os.path.join(".venv", "bin", "python"),
    ):
        candidate = os.path.join(root, rel)
        if os.path.isfile(candidate):
            return candidate
    return None


def resolve_python_exe(python_exe: Optional[str], repo_root: Optional[str]) -> Tuple[str, str]:
    """Return (interpreter, working directory) for the Structural Toolbox venv.

    Rhino's own Python lacks the solver libraries, so a missing venv is an
    error rather than a reason to fall back to ``sys.executable``.
    """
    if python_exe:
        exe = os.path.abspath(python_exe)
        if not os.path.isfile(exe):
            raise FileNotFoundError("Python Exe does not exist: " + exe)
        root = repo_root or os.path.dirname(os.path.dirname(os.path.dirname(exe)))
        return exe, os.path.abspath(root)

    roots = candidate_roots(repo_root)
    for root in roots:
        found = venv_python(root)
        if found:
            return found, root

    raise FileNotFoundError(
        "Structural Toolbox Python was not found. Run the first-time setup "
        "(Install_once) from the install folder, or set pythonExe. Looked in: "
        + "; ".join(roots)
    )


def run_stb_analyze(
    dat_path: str,
    python_exe: Optional[str],
    repo_root: Optional[str],
    run: bool,
    out_path: Optional[str] = None,
    load_case: Optional[int] = None,
) -> AnalyzeResult:
    if not run:
        return AnalyzeResult(
            success=False,
            exit_code=-1,
            out_path=out_path or "",
            stdout="",
            stderr="",
            summary="run is False; STB was not executed.",
            node_ids=[],
            load_cases=[],
            translations=[],
            rotations=[],
        )

    dat_path = os.path.abspath(dat_path)
    out_path = os.path.abspath(out_path or default_output_path(dat_path))
    try:
        exe, repo_root = resolve_python_exe(python_exe, repo_root)
    except FileNotFoundError as ex:
        return AnalyzeResult(
            success=False,
            exit_code=1,
            out_path=out_path,
            stdout="",
            stderr=str(ex),
            summary="Structural Toolbox Python was not found.",
            node_ids=[],
            load_cases=[],
            translations=[],
            rotations=[],
        )

    if not os.path.isfile(dat_path):
        return AnalyzeResult(
            success=False,
            exit_code=1,
            out_path=out_path,
            stdout="",
            stderr="Input file not found: " + dat_path,
            summary="STB input file was not found.",
            node_ids=[],
            load_cases=[],
            translations=[],
            rotations=[],
        )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        exe,
        "-m",
        "stb_cli",
        "solve",
        dat_path,
        "-o",
        out_path,
        "-q",
        "-v",
    ]

    completed = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        return AnalyzeResult(
            success=False,
            exit_code=completed.returncode,
            out_path=out_path,
            stdout=completed.stdout,
            stderr=completed.stderr,
            summary="STB solve failed with exit code " + str(completed.returncode),
            node_ids=[],
            load_cases=[],
            translations=[],
            rotations=[],
        )

    results = parse_stb_out_file(out_path, load_case=load_case)
    displacements = results.displacements

    return AnalyzeResult(
        success=True,
        exit_code=completed.returncode,
        out_path=out_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
        summary=(
            "Solved "
            + os.path.basename(dat_path)
            + "; displacements="
            + str(len(displacements))
            + "; load_cases="
            + str(results.load_cases)
            + "; python="
            + exe
        ),
        node_ids=[row.node_id for row in displacements],
        load_cases=[row.load_case for row in displacements],
        translations=[(row.x, row.y, row.z) for row in displacements],
        rotations=[(row.theta_x, row.theta_y, row.theta_z) for row in displacements],
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run STB the same way as the Grasshopper script sample.")
    parser.add_argument("dat_path")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--python-exe", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--load-case", type=int, default=None)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_stb_analyze(
        dat_path=args.dat_path,
        python_exe=args.python_exe,
        repo_root=args.repo_root,
        run=True,
        out_path=args.out,
        load_case=args.load_case,
    )
    print(result.summary)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.exit_code if result.exit_code >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
