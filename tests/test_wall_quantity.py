import copy
import math
import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import WallQuantityError, build_wall_quantity_summary
from stb_checks.wall_quantity import brace_height_reduction, layer_shear_distribution_ai
from stb_engine import parse_input
from stb_project import ProjectSchemaError, validate_project_dict


def _project(wall_quantity, stories=None):
    return {
        "schema": 1,
        "model": {"dat": "model.dat"},
        "building": {"name": "Wall quantity sample", "structure": "wood"},
        "grids": [],
        "stories": stories if stories is not None else [
            {"name": "1", "elevation": 0.0, "height": 3.0},
            {"name": "2", "elevation": 3.0, "height": 2.86},
        ],
        "member_classes": [],
        "report": {"title": "壁量計算書", "mode": "practice", "format": "markdown"},
        "wall_quantity": wall_quantity,
    }


def _spec_settings(**overrides):
    wq = {
        "seismic": {
            "method": "spec",
            "roof": "tile",
            "exterior_wall": "siding",
            "solar": {"mode": "standard"},
        },
        "stories": [
            {"story": "1", "floor_area_m2": 50.0, "wind_area_x_m2": 30.0, "wind_area_y_m2": 20.0},
            {"story": "2", "floor_area_m2": 50.0, "wind_area_x_m2": 12.0, "wind_area_y_m2": 8.0},
        ],
    }
    wq.update(overrides)
    return wq


def _wall_lines(walls):
    """Build a parse-only model with one vertical rectangle per wall.

    walls: list of (wwll_id, multiplier, dir_code, x0, y0, x1, y1, z0, z1)
    """
    lines = [
        "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
        "SECT, 1, C120, 1, 0, 120, 120",
    ]
    nid = 1
    for wid, m, d, x0, y0, x1, y1, z0, z1 in walls:
        ids = []
        for x, y, z in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)):
            lines.append("NODE, {0}, {1}, {2}, {3}".format(nid, x, y, z))
            ids.append(nid)
            nid += 1
        lines.append("WWLL, {0}, W{0}, 1, {1}, , , {2}, 0.0083333333, {3}, {4}, {5}, {6}, , 1".format(
            wid, m, d, *ids))
    return lines


class TestSeismicDemandAgainstOfficialExamples(unittest.TestCase):
    """Lw must reproduce the MLIT/howtec tool example and 早見表 values."""

    def _lw(self, roof, wall, solar, heights, areas):
        stories = []
        elev = 0.0
        for i, h in enumerate(heights):
            stories.append({"name": str(i + 1), "elevation": elev, "height": h})
            elev += h
        wq = {
            "seismic": {"roof": roof, "exterior_wall": wall, "solar": {"mode": solar}},
            "stories": [{"story": str(i + 1), "floor_area_m2": a} for i, a in enumerate(areas)],
        }
        project = validate_project_dict(_project(wq, stories=stories))
        summary = build_wall_quantity_summary(parse_input([]), project)
        return [s.lw_cm_m2 for s in summary.seismic.stories]

    def test_mlit_tool_input_example(self):
        # 補足資料 p.5: 2F 2.86 m, 1F 3.00 m, 50/50 m2, 瓦(ふき土無), サイディング, 太陽光あり(260)
        self.assertEqual(self._lw("tile", "siding", "standard", [3.0, 2.86], [50.0, 50.0]), [46.0, 28.0])

    def test_quick_reference_table_spec2_equal_areas(self):
        # 補足資料 p.4 早見表 (太陽光なし, 仕様② 2F 2.9 m / 1F 3.0 m, 100/100)
        cases = [
            ("tile", "siding", [44.0, 26.0]),
            ("tile", "earth", [51.0, 29.0]),
            ("slate", "earth", [48.0, 26.0]),
            ("metal", "wood_board", [32.0, 16.0]),
        ]
        for roof, wall, expected in cases:
            with self.subTest(roof=roof, wall=wall):
                self.assertEqual(self._lw(roof, wall, "none", [3.0, 2.9], [50.0, 50.0]), expected)

    def test_quick_reference_table_single_story(self):
        self.assertEqual(self._lw("tile", "siding", "none", [3.0], [50.0]), [20.0])

    def test_two_story_breakdown_is_traceable(self):
        project = validate_project_dict(_project(_spec_settings()))
        summary = build_wall_quantity_summary(parse_input([]), project)
        s1, s2 = summary.seismic.stories
        self.assertAlmostEqual(summary.seismic.building_height_m, 0.9 + 3.0 + 2.86 + 0.5)
        self.assertAlmostEqual(s1.alpha, 1.0)
        self.assertAlmostEqual(s1.ai, 1.0)
        self.assertTrue(s2.ai > 1.0)
        self.assertAlmostEqual(s2.alpha, s2.weight_kN / s1.weight_kN)
        self.assertAlmostEqual(s1.required_cm, 46.0 * 50.0)
        keys = [item.key for item in summary.seismic.load_items]
        self.assertIn("roof", keys)
        self.assertIn("story_wall_2", keys)
        self.assertIn("story_wall_1", keys)


class TestDirectMethod(unittest.TestCase):

    def test_direct_weights_use_ai_formula(self):
        wq = {
            "seismic": {"method": "direct", "c0": 0.2, "building_height_m": 7.0},
            "stories": [
                {"story": "1", "floor_area_m2": 60.0, "weight_kN": 240.0},
                {"story": "2", "floor_area_m2": 40.0, "weight_kN": 90.0},
            ],
        }
        project = validate_project_dict(_project(wq))
        summary = build_wall_quantity_summary(parse_input([]), project)
        s1, s2 = summary.seismic.stories
        self.assertEqual(s1.lw_cm_m2, math.ceil(0.2 * 240.0 / (0.0196 * 60.0)))
        ai2 = layer_shear_distribution_ai(90.0 / 240.0, 0.03 * 7.0)
        self.assertAlmostEqual(s2.ai, ai2)
        self.assertEqual(s2.lw_cm_m2, math.ceil(ai2 * 0.2 * 90.0 / (0.0196 * 40.0)))

    def test_direct_requires_weights(self):
        wq = {"seismic": {"method": "direct"}, "stories": [
            {"story": "1", "floor_area_m2": 60.0},
            {"story": "2", "floor_area_m2": 40.0},
        ]}
        project = validate_project_dict(_project(wq))
        with self.assertRaises(WallQuantityError):
            build_wall_quantity_summary(parse_input([]), project)


class TestExistingWalls(unittest.TestCase):

    def test_walls_are_assigned_to_stories_and_checked(self):
        mdl = parse_input(_wall_lines([
            (1, 2.5, 0, 0.0, 0.0, 9.1, 0.0, 0.0, 3.0),    # 1F X, 9.1 m x 2.5
            (2, 2.5, 0, 0.0, 7.28, 9.1, 7.28, 0.0, 3.0),  # 1F X
            (3, 2.5, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),   # 1F Y
            (4, 2.5, 0, 0.0, 0.0, 9.1, 0.0, 3.0, 5.86),   # 2F X
            (5, 2.5, 1, 0.0, 0.0, 0.0, 7.28, 3.0, 5.86),  # 2F Y
        ]))
        project = validate_project_dict(_project(_spec_settings()))
        summary = build_wall_quantity_summary(mdl, project)

        stories = {w.ref: w.story for w in summary.walls}
        self.assertEqual(stories, {"1": "1", "2": "1", "3": "1", "4": "2", "5": "2"})
        check = {(c.story, c.direction): c for c in summary.checks}
        self.assertAlmostEqual(check[("1", "x")].bearing_cm, 2 * 2.5 * 910.0)
        self.assertAlmostEqual(check[("1", "y")].bearing_cm, 2.5 * 728.0)
        self.assertEqual(check[("1", "x")].status, "OK")      # 4550 >= 46*50=2300
        self.assertEqual(check[("1", "y")].status, "NG")      # 1820 < 2300
        self.assertEqual(summary.status, "NG")
        self.assertEqual(check[("2", "x")].required_cm, 28.0 * 50.0)

    def test_wind_can_govern(self):
        wq = _spec_settings()
        wq["stories"][1]["wind_area_x_m2"] = 40.0   # 40 x 50 = 2000 > 28 x 50 = 1400
        project = validate_project_dict(_project(wq))
        summary = build_wall_quantity_summary(parse_input([]), project)
        check = {(c.story, c.direction): c for c in summary.checks}
        self.assertEqual(check[("2", "x")].governing, "wind")
        self.assertAlmostEqual(check[("2", "x")].required_cm, 2000.0)
        self.assertEqual(check[("2", "y")].governing, "seismic")

    def test_multiplier_cap_on_same_frame_and_overrides(self):
        mdl = parse_input(_wall_lines([
            (1, 4.0, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0),
            (2, 4.0, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0),   # same frame -> total 8.0 capped to 7.0
            (3, 2.0, 0, 3.0, 0.0, 4.82, 0.0, 0.0, 3.0),   # excluded
        ]))
        wq = _spec_settings(walls=[{"wwll_id": 3, "exclude": True}])
        wq_single = copy.deepcopy(wq)
        wq_single["stories"] = [{"story": "1", "floor_area_m2": 50.0}]
        project = validate_project_dict(_project(wq_single, stories=[{"name": "1", "elevation": 0.0, "height": 3.0}]))
        summary = build_wall_quantity_summary(mdl, project)
        refs = sorted(w.ref for w in summary.walls)
        self.assertEqual(refs, ["1", "2"])
        total_m = sum(w.multiplier for w in summary.walls)
        self.assertAlmostEqual(total_m, 7.0)
        self.assertTrue(all(w.capped for w in summary.walls))
        self.assertTrue(any("7.0" in msg for msg in summary.warnings))

    def test_brace_height_reduction(self):
        self.assertEqual(brace_height_reduction(0.91, 3.2), 1.0)
        self.assertAlmostEqual(brace_height_reduction(0.91, 3.5), 3.5 * 0.91 / 3.5)
        self.assertEqual(brace_height_reduction(1.82, 3.5), 1.0)
        mdl = parse_input(_wall_lines([(1, 2.0, 0, 0.0, 0.0, 0.91, 0.0, 0.0, 3.5)]))
        wq = {
            "seismic": {"roof": "metal", "exterior_wall": "siding"},
            "stories": [{"story": "1", "floor_area_m2": 30.0}],
            "walls": [{"wwll_id": 1, "kind": "brace"}],
        }
        project = validate_project_dict(_project(wq, stories=[{"name": "1", "elevation": 0.0, "height": 3.5}]))
        summary = build_wall_quantity_summary(mdl, project)
        wall = summary.walls[0]
        self.assertAlmostEqual(wall.alpha_h, 0.91)
        self.assertAlmostEqual(wall.multiplier, 2.0 * 0.91)


class TestQuasiWalls(unittest.TestCase):

    def _summary(self, quasi, verified=False):
        wq = {
            "seismic": {"roof": "tile", "exterior_wall": "siding"},
            "stories": [{"story": "1", "floor_area_m2": 50.0}],
            "quasi_walls": quasi,
            "quasi_over_half_verified": verified,
        }
        project = validate_project_dict(_project(wq, stories=[{"name": "1", "elevation": 0.0, "height": 3.0}]))
        return build_wall_quantity_summary(parse_input([]), project)

    def test_panel_and_lath_multipliers(self):
        summary = self._summary([
            {"name": "Q1", "story": "1", "direction": "x", "length_m": 1.0, "type": "quasi",
             "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.1, "clear_height_m": 2.6},
            {"name": "Q2", "story": "1", "direction": "y", "length_m": 1.0, "type": "hanging_waist",
             "material": "lath", "material_height_m": 1.3, "clear_height_m": 2.6},
        ])
        by_name = {w.ref: w for w in summary.walls}
        self.assertAlmostEqual(by_name["Q1"].multiplier, 2.5 * 0.6 * 2.1 / 2.6)  # 補足資料 p.8 ≒ 1.2
        self.assertAlmostEqual(by_name["Q2"].multiplier, 0.25)                   # 補足資料 p.8
        self.assertAlmostEqual(by_name["Q2"].amount_cm, 25.0)

    def test_quasi_walls_capped_at_half_of_required(self):
        big = [{"name": "Q", "story": "1", "direction": "x", "length_m": 20.0, "type": "quasi",
                "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.6, "clear_height_m": 2.6}]
        summary = self._summary(big)
        check = {(c.story, c.direction): c for c in summary.checks}[("1", "x")]
        self.assertTrue(check.quasi_exceeds_half)
        self.assertTrue(summary.quasi_exceeds_half)
        self.assertAlmostEqual(check.quasi_counted_cm, 0.5 * check.required_cm)
        self.assertEqual(check.status, "NG")

        verified = self._summary(big, verified=True)
        check_v = {(c.story, c.direction): c for c in verified.checks}[("1", "x")]
        self.assertAlmostEqual(check_v.quasi_counted_cm, check_v.quasi_raw_cm)
        self.assertEqual(check_v.status, "OK")


class TestWallQuantitySchema(unittest.TestCase):

    def test_projects_without_wall_quantity_are_unchanged(self):
        raw = _project(None)
        del raw["wall_quantity"]
        project = validate_project_dict(raw)
        self.assertTrue(project.wall_quantity.is_default)
        self.assertNotIn("wall_quantity", project.to_dict())

    def test_round_trip(self):
        wq = _spec_settings(
            walls=[{"wwll_id": 1, "kind": "brace", "story": "1", "multiplier": 2.0,
                    "brace_section": "45x90", "brace_layout": "single"}],
            columns=[{"story": "1", "x": 0.0, "y": 0.0, "corner": True, "name": "C1"}],
            quasi_walls=[{"name": "Q1", "story": "1", "direction": "x", "length_m": 1.0, "type": "quasi",
                          "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.1,
                          "clear_height_m": 2.6, "x": 1.0, "y": 0.0}],
        )
        wq["stories"][0]["plan_polygons"] = [[[0, 0], [9.1, 0], [9.1, 7.28], [0, 7.28]]]
        wq["seismic"]["single_story_lw_cm_m2"] = 21.0
        wq["seismic"]["wall_insulation"] = {"mode": "custom", "layers": [
            {"density_kg_m3": 16.0, "thickness_mm": 105.0},
            {"density_kg_m3": 30.0, "thickness_mm": 25.0},
        ]}
        project = validate_project_dict(_project(wq))
        again = validate_project_dict(project.to_dict())
        self.assertEqual(again.wall_quantity, project.wall_quantity)

    def test_rejects_invalid_input(self):
        bad_cases = [
            {"seismic": {"roof": "straw", "exterior_wall": "siding"}},
            {"seismic": {"roof": "tile"}},
            {"seismic": {"roof": "tile", "exterior_wall": "siding"}, "unknown": 1},
            {"seismic": {"roof": "tile", "exterior_wall": "siding"},
             "walls": [{"wwll_id": 1, "kind": "panel", "brace_section": "45x90"}]},
            {"seismic": {"roof": "tile", "exterior_wall": "siding"},
             "stories": [{"story": "1", "floor_area_m2": 10.0, "plan_polygons": [[[0, 0], [1, 0]]]}]},
            {"seismic": {"roof": "tile", "exterior_wall": "siding"},
             "stories": [{"story": "1", "floor_area_m2": -1.0}]},
            {"seismic": {"roof": "tile", "exterior_wall": "siding"},
             "quasi_walls": [{"name": "Q", "story": "1", "direction": "x", "length_m": 1.0, "type": "quasi",
                              "material": "panel", "material_height_m": 2.0, "clear_height_m": 2.6}]},
        ]
        for wq in bad_cases:
            with self.subTest(wq=wq):
                with self.assertRaises(ProjectSchemaError):
                    validate_project_dict(_project(wq))

    def test_three_stories_are_rejected(self):
        stories = [
            {"name": "1", "elevation": 0.0, "height": 3.0},
            {"name": "2", "elevation": 3.0, "height": 3.0},
            {"name": "3", "elevation": 6.0, "height": 3.0},
        ]
        wq = {"seismic": {"roof": "tile", "exterior_wall": "siding"},
              "stories": [{"story": s["name"], "floor_area_m2": 50.0} for s in stories]}
        project = validate_project_dict(_project(wq, stories=stories))
        with self.assertRaises(WallQuantityError):
            build_wall_quantity_summary(parse_input([]), project)


if __name__ == "__main__":
    unittest.main()
