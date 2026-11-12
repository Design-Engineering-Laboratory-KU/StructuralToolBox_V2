import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional, Tuple


SCHEMA_VERSION = 1
DEFAULT_PROJECT_SUFFIX = ".project.json"

ALLOWED_GRID_DIRECTIONS = ("x", "y")
ALLOWED_MEMBER_KINDS = (
    "beam",
    "column",
    "brace",
    "foundation_beam",
    "panel",
    "support",
    "lateral_resisting_element",
    "other",
)
ALLOWED_REPORT_MODES = ("practice", "education", "debug")
ALLOWED_REPORT_FORMATS = ("markdown", "html", "pdf")
ALLOWED_SEISMIC_AXES = ("x", "y")
DEFAULT_SEISMIC_RT = 1.0
DEFAULT_SEISMIC_TC = 0.6
DEFAULT_SEISMIC_STEEL_RATIO_ALPHA = 0.0
ALLOWED_BASE_MASS_POLICIES = (
    "IGNORE_AT_BASE",
    "LUMP_TO_ABOVE_DIAPHRAGM",
    "DISTRIBUTE_TO_ADJACENT_LEVELS",
    "APPLY_TO_1F_DIAPHRAGM",
    "APPLY_TO_WALL_NODES",
)
DEFAULT_BASE_MASS_POLICY = "LUMP_TO_ABOVE_DIAPHRAGM"
ALLOWED_SEISMIC_WEIGHT_ROLES = ("DL", "LL_E", "OTHER")
ALLOWED_FLOOR_LOAD_ROLES = ("LL", "LL_E")
ALLOWED_MASS_ROLES = ("BASE_MASS", "DIAPHRAGM_MASS")
ALLOWED_WIND_DIRECTIONS = ("X_PLUS", "X_MINUS", "Y_PLUS", "Y_MINUS")
ALLOWED_WIND_FACES = ("X_MIN", "X_MAX", "Y_MIN", "Y_MAX")
ALLOWED_ROUGHNESS_CATEGORIES = ("I", "II", "III", "IV")
ALLOWED_WIND_PRESSURE_MODES = ("BUILDING_HEIGHT_UNIFORM", "STORY_HEIGHT_KZ")
ALLOWED_WIND_DIAPHRAGM_INPUT_MODES = (
    "DIAPHRAGM_DIRECT",
    "DIAPHRAGM_UNIFORM",
    "DIAPHRAGM_FORCE_WITH_TORSION",
    "EDGE_OR_MEMBER_LOAD",
)
ALLOWED_WIND_SURFACE_ROLES = ("WINDWARD", "LEEWARD", "SIDE", "ROOF", "PARAPET")
DEFAULT_WIND_PRESSURE_MODE = "BUILDING_HEIGHT_UNIFORM"
DEFAULT_WIND_DIAPHRAGM_INPUT_MODE = "DIAPHRAGM_DIRECT"
DEFAULT_WIND_SURFACE_ROLE = "WINDWARD"
ALLOWED_LOAD_COMBINATION_DURATIONS = ("LONG_TERM", "SHORT_TERM", "LONG_TERM_SNOW", "SHORT_TERM_SNOW")
ALLOWED_WOOD_CONDITION_KINDS = ("beam", "column", "brace")
DEFAULT_LOAD_COMBINATION_DURATION = "LONG_TERM"

ROUGHNESS_ZB = {"I": 5.0, "II": 5.0, "III": 5.0, "IV": 10.0}
ROUGHNESS_ZG = {"I": 250.0, "II": 350.0, "III": 450.0, "IV": 550.0}
ROUGHNESS_ALPHA = {"I": 0.10, "II": 0.15, "III": 0.20, "IV": 0.27}
GUST_GF_AT_10M = {"I": 2.0, "II": 2.2, "III": 2.5, "IV": 3.1}
GUST_GF_AT_40M = {"I": 1.8, "II": 2.0, "III": 2.1, "IV": 2.3}


PROJECT_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://structural-toolbox.local/schema/project-1.json",
    "title": "Structural Toolbox project sidecar",
    "type": "object",
    "required": ["schema", "model", "building", "grids", "stories", "member_classes", "report"],
    "additionalProperties": False,
    "properties": {
        "schema": {"const": SCHEMA_VERSION},
        "model": {
            "type": "object",
            "required": ["dat"],
            "additionalProperties": False,
            "properties": {
                "dat": {
                    "type": "string",
                    "description": "Path to the analysis .dat file, relative to this project JSON.",
                },
            },
        },
        "building": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "location": {"type": "string"},
                "use": {"type": "string"},
                "structure": {"type": "string"},
                "calculation_route": {"type": "string"},
                "designer": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "qualification": {"type": "string"},
                        "license_number": {"type": "string"},
                        "contact": {"type": "string"},
                    },
                },
            },
        },
        "grids": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "direction", "coordinate"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "direction": {"enum": list(ALLOWED_GRID_DIRECTIONS)},
                    "coordinate": {"type": "number"},
                },
            },
        },
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "elevation", "height"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "elevation": {"type": "number"},
                    "height": {"type": "number"},
                },
            },
        },
        "member_classes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "kind", "element_ids"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"enum": list(ALLOWED_MEMBER_KINDS)},
                    "element_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "story": {"type": "string"},
                    "use": {"type": "string"},
                    "notes": {"type": "string"},
                },
            },
        },
        "load_conditions": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "seismic": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "ci": {"type": "number"},
                        "rt": {
                            "type": "number",
                            "description": "Vibration characteristic factor Rt override (auto when omitted).",
                        },
                        "design_period_s": {"type": "number"},
                        "height_m": {"type": "number"},
                        "steel_ratio_alpha": {"type": "number"},
                        "tc": {"type": "number"},
                        "base_level": {"type": "string"},
                        "base_elevation": {"type": "number"},
                        "base_mass_policy": {"type": "string"},
                        "dead_load_lc": {"type": "integer"},
                        "live_load_lc": {"type": ["integer", "null"]},
                        "live_load_factor": {"type": "number"},
                        "weight_load_cases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["load_case"],
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "load_case": {"type": "integer"},
                                    "factor": {"type": "number"},
                                    "role": {"enum": list(ALLOWED_SEISMIC_WEIGHT_ROLES)},
                                },
                            },
                        },
                        "directions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "axis", "load_case"],
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "axis": {"enum": list(ALLOWED_SEISMIC_AXES)},
                                    "load_case": {"type": "integer"},
                                    "sign": {"type": "integer"},
                                },
                            },
                        },
                    },
                },
                "diaphragms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "story"],
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "integer"},
                            "story": {"type": "string"},
                        },
                    },
                },
                "floor_loads": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["diaphragm_id", "load_case", "role", "pressure_kN_m2"],
                        "additionalProperties": False,
                        "properties": {
                            "story": {"type": "string"},
                            "diaphragm_id": {"type": "integer"},
                            "load_case": {"type": "integer"},
                            "role": {"enum": list(ALLOWED_FLOOR_LOAD_ROLES)},
                            "name": {"type": "string"},
                            "pressure_kN_m2": {"type": "number"},
                        },
                    },
                },
                "load_combinations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["load_case", "name", "duration", "factors", "load_cases"],
                        "additionalProperties": False,
                        "properties": {
                            "load_case": {"type": "integer"},
                            "name": {"type": "string"},
                            "duration": {"enum": list(ALLOWED_LOAD_COMBINATION_DURATIONS)},
                            "factors": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                            "load_cases": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                        },
                    },
                },
            },
        },
        "design_checks": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "wood": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "load_cases": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "deflection_limit_ratio": {"type": "number"},
                        "allowable_stresses": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "bending": {"type": "number"},
                                "shear": {"type": "number"},
                                "compression": {"type": "number"},
                                "tension": {"type": "number"},
                            },
                        },
                        "load_case_durations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["load_case", "duration"],
                                "properties": {
                                    "load_case": {"type": "integer"},
                                    "duration": {"enum": list(ALLOWED_LOAD_COMBINATION_DURATIONS)},
                                },
                            },
                        },
                        "materials": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "compression", "tension", "bending", "shear"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "compression": {"type": "number"},
                                    "tension": {"type": "number"},
                                    "bending": {"type": "number"},
                                    "shear": {"type": "number"},
                                    "bearing": {"type": "number"},
                                    "bending_depth_factors": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["max_depth_mm", "factor"],
                                            "properties": {
                                                "max_depth_mm": {"type": "number"},
                                                "factor": {"type": "number"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {"enum": list(ALLOWED_WOOD_CONDITION_KINDS)},
                                    "member_class": {"type": "string"},
                                    "area_reduction_percent": {"type": "number"},
                                    "section_modulus_reduction_percent": {"type": "number"},
                                    "shear_area_reduction_percent": {"type": "number"},
                                    "inertia_reduction_percent": {"type": "number"},
                                    "buckling_factor_y": {"type": "number"},
                                    "buckling_factor_z": {"type": "number"},
                                    "lateral_buckling_coefficient": {"type": "number"},
                                    "biaxial_bending": {"type": "boolean"},
                                    "slenderness_limit": {"type": "number"},
                                    "check_bearing": {"type": "boolean"},
                                    "bearing_area_loss_mm2": {"type": "number"},
                                    "deflection_ratio_long_term": {"type": "number"},
                                    "deflection_ratio_long_term_snow": {"type": "number"},
                                    "deflection_ratio_short_term_snow": {"type": "number"},
                                    "deflection_mm_long_term": {"type": "number"},
                                    "deflection_mm_long_term_snow": {"type": "number"},
                                    "deflection_mm_short_term_snow": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "report": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "mode": {"enum": list(ALLOWED_REPORT_MODES)},
                "language": {"type": "string"},
                "format": {"enum": list(ALLOWED_REPORT_FORMATS)},
                "include_manual_items": {"type": "boolean"},
                "include_warnings": {"type": "boolean"},
            },
        },
    },
}


class ProjectSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class DesignerInfo:
    name: str = ""
    qualification: str = ""
    license_number: str = ""
    contact: str = ""


@dataclass(frozen=True)
class BuildingInfo:
    name: str = ""
    location: str = ""
    use: str = ""
    structure: str = ""
    calculation_route: str = ""
    designer: DesignerInfo = DesignerInfo()


@dataclass(frozen=True)
class GridLine:
    name: str
    direction: str
    coordinate: float


@dataclass(frozen=True)
class Story:
    name: str
    elevation: float
    height: float


@dataclass(frozen=True)
class MemberClass:
    name: str
    kind: str
    element_ids: Tuple[int, ...]
    story: str = ""
    use: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ReportSettings:
    title: str = ""
    mode: str = "practice"
    language: str = "ja"
    format: str = "markdown"
    include_manual_items: bool = True
    include_warnings: bool = True


@dataclass(frozen=True)
class WoodAllowableStresses:
    bending: float = 0.0
    shear: float = 0.0
    compression: float = 0.0
    tension: float = 0.0


@dataclass(frozen=True)
class WoodBendingDepthFactor:
    """Size factor applied to the bending strength for depths up to max_depth_mm."""

    max_depth_mm: float
    factor: float


@dataclass(frozen=True)
class WoodMaterialStrength:
    """Base design strengths (N/mm2) for a material, matched by its MATE name."""

    name: str
    compression: float
    tension: float
    bending: float
    shear: float
    bearing: float = 0.0
    bending_depth_factors: Tuple[WoodBendingDepthFactor, ...] = ()


@dataclass(frozen=True)
class WoodLoadCaseDuration:
    load_case: int
    duration: str


@dataclass(frozen=True)
class WoodMemberCondition:
    """Check conditions for a member class, or for every member of a kind."""

    kind: str = ""
    member_class: str = ""
    area_reduction_percent: float = 0.0
    section_modulus_reduction_percent: float = 0.0
    shear_area_reduction_percent: float = 0.0
    inertia_reduction_percent: float = 0.0
    buckling_factor_y: float = 1.0
    buckling_factor_z: float = 1.0
    lateral_buckling_coefficient: float = 1.9
    biaxial_bending: bool = True
    slenderness_limit: float = 150.0
    check_bearing: bool = False
    bearing_area_loss_mm2: float = 0.0
    deflection_ratio_long_term: float = 0.0
    deflection_ratio_long_term_snow: float = 0.0
    deflection_ratio_short_term_snow: float = 0.0
    deflection_mm_long_term: float = 0.0
    deflection_mm_long_term_snow: float = 0.0
    deflection_mm_short_term_snow: float = 0.0


@dataclass(frozen=True)
class WoodCheckSettings:
    enabled: bool = False
    load_cases: Tuple[int, ...] = ()
    deflection_limit_ratio: float = 0.0
    allowable_stresses: WoodAllowableStresses = field(default_factory=WoodAllowableStresses)
    load_case_durations: Tuple[WoodLoadCaseDuration, ...] = ()
    materials: Tuple[WoodMaterialStrength, ...] = ()
    conditions: Tuple[WoodMemberCondition, ...] = ()


@dataclass(frozen=True)
class DesignCheckSettings:
    wood: WoodCheckSettings = field(default_factory=WoodCheckSettings)


@dataclass(frozen=True)
class SeismicDirectionSettings:
    name: str
    axis: str
    load_case: int
    sign: int = 1


@dataclass(frozen=True)
class SeismicWeightLoadCaseSettings:
    load_case: int
    factor: float = 1.0
    role: str = "OTHER"
    name: str = ""


@dataclass(frozen=True)
class SeismicLoadSettings:
    ci: float = 0.0
    c0: Optional[float] = None
    z: Optional[float] = None
    rt: Optional[float] = None
    design_period_s: Optional[float] = None
    height_m: Optional[float] = None
    steel_ratio_alpha: float = DEFAULT_SEISMIC_STEEL_RATIO_ALPHA
    tc: float = DEFAULT_SEISMIC_TC
    base_level: Optional[str] = None
    base_elevation: Optional[float] = None
    base_mass_policy: str = DEFAULT_BASE_MASS_POLICY
    dead_load_lc: Optional[int] = None
    live_load_lc: Optional[int] = None
    live_load_factor: float = 0.0
    weight_load_cases: Tuple[SeismicWeightLoadCaseSettings, ...] = ()
    directions: Tuple[SeismicDirectionSettings, ...] = ()


def resolve_seismic_c0_z(seismic: SeismicLoadSettings):
    """Return (c0, z, z_is_default). Legacy ``ci`` holds C0×Z when ``c0`` is omitted."""

    if seismic.c0 is not None:
        c0 = float(seismic.c0)
        z = float(seismic.z) if seismic.z is not None else 1.0
        return c0, z, seismic.z is None
    if seismic.ci <= 0.0:
        raise ValueError("load_conditions.seismic.c0 or ci must be positive")
    z = float(seismic.z) if seismic.z is not None else 1.0
    c0 = float(seismic.ci) / z if z > 0.0 else float(seismic.ci)
    return c0, z, seismic.z is None


def effective_seismic_ci(seismic: SeismicLoadSettings) -> float:
    """Legacy combined coefficient C0×Z×Rt (per-story Ci uses Ai separately)."""

    c0, z, _ = resolve_seismic_c0_z(seismic)
    rt = seismic.rt if seismic.rt is not None else DEFAULT_SEISMIC_RT
    if rt <= 0.0:
        raise ValueError("load_conditions.seismic.rt must be positive")
    return c0 * z * rt


@dataclass(frozen=True)
class DiaphragmAssignment:
    diaphragm_id: int
    story: str


@dataclass(frozen=True)
class FloorLoadSettings:
    diaphragm_id: int
    load_case: int
    role: str
    pressure_kN_m2: float
    story: str = ""
    name: str = ""


@dataclass(frozen=True)
class SeismicMassEntry:
    name: str
    mass_role: str
    story: Optional[str] = None
    weight: Optional[float] = None
    include_in_total_seismic_weight: bool = True
    include_in_alpha_denominator: bool = True
    generate_diaphragm_load: bool = False
    application_level: Optional[str] = None
    application_diaphragm: Optional[int] = None


@dataclass(frozen=True)
class RoughnessParams:
    category: str
    zb: float
    zg: float
    alpha: float


@dataclass(frozen=True)
class WindLoadCaseSettings:
    case_id: int
    name: str
    direction: str
    v0: float
    roughness_category: str
    load_case: int
    building_height_H: Optional[float] = None
    gf: Optional[float] = None
    cf_default: float = 1.0
    use_kz: bool = False
    pressure_mode: str = DEFAULT_WIND_PRESSURE_MODE
    diaphragm_input_mode: str = DEFAULT_WIND_DIAPHRAGM_INPUT_MODE


@dataclass(frozen=True)
class WindSurfaceSettings:
    surface_id: int
    name: str
    wind_case_id: int
    face_direction: str
    z_bottom: float
    z_top: float
    width: float
    cf: Optional[float] = None
    surface_role: str = DEFAULT_WIND_SURFACE_ROLE
    force_eccentricity_m: Optional[float] = None


@dataclass(frozen=True)
class WindMemberLoadPlaceholder:
    load_case: int
    member_id: int
    direction: str
    pressure: float = 0.0
    tributary_width: float = 0.0
    line_load: float = 0.0
    note: str = ""


@dataclass(frozen=True)
class WindLoadSettings:
    cases: Tuple[WindLoadCaseSettings, ...] = ()
    surfaces: Tuple[WindSurfaceSettings, ...] = ()
    member_loads: Tuple[WindMemberLoadPlaceholder, ...] = ()


@dataclass(frozen=True)
class LoadCombinationSettings:
    load_case: int
    name: str
    duration: str
    factors: Tuple[float, ...]
    load_cases: Tuple[int, ...]


def normalize_roughness_category(value: str) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "1": "I", "2": "II", "3": "III", "4": "IV",
        "Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV",
    }
    text = aliases.get(text, text)
    if text not in ALLOWED_ROUGHNESS_CATEGORIES:
        raise ValueError("roughness_category must be I, II, III, or IV")
    return text


def roughness_params(category: str) -> RoughnessParams:
    cat = normalize_roughness_category(category)
    return RoughnessParams(
        category=cat,
        zb=ROUGHNESS_ZB[cat],
        zg=ROUGHNESS_ZG[cat],
        alpha=ROUGHNESS_ALPHA[cat],
    )


def compute_gust_factor_auto(building_height_m: float, roughness_category: str) -> float:
    cat = normalize_roughness_category(roughness_category)
    h = max(0.0, float(building_height_m))
    g10 = GUST_GF_AT_10M[cat]
    g40 = GUST_GF_AT_40M[cat]
    if h <= 10.0:
        return g10
    if h >= 40.0:
        return g40
    t = (h - 10.0) / 30.0
    return g10 + t * (g40 - g10)


def resolve_wind_gf(case: WindLoadCaseSettings, building_height_m: float) -> Tuple[float, bool]:
    if case.gf is not None:
        if case.gf <= 0.0:
            raise ValueError("Wind Gf must be positive")
        return float(case.gf), False
    return compute_gust_factor_auto(building_height_m, case.roughness_category), True


def resolve_building_height_m(case: WindLoadCaseSettings, stories) -> float:
    if case.building_height_H is not None:
        return max(0.0, float(case.building_height_H))
    if not stories:
        return 0.0
    z_min = min(s.elevation for s in stories)
    z_top = max(s.elevation + s.height for s in stories)
    return max(0.0, z_top - z_min)


def normalize_wind_surface_role(value: str) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "WINDWARD": "WINDWARD",
        "WIND": "WINDWARD",
        "LEEWARD": "LEEWARD",
        "LEWARD": "LEEWARD",
        "LEESIDE": "LEEWARD",
        "SIDE": "SIDE",
        "ROOF": "ROOF",
        "PARAPET": "PARAPET",
    }
    if text not in aliases:
        raise ValueError("surface_role must be WINDWARD, LEEWARD, SIDE, ROOF, or PARAPET")
    return aliases[text]


def normalize_diaphragm_input_mode(value: str) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "DIAPHRAGM_DIRECT": "DIAPHRAGM_DIRECT",
        "DIAPHRAGM_UNIFORM": "DIAPHRAGM_UNIFORM",
        "DIAPHRAGM_DLOD": "DIAPHRAGM_UNIFORM",
        "DIAPHRAGM_FORCE_WITH_TORSION": "DIAPHRAGM_FORCE_WITH_TORSION",
        "EDGE_OR_MEMBER_LOAD": "EDGE_OR_MEMBER_LOAD",
        "MEMBER_LOAD": "EDGE_OR_MEMBER_LOAD",
        "MEMBER_TRANSFER": "EDGE_OR_MEMBER_LOAD",
        "BOTH_WITH_CHECK": "DIAPHRAGM_DIRECT",
    }
    if text not in aliases:
        raise ValueError(
            "diaphragm_input_mode must be DIAPHRAGM_DIRECT, DIAPHRAGM_UNIFORM, "
            "DIAPHRAGM_FORCE_WITH_TORSION, or EDGE_OR_MEMBER_LOAD"
        )
    return aliases[text]


def normalize_wind_direction(value: str) -> str:
    """Normalize applied horizontal load direction (building resultant sign)."""
    text = str(value or "").strip().upper().replace(" ", "")
    aliases = {
        "X+": "X_PLUS", "X_PLUS": "X_PLUS", "XPLUS": "X_PLUS",
        "WX+": "X_PLUS", "WX_PLUS": "X_PLUS", "WXPLUS": "X_PLUS",
        "X-": "X_MINUS", "X_MINUS": "X_MINUS", "XMINUS": "X_MINUS",
        "WX-": "X_MINUS", "WX_MINUS": "X_MINUS", "WXMINUS": "X_MINUS",
        "Y+": "Y_PLUS", "Y_PLUS": "Y_PLUS", "YPLUS": "Y_PLUS",
        "WY+": "Y_PLUS", "WY_PLUS": "Y_PLUS", "WYPLUS": "Y_PLUS",
        "Y-": "Y_MINUS", "Y_MINUS": "Y_MINUS", "YMINUS": "Y_MINUS",
        "WY-": "Y_MINUS", "WY_MINUS": "Y_MINUS", "WYMINUS": "Y_MINUS",
    }
    if text not in aliases:
        raise ValueError("wind direction must be X_PLUS, X_MINUS, Y_PLUS, or Y_MINUS")
    return aliases[text]


def normalize_wind_face(value: str) -> str:
    """Normalize building face location (X_MIN/X_MAX/Y_MIN/Y_MAX)."""
    text = str(value or "").strip().upper().replace(" ", "")
    aliases = {
        "XMIN": "X_MIN", "X_MIN": "X_MIN", "X-MIN": "X_MIN",
        "XMAX": "X_MAX", "X_MAX": "X_MAX", "X-MAX": "X_MAX",
        "YMIN": "Y_MIN", "Y_MIN": "Y_MIN", "Y-MIN": "Y_MIN",
        "YMAX": "Y_MAX", "Y_MAX": "Y_MAX", "Y-MAX": "Y_MAX",
        # Legacy: +/- side of building (not applied load direction).
        "X+": "X_MAX", "X_PLUS": "X_MAX", "XPLUS": "X_MAX",
        "X-": "X_MIN", "X_MINUS": "X_MIN", "XMINUS": "X_MIN",
        "Y+": "Y_MAX", "Y_PLUS": "Y_MAX", "YPLUS": "Y_MAX",
        "Y-": "Y_MIN", "Y_MINUS": "Y_MIN", "YMINUS": "Y_MIN",
    }
    if text not in aliases:
        raise ValueError("wind face must be X_MIN, X_MAX, Y_MIN, or Y_MAX")
    return aliases[text]


@dataclass(frozen=True)
class WindDirectionConvention:
    """Sign convention for a wind load case (applied load direction, not wind origin)."""
    applied_load_direction: str
    axis: str
    sign: int
    wind_flow_from: str
    wind_flow_to: str
    windward_face: str
    leeward_face: str


_WIND_DIRECTION_CONVENTIONS = {
    "X_PLUS": WindDirectionConvention(
        applied_load_direction="X_PLUS",
        axis="x",
        sign=1,
        wind_flow_from="X_MINUS",
        wind_flow_to="X_PLUS",
        windward_face="X_MIN",
        leeward_face="X_MAX",
    ),
    "X_MINUS": WindDirectionConvention(
        applied_load_direction="X_MINUS",
        axis="x",
        sign=-1,
        wind_flow_from="X_PLUS",
        wind_flow_to="X_MINUS",
        windward_face="X_MAX",
        leeward_face="X_MIN",
    ),
    "Y_PLUS": WindDirectionConvention(
        applied_load_direction="Y_PLUS",
        axis="y",
        sign=1,
        wind_flow_from="Y_MINUS",
        wind_flow_to="Y_PLUS",
        windward_face="Y_MIN",
        leeward_face="Y_MAX",
    ),
    "Y_MINUS": WindDirectionConvention(
        applied_load_direction="Y_MINUS",
        axis="y",
        sign=-1,
        wind_flow_from="Y_PLUS",
        wind_flow_to="Y_MINUS",
        windward_face="Y_MAX",
        leeward_face="Y_MIN",
    ),
}


def resolve_wind_direction_convention(direction: str) -> WindDirectionConvention:
    key = normalize_wind_direction(direction)
    return _WIND_DIRECTION_CONVENTIONS[key]


def wind_face_to_wall_side(face: str) -> str:
    mapping = {
        "X_MIN": "x_min",
        "X_MAX": "x_max",
        "Y_MIN": "y_min",
        "Y_MAX": "y_max",
    }
    return mapping[normalize_wind_face(face)]


def format_applied_load_direction_label(direction: str) -> str:
    conv = resolve_wind_direction_convention(direction)
    if conv.axis == "x":
        return "+X" if conv.sign > 0 else "-X"
    return "+Y" if conv.sign > 0 else "-Y"


def format_wind_flow_endpoint_label(endpoint: str) -> str:
    labels = {
        "X_PLUS": "+X側",
        "X_MINUS": "-X側",
        "Y_PLUS": "+Y側",
        "Y_MINUS": "-Y側",
    }
    return labels[normalize_wind_direction(endpoint)]


def format_wind_flow_label(direction: str) -> str:
    conv = resolve_wind_direction_convention(direction)
    return (
        format_wind_flow_endpoint_label(conv.wind_flow_from)
        + " → "
        + format_wind_flow_endpoint_label(conv.wind_flow_to)
    )


def format_wind_face_label_jp(face: str) -> str:
    labels = {
        "X_MIN": "X最小側",
        "X_MAX": "X最大側",
        "Y_MIN": "Y最小側",
        "Y_MAX": "Y最大側",
    }
    return labels[normalize_wind_face(face)]


def format_wind_case_short_name(direction: str) -> str:
    labels = {
        "X_PLUS": "WX+",
        "X_MINUS": "WX-",
        "Y_PLUS": "WY+",
        "Y_MINUS": "WY-",
    }
    return labels[normalize_wind_direction(direction)]


def direction_to_axis_sign(direction: str) -> Tuple[str, int]:
    conv = resolve_wind_direction_convention(direction)
    return conv.axis, conv.sign


@dataclass(frozen=True)
class LoadConditionSettings:
    seismic: SeismicLoadSettings = field(default_factory=SeismicLoadSettings)
    diaphragms: Tuple[DiaphragmAssignment, ...] = ()
    floor_loads: Tuple[FloorLoadSettings, ...] = ()
    seismic_masses: Tuple[SeismicMassEntry, ...] = ()
    wind: WindLoadSettings = field(default_factory=WindLoadSettings)
    load_combinations: Tuple[LoadCombinationSettings, ...] = ()


@dataclass(frozen=True)
class ProjectDefinition:
    schema: int
    dat_path: str
    building: BuildingInfo
    grids: Tuple[GridLine, ...]
    stories: Tuple[Story, ...]
    member_classes: Tuple[MemberClass, ...]
    design_checks: DesignCheckSettings
    load_conditions: LoadConditionSettings
    report: ReportSettings
    source_path: Optional[str] = None
    wall_quantity: "WallQuantitySettings" = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.wall_quantity is None:
            from stb_project.wall_quantity_settings import WallQuantitySettings
            object.__setattr__(self, "wall_quantity", WallQuantitySettings())

    def to_dict(self):
        out = {
            "schema": self.schema,
            "model": {"dat": self.dat_path},
            "building": {
                "name": self.building.name,
                "location": self.building.location,
                "use": self.building.use,
                "structure": self.building.structure,
                "calculation_route": self.building.calculation_route,
                "designer": {
                    "name": self.building.designer.name,
                    "qualification": self.building.designer.qualification,
                    "license_number": self.building.designer.license_number,
                    "contact": self.building.designer.contact,
                },
            },
            "grids": [
                {"name": g.name, "direction": g.direction, "coordinate": g.coordinate}
                for g in self.grids
            ],
            "stories": [
                {"name": s.name, "elevation": s.elevation, "height": s.height}
                for s in self.stories
            ],
            "member_classes": [
                {
                    "name": c.name,
                    "kind": c.kind,
                    "element_ids": list(c.element_ids),
                    "story": c.story,
                    "use": c.use,
                    "notes": c.notes,
                }
                for c in self.member_classes
            ],
            "design_checks": {
                "wood": _wood_settings_to_dict(self.design_checks.wood),
            },
            "load_conditions": {
                "seismic": _seismic_settings_to_dict(self.load_conditions.seismic),
                "diaphragms": [
                    {"id": d.diaphragm_id, "story": d.story}
                    for d in self.load_conditions.diaphragms
                ],
                "floor_loads": [
                    _floor_load_settings_to_dict(entry)
                    for entry in self.load_conditions.floor_loads
                ] if self.load_conditions.floor_loads else [],
                "seismic_masses": [
                    _seismic_mass_entry_to_dict(entry)
                    for entry in self.load_conditions.seismic_masses
                ] if self.load_conditions.seismic_masses else [],
                "wind": _wind_settings_to_dict(self.load_conditions.wind),
                "load_combinations": [
                    {
                        "load_case": c.load_case,
                        "name": c.name,
                        "duration": c.duration,
                        "factors": list(c.factors),
                        "load_cases": list(c.load_cases),
                    }
                    for c in self.load_conditions.load_combinations
                ],
            },
            "report": {
                "title": self.report.title,
                "mode": self.report.mode,
                "language": self.report.language,
                "format": self.report.format,
                "include_manual_items": self.report.include_manual_items,
                "include_warnings": self.report.include_warnings,
            },
        }
        if not self.wall_quantity.is_default:
            from stb_project.wall_quantity_settings import wall_quantity_settings_to_dict
            out["wall_quantity"] = wall_quantity_settings_to_dict(self.wall_quantity)
        return out


def _seismic_settings_to_dict(seismic: SeismicLoadSettings):
    if (
        seismic.ci == 0.0
        and seismic.c0 is None
        and seismic.z is None
        and seismic.rt is None
        and seismic.design_period_s is None
        and seismic.height_m is None
        and abs(seismic.steel_ratio_alpha - DEFAULT_SEISMIC_STEEL_RATIO_ALPHA) <= 1.0e-12
        and abs(seismic.tc - DEFAULT_SEISMIC_TC) <= 1.0e-12
        and seismic.base_level is None
        and seismic.base_elevation is None
        and seismic.base_mass_policy == DEFAULT_BASE_MASS_POLICY
        and seismic.dead_load_lc is None
        and seismic.live_load_lc is None
        and seismic.live_load_factor == 0.0
        and not seismic.weight_load_cases
        and not seismic.directions
    ):
        return {}

    out = {
        "ci": seismic.ci,
        "dead_load_lc": seismic.dead_load_lc,
        "live_load_lc": seismic.live_load_lc,
        "live_load_factor": seismic.live_load_factor,
        "weight_load_cases": [
            {
                "name": c.name,
                "load_case": c.load_case,
                "factor": c.factor,
                "role": c.role,
            }
            for c in seismic.weight_load_cases
        ],
        "directions": [
            {
                "name": d.name,
                "axis": d.axis,
                "load_case": d.load_case,
                "sign": d.sign,
            }
            for d in seismic.directions
        ],
    }
    if seismic.c0 is not None:
        out["c0"] = seismic.c0
    if seismic.z is not None:
        out["z"] = seismic.z
    if seismic.rt is not None:
        out["rt"] = seismic.rt
    if seismic.design_period_s is not None:
        out["design_period_s"] = seismic.design_period_s
    if seismic.height_m is not None:
        out["height_m"] = seismic.height_m
    if abs(seismic.steel_ratio_alpha - DEFAULT_SEISMIC_STEEL_RATIO_ALPHA) > 1.0e-12:
        out["steel_ratio_alpha"] = seismic.steel_ratio_alpha
    if abs(seismic.tc - DEFAULT_SEISMIC_TC) > 1.0e-12:
        out["tc"] = seismic.tc
    if seismic.base_level:
        out["base_level"] = seismic.base_level
    if seismic.base_elevation is not None:
        out["base_elevation"] = seismic.base_elevation
    if seismic.base_mass_policy != DEFAULT_BASE_MASS_POLICY:
        out["base_mass_policy"] = seismic.base_mass_policy
    return out


def project_path_for_dat(dat_path):
    """Return the default sidecar path for an existing analysis file."""

    base, _ext = os.path.splitext(dat_path)
    return base + DEFAULT_PROJECT_SUFFIX


def load_project_for_dat(dat_path, required=False):
    """Load the sidecar project JSON next to a .dat file.

    This deliberately does not read or parse the .dat file; the sidecar is an
    optional layer above the existing analysis format.
    """

    project_path = project_path_for_dat(dat_path)
    if not os.path.isfile(project_path):
        if required:
            raise IOError("Project file not found: " + project_path)
        return None
    return load_project_file(project_path)


def load_project_file(path):
    f = open(path, "r", encoding="utf-8")
    try:
        raw = json.load(f)
    finally:
        f.close()
    return validate_project_dict(raw, source_path=path)


def validate_project_dict(raw, source_path=None):
    _require_type(raw, dict, "project")
    _reject_unknown(
        raw,
        [
            "schema", "model", "building", "grids", "stories", "member_classes",
            "design_checks", "load_conditions", "report", "wall_quantity",
        ],
        "project",
    )

    schema = _required(raw, "schema", "project")
    if schema != SCHEMA_VERSION:
        raise ProjectSchemaError("project.schema must be " + str(SCHEMA_VERSION))

    model = _required(raw, "model", "project")
    _require_type(model, dict, "project.model")
    _reject_unknown(model, ["dat"], "project.model")
    dat_path = _required_string(model, "dat", "project.model")

    building = _parse_building(_required(raw, "building", "project"))
    grids = tuple(_parse_grid_lines(_required(raw, "grids", "project")))
    stories = tuple(_parse_stories(_required(raw, "stories", "project")))
    member_classes = tuple(_parse_member_classes(_required(raw, "member_classes", "project")))
    design_checks = _parse_design_checks(raw.get("design_checks", {}))
    load_conditions = _parse_load_conditions(raw.get("load_conditions", {}))
    report = _parse_report(_required(raw, "report", "project"))
    from stb_project.wall_quantity_settings import parse_wall_quantity_settings
    wall_quantity = parse_wall_quantity_settings(raw.get("wall_quantity"))

    return ProjectDefinition(
        schema=schema,
        dat_path=dat_path,
        building=building,
        grids=grids,
        stories=stories,
        member_classes=member_classes,
        design_checks=design_checks,
        load_conditions=load_conditions,
        report=report,
        source_path=source_path,
        wall_quantity=wall_quantity,
    )


def _parse_building(raw):
    _require_type(raw, dict, "project.building")
    _reject_unknown(
        raw,
        ["name", "location", "use", "structure", "calculation_route", "designer"],
        "project.building",
    )
    designer_raw = raw.get("designer", {})
    _require_type(designer_raw, dict, "project.building.designer")
    _reject_unknown(
        designer_raw,
        ["name", "qualification", "license_number", "contact"],
        "project.building.designer",
    )

    designer = DesignerInfo(
        name=_optional_string(designer_raw, "name", "project.building.designer"),
        qualification=_optional_string(designer_raw, "qualification", "project.building.designer"),
        license_number=_optional_string(designer_raw, "license_number", "project.building.designer"),
        contact=_optional_string(designer_raw, "contact", "project.building.designer"),
    )
    return BuildingInfo(
        name=_optional_string(raw, "name", "project.building"),
        location=_optional_string(raw, "location", "project.building"),
        use=_optional_string(raw, "use", "project.building"),
        structure=_optional_string(raw, "structure", "project.building"),
        calculation_route=_optional_string(raw, "calculation_route", "project.building"),
        designer=designer,
    )


def _parse_grid_lines(raw):
    _require_type(raw, list, "project.grids")
    seen = set()
    grids = []
    for idx, item in enumerate(raw):
        path = "project.grids[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "direction", "coordinate"], path)
        name = _required_string(item, "name", path)
        direction = _required_string(item, "direction", path).lower()
        if direction not in ALLOWED_GRID_DIRECTIONS:
            raise ProjectSchemaError(path + ".direction must be x or y")
        coordinate = _required_number(item, "coordinate", path)
        key = (direction, name)
        if key in seen:
            raise ProjectSchemaError(path + " duplicates grid " + direction + ":" + name)
        seen.add(key)
        grids.append(GridLine(name=name, direction=direction, coordinate=coordinate))
    return grids


def _parse_stories(raw):
    _require_type(raw, list, "project.stories")
    seen = set()
    stories = []
    for idx, item in enumerate(raw):
        path = "project.stories[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "elevation", "height"], path)
        name = _required_string(item, "name", path)
        if name in seen:
            raise ProjectSchemaError(path + " duplicates story " + name)
        seen.add(name)
        stories.append(Story(
            name=name,
            elevation=_required_number(item, "elevation", path),
            height=_required_number(item, "height", path),
        ))
    return stories


def _parse_member_classes(raw):
    _require_type(raw, list, "project.member_classes")
    seen = set()
    classes = []
    for idx, item in enumerate(raw):
        path = "project.member_classes[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "kind", "element_ids", "story", "use", "notes"], path)
        name = _required_string(item, "name", path)
        if name in seen:
            raise ProjectSchemaError(path + " duplicates member class " + name)
        seen.add(name)
        kind = _required_string(item, "kind", path)
        if kind not in ALLOWED_MEMBER_KINDS:
            raise ProjectSchemaError(path + ".kind is not supported: " + kind)
        classes.append(MemberClass(
            name=name,
            kind=kind,
            element_ids=tuple(_parse_int_list(_required(item, "element_ids", path), path + ".element_ids")),
            story=_optional_string(item, "story", path),
            use=_optional_string(item, "use", path),
            notes=_optional_string(item, "notes", path),
        ))
    return classes


def _parse_report(raw):
    _require_type(raw, dict, "project.report")
    _reject_unknown(
        raw,
        ["title", "mode", "language", "format", "include_manual_items", "include_warnings"],
        "project.report",
    )
    mode = _optional_string(raw, "mode", "project.report", default="practice")
    if mode not in ALLOWED_REPORT_MODES:
        raise ProjectSchemaError("project.report.mode is not supported: " + mode)
    output_format = _optional_string(raw, "format", "project.report", default="markdown")
    if output_format not in ALLOWED_REPORT_FORMATS:
        raise ProjectSchemaError("project.report.format is not supported: " + output_format)
    return ReportSettings(
        title=_optional_string(raw, "title", "project.report"),
        mode=mode,
        language=_optional_string(raw, "language", "project.report", default="ja"),
        format=output_format,
        include_manual_items=_optional_bool(raw, "include_manual_items", "project.report", default=True),
        include_warnings=_optional_bool(raw, "include_warnings", "project.report", default=True),
    )


def _parse_design_checks(raw):
    _require_type(raw, dict, "project.design_checks")
    _reject_unknown(raw, ["wood"], "project.design_checks")
    return DesignCheckSettings(wood=_parse_wood_check_settings(raw.get("wood", {})))


def _seismic_mass_entry_to_dict(entry: SeismicMassEntry):
    out = {
        "name": entry.name,
        "mass_role": entry.mass_role,
        "include_in_total_seismic_weight": entry.include_in_total_seismic_weight,
        "include_in_alpha_denominator": entry.include_in_alpha_denominator,
        "generate_diaphragm_load": entry.generate_diaphragm_load,
    }
    if entry.story:
        out["story"] = entry.story
    if entry.weight is not None:
        out["weight"] = entry.weight
    if entry.application_level:
        out["application_level"] = entry.application_level
    if entry.application_diaphragm is not None:
        out["application_diaphragm"] = entry.application_diaphragm
    return out


def _parse_seismic_mass_entries(raw):
    _require_type(raw, list, "project.load_conditions.seismic_masses")
    entries = []
    for idx, item in enumerate(raw):
        path = "project.load_conditions.seismic_masses[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(
            item,
            [
                "name",
                "story",
                "weight",
                "mass_role",
                "include_in_total_seismic_weight",
                "include_in_alpha_denominator",
                "generate_diaphragm_load",
                "application_level",
                "application_diaphragm",
            ],
            path,
        )
        name = _required_string(item, "name", path)
        mass_role = _required_string(item, "mass_role", path)
        if mass_role not in ALLOWED_MASS_ROLES:
            raise ProjectSchemaError(path + ".mass_role is not supported: " + str(mass_role))

        story = _optional_string(item, "story", path)
        weight_raw = item.get("weight")
        weight = None
        if weight_raw is not None:
            weight = _optional_number(item, "weight", path, default=0.0)
            if weight < 0.0:
                raise ProjectSchemaError(path + ".weight must be non-negative")

        if mass_role == "BASE_MASS":
            include_total = _optional_bool(
                item, "include_in_total_seismic_weight", path, default=True
            )
            include_alpha = _optional_bool(
                item, "include_in_alpha_denominator", path, default=True
            )
            generate_dlod = _optional_bool(item, "generate_diaphragm_load", path, default=False)
            application_level = _optional_string(item, "application_level", path) or "base"
            application_diaphragm = item.get("application_diaphragm")
            if application_diaphragm is not None:
                raise ProjectSchemaError(
                    path + ": BASE_MASS must not specify application_diaphragm"
                )
        else:
            include_total = _optional_bool(
                item, "include_in_total_seismic_weight", path, default=True
            )
            include_alpha = _optional_bool(
                item, "include_in_alpha_denominator", path, default=True
            )
            generate_dlod = _optional_bool(item, "generate_diaphragm_load", path, default=True)
            application_level = _optional_string(item, "application_level", path)
            application_diaphragm_raw = item.get("application_diaphragm")
            if application_diaphragm_raw is None:
                raise ProjectSchemaError("DIAPHRAGM_MASS には application_diaphragm が必要です。")
            if type(application_diaphragm_raw) is not int:
                raise ProjectSchemaError(path + ".application_diaphragm must be an integer")
            application_diaphragm = application_diaphragm_raw

        if story is None and weight is None:
            raise ProjectSchemaError(path + ": story or weight is required")

        entries.append(SeismicMassEntry(
            name=name,
            mass_role=mass_role,
            story=story,
            weight=weight,
            include_in_total_seismic_weight=include_total,
            include_in_alpha_denominator=include_alpha,
            generate_diaphragm_load=generate_dlod,
            application_level=application_level,
            application_diaphragm=application_diaphragm,
        ))
    return entries


def _parse_wind_load_settings(raw):
    if not raw:
        return WindLoadSettings()
    _require_type(raw, dict, "project.load_conditions.wind")
    _reject_unknown(raw, ["cases", "surfaces", "member_loads"], "project.load_conditions.wind")

    cases_raw = raw.get("cases", [])
    _require_type(cases_raw, list, "project.load_conditions.wind.cases")
    cases = []
    for idx, item in enumerate(cases_raw):
        path = "project.load_conditions.wind.cases[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(
            item,
            [
                "id", "name", "direction", "V0", "v0", "roughness_category",
                "building_height_H", "Gf", "gf", "Cf_default", "cf_default",
                "use_Kz", "use_kz", "pressure_mode",
                "diaphragm_input_mode", "target_mode", "load_case",
            ],
            path,
        )
        v0 = item.get("V0", item.get("v0"))
        if v0 is None:
            raise ProjectSchemaError(path + ": V0 is required")
        gf_raw = item.get("Gf", item.get("gf"))
        gf = None if gf_raw is None else float(gf_raw)
        cf_raw = item.get("Cf_default", item.get("cf_default", 1.0))
        use_kz = bool(item.get("use_Kz", item.get("use_kz", False)))
        pressure_mode = str(item.get("pressure_mode", DEFAULT_WIND_PRESSURE_MODE)).upper()
        if pressure_mode not in ALLOWED_WIND_PRESSURE_MODES:
            raise ProjectSchemaError(path + ".pressure_mode is invalid")
        mode_raw = item.get("diaphragm_input_mode", item.get("target_mode", DEFAULT_WIND_DIAPHRAGM_INPUT_MODE))
        try:
            diaphragm_input_mode = normalize_diaphragm_input_mode(str(mode_raw).upper())
        except ValueError as ex:
            raise ProjectSchemaError(path + ".diaphragm_input_mode is invalid: " + str(ex)) from ex
        load_case = item.get("load_case")
        if load_case is None:
            raise ProjectSchemaError(path + ": load_case is required")
        bh_raw = item.get("building_height_H")
        building_height_H = None if bh_raw is None else float(bh_raw)
        cases.append(WindLoadCaseSettings(
            case_id=int(_required_number(item, "id", path)),
            name=_required_string(item, "name", path),
            direction=normalize_wind_direction(_required_string(item, "direction", path)),
            v0=float(v0),
            roughness_category=normalize_roughness_category(
                _required_string(item, "roughness_category", path)
            ),
            load_case=int(load_case),
            building_height_H=building_height_H,
            gf=gf,
            cf_default=float(cf_raw),
            use_kz=use_kz,
            pressure_mode=pressure_mode,
            diaphragm_input_mode=diaphragm_input_mode,
        ))

    surfaces_raw = raw.get("surfaces", [])
    _require_type(surfaces_raw, list, "project.load_conditions.wind.surfaces")
    surfaces = []
    for idx, item in enumerate(surfaces_raw):
        path = "project.load_conditions.wind.surfaces[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(
            item,
            [
                "id", "name", "wind_case_id", "face_direction",
                "z_bottom", "z_top", "width", "Cf", "cf",
                "surface_role", "force_eccentricity_m",
                "load_transfer_mode", "target_diaphragms", "target_members",
            ],
            path,
        )
        cf_raw = item.get("Cf", item.get("cf"))
        role_raw = item.get("surface_role")
        if role_raw is None and item.get("load_transfer_mode") == "MEMBER_TRANSFER":
            role_raw = "SIDE"
        try:
            surface_role = normalize_wind_surface_role(
                str(role_raw or DEFAULT_WIND_SURFACE_ROLE).upper()
            )
        except ValueError as ex:
            raise ProjectSchemaError(path + ".surface_role is invalid: " + str(ex)) from ex
        ecc_raw = item.get("force_eccentricity_m")
        force_eccentricity_m = None if ecc_raw is None else float(ecc_raw)
        surfaces.append(WindSurfaceSettings(
            surface_id=int(_required_number(item, "id", path)),
            name=_required_string(item, "name", path),
            wind_case_id=int(_required_number(item, "wind_case_id", path)),
            face_direction=normalize_wind_face(_required_string(item, "face_direction", path)),
            z_bottom=float(_required_number(item, "z_bottom", path)),
            z_top=float(_required_number(item, "z_top", path)),
            width=float(_required_number(item, "width", path)),
            cf=None if cf_raw is None else float(cf_raw),
            surface_role=surface_role,
            force_eccentricity_m=force_eccentricity_m,
        ))

    member_raw = raw.get("member_loads", [])
    _require_type(member_raw, list, "project.load_conditions.wind.member_loads")
    member_loads = []
    for idx, item in enumerate(member_raw):
        path = "project.load_conditions.wind.member_loads[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(
            item,
            ["load_case", "member_id", "direction", "pressure", "tributary_width", "line_load", "note"],
            path,
        )
        member_loads.append(WindMemberLoadPlaceholder(
            load_case=int(_required_number(item, "load_case", path)),
            member_id=int(_required_number(item, "member_id", path)),
            direction=normalize_wind_direction(_required_string(item, "direction", path)),
            pressure=float(_optional_number(item, "pressure", path, default=0.0)),
            tributary_width=float(_optional_number(item, "tributary_width", path, default=0.0)),
            line_load=float(_optional_number(item, "line_load", path, default=0.0)),
            note=_optional_string(item, "note", path) or "",
        ))

    return WindLoadSettings(
        cases=tuple(cases),
        surfaces=tuple(surfaces),
        member_loads=tuple(member_loads),
    )


def _wind_settings_to_dict(wind: WindLoadSettings):
    if not wind.cases and not wind.surfaces and not wind.member_loads:
        return {"cases": [], "surfaces": [], "member_loads": []}
    return {
        "cases": [
            {
                "id": c.case_id,
                "name": c.name,
                "direction": c.direction,
                "V0": c.v0,
                "roughness_category": c.roughness_category,
                "load_case": c.load_case,
                **({"building_height_H": c.building_height_H} if c.building_height_H is not None else {}),
                **({"Gf": c.gf} if c.gf is not None else {}),
                "Cf_default": c.cf_default,
                **({"use_Kz": c.use_kz} if c.use_kz else {}),
                "pressure_mode": c.pressure_mode,
                "diaphragm_input_mode": c.diaphragm_input_mode,
            }
            for c in wind.cases
        ],
        "surfaces": [
            {
                "id": s.surface_id,
                "name": s.name,
                "wind_case_id": s.wind_case_id,
                "face_direction": s.face_direction,
                "z_bottom": s.z_bottom,
                "z_top": s.z_top,
                "width": s.width,
                **({"Cf": s.cf} if s.cf is not None else {}),
                **({"surface_role": s.surface_role}
                   if s.surface_role != DEFAULT_WIND_SURFACE_ROLE else {}),
                **({"force_eccentricity_m": s.force_eccentricity_m}
                   if s.force_eccentricity_m is not None else {}),
            }
            for s in wind.surfaces
        ],
        "member_loads": [
            {
                "load_case": m.load_case,
                "member_id": m.member_id,
                "direction": m.direction,
                "pressure": m.pressure,
                "tributary_width": m.tributary_width,
                "line_load": m.line_load,
                "note": m.note,
            }
            for m in wind.member_loads
        ],
    }


def _parse_load_conditions(raw):
    _require_type(raw, dict, "project.load_conditions")
    _reject_unknown(
        raw,
        ["seismic", "diaphragms", "floor_loads", "seismic_masses", "wind", "load_combinations"],
        "project.load_conditions",
    )
    seismic_raw = raw.get("seismic")
    floor_loads = tuple(_parse_floor_load_settings(raw.get("floor_loads", [])))
    seismic = _parse_seismic_load_settings(seismic_raw) if seismic_raw else SeismicLoadSettings()
    seismic = _with_floor_load_weight_cases(seismic, floor_loads)
    return LoadConditionSettings(
        seismic=seismic,
        diaphragms=tuple(_parse_diaphragm_assignments(raw.get("diaphragms", []))),
        floor_loads=floor_loads,
        seismic_masses=tuple(_parse_seismic_mass_entries(raw.get("seismic_masses", []))),
        wind=_parse_wind_load_settings(raw.get("wind", {})),
        load_combinations=tuple(_parse_load_combinations(raw.get("load_combinations", []))),
    )


def _parse_load_combinations(raw):
    _require_type(raw, list, "project.load_conditions.load_combinations")
    seen = set()
    out = []
    for idx, item in enumerate(raw):
        path = "project.load_conditions.load_combinations[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["load_case", "name", "duration", "factors", "load_cases"], path)
        load_case = int(_required_number(item, "load_case", path))
        if load_case in seen:
            raise ProjectSchemaError(path + " duplicates load_case " + str(load_case))
        seen.add(load_case)
        factors = tuple(
            float(v) for v in _parse_number_list(_required(item, "factors", path), path + ".factors")
        )
        load_cases = tuple(
            _parse_int_list(_required(item, "load_cases", path), path + ".load_cases")
        )
        if len(factors) == 0:
            raise ProjectSchemaError(path + ".factors must not be empty")
        if len(factors) != len(load_cases):
            raise ProjectSchemaError(path + ".factors and .load_cases must have the same length")
        duration = _required_string(item, "duration", path).strip().upper()
        if duration not in ALLOWED_LOAD_COMBINATION_DURATIONS:
            raise ProjectSchemaError(path + ".duration is not supported: " + duration)
        out.append(LoadCombinationSettings(
            load_case=load_case,
            name=_required_string(item, "name", path),
            duration=duration,
            factors=factors,
            load_cases=load_cases,
        ))
    return out


def _parse_seismic_load_settings(raw):
    _require_type(raw, dict, "project.load_conditions.seismic")
    _reject_unknown(
        raw,
        [
            "ci",
            "c0",
            "z",
            "rt",
            "design_period_s",
            "height_m",
            "steel_ratio_alpha",
            "tc",
            "base_level",
            "base_elevation",
            "base_mass_policy",
            "dead_load_lc",
            "live_load_lc",
            "live_load_factor",
            "weight_load_cases",
            "directions",
        ],
        "project.load_conditions.seismic",
    )
    weight_cases_raw = raw.get("weight_load_cases", [])
    _require_type(weight_cases_raw, list, "project.load_conditions.seismic.weight_load_cases")
    weight_cases = []
    seen_weight_lcs = set()
    for idx, item in enumerate(weight_cases_raw):
        path = "project.load_conditions.seismic.weight_load_cases[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "load_case", "factor", "role"], path)
        load_case = int(_required_number(item, "load_case", path))
        if load_case in seen_weight_lcs:
            raise ProjectSchemaError(path + " duplicates load_case " + str(load_case))
        seen_weight_lcs.add(load_case)
        factor = _optional_number(item, "factor", path, default=1.0)
        role = (_optional_string(item, "role", path, default="OTHER") or "OTHER").upper()
        if role not in ALLOWED_SEISMIC_WEIGHT_ROLES:
            raise ProjectSchemaError(path + ".role is not supported: " + role)
        weight_cases.append(SeismicWeightLoadCaseSettings(
            name=_optional_string(item, "name", path, default=""),
            load_case=load_case,
            factor=factor,
            role=role,
        ))

    directions_raw = raw.get("directions", [])
    _require_type(directions_raw, list, "project.load_conditions.seismic.directions")
    directions = []
    for idx, item in enumerate(directions_raw):
        path = "project.load_conditions.seismic.directions[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["name", "axis", "load_case", "sign"], path)
        axis = _required_string(item, "axis", path).lower()
        if axis not in ALLOWED_SEISMIC_AXES:
            raise ProjectSchemaError(path + ".axis must be x or y")
        sign = int(_optional_number(item, "sign", path, default=1))
        if sign not in (-1, 1):
            raise ProjectSchemaError(path + ".sign must be -1 or 1")
        directions.append(SeismicDirectionSettings(
            name=_required_string(item, "name", path),
            axis=axis,
            load_case=int(_required_number(item, "load_case", path)),
            sign=sign,
        ))

    live_lc_raw = raw.get("live_load_lc")
    live_lc = None
    if live_lc_raw is not None:
        if type(live_lc_raw) is not int:
            raise ProjectSchemaError("project.load_conditions.seismic.live_load_lc must be an integer or null")
        live_lc = live_lc_raw

    dead_lc_raw = raw.get("dead_load_lc")
    dead_lc = None
    if dead_lc_raw is not None:
        if type(dead_lc_raw) is not int:
            raise ProjectSchemaError("project.load_conditions.seismic.dead_load_lc must be an integer or null")
        dead_lc = dead_lc_raw

    rt_raw = raw.get("rt")
    rt = None
    if rt_raw is not None:
        rt = _optional_number(raw, "rt", "project.load_conditions.seismic", default=DEFAULT_SEISMIC_RT)
        if rt <= 0.0:
            raise ProjectSchemaError("project.load_conditions.seismic.rt must be positive")

    design_period_raw = raw.get("design_period_s")
    design_period_s = None
    if design_period_raw is not None:
        design_period_s = _optional_number(raw, "design_period_s", "project.load_conditions.seismic", default=0.0)
        if design_period_s <= 0.0:
            raise ProjectSchemaError("project.load_conditions.seismic.design_period_s must be positive")

    height_raw = raw.get("height_m")
    height_m = None
    if height_raw is not None:
        height_m = _optional_number(raw, "height_m", "project.load_conditions.seismic", default=0.0)
        if height_m < 0.0:
            raise ProjectSchemaError("project.load_conditions.seismic.height_m must be non-negative")

    steel_ratio_alpha = _optional_number(
        raw,
        "steel_ratio_alpha",
        "project.load_conditions.seismic",
        default=DEFAULT_SEISMIC_STEEL_RATIO_ALPHA,
    )
    if steel_ratio_alpha < 0.0 or steel_ratio_alpha > 1.0:
        raise ProjectSchemaError("project.load_conditions.seismic.steel_ratio_alpha must be within [0,1]")

    tc = _optional_number(raw, "tc", "project.load_conditions.seismic", default=DEFAULT_SEISMIC_TC)
    if tc <= 0.0:
        raise ProjectSchemaError("project.load_conditions.seismic.tc must be positive")

    base_level = _optional_string(raw, "base_level", "project.load_conditions.seismic")
    base_elevation_raw = raw.get("base_elevation")
    base_elevation = None
    if base_elevation_raw is not None:
        base_elevation = _optional_number(
            raw, "base_elevation", "project.load_conditions.seismic", default=0.0
        )

    base_mass_policy = _optional_string(
        raw,
        "base_mass_policy",
        "project.load_conditions.seismic",
        default=DEFAULT_BASE_MASS_POLICY,
    )
    if base_mass_policy not in ALLOWED_BASE_MASS_POLICIES:
        raise ProjectSchemaError(
            "project.load_conditions.seismic.base_mass_policy is not supported: "
            + str(base_mass_policy)
        )

    c0_raw = raw.get("c0")
    c0 = None
    if c0_raw is not None:
        c0 = _optional_number(raw, "c0", "project.load_conditions.seismic", default=0.0)
        if c0 <= 0.0:
            raise ProjectSchemaError("project.load_conditions.seismic.c0 must be positive")

    z_raw = raw.get("z")
    z = None
    if z_raw is not None:
        z = _optional_number(raw, "z", "project.load_conditions.seismic", default=1.0)
        if z <= 0.0:
            raise ProjectSchemaError("project.load_conditions.seismic.z must be positive")

    ci = _optional_number(raw, "ci", "project.load_conditions.seismic", default=0.0)
    if c0 is None and ci <= 0.0 and directions:
        raise ProjectSchemaError("project.load_conditions.seismic.c0 or ci must be positive")

    return SeismicLoadSettings(
        ci=ci,
        c0=c0,
        z=z,
        rt=rt,
        design_period_s=design_period_s,
        height_m=height_m,
        steel_ratio_alpha=steel_ratio_alpha,
        tc=tc,
        base_level=base_level,
        base_elevation=base_elevation,
        base_mass_policy=base_mass_policy,
        dead_load_lc=dead_lc,
        live_load_lc=live_lc,
        live_load_factor=_optional_number(
            raw, "live_load_factor", "project.load_conditions.seismic", default=0.0
        ),
        weight_load_cases=tuple(weight_cases),
        directions=tuple(directions),
    )


def _parse_diaphragm_assignments(raw):
    _require_type(raw, list, "project.load_conditions.diaphragms")
    seen = set()
    out = []
    for idx, item in enumerate(raw):
        path = "project.load_conditions.diaphragms[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(item, ["id", "story"], path)
        diap_id = int(_required_number(item, "id", path))
        if diap_id in seen:
            raise ProjectSchemaError(path + " duplicates diaphragm id " + str(diap_id))
        seen.add(diap_id)
        out.append(DiaphragmAssignment(
            diaphragm_id=diap_id,
            story=_required_string(item, "story", path),
        ))
    return out


def _floor_load_settings_to_dict(entry: FloorLoadSettings):
    out = {
        "diaphragm_id": entry.diaphragm_id,
        "load_case": entry.load_case,
        "role": entry.role,
        "name": entry.name,
        "pressure_kN_m2": entry.pressure_kN_m2,
    }
    if entry.story:
        out["story"] = entry.story
    return out


def _parse_floor_load_settings(raw):
    _require_type(raw, list, "project.load_conditions.floor_loads")
    seen = {}
    out = []
    for idx, item in enumerate(raw):
        path = "project.load_conditions.floor_loads[" + str(idx) + "]"
        _require_type(item, dict, path)
        _reject_unknown(
            item,
            ["story", "diaphragm_id", "load_case", "role", "name", "pressure_kN_m2"],
            path,
        )
        role = _required_string(item, "role", path).upper()
        if role not in ALLOWED_FLOOR_LOAD_ROLES:
            raise ProjectSchemaError(path + ".role is not supported: " + role)
        pressure = _required_number(item, "pressure_kN_m2", path)
        if pressure < 0.0:
            raise ProjectSchemaError(path + ".pressure_kN_m2 must be non-negative")
        diaphragm_id = int(_required_number(item, "diaphragm_id", path))
        load_case = int(_required_number(item, "load_case", path))
        name = _optional_string(item, "name", path, default=role)
        story = _optional_string(item, "story", path, default="")
        key = (diaphragm_id, load_case)
        current = (role, name, pressure)
        if key in seen and seen[key] != current:
            raise ProjectSchemaError(
                path + " duplicates DIAP/LC with different floor load settings: "
                + str(diaphragm_id) + "/" + str(load_case)
            )
        seen[key] = current
        out.append(FloorLoadSettings(
            diaphragm_id=diaphragm_id,
            load_case=load_case,
            role=role,
            pressure_kN_m2=pressure,
            story=story,
            name=name,
        ))
    return out


def _with_floor_load_weight_cases(seismic: SeismicLoadSettings, floor_loads):
    cases = list(seismic.weight_load_cases)
    by_lc = {c.load_case: c for c in cases}
    for entry in floor_loads:
        if entry.role != "LL_E":
            continue
        existing = by_lc.get(entry.load_case)
        if existing is not None:
            if existing.role != "LL_E":
                raise ProjectSchemaError(
                    "project.load_conditions.floor_loads LL_E load case "
                    + str(entry.load_case)
                    + " conflicts with seismic.weight_load_cases role "
                    + existing.role
                )
            continue
        added = SeismicWeightLoadCaseSettings(
            name=entry.name or "LL(E)",
            load_case=entry.load_case,
            factor=1.0,
            role="LL_E",
        )
        cases.append(added)
        by_lc[entry.load_case] = added
    if len(cases) == len(seismic.weight_load_cases):
        return seismic
    return SeismicLoadSettings(
        ci=seismic.ci,
        c0=seismic.c0,
        z=seismic.z,
        rt=seismic.rt,
        design_period_s=seismic.design_period_s,
        height_m=seismic.height_m,
        steel_ratio_alpha=seismic.steel_ratio_alpha,
        tc=seismic.tc,
        base_level=seismic.base_level,
        base_elevation=seismic.base_elevation,
        base_mass_policy=seismic.base_mass_policy,
        dead_load_lc=seismic.dead_load_lc,
        live_load_lc=seismic.live_load_lc,
        live_load_factor=seismic.live_load_factor,
        weight_load_cases=tuple(cases),
        directions=seismic.directions,
    )


def _wood_settings_to_dict(wood):
    out = {
        "enabled": wood.enabled,
        "load_cases": list(wood.load_cases),
        "deflection_limit_ratio": wood.deflection_limit_ratio,
        "allowable_stresses": {
            "bending": wood.allowable_stresses.bending,
            "shear": wood.allowable_stresses.shear,
            "compression": wood.allowable_stresses.compression,
            "tension": wood.allowable_stresses.tension,
        },
    }
    # Optional sections stay out of the file until used, so saving an older
    # project does not rewrite it with empty keys.
    if wood.load_case_durations:
        out["load_case_durations"] = [asdict(d) for d in wood.load_case_durations]
    if wood.materials:
        out["materials"] = [
            {**asdict(m), "bending_depth_factors": [asdict(f) for f in m.bending_depth_factors]}
            for m in wood.materials
        ]
    if wood.conditions:
        out["conditions"] = [asdict(c) for c in wood.conditions]
    return out


def _parse_wood_check_settings(raw):
    _require_type(raw, dict, "project.design_checks.wood")
    _reject_unknown(
        raw,
        [
            "enabled",
            "load_cases",
            "deflection_limit_ratio",
            "allowable_stresses",
            "load_case_durations",
            "materials",
            "conditions",
        ],
        "project.design_checks.wood",
    )
    allowable = _parse_wood_allowable_stresses(raw.get("allowable_stresses", {}))
    return WoodCheckSettings(
        enabled=_optional_bool(raw, "enabled", "project.design_checks.wood", default=False),
        load_cases=tuple(_parse_int_list(raw.get("load_cases", []), "project.design_checks.wood.load_cases")),
        deflection_limit_ratio=_optional_number(
            raw,
            "deflection_limit_ratio",
            "project.design_checks.wood",
            default=0.0,
        ),
        allowable_stresses=allowable,
        load_case_durations=_parse_wood_load_case_durations(raw.get("load_case_durations", [])),
        materials=_parse_wood_materials(raw.get("materials", [])),
        conditions=_parse_wood_conditions(raw.get("conditions", [])),
    )


def _parse_wood_load_case_durations(raw):
    path = "project.design_checks.wood.load_case_durations"
    _require_type(raw, list, path)
    out = []
    for idx, item in enumerate(raw):
        item_path = path + "[" + str(idx) + "]"
        _require_type(item, dict, item_path)
        _reject_unknown(item, ["load_case", "duration"], item_path)
        load_case = item.get("load_case")
        if type(load_case) is not int:
            raise ProjectSchemaError(item_path + ".load_case must be an integer")
        duration = _required_string(item, "duration", item_path).strip().upper()
        if duration not in ALLOWED_LOAD_COMBINATION_DURATIONS:
            raise ProjectSchemaError(item_path + ".duration is not supported: " + duration)
        out.append(WoodLoadCaseDuration(load_case=load_case, duration=duration))
    return tuple(out)


def _parse_wood_materials(raw):
    path = "project.design_checks.wood.materials"
    _require_type(raw, list, path)
    out = []
    for idx, item in enumerate(raw):
        item_path = path + "[" + str(idx) + "]"
        _require_type(item, dict, item_path)
        _reject_unknown(
            item,
            ["name", "compression", "tension", "bending", "shear", "bearing", "bending_depth_factors"],
            item_path,
        )
        name = _required_string(item, "name", item_path).strip()
        if not name:
            raise ProjectSchemaError(item_path + ".name must not be empty")
        strengths = {}
        for key in ("compression", "tension", "bending", "shear"):
            value = _optional_number(item, key, item_path, default=0.0)
            if value <= 0.0:
                raise ProjectSchemaError(item_path + "." + key + " must be positive")
            strengths[key] = value
        bearing = _optional_number(item, "bearing", item_path, default=0.0)
        if bearing < 0.0:
            raise ProjectSchemaError(item_path + ".bearing must not be negative")
        out.append(WoodMaterialStrength(
            name=name,
            bearing=bearing,
            bending_depth_factors=_parse_wood_depth_factors(
                item.get("bending_depth_factors", []),
                item_path + ".bending_depth_factors",
            ),
            **strengths,
        ))
    return tuple(out)


def _parse_wood_depth_factors(raw, path):
    _require_type(raw, list, path)
    out = []
    for idx, item in enumerate(raw):
        item_path = path + "[" + str(idx) + "]"
        _require_type(item, dict, item_path)
        _reject_unknown(item, ["max_depth_mm", "factor"], item_path)
        max_depth = _optional_number(item, "max_depth_mm", item_path, default=0.0)
        factor = _optional_number(item, "factor", item_path, default=0.0)
        if max_depth <= 0.0 or factor <= 0.0:
            raise ProjectSchemaError(item_path + " requires positive max_depth_mm and factor")
        out.append(WoodBendingDepthFactor(max_depth_mm=max_depth, factor=factor))
    return tuple(sorted(out, key=lambda f: f.max_depth_mm))


_WOOD_CONDITION_PERCENT_KEYS = (
    "area_reduction_percent",
    "section_modulus_reduction_percent",
    "shear_area_reduction_percent",
    "inertia_reduction_percent",
)
_WOOD_CONDITION_NON_NEGATIVE_KEYS = (
    "slenderness_limit",
    "bearing_area_loss_mm2",
    "deflection_ratio_long_term",
    "deflection_ratio_long_term_snow",
    "deflection_ratio_short_term_snow",
    "deflection_mm_long_term",
    "deflection_mm_long_term_snow",
    "deflection_mm_short_term_snow",
)
_WOOD_CONDITION_POSITIVE_KEYS = (
    "buckling_factor_y",
    "buckling_factor_z",
    "lateral_buckling_coefficient",
)


def _parse_wood_conditions(raw):
    path = "project.design_checks.wood.conditions"
    _require_type(raw, list, path)
    out = []
    defaults = WoodMemberCondition()
    for idx, item in enumerate(raw):
        item_path = path + "[" + str(idx) + "]"
        _require_type(item, dict, item_path)
        _reject_unknown(
            item,
            ["kind", "member_class", "biaxial_bending", "check_bearing"]
            + list(_WOOD_CONDITION_PERCENT_KEYS)
            + list(_WOOD_CONDITION_NON_NEGATIVE_KEYS)
            + list(_WOOD_CONDITION_POSITIVE_KEYS),
            item_path,
        )
        kind = str(item.get("kind", "") or "").strip()
        member_class = str(item.get("member_class", "") or "").strip()
        if bool(kind) == bool(member_class):
            raise ProjectSchemaError(item_path + " requires exactly one of kind or member_class")
        if kind and kind not in ALLOWED_WOOD_CONDITION_KINDS:
            raise ProjectSchemaError(item_path + ".kind is not supported: " + kind)

        numbers = {}
        for key in _WOOD_CONDITION_PERCENT_KEYS:
            value = _optional_number(item, key, item_path, default=getattr(defaults, key))
            if value < 0.0 or value >= 100.0:
                raise ProjectSchemaError(item_path + "." + key + " must be at least 0 and below 100")
            numbers[key] = value
        for key in _WOOD_CONDITION_NON_NEGATIVE_KEYS:
            value = _optional_number(item, key, item_path, default=getattr(defaults, key))
            if value < 0.0:
                raise ProjectSchemaError(item_path + "." + key + " must not be negative")
            numbers[key] = value
        for key in _WOOD_CONDITION_POSITIVE_KEYS:
            value = _optional_number(item, key, item_path, default=getattr(defaults, key))
            if value <= 0.0:
                raise ProjectSchemaError(item_path + "." + key + " must be positive")
            numbers[key] = value

        out.append(WoodMemberCondition(
            kind=kind,
            member_class=member_class,
            biaxial_bending=_optional_bool(item, "biaxial_bending", item_path, default=defaults.biaxial_bending),
            check_bearing=_optional_bool(item, "check_bearing", item_path, default=defaults.check_bearing),
            **numbers,
        ))
    return tuple(out)


def _parse_wood_allowable_stresses(raw):
    _require_type(raw, dict, "project.design_checks.wood.allowable_stresses")
    _reject_unknown(
        raw,
        ["bending", "shear", "compression", "tension"],
        "project.design_checks.wood.allowable_stresses",
    )
    return WoodAllowableStresses(
        bending=_optional_number(raw, "bending", "project.design_checks.wood.allowable_stresses", default=0.0),
        shear=_optional_number(raw, "shear", "project.design_checks.wood.allowable_stresses", default=0.0),
        compression=_optional_number(raw, "compression", "project.design_checks.wood.allowable_stresses", default=0.0),
        tension=_optional_number(raw, "tension", "project.design_checks.wood.allowable_stresses", default=0.0),
    )


def _parse_int_list(raw, path):
    _require_type(raw, list, path)
    values = []
    for idx, item in enumerate(raw):
        if type(item) is not int:
            raise ProjectSchemaError(path + "[" + str(idx) + "] must be an integer")
        values.append(item)
    return values


def _parse_number_list(raw, path):
    _require_type(raw, list, path)
    values = []
    for idx, item in enumerate(raw):
        if type(item) not in (int, float):
            raise ProjectSchemaError(path + "[" + str(idx) + "] must be a number")
        values.append(float(item))
    return values


def _required(raw, key, path):
    if key not in raw:
        raise ProjectSchemaError(path + "." + key + " is required")
    return raw[key]


def _required_string(raw, key, path):
    value = _required(raw, key, path)
    if type(value) is not str or value.strip() == "":
        raise ProjectSchemaError(path + "." + key + " must be a non-empty string")
    return value


def _optional_string(raw, key, path, default=""):
    value = raw.get(key, default)
    if type(value) is not str:
        raise ProjectSchemaError(path + "." + key + " must be a string")
    if value == "" and default != "":
        return default
    return value


def _required_number(raw, key, path):
    value = _required(raw, key, path)
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _optional_number(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) not in (int, float):
        raise ProjectSchemaError(path + "." + key + " must be a number")
    return float(value)


def _optional_bool(raw, key, path, default):
    value = raw.get(key, default)
    if type(value) is not bool:
        raise ProjectSchemaError(path + "." + key + " must be true or false")
    return value


def _require_type(value, expected_type, path):
    if type(value) is not expected_type:
        raise ProjectSchemaError(path + " must be " + expected_type.__name__)


def _reject_unknown(raw, allowed, path):
    for key in raw.keys():
        if key not in allowed:
            raise ProjectSchemaError(path + "." + str(key) + " is not supported")


from stb_project.wall_quantity_settings import WALL_QUANTITY_JSON_SCHEMA as _WALL_QUANTITY_JSON_SCHEMA  # noqa: E402

PROJECT_JSON_SCHEMA["properties"]["wall_quantity"] = _WALL_QUANTITY_JSON_SCHEMA
