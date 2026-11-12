"""Wood member checks by the standard method.

Expected numbers marked "sample" come from a reviewed structural calculation
report (ASTIM output): 105x105 columns C1 and 105x300 beam G1(300) in
E120-F330 glulam with Fc=25.9, Ft=22.4, Fb=33.0, Fs=3.0, Fcv=6.0, E=12000.
"""

import dataclasses
import os
import sys
import tempfile
import unittest

import numpy as np

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from classes.mat import Mat
from classes.sec import Sec
from stb_checks import build_wood_check_summary
from stb_checks import wood_standard as ws
from stb_engine import run_from_file
from stb_project import (
    ProjectSchemaError,
    WoodBendingDepthFactor,
    WoodMaterialStrength,
    WoodMemberCondition,
    load_project_file,
    validate_project_dict,
)
from stb_reports import render_confirmation_draft_markdown


# Size factors that reproduce the sample's Fb for its four depths.
SAMPLE_DEPTH_FACTORS = (
    WoodBendingDepthFactor(150.0, 1.08),
    WoodBendingDepthFactor(250.0, 1.05),
    WoodBendingDepthFactor(300.0, 1.0),
    WoodBendingDepthFactor(450.0, 0.96),
)
SAMPLE_MATERIAL = WoodMaterialStrength(
    name="E120-F330",
    compression=25.9,
    tension=22.4,
    bending=33.0,
    shear=3.0,
    bearing=6.0,
    bending_depth_factors=SAMPLE_DEPTH_FACTORS,
)
SAMPLE_BEAM_CONDITION = WoodMemberCondition(
    kind="beam",
    area_reduction_percent=15.0,
    section_modulus_reduction_percent=15.0,
    shear_area_reduction_percent=15.0,
    inertia_reduction_percent=15.0,
    buckling_factor_z=0.5,
    biaxial_bending=False,
)
SAMPLE_COLUMN_CONDITION = WoodMemberCondition(kind="column", biaxial_bending=False)


def _element(width_mm, depth_mm, length, forces):
    """A member with the given section and per-load-case 14-component forces."""

    mat = Mat(1, "E120-F330", 12000.0e6, 800.0e6, 5000.0, 3.0e-6, 0.0)
    sec = Sec(1, "S", mat, 0, [width_mm * 1.0e-3, depth_mm * 1.0e-3])
    return _Member(sec, length, np.array(forces, dtype=float).T)


class _Member:
    def __init__(self, sec, length, forces):
        self.sec = sec
        self.len = length
        self.forces = forces
        self.ndisps = None


def _forces(n=0.0, q=0.0, my_i=0.0, my_j=0.0, my_mid=0.0):
    """Components: 0/6 axial, 2/8 shear z, 4/10 end My, 12 mid-span My (N, N*m)."""

    f = [0.0] * 14
    f[0] = f[6] = n * 1.0e3
    f[2] = f[8] = q * 1.0e3
    f[4] = my_i * 1.0e3
    f[10] = my_j * 1.0e3
    f[12] = my_mid * 1.0e3
    return f


class TestSampleFormulas(unittest.TestCase):

    def test_allowable_factors_match_sample(self):
        fc = 25.9
        self.assertAlmostEqual(fc * ws.DURATION_FACTORS[ws.LONG_TERM], 9.50, places=2)
        self.assertAlmostEqual(fc * ws.DURATION_FACTORS[ws.LONG_TERM_SNOW], 12.35, places=2)
        self.assertAlmostEqual(fc * ws.DURATION_FACTORS[ws.SHORT_TERM_SNOW], 13.81, places=2)
        self.assertAlmostEqual(fc * ws.DURATION_FACTORS[ws.SHORT_TERM], 17.27, places=2)

    def test_buckling_reduction_matches_sample(self):
        for slenderness, expected in ((26.4, 1.00), (37.8, 0.92), (85.2, 0.45), (90.1, 0.40), (97.0, 0.33)):
            self.assertAlmostEqual(ws.buckling_reduction(slenderness), expected, delta=0.005)

    def test_buckling_reduction_is_continuous_at_breakpoints(self):
        self.assertAlmostEqual(ws.buckling_reduction(30.0), ws.buckling_reduction(30.0001), places=3)
        self.assertAlmostEqual(ws.buckling_reduction(100.0), ws.buckling_reduction(100.0001), places=3)

    def test_lateral_buckling_matches_sample(self):
        ck, cs, cb = ws.lateral_buckling(12000.0, 33.0 * 1.1 / 3.0, 300.0, 105.0, 1520.0)
        self.assertAlmostEqual(ck, 24.39, places=2)
        self.assertAlmostEqual(cs, 6.43, places=2)
        self.assertEqual(cb, 1.0)

    def test_lateral_buckling_reduction_matches_sample(self):
        self.assertAlmostEqual(1.0 - (15.25 / 24.39) ** 4 / 3.0, 0.95, delta=0.005)
        self.assertAlmostEqual(1.0 - (11.81 / 23.81) ** 4 / 3.0, 0.98, delta=0.005)
        _ck, _cs, cb = ws.lateral_buckling(12000.0, 12.10, 1000.0, 105.0, 3300.0)
        self.assertLess(cb, 1.0)

    def test_lateral_buckling_is_continuous_at_ck(self):
        young, fb = 12000.0, 12.10
        ck = (0.6 * young / fb) ** 0.5
        below = 1.0 - (1.0 - 1.0e-6) ** 4 / 3.0
        above = 0.4 * young / (ck * ck * fb)
        self.assertAlmostEqual(below, above, places=4)

    def test_depth_factor_reproduces_sample_fb(self):
        for depth, expected in ((105.0, 35.6), (180.0, 34.6), (300.0, 33.0), (360.0, 31.7)):
            self.assertAlmostEqual(33.0 * ws.bending_depth_factor(SAMPLE_MATERIAL, depth), expected, delta=0.06)

    def test_depth_factor_defaults_to_one(self):
        material = dataclasses.replace(SAMPLE_MATERIAL, bending_depth_factors=())
        self.assertEqual(ws.bending_depth_factor(material, 300.0), 1.0)

    def test_midspan_deflection_matches_closed_forms(self):
        w, length, ei = 2000.0, 4.0, 1.0e6
        simple = ws.midspan_bending_deflection(0.0, 0.0, w * length ** 2 / 8.0, length, ei)
        self.assertAlmostEqual(simple, 5.0 * w * length ** 4 / (384.0 * ei))
        fixed = ws.midspan_bending_deflection(
            -w * length ** 2 / 12.0, -w * length ** 2 / 12.0, w * length ** 2 / 24.0, length, ei
        )
        self.assertAlmostEqual(fixed, w * length ** 4 / (384.0 * ei))


class TestSampleMembers(unittest.TestCase):

    def _check(self, e, condition, kind, durations):
        cases = list(range(len(durations)))
        return ws.check_element(
            e,
            SAMPLE_MATERIAL,
            condition,
            kind,
            cases,
            {c: c for c in cases},
            dict(enumerate(durations)),
        )

    def test_column_c1_matches_sample(self):
        e = _element(105, 105, 2.581, [_forces(n=-8.01), _forces(n=-30.50)])
        result = self._check(e, SAMPLE_COLUMN_CONDITION, "column", [ws.LONG_TERM, ws.SHORT_TERM])

        self.assertAlmostEqual(result.properties.slenderness, 85.2, delta=0.1)
        self.assertAlmostEqual(result.properties.eta, 0.45, delta=0.005)
        long_term, short_term = result.results
        self.assertAlmostEqual(long_term.ratio, 0.171, delta=0.001)
        self.assertAlmostEqual(short_term.ratio, 0.357, delta=0.001)
        self.assertAlmostEqual(short_term.allowable_compression / ws.STRESS_UNIT, 17.27, places=2)
        self.assertAlmostEqual(short_term.allowable_bending_y / ws.STRESS_UNIT, 23.76, places=2)
        self.assertIs(result.governing, short_term)

    def test_beam_g1_matches_sample(self):
        e = _element(
            105,
            300,
            1.6,
            [_forces(n=0.12, q=-3.29, my_i=-3.63), _forces(n=0.13, q=-3.85, my_i=-4.28)],
        )
        result = self._check(e, SAMPLE_BEAM_CONDITION, "beam", [ws.LONG_TERM, ws.SHORT_TERM_SNOW])

        props = result.properties
        self.assertAlmostEqual(props.area * 1.0e4, 267.8, delta=0.1)
        self.assertAlmostEqual(props.section_modulus_y * 1.0e6, 1338.8, delta=0.1)
        self.assertAlmostEqual(props.slenderness, 26.4, delta=0.1)
        self.assertAlmostEqual(props.lateral_length, 1.52)
        self.assertEqual(props.lateral_cb, 1.0)

        long_term, snow = result.results
        self.assertAlmostEqual(long_term.allowable_bending_y / ws.STRESS_UNIT, 12.10, places=2)
        self.assertAlmostEqual(long_term.bending_ratio, 0.224, delta=0.001)
        self.assertAlmostEqual(long_term.shear_ratio, 0.168, delta=0.001)
        self.assertAlmostEqual(snow.allowable_bending_y / ws.STRESS_UNIT, 17.60, places=2)
        self.assertAlmostEqual(snow.bending_ratio, 0.182, delta=0.001)
        self.assertAlmostEqual(snow.shear_ratio, 0.135, delta=0.001)

    def test_bearing_matches_sample(self):
        condition = dataclasses.replace(SAMPLE_COLUMN_CONDITION, check_bearing=True)
        e = _element(105, 105, 2.94, [_forces(n=-4.01)])
        result = self._check(e, condition, "column", [ws.LONG_TERM])
        self.assertAlmostEqual(result.results[0].allowable_bearing / ws.STRESS_UNIT, 2.20, places=2)
        self.assertAlmostEqual(result.results[0].bearing_ratio, 0.165, delta=0.001)

    def test_tension_is_not_reduced_by_buckling(self):
        compression = self._check(
            _element(105, 105, 2.581, [_forces(n=-8.0)]), SAMPLE_COLUMN_CONDITION, "column", [ws.LONG_TERM]
        )
        tension = self._check(
            _element(105, 105, 2.581, [_forces(n=8.0)]), SAMPLE_COLUMN_CONDITION, "column", [ws.LONG_TERM]
        )
        sigma = 8000.0 / (0.105 * 0.105)
        self.assertAlmostEqual(tension.results[0].axial_ratio, sigma / (22.4e6 * 1.1 / 3.0))
        self.assertGreater(compression.results[0].axial_ratio, tension.results[0].axial_ratio)

    def test_deflection_passes_when_either_limit_is_met(self):
        condition = dataclasses.replace(
            SAMPLE_BEAM_CONDITION, deflection_ratio_long_term=500.0, deflection_mm_long_term=10.0
        )
        # 6.6 mm over 1.6 m is 1/243: beyond L/500 but within 10 mm, as in the sample.
        ei = 12000.0e6 * (0.105 * 0.3 ** 3 / 12.0) * 0.85
        moment_mid = 0.0066 * 96.0 * ei / (10.0 * 1.6 ** 2) * 1.0e-3
        e = _element(105, 300, 1.6, [_forces(my_mid=moment_mid)])
        result = self._check(e, condition, "beam", [ws.LONG_TERM])
        self.assertAlmostEqual(result.results[0].deflection, 0.0066, places=6)
        self.assertAlmostEqual(result.results[0].deflection_ratio, 0.66, places=3)

    def test_short_term_has_no_deflection_check(self):
        condition = dataclasses.replace(SAMPLE_BEAM_CONDITION, deflection_ratio_long_term=500.0)
        e = _element(105, 300, 1.6, [_forces(my_mid=1.0)])
        result = self._check(e, condition, "beam", [ws.SHORT_TERM])
        self.assertIsNone(result.results[0].deflection_ratio)

    def test_excess_slenderness_reports_message(self):
        e = _element(105, 105, 5.0, [_forces(n=-1.0)])
        result = self._check(e, SAMPLE_COLUMN_CONDITION, "column", [ws.LONG_TERM])
        self.assertEqual(result.messages, (ws.MESSAGE_SLENDERNESS,))

    def test_flatwise_beam_bending_about_weak_axis_is_checked(self):
        # Width exceeds depth, so the vertical moment My acts about the weak axis.
        e = _element(450, 300, 1.8, [_forces(my_i=-20.0)])
        result = self._check(e, SAMPLE_BEAM_CONDITION, "beam", [ws.LONG_TERM])
        sigma = 20000.0 / (e.sec.Wy * 0.85)
        self.assertAlmostEqual(result.results[0].sigma_by, sigma)
        self.assertGreater(result.results[0].bending_ratio, 0.0)

    def test_biaxial_bending_adds_both_axes(self):
        forces = _forces(my_i=1.0)
        forces[5] = 1000.0
        uniaxial = self._check(_element(105, 105, 2.0, [forces]), SAMPLE_COLUMN_CONDITION, "column", [ws.LONG_TERM])
        biaxial = self._check(
            _element(105, 105, 2.0, [forces]),
            dataclasses.replace(SAMPLE_COLUMN_CONDITION, biaxial_bending=True),
            "column",
            [ws.LONG_TERM],
        )
        self.assertAlmostEqual(biaxial.results[0].bending_ratio, 2.0 * uniaxial.results[0].bending_ratio)


MODEL_HEADER = """MATE, 1, Wood, 12000, 800, 5.0, 3e-06, 0
SECT, 1, S105, 1, 0, 105.0, 105.0
SECT, 2, B120, 1, 0, 120.0, 240.0
"""


def _project(member_classes, wood):
    return validate_project_dict({
        "schema": 1,
        "model": {"dat": "model.dat"},
        "building": {
            "name": "Wood",
            "location": "",
            "use": "",
            "structure": "wood",
            "calculation_route": "",
            "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""},
        },
        "grids": [{"name": "X1", "direction": "x", "coordinate": 0.0}],
        "stories": [{"name": "1", "elevation": 0.0, "height": 3.0}],
        "member_classes": member_classes,
        "design_checks": {"wood": dict({"enabled": True}, **wood)},
        "report": {
            "title": "Wood",
            "mode": "practice",
            "language": "ja",
            "format": "markdown",
            "include_manual_items": True,
            "include_warnings": True,
        },
    })


def _member_class(name, kind):
    return {"name": name, "kind": kind, "element_ids": [1], "story": "1", "use": "", "notes": ""}


MATERIAL = {"name": "Wood", "compression": 25.9, "tension": 22.4, "bending": 33.0, "shear": 3.0}


def _solve(body):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.dat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(MODEL_HEADER + body)
        mdl, _txt = run_from_file(path)
    return mdl


class TestSolvedModels(unittest.TestCase):

    COLUMN = """NODE, 1, 0.0, 0.0, 0.0
NODE, 2, 0.0, 0.0, 2.581
ELEM, 1, 1, 2, 1, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
PLOD, 2, 0, 0.0, 0.0, -8.01, 0.0, 0.0, 0.0
PLOD, 2, 1, 0.0, 0.0, -30.5, 0.0, 0.0, 0.0
"""
    FIXED_BEAM = """NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 4.0, 0.0, 3.0
ELEM, 1, 1, 2, 2, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
CONS, 2, 1, 1, 1, 1, 1, 1
ELOD, 1, 0, 1, 0.0, 0.0, -2.0, 0.0, 0.0, -2.0
"""
    CANTILEVER = """NODE, 1, 0.0, 0.0, 3.0
NODE, 2, 2.0, 0.0, 3.0
ELEM, 1, 1, 2, 2, 0.0
CONS, 1, 1, 1, 1, 1, 1, 1
PLOD, 2, 0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0
"""
    BEAM_CONDITION = {"kind": "beam", "deflection_ratio_long_term": 500.0}

    def test_solved_column_compression_uses_buckling(self):
        project = _project(
            [_member_class("columns", "column")],
            {
                "load_cases": [0, 1],
                "load_case_durations": [
                    {"load_case": 0, "duration": "LONG_TERM"},
                    {"load_case": 1, "duration": "SHORT_TERM"},
                ],
                "materials": [MATERIAL],
                "conditions": [{"kind": "column", "biaxial_bending": False}],
            },
        )
        summary = build_wood_check_summary(_solve(self.COLUMN), project)

        self.assertEqual(summary.method, "standard")
        check = summary.element_checks[0]
        self.assertEqual(check.duration, ws.SHORT_TERM)
        self.assertAlmostEqual(check.combined_ratio, 0.357, delta=0.001)
        self.assertAlmostEqual(check.standard.results[0].ratio, 0.171, delta=0.001)
        self.assertEqual(summary.status, "OK")

    def test_solved_fixed_beam_deflection_matches_theory(self):
        project = _project(
            [_member_class("beams", "beam")],
            {"load_cases": [0], "materials": [MATERIAL], "conditions": [self.BEAM_CONDITION]},
        )
        summary = build_wood_check_summary(_solve(self.FIXED_BEAM), project)

        inertia = 0.12 * 0.24 ** 3 / 12.0
        expected = 2000.0 * 4.0 ** 4 / (384.0 * 12000.0e6 * inertia)
        check = summary.element_checks[0]
        self.assertAlmostEqual(check.demand.deflection, expected, places=7)
        self.assertAlmostEqual(check.deflection_ratio, expected / (4.0 / 500.0), places=5)

    def test_solved_cantilever_uses_tip_displacement(self):
        project = _project(
            [_member_class("beams", "beam")],
            {"load_cases": [0], "materials": [MATERIAL], "conditions": [self.BEAM_CONDITION]},
        )
        mdl = _solve(self.CANTILEVER)
        summary = build_wood_check_summary(mdl, project)

        tip = abs(float(mdl.FindElemFromEid(1).n1.disps[2, 0]))
        self.assertGreater(tip, 0.0)
        self.assertAlmostEqual(summary.element_checks[0].demand.deflection, tip, places=9)

    def test_duration_defaults_to_long_term_with_warning(self):
        project = _project(
            [_member_class("columns", "column")],
            {"load_cases": [0], "materials": [MATERIAL]},
        )
        summary = build_wood_check_summary(_solve(self.COLUMN), project)
        self.assertEqual(summary.element_checks[0].duration, ws.LONG_TERM)
        self.assertTrue(any("no duration" in w for w in summary.warnings))

    def test_load_combination_duration_is_used(self):
        project = _project(
            [_member_class("columns", "column")],
            {"load_cases": [0], "materials": [MATERIAL]},
        )
        combination = dataclasses.replace(
            project.load_conditions,
            load_combinations=(
                _combination(load_case=0, duration="LONG_TERM_SNOW"),
            ),
        )
        project = dataclasses.replace(project, load_conditions=combination)
        summary = build_wood_check_summary(_solve(self.COLUMN), project)
        self.assertEqual(summary.element_checks[0].duration, ws.LONG_TERM_SNOW)

    def test_unknown_material_is_reported_and_not_passed(self):
        other = dict(MATERIAL, name="Other")
        project = _project([_member_class("columns", "column")], {"load_cases": [0], "materials": [other]})
        summary = build_wood_check_summary(_solve(self.COLUMN), project)
        self.assertEqual(summary.element_checks[0].status, "WARN")
        self.assertEqual(summary.status, "WARN")
        self.assertEqual(summary.tables.member_classes[0]["status"], "WARN")

    def test_overstress_is_ng(self):
        weak = dict(MATERIAL, compression=1.0)
        project = _project([_member_class("columns", "column")], {"load_cases": [0], "materials": [weak]})
        summary = build_wood_check_summary(_solve(self.COLUMN), project)
        self.assertGreater(summary.max_ratio, 1.0)
        self.assertEqual(summary.status, "NG")


def _combination(load_case, duration):
    from stb_project.schema import LoadCombinationSettings

    return LoadCombinationSettings(
        load_case=load_case,
        name="C",
        duration=duration,
        factors=(1.0,),
        load_cases=(0,),
    )


class TestExistingProjects(unittest.TestCase):

    def _sample(self):
        project = load_project_file(os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json"))
        mdl, _txt = run_from_file(os.path.join(_STB_ROOT, "data", project.dat_path))
        return mdl, project

    def test_simplified_method_is_kept_and_flagged(self):
        mdl, project = self._sample()
        summary = build_wood_check_summary(mdl, project)
        self.assertEqual(summary.method, "simplified")
        self.assertTrue(any("簡易法" in w for w in summary.warnings))
        self.assertIn("簡易法", render_confirmation_draft_markdown(mdl, project))

    def test_report_shows_standard_tables(self):
        mdl, project = self._sample()
        wood = dataclasses.replace(
            project.design_checks.wood,
            materials=(WoodMaterialStrength("Sugi", 17.7, 13.5, 22.2, 1.8),),
        )
        project = dataclasses.replace(
            project, design_checks=dataclasses.replace(project.design_checks, wood=wood)
        )
        text = render_confirmation_draft_markdown(mdl, project)
        self.assertIn("許容応力度計算", text)
        self.assertIn("部材の断面性能・座屈", text)
        self.assertIn("荷重継続期間別の検定", text)
        self.assertIn("長期", text)


class TestSchema(unittest.TestCase):

    def test_round_trip(self):
        project = _project(
            [_member_class("beams", "beam")],
            {
                "load_cases": [0],
                "load_case_durations": [{"load_case": 0, "duration": "short_term_snow"}],
                "materials": [
                    dict(MATERIAL, bearing=6.0, bending_depth_factors=[
                        {"max_depth_mm": 300.0, "factor": 1.0},
                        {"max_depth_mm": 150.0, "factor": 1.08},
                    ]),
                ],
                "conditions": [{"kind": "beam", "buckling_factor_z": 0.5, "biaxial_bending": False}],
            },
        )
        wood = project.design_checks.wood
        self.assertEqual(wood.load_case_durations[0].duration, "SHORT_TERM_SNOW")
        self.assertEqual([f.max_depth_mm for f in wood.materials[0].bending_depth_factors], [150.0, 300.0])
        self.assertEqual(wood.conditions[0].lateral_buckling_coefficient, 1.9)
        self.assertEqual(validate_project_dict(project.to_dict()).to_dict(), project.to_dict())

    def _assert_rejected(self, wood):
        with self.assertRaises(ProjectSchemaError):
            _project([_member_class("beams", "beam")], wood)

    def test_rejects_non_positive_strength(self):
        self._assert_rejected({"materials": [dict(MATERIAL, bending=0.0)]})

    def test_rejects_unknown_duration(self):
        self._assert_rejected({"load_case_durations": [{"load_case": 0, "duration": "FOREVER"}]})

    def test_rejects_condition_without_target(self):
        self._assert_rejected({"conditions": [{"buckling_factor_y": 1.0}]})

    def test_rejects_condition_with_both_targets(self):
        self._assert_rejected({"conditions": [{"kind": "beam", "member_class": "beams"}]})

    def test_rejects_reduction_of_100_percent(self):
        self._assert_rejected({"conditions": [{"kind": "beam", "area_reduction_percent": 100.0}]})


if __name__ == "__main__":
    unittest.main()
