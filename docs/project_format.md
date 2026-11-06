# Project sidecar format (`model.project.json`)

`model.project.json` is an optional JSON file placed next to an existing
analysis input file. It does not replace or change the low-level `.dat` format.
The `.dat` file remains the source for nodes, elements, sections, loads, and
analysis cases. The project file adds the minimum building-level information
needed for practice reports and classroom views.

Default sidecar name:

| Analysis file | Project file |
|---|---|
| `model.dat` | `model.project.json` |
| `data/input01.dat` | `data/input01.project.json` |

## Minimal example

```json
{
  "schema": 1,
  "model": {
    "dat": "model.dat"
  },
  "building": {
    "name": "Sample wooden single-story building",
    "location": "Tokyo",
    "use": "residential",
    "structure": "wood",
    "calculation_route": "route-1",
    "designer": {
      "name": "Structural Toolbox User",
      "qualification": "",
      "license_number": "",
      "contact": ""
    }
  },
  "grids": [
    {"name": "X1", "direction": "x", "coordinate": 0.0},
    {"name": "X2", "direction": "x", "coordinate": 3.64},
    {"name": "Y1", "direction": "y", "coordinate": 0.0},
    {"name": "Y2", "direction": "y", "coordinate": 2.73}
  ],
  "stories": [
    {"name": "1", "elevation": 0.0, "height": 3.0}
  ],
  "member_classes": [
    {
      "name": "main_columns",
      "kind": "column",
      "element_ids": [1, 2, 3, 4],
      "story": "1",
      "use": "wood column",
      "notes": ""
    },
    {
      "name": "roof_beams",
      "kind": "beam",
      "element_ids": [5, 6],
      "story": "1",
      "use": "wood beam",
      "notes": ""
    }
  ],
  "report": {
    "title": "Structural calculation draft",
    "mode": "practice",
    "language": "ja",
    "format": "markdown",
    "include_manual_items": true,
    "include_warnings": true
  }
}
```

## Fields

`schema`
: Schema version. The first supported version is `1`.

`model.dat`
: Path to the existing analysis `.dat` file, relative to this JSON file.

`building`
: Building overview for report front matter: name, location, use, structure,
  calculation route, and designer information.

`grids`
: Grid lines used by practice and education layers. `direction` is `x` or `y`;
  `coordinate` uses the same metre coordinate system as `NODE` records.

`stories`
: Story definitions. `elevation` and `height` are metres. For the first MVP,
  a wooden single-story project can define one story with `name: "1"`.

`member_classes`
: Meaning added on top of `.dat` element IDs. Supported `kind` values are
  `beam`, `column`, `brace`, `foundation_beam`, `panel`, `support`,
  `lateral_resisting_element`, and `other`.

`report`
: Report generation settings. `mode` is `practice`, `education`, or `debug`.
  `format` is `markdown`, `html`, or `pdf`; the MVP starts from Markdown.

`wall_quantity` (optional)
: 木造壁量計算（2025年4月施行の壁量基準、在来軸組構法、2階建てまで）。
  See [壁量計算 (`wall_quantity`)](#壁量計算-wall_quantity) below.

## 壁量計算 (`wall_quantity`)

Optional block for the 2025 wall-quantity check (令第46条第4項・昭56建告第1100号改正).
The calculation lives in `stb_checks/wall_quantity.py`
(`build_wall_quantity_summary(mdl, project)`); rated walls come from the model's `WWLL`
records and stories from `project.stories` (1 or 2 stories, sorted by `elevation`).

```json
"wall_quantity": {
  "enabled": true,
  "standard": "2025",
  "seismic": {
    "method": "spec",
    "c0": 0.2,
    "roof": "tile",
    "exterior_wall": "siding",
    "solar": {"mode": "standard"},
    "ceiling_insulation": {"mode": "default"},
    "wall_insulation": {"mode": "custom", "layers": [{"density_kg_m3": 16, "thickness_mm": 105}]}
  },
  "wind": {"coefficient_cm_m2": 50},
  "stories": [
    {"story": "1", "floor_area_m2": 62.93, "height_m": 2.985, "wind_area_x_m2": 30.5, "wind_area_y_m2": 24.0,
     "plan_polygons": [[[0, 0], [8.19, 0], [8.19, 7.28], [0, 7.28]]]},
    {"story": "2", "floor_area_m2": 49.68, "height_m": 2.86,  "wind_area_x_m2": 12.2, "wind_area_y_m2": 9.8,
     "plan_polygons": [[[0, 0], [6.825, 0], [6.825, 7.28], [0, 7.28]]]}
  ],
  "walls": [
    {"wwll_id": 12, "kind": "brace", "brace_section": "45x90", "brace_layout": "single"},
    {"wwll_id": 30, "exclude": true, "notes": "開口部のため除外"}
  ],
  "columns": [
    {"story": "1", "x": 8.19, "y": 3.64, "corner": false, "name": "C12"}
  ],
  "quasi_walls": [
    {"name": "Q1", "story": "1", "direction": "x", "length_m": 0.91, "type": "quasi",
     "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.1, "clear_height_m": 2.6,
     "x": 3.64, "y": 0.0}
  ],
  "quasi_over_half_verified": false
}
```

### 地震力に対する必要壁量

`Lw = (Ai·C0·Σwi) / (0.0196·Afi)` [cm/m²], `Ai = 1 + (1/√αi − αi)·2T/(1+3T)`, `T = 0.03h`.
The result is rounded up to an integer and multiplied by the floor area.

| `seismic` key | Meaning |
| --- | --- |
| `method` | `spec` (default): Σwi is built the same way as the 日本住宅・木材技術センター 表計算ツール（在来軸組工法用 ver1.2）. `direct`: Σwi per story is given by `stories[].weight_kN` (the load each story carries, kN). |
| `c0` | 標準せん断力係数 (default 0.2; 0.3 where 令88条2項の軟弱地盤 is designated) |
| `building_height_m` | 建物の高さ h. Default = 0.9 + Σ階高 + 0.5 (the tool's convention) |
| `single_story_lw_cm_m2` | 平屋の床面積に乗ずる数値 for 四分割法 (1F side strips with no 2nd floor above). Computed automatically with `spec`; give it for `direct`. |
| `roof` | `tile` 瓦屋根（ふき土無）1300 / `slate` スレート屋根 1000 / `metal` 金属板ぶき 650 N/m² |
| `exterior_wall` | `earth` 土塗り壁等 1000 / `mortar` モルタル等 890 / `siding` サイディング 600 / `metal` 金属板張 500 / `wood_board` 下見板張 350 N/m² |
| `solar.mode` | `none`, `standard` (260 N/m²), `mass` (`mass_kg` spread over the largest floor area) |
| `ceiling_insulation`, `wall_insulation` | `default` (100 / 70 N/m²) or `custom` with density × thickness layers (wall: up to 2 layers) |

`spec` also uses the tool's fixed values: 開口部（トリプルガラス）400, 内壁 200 N/m² per 2.8 m story height,
床 610, 積載（地震用）600 N/m². Wall loads are converted to floor-area loads with the tool's 6 m × 16.5 m
reference plan and 9 % opening ratio. Results reproduce the MLIT 補足資料 example (1F 46 / 2F 28 cm/m²)
and the 早見表 values (see `tests/test_wall_quantity.py`).

`stories[].height_m` is the tool's 階高: 2F = 小屋梁・桁上端〜2階床梁上端, 1F = 2階床梁上端〜土台上端.
It defaults to `project.stories[].height`.

### 風圧力に対する必要壁量

`stories[].wind_area_x_m2 × wind.coefficient_cm_m2` (default 50; 特定行政庁が指定する区域は 50〜75).
`wind_area_x_m2` is the 見付面積 used for the **X-direction walls** (the elevation that faces wind blowing
along X, i.e. the YZ-plane projection), measured above each floor level + 1.35 m. `wind_area_y_m2` is the
same for Y-direction walls.

### 存在壁量

- Rated walls: every `WWLL` record, assigned to the story whose `elevation` matches the bottom nodes
  (or `walls[].story`). Amount = effective multiplier × length (cm).
- `walls[]` overrides per `wwll_id`: `kind` (`brace` applies αh = 3.5·Ld/H0 ≤ 1.0 when the wall height
  exceeds 3.2 m), `multiplier`, `story`, `exclude`.
- 倍率上限 7.0: WWLL records on the same frame (same story, direction, position, length) are summed and
  scaled down to 7.0 in total.
- `quasi_walls[]` (準耐力壁等): `type` = `quasi` (準耐力壁) or `hanging_waist` (垂れ壁・腰壁);
  multiplier = `base_multiplier` × 0.6 × `material_height_m`/`clear_height_m` (`material: panel`) or
  0.5 × ratio (`material: lath` 木ずり). Width / height conditions are reported as warnings.
  `x`, `y` are the plan coordinates of the wall **center** (needed for 四分割法 and N値計算).
- 準耐力壁等 are counted up to 1/2 of the required quantity of each story and direction. Set
  `quasi_over_half_verified: true` only when 柱の折損等の脆性的な破壊が生じないこと has been confirmed;
  then the full amount is counted.

Each story and direction passes when 存在壁量 ≥ max(地震力, 風圧力の必要壁量). The summary also lists the
applicability limits (階数 ≤ 2, 延べ面積 ≤ 300 m², 高さ ≤ 16 m).

### 壁配置のバランス（四分割法）

`stb_checks/wall_balance.py` (`summary.balance`). `stories[].plan_polygons` gives the floor outline of each
story ([[x, y], ...], m; several polygons are merged). Without it the bounding rectangle of the wall end
points is used and a warning is issued.

- The plan's extent perpendicular to the walls is split into quarters. X-direction walls use the 下/上
  strips (y), Y-direction walls the 左/右 strips (x). Walls whose line lies in a strip, including on the 1/4
  line, are counted.
- 必要壁量 = strip area (plan ∩ strip) × 床面積に乗ずる数値. In a two-story building a 1F strip uses the
  2階建ての1階 value when any part of the 2F plan lies over it, otherwise the 平屋 value
  (`single_story_lw_cm_m2`; 審査マニュアル 図3-18).
- Passes when both 壁量充足率 > 1.0, or 壁率比 (small/large) ≥ 0.5.
- 準耐力壁等 are excluded unless they exceed 1/2 of the required quantity in some story and direction.
- When a frame exceeds the 7.0 cap, the check is done both with the capped and with the actual (実態)
  multipliers, and both must pass.

### 柱頭・柱脚の接合方法（N値計算法）

`stb_checks/n_value.py` (`summary.n_values`). Columns are taken from the wall end points (WWLL bottom line
N1–N2, quasi walls from center ± length/2), and also from 1F positions below 2F wall-end columns.

- `N = A1·B1·H1/2.7 − L` (平屋, 2F, 1F with no 2F above);
  `N = A1·B1·H1/2.7 + A2·B2·H2/2.7 − L` (1F with 2F above). H is the story height; 3.2 m or less counts as
  2.7. B = 0.8 at a 出隅 column, otherwise 0.5. L = 0.4 / 0.6 for single-story-type columns, and
  1.0 / 1.6 for 1F columns with a 2nd floor above (出隅 / other).
- A = |Σ multiplier on one side − Σ on the other side| + 筋かい補正値 (表3-14), using the actual
  multipliers (after αh, without the 7.0 cap). N is computed for X and Y and the larger value governs.
- 筋かい: give `walls[].brace_section` (`15x90` (also 鉄筋φ9), `30x90`, `45x90`, `90x90`) and
  `brace_layout` (`single` / `x`; default from WWLL `LAYO`). A single brace runs from the N1 column foot
  to the column head above N2, so the N2 column takes the brace top (柱頭側 +, 柱脚側 −).
- 出隅: from `columns[].corner` when given, otherwise convex vertices of `plan_polygons`, otherwise
  L-shaped wall junctions.
- 準耐力壁等 count as multiplier 0 unless they exceed 1/2 of the required quantity, except frames whose
  準耐力壁等 multiplier exceeds 1.5.
- The joint is selected from 表3-16 (い)〜(ぬ) (N ≤ 0, 0.65, 1.0, 1.4, 1.6, 1.8, 2.8, 3.7, 4.7, 5.6).
  Above 5.6 the column is reported as 要検討 with 必要耐力 5.3·N kN.

### 柱の小径

`stb_checks/column_size.py` (`summary.column_size`), following the three methods of the 表計算ツール
(令43条1項・6項, 平12建告1349号). Optional `wall_quantity.column_size` block:

```json
"column_size": {
  "enabled": true,
  "check_model_columns": true,
  "stories": [
    {"story": "1", "jas": "JAS目視等級区分構造用製材", "species": "すぎ", "grade": "二級"},
    {"story": "2", "fc_n_mm2": 24.6, "label": "ひのき E90", "length_mm": 2700}
  ],
  "tributary_checks": [
    {"name": "C12", "story": "1", "location": "outer", "b_mm": 105, "d_mm": 105, "area_m2": 6.2}
  ]
}
```

- Column load Wd (kN/m², 固定+積載, 積載 1300 N/m² for columns, no snow) is built from the same
  specification as the seismic `spec` method, for 外周部 and 内部 columns. With `seismic.method: direct`
  give `outer_load_kN_m2` / `inner_load_kN_m2` per story.
- l (横架材相互間の垂直距離) = 階高 − 105 mm (平屋・2F) / − 120 mm (2階建ての1階), or `length_mm`.
- 必要小径 de (2-1: すぎ無等級 Fc 17.7, 2-2: the story's material) uses the 外周部 load with Ae = 5 m² and
  the 告示 buckling formula, and 有効細長比 ≤ 150. Materials are given by (`jas`, `species`, `grade`) from
  the tool's 基準強度 table (`stb_project/column_fc_table.py`) or directly by `fc_n_mm2`.
- 2-3 柱の負担可能面積 is listed for 105 and 120 square columns (外周部 / 内部); `tributary_checks`
  compare a given column size and load area against it.
- Model columns (vertical, rectangular, not auto-generated elements) are grouped by story and section and
  checked as min(b, d) ≥ de.
- Results reproduce the tool's 入力例 sheet (see `tests/test_column_size.py`).

`summary.overall_status` combines the 壁量, 四分割法, N値 and 柱の小径 results.

### 壁量計算書の出力

`stb_reports/wall_quantity_report.py` builds the 確認申請用 壁量計算書 (draft) from the summary:
一般事項・総合判定, 準拠基準・適用範囲, 地震力（単位荷重・Lw）, 風圧力, 存在壁量（壁リスト）, 壁量判定（表3-12）,
準耐力壁等の割合（表3-11）, 四分割法（表3-13・耐力壁配置図）, N値計算（柱リスト・接合部図）, 柱の小径, 警告.

- HTML: A4 print layout with SVG plan figures; open it in a browser and print / save as PDF.
- Markdown: the same tables without figures.

```bash
stb wallcalc data/sample_wall_quantity_2f.project.json -o wall_quantity.html -v
```

The input may also be a `.dat` with a `.project.json` sidecar. Only parsing is needed (no solve). In the
GUI (Advanced), **Wall quantity…** opens the report for the current model
(`GET /api/wall-quantity/report?path=...`). A complete example is
`data/sample_wall_quantity_2f.dat` + `data/sample_wall_quantity_2f.project.json` (synthetic two-story house
with a single-story 下屋, a braced wall, a 腰壁・垂れ壁 and column materials).

## Python API

```python
from stb_project import load_project_for_dat

project = load_project_for_dat("data/input01.dat")
if project is not None:
    print(project.building.name)
```

`load_project_for_dat()` returns `None` when the sidecar file is missing unless
`required=True` is passed. This keeps existing `.dat` workflows unchanged.

