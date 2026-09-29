# Grasshopper Sample Definitions

This folder is reserved for Grasshopper sample files.

## Why the sample is not hand-written

`.ghx` is XML, but it is a serialized Grasshopper document. Each component writes
its own internal data, identifiers, parameter layout, and connection state. A
hand-written `.ghx` can look valid as XML but still fail to open or fail to bind
to the intended components.

For this project, create `.ghx` samples from Rhino 8 / Grasshopper itself after
loading `StbGrasshopper.gha`.

## Create `stb_analyze_rhino8.ghx`

1. Build the `.gha`:

   Windows:

   ```powershell
   dotnet build grasshopper\gha\StbGrasshopper.csproj -c Release
   ```

   macOS:

   ```bash
   dotnet build grasshopper/gha/StbGrasshopper.csproj -c Release
   ```

2. Open Rhino 8 and start Grasshopper.

3. Load the compiled file:

   ```text
   grasshopper/gha/bin/Release/StbGrasshopper.gha
   ```

4. Create a sample definition with these components:

   - `STB Analyze`
   - `STB Load Cases`
   - `STB Displacements`
   - `STB Forces`
   - `STB Deformed Shape`

5. Set the `STB Analyze` inputs:

   ```text
   DAT Path:   <path to>/data/UK_240416_floors_1to3_diaphragm.dat
   Python Exe: (empty — auto-detected)
   Repo Root:  (empty — auto-detected)
   Run:        false initially, then true
   Load Case:  -1
   ```

   Set `Repo Root` only to point at a specific checkout, and `Python Exe` only to
   override the interpreter. See `grasshopper/gha/README.md` for the search order.

6. Set result display load cases:

   ```text
   STB Displacements.Load Case = 0
   STB Forces.Load Case = 0
   STB Deformed Shape.Load Case = 0
   ```

7. Connect:

   ```text
   STB Analyze.Results -> STB Load Cases.Results
   STB Analyze.Results -> STB Displacements.Results
   STB Analyze.Results -> STB Forces.Results
   STB Analyze.Results -> STB Deformed Shape.Results
   ```

8. Save as:

   ```text
   grasshopper/samples/stb_analyze_rhino8.ghx
   ```

## Notes for cross-platform use

- Keep paths as editable panel values rather than hard-coding them inside custom
  components.
- Leave `Python Exe` and `Repo Root` empty so the same definition works on
  Windows and macOS, and on student installs.
- The `.ghx` sample should not include machine-specific absolute paths unless it
  is clearly marked as a local smoke-test file.
