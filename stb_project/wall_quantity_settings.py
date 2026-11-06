"""``wall_quantity`` settings in ``model.project.json`` (木造壁量計算).

Targets the 2025 (令和7年4月施行) wall-quantity rules for 在来軸組構法 houses with
up to two stories (令第46条第4項, 昭56建告第1100号). The seismic required wall
quantity follows the MLIT 算定式 and the 日本住宅・木材技術センター 表計算ツール
(在来軸組工法用 ver1.2); see ``stb_checks/wall_quantity.py`` for the formulas.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from stb_project.schema import ProjectSchemaError


WALL_QUANTITY_STANDARD_2025 = "2025"
ALLOWED_WALL_QUANTITY_STANDARDS = (WALL_QUANTITY_STANDARD_2025,)

# Seismic weight methods: "spec" = 表計算ツール (仕様選択), "direct" = Σwi given per story.
ALLOWED_SEISMIC_WEIGHT_METHODS = ("spec", "direct")

# 屋根の仕様 (N/m2 of roof). 表計算ツール ver1.2.
ROOF_UNIT_LOADS_N_M2 = {
    "tile": 1300.0,      # 瓦屋根（ふき土無）
    "slate": 1000.0,     # スレート屋根
    "metal": 650.0,      # 金属板ぶき
}
ROOF_LABELS_JA = {
    "tile": "瓦屋根（ふき土無）",
    "slate": "スレート屋根",
    "metal": "金属板ぶき",
}

# 外壁の仕様 (N/m2 of wall). 表計算ツール ver1.2.
EXTERIOR_WALL_UNIT_LOADS_N_M2 = {
    "earth": 1000.0,      # 土塗り壁等
    "mortar": 890.0,      # モルタル等
    "siding": 600.0,      # サイディング
    "metal": 500.0,       # 金属板張
    "wood_board": 350.0,  # 下見板張
}
EXTERIOR_WALL_LABELS_JA = {
    "earth": "土塗り壁等",
    "mortar": "モルタル等",
    "siding": "サイディング",
    "metal": "金属板張",
    "wood_board": "下見板張",
}

ALLOWED_SOLAR_MODES = ("none", "standard", "mass")
ALLOWED_INSULATION_MODES = ("default", "custom")

ALLOWED_WALL_KINDS = ("brace", "panel", "other")
ALLOWED_QUASI_WALL_TYPES = ("quasi", "hanging_waist")  # 準耐力壁 / 垂れ壁・腰壁
ALLOWED_QUASI_WALL_MATERIALS = ("panel", "lath")       # 面材 / 木ずり
ALLOWED_WALL_DIRECTIONS = ("x", "y")
# 筋かいの種類 (H12建告1460号 / 審査マニュアル表3-14). "15x90" includes 鉄筋φ9.
ALLOWED_BRACE_SECTIONS = ("15x90", "30x90", "45x90", "90x90")
ALLOWED_BRACE_LAYOUTS = ("single", "x")

DEFAULT_SEISMIC_C0 = 0.2
DEFAULT_WIND_COEFFICIENT_CM_M2 = 50.0
DEFAULT_MULTIPLIER_CAP = 7.0


WALL_QUANTITY_JSON_SCHEMA = {
    "type": "object",
    "description": "木造壁量計算 (2025 standard, up to 2 stories).",
    "additionalProperties": False,
    "properties": {
        "enabled": {"type": "boolean"},
        "standard": {"enum": list(ALLOWED_WALL_QUANTITY_STANDARDS)},
        "seismic": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "method": {"enum": list(ALLOWED_SEISMIC_WEIGHT_METHODS)},
                "c0": {"type": "number"},
                "building_height_m": {"type": "number"},
                "single_story_lw_cm_m2": {
                    "type": "number",
                    "description": "平屋の床面積に乗ずる数値 for 1F side strips without a 2nd floor above (direct method).",
                },
                "roof": {"enum": list(ROOF_UNIT_LOADS_N_M2)},
                "exterior_wall": {"enum": list(EXTERIOR_WALL_UNIT_LOADS_N_M2)},
                "solar": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "mode": {"enum": list(ALLOWED_SOLAR_MODES)},
                        "mass_kg": {"type": "number"},
                    },
                },
                "ceiling_insulation": {"$ref": "#/$defs/insulation"},
                "wall_insulation": {"$ref": "#/$defs/insulation"},
            },
        },
        "wind": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "coefficient_cm_m2": {"type": "number"},
            },
        },
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["story", "floor_area_m2"],
                "additionalProperties": False,
                "properties": {
                    "story": {"type": "string"},
                    "floor_area_m2": {"type": "number"},
                    "height_m": {"type": "number"},
                    "weight_kN": {"type": "number"},
                    "wind_area_x_m2": {"type": "number"},
                    "wind_area_y_m2": {"type": "number"},
                    "plan_polygons": {
                        "type": "array",
                        "description": "Floor plan outline(s) of the story as [[x, y], ...] (m).",
                        "items": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
                        },
                    },
                },
            },
        },
        "walls": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["wwll_id"],
                "additionalProperties": False,
                "properties": {
                    "wwll_id": {"type": "integer"},
                    "story": {"type": "string"},
                    "kind": {"enum": list(ALLOWED_WALL_KINDS)},
                    "multiplier": {"type": "number"},
                    "exclude": {"type": "boolean"},
                    "brace_section": {"enum": list(ALLOWED_BRACE_SECTIONS)},
                    "brace_layout": {"enum": list(ALLOWED_BRACE_LAYOUTS)},
                    "notes": {"type": "string"},
                },
            },
        },
        "columns": {
            "type": "array",
            "description": "Per-column overrides for N値計算 (matched by story and plan position).",
            "items": {
                "type": "object",
                "required": ["story", "x", "y"],
                "additionalProperties": False,
                "properties": {
                    "story": {"type": "string"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "corner": {"type": "boolean"},
                    "name": {"type": "string"},
                },
            },
        },
        "quasi_walls": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "story", "direction", "length_m", "type", "material", "material_height_m", "clear_height_m"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "story": {"type": "string"},
                    "direction": {"enum": list(ALLOWED_WALL_DIRECTIONS)},
                    "length_m": {"type": "number"},
                    "type": {"enum": list(ALLOWED_QUASI_WALL_TYPES)},
                    "material": {"enum": list(ALLOWED_QUASI_WALL_MATERIALS)},
                    "base_multiplier": {"type": "number"},
                    "material_height_m": {"type": "number"},
                    "clear_height_m": {"type": "number"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "notes": {"type": "string"},
                },
            },
        },
        "quasi_over_half_verified": {"type": "boolean"},
        "column_size": {
            "type": "object",
            "description": "柱の小径 (令43条1項・6項, 平12建告1349号).",
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "check_model_columns": {"type": "boolean"},
                "stories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["story"],
                        "additionalProperties": False,
                        "properties": {
                            "story": {"type": "string"},
                            "jas": {"type": "string"},
                            "species": {"type": "string"},
                            "grade": {"type": "string"},
                            "fc_n_mm2": {"type": "number"},
                            "label": {"type": "string"},
                            "length_mm": {"type": "number"},
                            "outer_load_kN_m2": {"type": "number"},
                            "inner_load_kN_m2": {"type": "number"},
                        },
                    },
                },
                "tributary_checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["story", "location", "b_mm", "d_mm", "area_m2"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "story": {"type": "string"},
                            "location": {"enum": ["outer", "inner"]},
                            "b_mm": {"type": "number"},
                            "d_mm": {"type": "number"},
                            "area_m2": {"type": "number"},
                        },
                    },
                },
            },
        },
    },
    "$defs": {
        "insulation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "mode": {"enum": list(ALLOWED_INSULATION_MODES)},
                "layers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["density_kg_m3", "thickness_mm"],
                        "additionalProperties": False,
                        "properties": {
                            "density_kg_m3": {"type": "number"},
                            "thickness_mm": {"type": "number"},
                        },
                    },
                },
            },
        },
    },
}


@dataclass(frozen=True)
class InsulationLayer:
    density_kg_m3: float
    thickness_mm: float


@dataclass(frozen=True)
class InsulationSettings:
    mode: str = "default"
    layers: Tuple[InsulationLayer, ...] = ()


@dataclass(frozen=True)
class SolarSettings:
    mode: str = "none"
    mass_kg: float = 0.0


@dataclass(frozen=True)
class WallQuantitySeismicSettings:
    method: str = "spec"
    c0: float = DEFAULT_SEISMIC_C0
    building_height_m: Optional[float] = None
    single_story_lw_cm_m2: Optional[float] = None
    roof: str = ""
    exterior_wall: str = ""
    solar: SolarSettings = SolarSettings()
    ceiling_insulation: InsulationSettings = InsulationSettings()
    wall_insulation: InsulationSettings = InsulationSettings()


@dataclass(frozen=True)
class WallQuantityWindSettings:
    coefficient_cm_m2: float = DEFAULT_WIND_COEFFICIENT_CM_M2


@dataclass(frozen=True)
class WallQuantityStoryInput:
    story: str
    floor_area_m2: float
    height_m: Optional[float] = None
    weight_kN: Optional[float] = None
    wind_area_x_m2: float = 0.0
    wind_area_y_m2: float = 0.0
    plan_polygons: Tuple[Tuple[Tuple[float, float], ...], ...] = ()


@dataclass(frozen=True)
class WallQuantityWallOverride:
    wwll_id: int
    story: str = ""
    kind: str = "other"
    multiplier: Optional[float] = None
    exclude: bool = False
    brace_section: str = ""
    brace_layout: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ColumnOverride:
    story: str
    x: float
    y: float
    corner: Optional[bool] = None
    name: str = ""


@dataclass(frozen=True)
class QuasiWallInput:
    name: str
    story: str
    direction: str
    length_m: float
    type: str
    material: str
    material_height_m: float
    clear_height_m: float
    base_multiplier: Optional[float] = None
    x: Optional[float] = None  # wall center (plan)
    y: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class ColumnStorySettings:
    story: str
    jas: str = ""
    species: str = ""
    grade: str = ""
    fc_n_mm2: Optional[float] = None
    label: str = ""
    length_mm: Optional[float] = None
    outer_load_kN_m2: Optional[float] = None
    inner_load_kN_m2: Optional[float] = None


@dataclass(frozen=True)
class TributaryCheckInput:
    story: str
    location: str                  # "outer" (外周部の柱) / "inner" (内部の柱)
    b_mm: float
    d_mm: float
    area_m2: float
    name: str = ""


@dataclass(frozen=True)
class ColumnSizeSettings:
    enabled: bool = True
    check_model_columns: bool = True
    stories: Tuple[ColumnStorySettings, ...] = ()
    tributary_checks: Tuple[TributaryCheckInput, ...] = ()


@dataclass(frozen=True)
class WallQuantitySettings:
    enabled: bool = False
    standard: str = WALL_QUANTITY_STANDARD_2025
    seismic: WallQuantitySeismicSettings = WallQuantitySeismicSettings()
    wind: WallQuantityWindSettings = WallQuantityWindSettings()
    stories: Tuple[WallQuantityStoryInput, ...] = ()
    walls: Tuple[WallQuantityWallOverride, ...] = ()
    columns: Tuple[ColumnOverride, ...] = ()
    quasi_walls: Tuple[QuasiWallInput, ...] = ()
    quasi_over_half_verified: bool = False
    column_size: ColumnSizeSettings = ColumnSizeSettings()

    @property
    def is_default(self):
        return self == WallQuantitySettings()


# ---------------------------------------------------------------------------
# Parsing


def parse_wall_quantity_settings(raw, path="project.wall_quantity"):
    if raw is None:
        return WallQuantitySettings()
    _require_dict(raw, path)
    _reject_unknown(
        raw,
        ["enabled", "standard", "seismic", "wind", "stories", "walls", "columns", "quasi_walls",
         "quasi_over_half_verified", "column_size"],
        path,
    )
    standard = _opt_str(raw, "standard", path, WALL_QUANTITY_STANDARD_2025)
    if standard not in ALLOWED_WALL_QUANTITY_STANDARDS:
        raise ProjectSchemaError(path + ".standard is not supported: " + standard)

    seismic = _parse_seismic(raw.get("seismic", {}), path + ".seismic")
    wind = _parse_wind(raw.get("wind", {}), path + ".wind")

    stories_raw = raw.get("stories", [])
    _require_list(stories_raw, path + ".stories")
    stories = []
    seen = set()
    for idx, item in enumerate(stories_raw):
        p = path + ".stories[" + str(idx) + "]"
        story = _parse_story_input(item, p)
        if story.story in seen:
            raise ProjectSchemaError(p + " duplicates story " + story.story)
        seen.add(story.story)
        stories.append(story)

    walls_raw = raw.get("walls", [])
    _require_list(walls_raw, path + ".walls")
    walls = []
    seen_ids = set()
    for idx, item in enumerate(walls_raw):
        p = path + ".walls[" + str(idx) + "]"
        wall = _parse_wall_override(item, p)
        if wall.wwll_id in seen_ids:
            raise ProjectSchemaError(p + " duplicates wwll_id " + str(wall.wwll_id))
        seen_ids.add(wall.wwll_id)
        walls.append(wall)

    columns_raw = raw.get("columns", [])
    _require_list(columns_raw, path + ".columns")
    columns = [
        _parse_column_override(item, path + ".columns[" + str(idx) + "]")
        for idx, item in enumerate(columns_raw)
    ]

    quasi_raw = raw.get("quasi_walls", [])
    _require_list(quasi_raw, path + ".quasi_walls")
    quasi = [
        _parse_quasi_wall(item, path + ".quasi_walls[" + str(idx) + "]")
        for idx, item in enumerate(quasi_raw)
    ]

    return WallQuantitySettings(
        enabled=_opt_bool(raw, "enabled", path, True),
        standard=standard,
        seismic=seismic,
        wind=wind,
        stories=tuple(stories),
        walls=tuple(walls),
        columns=tuple(columns),
        quasi_walls=tuple(quasi),
        quasi_over_half_verified=_opt_bool(raw, "quasi_over_half_verified", path, False),
        column_size=_parse_column_size(raw.get("column_size", {}), path + ".column_size"),
    )


def _parse_column_size(raw, path):
    _require_dict(raw, path)
    _reject_unknown(raw, ["enabled", "check_model_columns", "stories", "tributary_checks"], path)
    stories_raw = raw.get("stories", [])
    _require_list(stories_raw, path + ".stories")
    stories = []
    seen = set()
    for idx, item in enumerate(stories_raw):
        p = path + ".stories[" + str(idx) + "]"
        _require_dict(item, p)
        _reject_unknown(
            item,
            ["story", "jas", "species", "grade", "fc_n_mm2", "label", "length_mm",
             "outer_load_kN_m2", "inner_load_kN_m2"],
            p,
        )
        story = _req_str(item, "story", p)
        if story in seen:
            raise ProjectSchemaError(p + " duplicates story " + story)
        seen.add(story)
        values = {}
        for key in ("fc_n_mm2", "length_mm", "outer_load_kN_m2", "inner_load_kN_m2"):
            values[key] = _opt_num(item, key, p, None)
            if values[key] is not None and values[key] <= 0.0:
                raise ProjectSchemaError(p + "." + key + " must be positive")
        jas = _opt_str(item, "jas", p, "")
        if values["fc_n_mm2"] is None and jas:
            from stb_project.column_fc_table import lookup_column_fc

            fc = lookup_column_fc(jas, _opt_str(item, "species", p, ""), _opt_str(item, "grade", p, ""))
            if fc is None:
                raise ProjectSchemaError(p + ": 柱材 (jas, species, grade) が基準強度表にありません")
        stories.append(ColumnStorySettings(
            story=story,
            jas=jas,
            species=_opt_str(item, "species", p, ""),
            grade=_opt_str(item, "grade", p, ""),
            fc_n_mm2=values["fc_n_mm2"],
            label=_opt_str(item, "label", p, ""),
            length_mm=values["length_mm"],
            outer_load_kN_m2=values["outer_load_kN_m2"],
            inner_load_kN_m2=values["inner_load_kN_m2"],
        ))
    checks_raw = raw.get("tributary_checks", [])
    _require_list(checks_raw, path + ".tributary_checks")
    checks = []
    for idx, item in enumerate(checks_raw):
        p = path + ".tributary_checks[" + str(idx) + "]"
        _require_dict(item, p)
        _reject_unknown(item, ["name", "story", "location", "b_mm", "d_mm", "area_m2"], p)
        location = _req_str(item, "location", p)
        if location not in ("outer", "inner"):
            raise ProjectSchemaError(p + ".location must be outer or inner")
        b = _req_num(item, "b_mm", p)
        d = _req_num(item, "d_mm", p)
        area = _req_num(item, "area_m2", p)
        if b <= 0.0 or d <= 0.0 or area <= 0.0:
            raise ProjectSchemaError(p + " b_mm, d_mm and area_m2 must be positive")
        checks.append(TributaryCheckInput(
            story=_req_str(item, "story", p), location=location, b_mm=b, d_mm=d, area_m2=area,
            name=_opt_str(item, "name", p, ""),
        ))
    return ColumnSizeSettings(
        enabled=_opt_bool(raw, "enabled", path, True),
        check_model_columns=_opt_bool(raw, "check_model_columns", path, True),
        stories=tuple(stories),
        tributary_checks=tuple(checks),
    )


def _parse_seismic(raw, path):
    _require_dict(raw, path)
    _reject_unknown(
        raw,
        ["method", "c0", "building_height_m", "single_story_lw_cm_m2", "roof", "exterior_wall", "solar",
         "ceiling_insulation", "wall_insulation"],
        path,
    )
    method = _opt_str(raw, "method", path, "spec")
    if method not in ALLOWED_SEISMIC_WEIGHT_METHODS:
        raise ProjectSchemaError(path + ".method is not supported: " + method)
    c0 = _opt_num(raw, "c0", path, DEFAULT_SEISMIC_C0)
    if c0 <= 0.0:
        raise ProjectSchemaError(path + ".c0 must be positive")
    height = _opt_num(raw, "building_height_m", path, None)
    if height is not None and height <= 0.0:
        raise ProjectSchemaError(path + ".building_height_m must be positive")
    single_lw = _opt_num(raw, "single_story_lw_cm_m2", path, None)
    if single_lw is not None and single_lw <= 0.0:
        raise ProjectSchemaError(path + ".single_story_lw_cm_m2 must be positive")
    roof = _opt_str(raw, "roof", path, "")
    if roof and roof not in ROOF_UNIT_LOADS_N_M2:
        raise ProjectSchemaError(path + ".roof is not supported: " + roof)
    exterior = _opt_str(raw, "exterior_wall", path, "")
    if exterior and exterior not in EXTERIOR_WALL_UNIT_LOADS_N_M2:
        raise ProjectSchemaError(path + ".exterior_wall is not supported: " + exterior)
    if method == "spec":
        if not roof:
            raise ProjectSchemaError(path + ".roof is required when method is spec")
        if not exterior:
            raise ProjectSchemaError(path + ".exterior_wall is required when method is spec")

    solar_raw = raw.get("solar", {})
    _require_dict(solar_raw, path + ".solar")
    _reject_unknown(solar_raw, ["mode", "mass_kg"], path + ".solar")
    solar_mode = _opt_str(solar_raw, "mode", path + ".solar", "none")
    if solar_mode not in ALLOWED_SOLAR_MODES:
        raise ProjectSchemaError(path + ".solar.mode is not supported: " + solar_mode)
    solar_mass = _opt_num(solar_raw, "mass_kg", path + ".solar", 0.0)
    if solar_mode == "mass" and solar_mass <= 0.0:
        raise ProjectSchemaError(path + ".solar.mass_kg must be positive when mode is mass")

    return WallQuantitySeismicSettings(
        method=method,
        c0=c0,
        building_height_m=height,
        single_story_lw_cm_m2=single_lw,
        roof=roof,
        exterior_wall=exterior,
        solar=SolarSettings(mode=solar_mode, mass_kg=solar_mass),
        ceiling_insulation=_parse_insulation(raw.get("ceiling_insulation", {}), path + ".ceiling_insulation", max_layers=1),
        wall_insulation=_parse_insulation(raw.get("wall_insulation", {}), path + ".wall_insulation", max_layers=2),
    )


def _parse_insulation(raw, path, max_layers):
    _require_dict(raw, path)
    _reject_unknown(raw, ["mode", "layers"], path)
    mode = _opt_str(raw, "mode", path, "default")
    if mode not in ALLOWED_INSULATION_MODES:
        raise ProjectSchemaError(path + ".mode is not supported: " + mode)
    layers_raw = raw.get("layers", [])
    _require_list(layers_raw, path + ".layers")
    layers = []
    for idx, item in enumerate(layers_raw):
        p = path + ".layers[" + str(idx) + "]"
        _require_dict(item, p)
        _reject_unknown(item, ["density_kg_m3", "thickness_mm"], p)
        density = _req_num(item, "density_kg_m3", p)
        thickness = _req_num(item, "thickness_mm", p)
        if density < 0.0 or thickness < 0.0:
            raise ProjectSchemaError(p + " values must not be negative")
        layers.append(InsulationLayer(density_kg_m3=density, thickness_mm=thickness))
    if mode == "custom" and not layers:
        raise ProjectSchemaError(path + ".layers is required when mode is custom")
    if len(layers) > max_layers:
        raise ProjectSchemaError(path + ".layers allows at most " + str(max_layers) + " layer(s)")
    return InsulationSettings(mode=mode, layers=tuple(layers))


def _parse_wind(raw, path):
    _require_dict(raw, path)
    _reject_unknown(raw, ["coefficient_cm_m2"], path)
    coef = _opt_num(raw, "coefficient_cm_m2", path, DEFAULT_WIND_COEFFICIENT_CM_M2)
    if coef <= 0.0:
        raise ProjectSchemaError(path + ".coefficient_cm_m2 must be positive")
    return WallQuantityWindSettings(coefficient_cm_m2=coef)


def _parse_story_input(raw, path):
    _require_dict(raw, path)
    _reject_unknown(
        raw,
        ["story", "floor_area_m2", "height_m", "weight_kN", "wind_area_x_m2", "wind_area_y_m2", "plan_polygons"],
        path,
    )
    story = _req_str(raw, "story", path)
    area = _req_num(raw, "floor_area_m2", path)
    if area <= 0.0:
        raise ProjectSchemaError(path + ".floor_area_m2 must be positive")
    height = _opt_num(raw, "height_m", path, None)
    if height is not None and height <= 0.0:
        raise ProjectSchemaError(path + ".height_m must be positive")
    weight = _opt_num(raw, "weight_kN", path, None)
    if weight is not None and weight <= 0.0:
        raise ProjectSchemaError(path + ".weight_kN must be positive")
    wx = _opt_num(raw, "wind_area_x_m2", path, 0.0)
    wy = _opt_num(raw, "wind_area_y_m2", path, 0.0)
    if wx < 0.0 or wy < 0.0:
        raise ProjectSchemaError(path + " wind areas must not be negative")
    return WallQuantityStoryInput(
        story=story,
        floor_area_m2=area,
        height_m=height,
        weight_kN=weight,
        wind_area_x_m2=wx,
        wind_area_y_m2=wy,
        plan_polygons=_parse_polygons(raw.get("plan_polygons", []), path + ".plan_polygons"),
    )


def _parse_wall_override(raw, path):
    _require_dict(raw, path)
    _reject_unknown(
        raw, ["wwll_id", "story", "kind", "multiplier", "exclude", "brace_section", "brace_layout", "notes"], path
    )
    wwll_id = raw.get("wwll_id")
    if type(wwll_id) is not int:
        raise ProjectSchemaError(path + ".wwll_id must be an integer")
    kind = _opt_str(raw, "kind", path, "other")
    if kind not in ALLOWED_WALL_KINDS:
        raise ProjectSchemaError(path + ".kind is not supported: " + kind)
    multiplier = _opt_num(raw, "multiplier", path, None)
    if multiplier is not None and multiplier <= 0.0:
        raise ProjectSchemaError(path + ".multiplier must be positive")
    brace_section = _opt_str(raw, "brace_section", path, "")
    if brace_section and brace_section not in ALLOWED_BRACE_SECTIONS:
        raise ProjectSchemaError(path + ".brace_section is not supported: " + brace_section)
    brace_layout = _opt_str(raw, "brace_layout", path, "")
    if brace_layout and brace_layout not in ALLOWED_BRACE_LAYOUTS:
        raise ProjectSchemaError(path + ".brace_layout is not supported: " + brace_layout)
    if (brace_section or brace_layout) and kind != "brace":
        raise ProjectSchemaError(path + ".brace_section/brace_layout require kind 'brace'")
    return WallQuantityWallOverride(
        wwll_id=wwll_id,
        story=_opt_str(raw, "story", path, ""),
        kind=kind,
        multiplier=multiplier,
        exclude=_opt_bool(raw, "exclude", path, False),
        brace_section=brace_section,
        brace_layout=brace_layout,
        notes=_opt_str(raw, "notes", path, ""),
    )


def _parse_column_override(raw, path):
    _require_dict(raw, path)
    _reject_unknown(raw, ["story", "x", "y", "corner", "name"], path)
    corner = raw.get("corner")
    if corner is not None and type(corner) is not bool:
        raise ProjectSchemaError(path + ".corner must be true or false")
    return ColumnOverride(
        story=_req_str(raw, "story", path),
        x=_req_num(raw, "x", path),
        y=_req_num(raw, "y", path),
        corner=corner,
        name=_opt_str(raw, "name", path, ""),
    )


def _parse_polygons(raw, path):
    _require_list(raw, path)
    polygons = []
    for idx, poly in enumerate(raw):
        p = path + "[" + str(idx) + "]"
        _require_list(poly, p)
        if len(poly) < 3:
            raise ProjectSchemaError(p + " needs at least 3 vertices")
        pts = []
        for jdx, pt in enumerate(poly):
            if type(pt) is not list or len(pt) != 2 or any(type(v) not in (int, float) for v in pt):
                raise ProjectSchemaError(p + "[" + str(jdx) + "] must be [x, y]")
            pts.append((float(pt[0]), float(pt[1])))
        polygons.append(tuple(pts))
    return tuple(polygons)


def _parse_quasi_wall(raw, path):
    _require_dict(raw, path)
    _reject_unknown(
        raw,
        ["name", "story", "direction", "length_m", "type", "material", "base_multiplier",
         "material_height_m", "clear_height_m", "x", "y", "notes"],
        path,
    )
    direction = _req_str(raw, "direction", path).lower()
    if direction not in ALLOWED_WALL_DIRECTIONS:
        raise ProjectSchemaError(path + ".direction must be x or y")
    wall_type = _req_str(raw, "type", path)
    if wall_type not in ALLOWED_QUASI_WALL_TYPES:
        raise ProjectSchemaError(path + ".type is not supported: " + wall_type)
    material = _req_str(raw, "material", path)
    if material not in ALLOWED_QUASI_WALL_MATERIALS:
        raise ProjectSchemaError(path + ".material is not supported: " + material)
    base = _opt_num(raw, "base_multiplier", path, None)
    if material == "panel" and (base is None or base <= 0.0):
        raise ProjectSchemaError(path + ".base_multiplier is required for panel quasi walls")
    length = _req_num(raw, "length_m", path)
    mat_h = _req_num(raw, "material_height_m", path)
    clear_h = _req_num(raw, "clear_height_m", path)
    if length <= 0.0 or mat_h <= 0.0 or clear_h <= 0.0:
        raise ProjectSchemaError(path + " length and heights must be positive")
    if mat_h > clear_h + 1.0e-9:
        raise ProjectSchemaError(path + ".material_height_m must not exceed clear_height_m")
    return QuasiWallInput(
        name=_req_str(raw, "name", path),
        story=_req_str(raw, "story", path),
        direction=direction,
        length_m=length,
        type=wall_type,
        material=material,
        material_height_m=mat_h,
        clear_height_m=clear_h,
        base_multiplier=base,
        x=_opt_num(raw, "x", path, None),
        y=_opt_num(raw, "y", path, None),
        notes=_opt_str(raw, "notes", path, ""),
    )


# ---------------------------------------------------------------------------
# Serialization


def wall_quantity_settings_to_dict(settings: WallQuantitySettings):
    s = settings.seismic
    seismic = {
        "method": s.method,
        "c0": s.c0,
        "roof": s.roof,
        "exterior_wall": s.exterior_wall,
        "solar": {"mode": s.solar.mode, "mass_kg": s.solar.mass_kg},
        "ceiling_insulation": _insulation_to_dict(s.ceiling_insulation),
        "wall_insulation": _insulation_to_dict(s.wall_insulation),
    }
    if s.building_height_m is not None:
        seismic["building_height_m"] = s.building_height_m
    if s.single_story_lw_cm_m2 is not None:
        seismic["single_story_lw_cm_m2"] = s.single_story_lw_cm_m2
    stories = []
    for st in settings.stories:
        item = {
            "story": st.story,
            "floor_area_m2": st.floor_area_m2,
            "wind_area_x_m2": st.wind_area_x_m2,
            "wind_area_y_m2": st.wind_area_y_m2,
        }
        if st.height_m is not None:
            item["height_m"] = st.height_m
        if st.weight_kN is not None:
            item["weight_kN"] = st.weight_kN
        if st.plan_polygons:
            item["plan_polygons"] = [[[x, y] for x, y in poly] for poly in st.plan_polygons]
        stories.append(item)
    walls = []
    for w in settings.walls:
        item = {"wwll_id": w.wwll_id, "kind": w.kind, "exclude": w.exclude}
        if w.story:
            item["story"] = w.story
        if w.multiplier is not None:
            item["multiplier"] = w.multiplier
        if w.brace_section:
            item["brace_section"] = w.brace_section
        if w.brace_layout:
            item["brace_layout"] = w.brace_layout
        if w.notes:
            item["notes"] = w.notes
        walls.append(item)
    quasi = []
    for q in settings.quasi_walls:
        item = {
            "name": q.name,
            "story": q.story,
            "direction": q.direction,
            "length_m": q.length_m,
            "type": q.type,
            "material": q.material,
            "material_height_m": q.material_height_m,
            "clear_height_m": q.clear_height_m,
        }
        if q.base_multiplier is not None:
            item["base_multiplier"] = q.base_multiplier
        if q.x is not None:
            item["x"] = q.x
        if q.y is not None:
            item["y"] = q.y
        if q.notes:
            item["notes"] = q.notes
        quasi.append(item)
    return {
        "enabled": settings.enabled,
        "standard": settings.standard,
        "seismic": seismic,
        "wind": {"coefficient_cm_m2": settings.wind.coefficient_cm_m2},
        "stories": stories,
        "walls": walls,
        "columns": [_column_to_dict(c) for c in settings.columns],
        "quasi_walls": quasi,
        "quasi_over_half_verified": settings.quasi_over_half_verified,
        "column_size": _column_size_to_dict(settings.column_size),
    }


def _column_size_to_dict(cs: ColumnSizeSettings):
    stories = []
    for s in cs.stories:
        item = {"story": s.story}
        for key in ("jas", "species", "grade", "label"):
            if getattr(s, key):
                item[key] = getattr(s, key)
        for key in ("fc_n_mm2", "length_mm", "outer_load_kN_m2", "inner_load_kN_m2"):
            if getattr(s, key) is not None:
                item[key] = getattr(s, key)
        stories.append(item)
    checks = []
    for c in cs.tributary_checks:
        item = {"story": c.story, "location": c.location, "b_mm": c.b_mm, "d_mm": c.d_mm, "area_m2": c.area_m2}
        if c.name:
            item["name"] = c.name
        checks.append(item)
    return {
        "enabled": cs.enabled,
        "check_model_columns": cs.check_model_columns,
        "stories": stories,
        "tributary_checks": checks,
    }


def _column_to_dict(c: ColumnOverride):
    out = {"story": c.story, "x": c.x, "y": c.y}
    if c.corner is not None:
        out["corner"] = c.corner
    if c.name:
        out["name"] = c.name
    return out


def _insulation_to_dict(ins: InsulationSettings):
    out = {"mode": ins.mode}
    if ins.layers:
        out["layers"] = [
            {"density_kg_m3": l.density_kg_m3, "thickness_mm": l.thickness_mm}
            for l in ins.layers
        ]
    return out


# ---------------------------------------------------------------------------
# Small validators (kept local to avoid importing private helpers from schema.py)


def _require_dict(value, path):
    if type(value) is not dict:
        raise ProjectSchemaError(path + " must be dict")


def _require_list(value, path):
    if type(value) is not list:
        raise ProjectSchemaError(path + " must be list")


def _reject_unknown(raw, allowed, path):
    for key in raw.keys():
        if key not in allowed:
            raise ProjectSchemaError(path + "." + str(key) + " is not supported")


def _req_str(raw, key, path):
    if key not in raw:
        raise ProjectSchemaError(path + "." + key + " is required")
    value = raw[key]
    if type(value) is not str or value.strip() == "":
        raise ProjectSchemaError(path + "." + key + " must be a non-empty string")
    return value


def _opt_str(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) is not str:
        raise ProjectSchemaError(path + "." + key + " must be a string")
    return value


def _req_num(raw, key, path):
    if key not in raw:
        raise ProjectSchemaError(path + "." + key + " is required")
    value = raw[key]
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _opt_num(raw, key, path, default):
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _opt_bool(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) is not bool:
        raise ProjectSchemaError(path + "." + key + " must be true or false")
    return value
