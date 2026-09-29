# STB Grasshopper .gha Scaffold

This is a Grasshopper SDK scaffold for the Karamba3D-like STB workflow.

The MVP intentionally calls the existing STB CLI instead of embedding Python in
Rhino. This keeps `numpy`, `scipy`, and `shapely` inside the repository virtual
environment and makes classroom Windows deployment easier.

## Components

- `STb Analyze`: accepts `STb Model`, runs `python -m stb_cli solve`, and outputs
  parsed `Results` plus an analyzed `STb Model`
- `STb Analyze from file`: accepts a `.dat` path, runs the same solver, and outputs
  parsed `Results` plus an analyzed `STb Model`
- `STB Load Cases`: accepts `STb Model` and lists available load cases in its results
- `STB Displacements`: accepts `STb Model` and exposes load case, node id, translation, and rotation rows
- `STB Forces`: accepts `STb Model` and exposes parsed element force rows
- `STB Stress`: accepts `STb Model` and previews maximum normal stress with a viewport color legend
- `STB DAT Nodes`: reads original node points from an existing `.dat` file
- `STB DAT Beams`: reads element connectivity from an existing `.dat` file
- `STB Element`: input `Name`, `Line`, `Section`, `Beta` → output typed `Element`
- `STB Material`: input `Name`, `E`, `G`, `Gamma`, `Alpha`, `Fy` → output typed `Mat`
- `STB Section`: select the section type from the component drop-down; its
  dimension inputs change to `B/H`, `D`, `H/B/tw/tf`, or `D/t` as appropriate
  → output typed `Section`
- `STB Support`: input `Point`, six on-component restraint toggles → output typed `Support`
- `STB Point Load`: input `Point`, `LC`, `F` (kN), `M` (kNm) → output typed `Load`
- `STB Line Load`: input typed `Element`, `LC`, coordinate-system toggle, `Wi`/`Wj`
  (kN/m) → output typed `Load`; different end vectors create a trapezoidal load
- `STB Area Load`: input three or four typed boundary `Element` objects, `LC`, and
  global pressure vector `P` (kN/m²) → output typed `Load`
- `STb Load/Mat/Section/Model/Elem/Support Container`: collect existing typed
  STb data and pass it on as a typed list or model value
- `STB Assemble Model`: input typed `Element`, `Load`, `Support`, optional `Results`, and
  `Write` → output `Text`, `DAT`, and typed `STb Model`
- `STb Assembly from file`: input `DAT Path` → output typed `STb Model`
- `View Support Condition`: input typed `STb Model`, `Size` → display fixed, pinned,
  roller, and rotational restraint symbols; output support points, symbol Breps,
  and condition descriptions
- `STB Deformed Shape`: displays the deformed model with a scale slider and legend

The current solver does not include the member-axis component of an `ELOD` in
its fixed-end forces. `STB Line Load` reports a warning when such a component is
detected.

## Build Notes

This project targets Rhino 8 and `net7.0` so the same source can be built for
Windows and macOS Grasshopper. Grasshopper/Rhino assemblies are not committed to
this repository; `StbGrasshopper.csproj` resolves them from a local Rhino 8
installation.

Default Windows Rhino 8 paths:

```text
C:\Program Files\Rhino 8\System\
C:\Program Files\Rhino 8\Plug-ins\Grasshopper\
```

Default macOS Rhino 8 paths:

```text
/Applications/Rhino 8.app/Contents/Resources/RhinoCommon.dll
/Applications/Rhino 8.app/Contents/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Grasshopper.dll
```

Build:

```powershell
dotnet build grasshopper\gha\StbGrasshopper.csproj -c Release
```

On macOS:

```bash
dotnet build grasshopper/gha/StbGrasshopper.csproj -c Release
```

If Rhino is installed somewhere else, pass explicit paths:

```bash
dotnet build grasshopper/gha/StbGrasshopper.csproj -c Release \
  -p:RhinoCommonPath="/path/to/RhinoCommon.dll" \
  -p:GrasshopperPath="/path/to/Grasshopper.dll"
```

The build output is `bin/Release/StbGrasshopper.gha`.

On Windows, a successful build also copies `StbGrasshopper.gha` to
`%APPDATA%\Grasshopper\Libraries` so Rhino/Grasshopper can load the latest
build. Override the destination when needed with
`-p:GrasshopperLibrariesPath="C:\path\to\Libraries"`.

## Runtime Notes

`STb Analyze` and `STb Analyze from file` call the Python CLI outside Rhino. Leave
`Python Exe` and `Repo Root` empty: the components locate the Structural Toolbox
virtual environment themselves, searching in this order.

1. `Repo Root`, when given
2. `%LOCALAPPDATA%\StructuralToolbox` (Windows student install)
3. `~/Library/Application Support/StructuralToolbox` (macOS student install)
4. The folders above the loaded `.gha`, for developer checkouts

Within each folder they accept `.venv\Scripts\python.exe`, `.venv/bin/python3`,
or `.venv/bin/python`. A Python found on `PATH` is never used, because it would
lack the solver libraries; the components report an error instead. The resolved
interpreter appears in the `Summary` output.

In a developer checkout, install the repository into that virtual environment:

```bash
python -m pip install -e ".[gui]"
```

Check which interpreter an install uses with `stb doctor`.

## Load case workflow

- `STb Analyze` and `STb Analyze from file` keep all load cases in `Results` when `Load Case` is `-1` (default).
- Set `Load Case` on `STB Displacements`, `STB Forces`, and `STB Deformed Shape` to choose which LC to display.
- Use `STB Load Cases` to inspect available LC ids from `Results`.
- Negative `Load Case` on result components means "show all load cases".
- Both Analyze components embed node coordinates and element connectivity from the `.dat` file into `Results`.
- `STB Deformed Shape` uses `Results` and `Load Case` inputs; its `Scale` is
  controlled by the component slider, and `Legend` toggles the viewport legend.

The first component to make production-ready is `StbAnalyzeComponent.cs`.

## Model-building workflow

1. `STB Material` → `STB Section` → `STB Element`
2. Create point, line, and area loads with the corresponding `STB ... Load`
   components. Area-load boundary elements must form one closed triangular or
   quadrilateral loop.
3. Merge typed objects into `STB Assemble Model`
4. Connect an Analyze component's `Results` to `STB Assemble Model` `Results` to embed
  solver results in `STb Model`.
5. Alternatively, connect `STB Assemble Model` `STb Model` directly to `STb Analyze`
  `STb Model`; it then outputs an analyzed `STb Model`.
6. Connect analyzed `STb Model` to any component in the `Results` group, or to
  `View Support Condition`, to inspect the model and results.
6. `STB Assemble Model` auto-assigns material/section/element/node ids, resolves
   load targets at the Rhino document tolerance, emits `PLOD`/`ELOD`/`ALOD`,
   merges duplicate nodes, and writes `.dat` text
