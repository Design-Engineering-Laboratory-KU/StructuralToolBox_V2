# Structural Toolbox

3D linear static analysis for frame structures. Use the **CLI** (`stb solve`) and **browser application** (`stb gui`); the headless engine (`stb_engine`) is the shared solver core.

## Virtual environment (each PC)

Do **not** commit or share `.venv` via Git. Create one local venv per machine (Linux / Windows each use `.venv` in the project folder, or a path outside Dropbox).

```bash
cd /path/to/stb_0_1
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[gui]"
```

Multi-machine / Dropbox notes: [docs/setup_venv.md](docs/setup_venv.md).

### Student distribution (Windows 11, policy B)

For classroom/home use without Git: build a Windows Setup.exe ([student/build_student_installer.ps1](student/build_student_installer.ps1), bundles **Windows embeddable Python**) or a Mac installer ([student/build_student_mac.ps1](student/build_student_mac.ps1)). Students do not install Python themselves. Guides: [docs/学生用_インストール_Windows.md](docs/学生用_インストール_Windows.md), [docs/学生用_インストール_Mac.md](docs/学生用_インストール_Mac.md). Instructor notes: [student/README.md](student/README.md).

## Command-line interface (Phase 1)

Install the `stb` command (once per virtual environment):

```bash
cd /path/to/stb_0_1
.venv/bin/pip install -e .
```

Use the `stb` inside the project virtual environment (recommended):

```bash
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever.out -q -v
```

Or activate the venv first: `source .venv/bin/activate`, then run `stb ...`.

### Troubleshooting: `ModuleNotFoundError` (e.g. shapely)

If `which stb` shows `~/.local/bin/stb`, you may be running a **user install** with system Python (`/usr/bin/python3`), not the project `.venv`. That Python often lacks solver dependencies.

Fix (pick one):

```bash
# A) Recommended: install into project .venv and call it explicitly
cd /path/to/stb_0_1
.venv/bin/pip install -e .
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever.out -q -v

# B) Remove the conflicting user entry, then use .venv only
python3 -m pip uninstall structural-toolbox
hash -r
```

Check which Python runs `stb`: `head -1 "$(which stb)"` should point to `.venv/bin/python`, not `/usr/bin/python3`.

### Commands

```bash
# Smallest sample (see examples/README.md)
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever.out -q -v

# Run analysis; write results to a file
stb solve data/input01.dat -o tests/_tmp_out/input01.out

# Same without installing (from project root)
.venv/bin/python -m stb_cli solve data/input01.dat -o tests/_tmp_out/input01.out

# Parse input only (no solve)
stb validate data/input01.dat -v

# Version
stb version

# Browser application
.venv/bin/pip install -e ".[gui]"
.venv/bin/stb gui
# or: .venv/bin/python -m stb_gui
```

### Structural Toolbox GUI

**Three.js** frame modeler and viewer in the browser. Lists models under `data/` and `examples/`. The last opened model is remembered in the browser (`localStorage`).

```bash
.venv/bin/pip install -e ".[gui]"
.venv/bin/stb gui --port 8765
```

Open http://127.0.0.1:8765/ — drag to orbit, scroll to zoom. Main bar: model, **Solve**, **Results** (forces, LC, deformation), **Options** (load arrow / label sizes; settings persist).

Stop the server with **Ctrl+C**.

### Options

| Flag | Effect |
|------|--------|
| `-o`, `--output` | Result file (`.out`; `solve` only; default is stdout) |
| `-q`, `--quiet` | Suppress solver progress messages on stderr/stdout |
| `-v`, `--verbose` | Print status (node count, load cases, output path) |

Result file naming convention: `model.dat` → `model.out` (same directory unless `-o` specifies otherwise).

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Input error (missing file, parse failure) |
| `2` | Analysis error |

### Python API (Phase 0)

```bash
.venv/bin/python -c "
from stb_engine import run_from_file
mdl, txt = run_from_file('data/input01.dat', 'tests/_tmp_out/input01.out')
print('load cases:', mdl.lcs)
"
```

**Public API:** `parse_input`, `solve_model`, `format_results`, `run_from_lines`, `run_from_file`

**Exceptions:** `StbParseError`, `StbSolveError`

Input and output use the same comma-separated text format (editable in the GUI).  
**Input reference:** [docs/input_format.md](docs/input_format.md) (`PLOD`, `ELOD`, `ALOD`, `GLOD`, … — not `LOAD`).

Project-level building metadata can be added without changing `.dat` files by
placing `model.project.json` next to the model.  
**Project reference:** [docs/project_format.md](docs/project_format.md).

### Tests

```bash
.venv/bin/python -m unittest tests.test_engine tests.test_cli tests.test_data_models tests.test_gui -v
```
