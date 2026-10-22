# Input text format (Structural Toolbox)

Comma-separated text files (`.dat`, `.stb`, etc.) for 3D linear static frame analysis.  
The GUI editor, `stb solve`, and `stb validate` all use the same parser (`ReadLines` in `classes/io.py`).

## General rules

- One record per line; fields separated by **commas** (`,`).
- Lines starting with `#` are comments and ignored.
- Blank lines are ignored.
- **First column is always a 4-character uppercase record type** (e.g. `MATE`, `WWLL`).
- **Data columns are positional numbers or minimal text** — do not use `KEY=value` syntax.
- **Enumerated values use integer codes** (documented in comment headers and below).
- Each record group in a file starts with `# ---` comment lines describing the columns.
- **Use explicit load keywords** — see [Loads](#loads) below.
- Define materials and sections before elements that reference them; define nodes before elements.

### Not supported: `LOAD`

The keyword **`LOAD` is not read**. It does not mean “point, line, or area” and is intentionally unsupported.

| Intent | Use |
|--------|-----|
| Point load (force/moment at a node) | **`PLOD`** |
| Distributed load on a member | **`ELOD`** |
| Pressure on a panel bounded by members | **`ALOD`** |
| Self-weight / gravity direction | **`GLOD`** |

Old files may still contain `LOAD` lines (e.g. `data/input01.dat`); those lines are **silently ignored**. Replace them with `PLOD` if you need those point loads.

---

## Units (input)

| Quantity | Input unit | Notes |
|----------|------------|--------|
| Node coordinates | m | |
| Material E, G, Fy | N/mm² | Converted internally to N/m² |
| Material γ (Gamma) | kN/m³ | Converted to N/m³ |
| Section dimensions | mm | Converted to m |
| Point loads (PLOD) | kN, kNm | |
| Member loads (ELOD) | kN/m | |
| Area loads (ALOD) | kN/m² | |
| Gravity (GLOD) | m/s² | Components gx, gy, gz |
| EJNT spring values | kNm/rad | Optional; blank = default rigid offsets |
| Element beta (ELEM) | degrees | |
| Diaphragm material Ex, Ey, Gxy | N/mm² | Converted internally to N/m² |
| Diaphragm thickness T | mm | Converted internally to m |
| Diaphragm material axis THETA | degrees | In-plane angle from each membrane element local x axis |

Load case IDs (`LC`) are integers you choose (e.g. `0`, `1`, `2`). Every load record must include an `LC` field.

---

## Geometry and properties

### `MATE` — material

```
MATE, ID, NAME, E, G, Gamma, Alpha, Fy
```

| Field | Unit | Description |
|-------|------|-------------|
| E, G | N/mm² | Young’s modulus, shear modulus |
| Gamma | kN/m³ | Weight density |
| Alpha | — | Thermal expansion coefficient |
| Fy | N/mm² | Yield stress (stored; linear analysis) |

---

### `SECT` — cross-section

```
SECT, ID, NAME, MAT_ID, TYPE, DIM1, DIM2, ...
```

| TYPE | Shape | Dimensions (mm) |
|------|--------|-----------------|
| 0 | Rectangle | B, H |
| 1 | Circle | D |
| 2 | I-section | H, B, tw, tf |
| 3 | CHS (tube) | D, t |
| 4 | RHS | H, B, t |

`MAT_ID` must refer to an existing `MATE` record.

---

### `NODE` — node

```
NODE, ID, X, Y, Z
```

Coordinates in **metres**. Optional trailing `*` in some GUI exports is ignored by the parser if present after the Z value (see legacy files).

---

### `ELEM` — frame element (straight member)

```
ELEM, ID, NODE_I, NODE_J, SEC_ID, BETA
```

- Connects two nodes with a 1D frame element.
- `BETA` (degrees): section rotation about the member axis; default `0` if omitted.

---

### `EJNT` — element end releases / springs (optional)

```
EJNT, ELEM_ID, Ryi, Rzi, Ryj, Rzj
```

| Field | Unit | Description |
|-------|------|-------------|
| Ryi, Rzi, Ryj, Rzj | kNm/rad | Rotational spring at ends; empty field = use built-in default |

If no `EJNT` line exists for an element, default joint stiffness is assigned in the model builder.

---

### `DMAT` — diaphragm material

```
DMAT, ID, NAME, Ex, Ey, Gxy, Nuxy, Gamma, Alpha
```

Plane-stress material used by diaphragm membrane elements. This remains the
low-level input for verification and advanced use when `Ex`, `Ey`, `Gxy`,
`Nuxy`, and membrane thickness should be specified directly.

| Field | Unit | Description |
|-------|------|-------------|
| Ex, Ey, Gxy | N/mm² | Orthotropic in-plane elastic constants |
| Nuxy | — | Major Poisson ratio |
| Gamma | kN/m³ | Weight density, stored for future use |
| Alpha | — | Thermal expansion coefficient, stored for future use |

For isotropic behavior, use `Ex = Ey = E`, `Gxy = E / (2(1 + nu))`, `Nuxy = nu`.

---

### `DIAP` — diaphragm region

```
DIAP, ID, NAME, TYPE, SRC, MAG/ID, T, THETA, RA, HMAX
```

| Col | Unit | Description |
|-----|------|-------------|
| TYPE | — | `0` = rigid, `1` = semi-rigid, `2` = flexible |
| SRC | — | `0` = explicit `DMAT`, `1` = timber floor, `2` = timber roof |
| MAG/ID | — | `SRC=0`: `DMAT` ID; `SRC=1/2`: floor/roof multiplier |
| T | mm | Membrane thickness (`SRC=1/2` defaults internally to 1000 mm if blank) |
| THETA | deg | Material axis angle in the membrane plane |
| RA | rad | Reference drift for timber conversion (default `1/150`) |
| HMAX | mm | **Metadata only** — maximum mesh/constraint spacing hint; not used by the current solver |

`TYPE=0` creates in-plane rigid-floor MPC constraints for nodes in the `DREG`
polygon (or an auto-derived polygon from `DMEM` when `DREG` is omitted).
`TYPE=1` uses `DMEM` membrane elements. `TYPE=2` stores metadata only.

Timber multipliers are converted internally to equivalent in-plane shear stiffness:

```
G*t = multiplier * 1.96 kN/m / reference_drift
```

Examples:

```
DIAP, 10, 2F_MAIN, 1, 1, 2.0, 1000, 0, 0.006667, 1820
DIAP, 20, ROOF_A, 1, 2, 1.0, 1000, 30, 0.006667, 1820
DIAP,  1, RC_SLAB, 1, 0, 10, 150, 0, ,
DIAP, 30, RIGID2F, 0, 0, , , 0, ,
```

---

### `DMEM` — 3-node CST membrane element

```
DMEM, ID, DIAP_ID, NODE1, NODE2, NODE3
```

Adds a 3-node constant-strain membrane element to a diaphragm. The element uses
local in-plane `u, v` displacement components and contributes stiffness to the
global translational DOFs `ux, uy, uz` of the three referenced nodes. Rotational
DOFs are not used by this element.

---

### `DCON` — diaphragm-to-member connection

```
DCON, DIAP, TRGT, ID, CONN, TOL, SPACING
```

| Col | Unit | Description |
|-----|------|-------------|
| TRGT | — | `0` = auto, `1` = element, `2` = node |
| ID | — | Element or node ID (`TRGT=0` → blank) |
| CONN | — | `0` = rigid in-plane tie, `1` = disconnected |
| TOL | m | Geometry tolerance for edge/triangle matching |
| SPACING | m | **Metadata only** — optional constraint spacing hint; not used by the current MPC generator |

`CONN=0` generates MPC constraints for horizontal `ux, uy` DOFs.

Examples:

```
DCON, 1, 0, , 0, 0.01
DCON, 1, 1, 201, 1,
DCON, 1, 2, 35, 0, 0.01
```

---

### `DREG` / `DOPN` — diaphragm outer polygon and openings

```
DREG, DIAP_ID, NODE1, NODE2, NODE3, ...
DOPN, DIAP_ID, NODE1, NODE2, NODE3, ...
```

**`DREG`** defines the outer polygon of a diaphragm region.

| Use | When `DREG` is needed |
|-----|------------------------|
| Rigid diaphragm (`TYPE=0`) | Required unless auto-derived from `DMEM` |
| Semi-rigid (`TYPE=1`) + `DLOD` area/mass | Recommended; auto-derived from `DMEM` outer boundary if omitted |
| Semi-rigid stiffness | Not used — stiffness comes from `DMEM` triangles |

When `DMEM` elements are supplied and `DREG` is omitted, the parser derives
the outer polygon by walking the exterior edges of the membrane mesh. An
informational warning is recorded in `mdl.input_warnings`.

When both explicit `DREG` and `DMEM` are supplied, the explicit polygon is used.
A warning is emitted if its node set differs from the `DMEM` outer boundary.

**`DOPN`** defines an opening polygon inside a diaphragm. Records are parsed
and stored, but **opening cut-outs are not applied** in the current analysis
engine. A warning is emitted when `DOPN` records are present.

---

### `CONS` — support (boundary condition)

```
CONS, NODE_ID, TX, TY, TZ, RX, RY, RZ
```

Each DOF: **`0` = free**, **`1` = fixed**.

---

## Loads

### `PLOD` — point load (nodal)

```
PLOD, NODE_ID, LC, PX, PY, PZ, MX, MY, MZ
```

Forces in **kN**, moments in **kNm**, in the **global** coordinate system.

Example (5 kN downward at node 1, load case 0):

```
PLOD, 1, 0, 0.00, 0.00, -5.00, 0.00, 0.00, 0.00
```

---

### `ELOD` — member distributed load (line load)

```
ELOD, ELEM_ID, LC, E_G, WXi, WYi, WZi, WXj, WYj, WZj[, T0, T1]
```

| Field | Description |
|-------|-------------|
| E_G | `0` = element local axes, `1` = global axes |
| WXi…WZj | Distributed load intensity at start/end (kN/m) |
| T0, T1 | Optional load range along the member (both or neither; empty = missing). `t = 0` at node Ni, `t = 1` at node Nj. Default `0, 1` (full length) |

With `T0`/`T1` the load is a linear segment: `Wi` acts at `T0`, `Wj` at `T1`,
linear in between, and zero outside `[T0, T1]`. It must satisfy
`0 <= T0 < T1 <= 1` (and `T1 - T0 > 1e-9`), otherwise the input is rejected.
A triangular or trapezoidal load is written as 2 or 3 `ELOD` records on the
same element and load case; segments are superposed. Records without
`T0`/`T1` behave exactly as before, and the `.out` input echo shows `T0, T1`
only for partial loads.

Example (10 kN/m downward, local axes, on the part of member 1 between 20 % and 40 % of its length):

```
ELOD, 1, 0, 0, 0.0, 0.0, -10.0, 0.0, 0.0, -10.0, 0.2, 0.4
```

---

### `ALOD` — area load (surface pressure)

```
ALOD, LC, PX, PY, PZ, ELEM1, ELEM2, ELEM3, ELEM4
```

| Field | Unit | Description |
|-------|------|-------------|
| PX, PY, PZ | kN/m² | Pressure components (global axes) |
| ELEM1…ELEM4 | — | Member IDs bounding the loaded panel (triangle: use 3 IDs; 4th optional) |

The pressure is distributed to the bounding members with the **tributary-area
method**: the panel surface is partitioned by nearest boundary edge
(medial-axis / 45° rule), and each member receives an equivalent
linearly-varying line load that reproduces the exact tributary resultant and
its centroid. This preserves global equilibrium and support reactions exactly,
including the member-axial pressure component. The bounding members must form a
single closed triangular or quadrilateral loop.

---

### `DLOD` — diaphragm load / seismic mass

```
DLOD, DIAP, LC, TYPE, ...
```

| TYPE | Following columns | Unit |
|------|-------------------|------|
| `0` AREA | PX, PY | kN/m² |
| `1` LINE | N1, N2, PX, PY | kN/m |
| `2` MBTR | ELEM, PX, PY | kN/m |
| `3` MASS | MASS, AX, AY | kg/m² |
| `4` WGHT | WGHT, AX, AY | kN/m² |

Examples:

```
DLOD, 10, 1, 0, 0.407, 0.0
DLOD,  1, 1, 1, 0, 1, 2.0, 0.0
DLOD,  1, 1, 4, 3.0, 1.0, 0.0
```

---

### `WWLL` — wood rated wall (multiplier input)

```
WWLL, ID, NAME, MODEL, M, L, H, DIR, RA, N1, N2, N3, N4, DIAP, LAYO
```

| Col | Unit | Description |
|-----|------|-------------|
| MODEL | — | `0` = equivalent brace, `1` = shear panel, `2` = membrane (reserved) |
| M | — | Wall multiplier |
| L, H | m | Wall length and height for conversion (optional; derived from N1..N4 when blank) |
| DIR | — | `0` = X, `1` = Y |
| RA | rad | Reference drift angle (default `1/120`) |
| N1..N4 | — | Corner node IDs (bottom line, then top line) |
| DIAP | — | Diaphragm ID for in-plane MPC tie to the wall line (blank = none) |
| LAYO | — | Brace layout: `0` = single brace, `1` = X-brace pair (default) |

The parser converts wall multiplier to allowable shear and stiffness:

```
Qa = 1.96 * m * L        (kN)
Delta = RA * H           (m)
K = Qa / Delta           (kN/m -> internally N/m)
```

For `MODEL=0`, diagonal length `d = sqrt(L^2 + H^2)` and
equivalent brace axial rigidity is:

```
EA = K * d^3 / L^2
```

For an X-brace pair, each brace uses half of this `EA`.

Users input rated-wall properties (`M, DIR, RA`) and corner nodes (`N1..N4`).
`L` and `H` may be omitted; they are then computed from the node rectangle
(bottom/top corners are identified by Z). When `L` or `H` is provided explicitly,
that value is used and a warning is emitted if it differs from the node geometry
by more than 1 mm. Explicit brace/EA input is not required.

---

### `GLOD` — gravity / acceleration

```
GLOD, LC, GX, GY, GZ
```

Acceleration components in **m/s²** (e.g. `0, 0, -9.80665` for downward Z).

---

## Load cases and combinations (optional)

### `LNME` — load case type (optional metadata)

```
LNME, LC_ID, TYPE[, LABEL]
```

| TYPE | Meaning | LABEL |
|---:|---|---|
| 1 | DL (dead / fixed load) | optional |
| 2 | LL (live load) | optional |
| 3 | LL(E) (live load for seismic weight) | optional |
| 4 | S (snow) | optional |
| 5 | W (wind) | optional |
| 6 | E (earthquake / horizontal seismic) | optional (e.g. `EQX`, `EQY`) |
| 7 | custom | **required** |

Examples:

```
LNME, 0, 1
LNME, 1, 2
LNME, 2, 3
LNME, 3, 6, EQX
LNME, 4, 6, EQY
LNME, 5, 7, COMB1
```

Legacy text names (`DL`, `EQX`, etc.) in the TYPE column are still accepted and mapped to the codes above.

For Ai seismic weight aggregation (`stb loads seismic`), **Wi uses TYPE 1 (DL) + TYPE 3 (LL(E))** on the referenced load cases. This can be overridden in `project.json` with **`load_conditions.seismic.weight_load_cases`**:

```json
"weight_load_cases": [
  { "load_case": 0, "factor": 1.0, "role": "DL", "name": "DL" },
  { "load_case": 3, "factor": 0.5, "role": "LL_E", "name": "LL(E)" }
]
```

Mass levels are defined per `project.json` **`load_conditions.seismic_masses`** when present; each entry has a **`mass_role`**:

- **`BASE_MASS`** (e.g. 1F floor supported on foundation, not on upper-structure diaphragms): included in ΣWi and αi denominator; **no DLOD** output.
- **`DIAPHRAGM_MASS`** (upper floors / roof): included in ΣWi and αi; **Fi** is written to **`application_diaphragm`** as TYPE 6 DLOD AREA.

If `seismic_masses` is omitted, legacy **`base_mass_policy`** redistribution applies. **DLOD AREA pressures use story seismic force Fi** (`Fi = Qi - Q(i+1)`; top story `Fi = Qi`), not layer shear Qi directly. Seismic force output uses **TYPE 6 (E)** load cases; axis hints come from LABEL (`EQX` → +X, `EQY` → +Y).

### `LCMB` — load combination

```
LCMB, COMB_LC, NAME, factor1, lc1, factor2, lc2, ...
```

Creates a combined load case `COMB_LC` from existing cases with factors.  
Pairs of `(factor, lc)` repeat for each term.

---

## Post-processing / plotting (optional, GUI)

### `AXIS` — plot axis definition

```
AXIS, ID, NAME, V_H, NODE_ID, X_DIR
```

| V_H | `0` = vertical plane, `1` = horizontal |
| X_DIR | For vertical: `0` = global X, `1` = global Y |

---

### `PLOT` — plot request

```
PLOT, ID, NAME, AXIS_ID, TYPE, LC, SCALE, DEFFAC
```

| TYPE | Meaning |
|------|---------|
| 0 | Model |
| 1 | Load |
| 2 | Force diagram |
| 3 | Utilization |

---

## Minimal input example

See `examples/cantilever.dat`:

```
MATE, ...
SECT, ...
NODE, ...
ELEM, ...
CONS, ...
PLOD, ...
```

Run:

```bash
.venv/bin/stb solve examples/cantilever.dat -o examples/cantilever.out -q
```

---

## Output format (after `stb solve`)

Result files are text, with records such as:

| Tag | Content |
|-----|---------|
| `SPRP` | Section properties (computed) |
| `NDSP` | Nodal displacements (m, rad) |
| `REAC` | Reactions at constrained nodes: Tx, Ty, Tz (kN), Rx, Ry, Rz (kNm) |
| `EFRC` | Element end forces (kN, kNm) |
| `EWLD` | Element load segments for section-force diagrams: `EWLD, LC, ELEM, T0, T1, WXi, WYi, WZi, WXj, WYj, WZj` (local axes, kN/m, WY/WZ in the diagram sign convention of `EFRC`); written only for members that carry line loads |

See `examples/cantilever.out` for a full example.

---

## Suggested order when writing a new file

1. `MATE`, `SECT`
2. `NODE`
3. `ELEM` (and optional `EJNT`)
4. `CONS`
5. `PLOD`, `ELOD`, `ALOD`, `GLOD` (and optional `LNME`, `LCMB`)
6. Optional `AXIS`, `PLOT` (mainly for GUI)

Validate before solving:

```bash
.venv/bin/stb validate mymodel.dat -v
```
