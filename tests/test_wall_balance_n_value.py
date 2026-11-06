import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import build_wall_quantity_summary
from stb_checks.n_value import brace_correction, height_factor, select_joint
from stb_engine import parse_input
from stb_project import validate_project_dict

from tests.test_wall_quantity import _project, _wall_lines


def _rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


SPEC = {"roof": "tile", "exterior_wall": "siding", "solar": {"mode": "standard"}}
TWO_STORIES = [
    {"name": "1", "elevation": 0.0, "height": 3.0},
    {"name": "2", "elevation": 3.0, "height": 2.86},
]
ONE_STORY = [{"name": "1", "elevation": 0.0, "height": 3.0}]


def _summary(walls, wq_extra, stories=TWO_STORIES):
    wq = {"seismic": dict(SPEC)}
    wq.update(wq_extra)
    project = validate_project_dict(_project(wq, stories=stories))
    return build_wall_quantity_summary(parse_input(_wall_lines(walls)), project)


class TestWallBalance(unittest.TestCase):
    """1F 9.1 x 7.28, 2F 5.46 x 7.28 on the left: the right 1F strip (Y direction) is a lean-to."""

    def _wq(self):
        return {"stories": [
            {"story": "1", "floor_area_m2": 9.1 * 7.28, "plan_polygons": [_rect(0, 0, 9.1, 7.28)]},
            {"story": "2", "floor_area_m2": 5.46 * 7.28, "plan_polygons": [_rect(0, 0, 5.46, 7.28)]},
        ]}

    def test_side_strips_use_lean_to_coefficient(self):
        summary = _summary([
            (1, 2.5, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),    # 1F Y, left strip: 2.5 x 728 = 1820 cm
            (2, 2.0, 1, 9.1, 0.0, 9.1, 3.64, 0.0, 3.0),    # 1F Y, right strip: 2.0 x 364 = 728 cm
        ], self._wq())
        # 平屋 value with the same spec: (1300+260+100)/1000 + 0.5*1.1042857 = 2.2121 kN/m2 -> 22.6 -> 23
        self.assertEqual(summary.seismic.single_story_lw_cm_m2, 23.0)
        check = [c for c in summary.balance.checks if c.story == "1" and c.direction == "y"][0]
        left, right = check.strips
        self.assertEqual((left.side, right.side), ("左", "右"))
        self.assertAlmostEqual(left.area_m2, 2.275 * 7.28)
        self.assertEqual(left.lw_basis, "2階建ての1階")
        self.assertEqual(left.lw_cm_m2, summary.seismic.stories[0].lw_cm_m2)
        self.assertEqual(right.lw_basis, "平屋")
        self.assertAlmostEqual(left.existing_cm, 1820.0)
        self.assertAlmostEqual(right.existing_cm, 728.0)
        self.assertAlmostEqual(right.fill_ratio, 728.0 / (2.275 * 7.28 * 23.0))
        self.assertEqual(check.status, "OK")

        check_2y = [c for c in summary.balance.checks if c.story == "2" and c.direction == "y"][0]
        self.assertEqual(check_2y.strips[0].lw_basis, "2階建ての2階")
        self.assertAlmostEqual(check_2y.strips[0].area_m2, 1.365 * 7.28)

    def test_wall_ratio_rule(self):
        # Right strip short of walls: fill < 1 and ratio < 0.5 -> NG
        ng = _summary([
            (1, 2.5, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),
            (2, 0.5, 1, 9.1, 0.0, 9.1, 3.64, 0.0, 3.0),
        ], self._wq())
        check = [c for c in ng.balance.checks if c.story == "1" and c.direction == "y"][0]
        self.assertLess(check.strips[1].fill_ratio, 1.0)
        self.assertLess(check.wall_ratio, 0.5)
        self.assertEqual(check.status, "NG")
        self.assertEqual(ng.overall_status, "NG")

        # Both strips below 1.0 but balanced (ratio >= 0.5) -> OK
        ok = _summary([
            (1, 0.5, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),   # 364 cm vs 46*16.56=761.8 -> 0.48
            (2, 0.5, 1, 9.1, 0.0, 9.1, 3.64, 0.0, 3.0),   # 182 cm vs 23*16.56=380.9 -> 0.48
        ], self._wq())
        check = [c for c in ok.balance.checks if c.story == "1" and c.direction == "y"][0]
        self.assertLess(check.strips[0].fill_ratio, 1.0)
        self.assertGreaterEqual(check.wall_ratio, 0.5)
        self.assertEqual(check.status, "OK")

    def test_walls_on_quarter_line_are_included(self):
        summary = _summary([(1, 2.0, 1, 2.275, 0.0, 2.275, 1.82, 0.0, 3.0)], self._wq())
        check = [c for c in summary.balance.checks if c.story == "1" and c.direction == "y"][0]
        self.assertEqual(check.strips[0].wall_refs, ("1",))

    def test_actual_multiplier_check_when_capped(self):
        summary = _summary([
            (1, 4.0, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),
            (2, 4.0, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0),   # same frame, 8.0 -> 7.0
            (3, 1.0, 1, 9.1, 0.0, 9.1, 7.28, 0.0, 3.0),
        ], self._wq())
        check = [c for c in summary.balance.checks if c.story == "1" and c.direction == "y"][0]
        self.assertTrue(check.actual_checked)
        self.assertAlmostEqual(check.strips[0].existing_cm, 7.0 * 728.0)
        self.assertAlmostEqual(check.strips[0].existing_actual_cm, 8.0 * 728.0)

    def test_quasi_walls_ignored_unless_over_half(self):
        quasi = [{"name": "Q1", "story": "1", "direction": "y", "length_m": 1.82, "type": "quasi",
                  "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.6,
                  "clear_height_m": 2.6, "x": 9.1, "y": 5.0}]
        wq = self._wq()
        wq["quasi_walls"] = quasi
        summary = _summary([(1, 2.5, 1, 0.0, 0.0, 0.0, 7.28, 0.0, 3.0)], wq)
        self.assertFalse(summary.balance.includes_quasi_walls)
        check = [c for c in summary.balance.checks if c.story == "1" and c.direction == "y"][0]
        self.assertEqual(check.strips[1].wall_refs, ())


class TestNValueRules(unittest.TestCase):

    def test_brace_corrections_table_3_14(self):
        self.assertEqual(brace_correction(None, None), 0.0)
        self.assertEqual(brace_correction(("90x90", "top"), None), 2.0)
        self.assertEqual(brace_correction(None, ("45x90", "bottom")), -0.5)
        self.assertEqual(brace_correction(("15x90", "top"), None), 0.0)
        self.assertEqual(brace_correction(("45x90", "x"), None), 0.0)
        self.assertEqual(brace_correction(("30x90", "top"), ("90x90", "top")), 2.5)
        self.assertEqual(brace_correction(("90x90", "top"), ("90x90", "top")), 4.0)
        self.assertEqual(brace_correction(("45x90", "bottom"), ("45x90", "bottom")), 0.0)
        self.assertEqual(brace_correction(("45x90", "top"), ("30x90", "bottom")), 0.5)
        self.assertEqual(brace_correction(("30x90", "bottom"), ("15x90", "top")), -0.5)
        self.assertEqual(brace_correction(("30x90", "top"), ("45x90", "bottom")), 0.0)
        self.assertEqual(brace_correction(("45x90", "x"), ("45x90", "top")), 0.5)
        self.assertEqual(brace_correction(("45x90", "x"), ("90x90", "bottom")), 0.0)
        self.assertEqual(brace_correction(("45x90", "x"), ("30x90", "x")), 0.0)

    def test_joint_selection_table_3_16(self):
        self.assertEqual(select_joint(-0.3), ("い", 0.0))
        self.assertEqual(select_joint(0.0), ("い", 0.0))
        self.assertEqual(select_joint(0.65), ("ろ", 3.4))
        self.assertEqual(select_joint(0.66), ("は", 5.1))
        self.assertEqual(select_joint(1.6), ("ほ", 8.5))
        self.assertEqual(select_joint(2.6), ("と", 15.0))
        self.assertEqual(select_joint(5.6), ("ぬ", 30.0))
        mark, kn = select_joint(6.0)
        self.assertEqual(mark, "要検討")
        self.assertAlmostEqual(kn, 31.8)

    def test_height_factor(self):
        self.assertEqual(height_factor(2.9), 1.0)
        self.assertEqual(height_factor(3.2), 1.0)
        self.assertAlmostEqual(height_factor(3.5), 3.5 / 2.7)


class TestNValueColumns(unittest.TestCase):

    def _cols(self, summary, story):
        return {(round(c.x, 3), round(c.y, 3)): c for c in summary.n_values.columns if c.story == story}

    def test_single_story_corner_and_middle_columns(self):
        wq = {"stories": [{"story": "1", "floor_area_m2": 3.64 * 3.64, "plan_polygons": [_rect(0, 0, 3.64, 3.64)]}]}
        summary = _summary([
            (1, 2.5, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0),
            (2, 2.5, 1, 0.0, 0.0, 0.0, 1.82, 0.0, 3.0),
        ], wq, stories=ONE_STORY)
        cols = self._cols(summary, "1")
        corner = cols[(0.0, 0.0)]
        self.assertTrue(corner.corner)
        self.assertAlmostEqual(corner.n, 2.5 * 0.8 - 0.4)   # 1.6
        self.assertEqual(corner.joint, "ほ")
        middle = cols[(1.82, 0.0)]
        self.assertFalse(middle.corner)
        self.assertAlmostEqual(middle.n, 2.5 * 0.5 - 0.6)   # 0.65
        self.assertEqual(middle.joint, "ろ")

    def test_single_brace_correction_by_end(self):
        wq = {
            "stories": [{"story": "1", "floor_area_m2": 3.64 * 3.64, "plan_polygons": [_rect(0, 0, 3.64, 3.64)]}],
            "walls": [{"wwll_id": 1, "kind": "brace", "brace_section": "45x90", "brace_layout": "single"}],
        }
        summary = _summary([(1, 2.0, 0, 0.0, 0.0, 0.91, 0.0, 0.0, 3.0)], wq, stories=ONE_STORY)
        cols = self._cols(summary, "1")
        top = cols[(0.91, 0.0)]       # brace runs N1 (0,0) foot -> N3 head above (0.91,0)
        self.assertAlmostEqual(top.directions[0].brace_correction, 0.5)
        self.assertAlmostEqual(top.n, (2.0 + 0.5) * 0.5 - 0.6)
        bottom = cols[(0.0, 0.0)]
        self.assertAlmostEqual(bottom.directions[0].brace_correction, -0.5)
        self.assertAlmostEqual(bottom.n, (2.0 - 0.5) * 0.8 - 0.4)
        self.assertEqual(bottom.joint, "は")

    def test_story_height_over_3_2m(self):
        stories = [{"name": "1", "elevation": 0.0, "height": 3.5}]
        wq = {"stories": [{"story": "1", "floor_area_m2": 3.64 * 3.64, "plan_polygons": [_rect(0, 0, 3.64, 3.64)]}]}
        summary = _summary([(1, 2.5, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.5)], wq, stories=stories)
        middle = self._cols(summary, "1")[(1.82, 0.0)]
        self.assertAlmostEqual(middle.n, 2.5 * 0.5 * 3.5 / 2.7 - 0.6)

    def test_two_story_lower_columns_include_upper_story(self):
        wq = {"stories": [
            {"story": "1", "floor_area_m2": 7.28 * 7.28, "plan_polygons": [_rect(0, 0, 7.28, 7.28)]},
            {"story": "2", "floor_area_m2": 7.28 * 7.28, "plan_polygons": [_rect(0, 0, 7.28, 7.28)]},
        ]}
        summary = _summary([
            (1, 2.5, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0),    # 1F X
            (2, 2.0, 0, 0.0, 0.0, 1.82, 0.0, 3.0, 5.86),   # 2F X, same line
            (3, 2.0, 0, 3.0, 0.0, 4.82, 0.0, 3.0, 5.86),   # 2F X only
        ], wq)
        up = self._cols(summary, "2")
        low = self._cols(summary, "1")
        self.assertAlmostEqual(up[(0.0, 0.0)].n, 2.0 * 0.8 - 0.4)                  # 1.2
        self.assertEqual(up[(0.0, 0.0)].joint, "に")
        c = low[(0.0, 0.0)]
        self.assertTrue(c.upper_story_above)
        self.assertEqual(c.formula, "lower")
        self.assertAlmostEqual(c.n, 2.5 * 0.8 + 2.0 * 0.8 - 1.0)                    # 2.6
        self.assertEqual(c.joint, "と")
        self.assertAlmostEqual(low[(1.82, 0.0)].n, 2.5 * 0.5 + 2.0 * 0.5 - 1.6)     # 0.65
        # 1F column below a 2F wall end without 1F walls
        self.assertAlmostEqual(low[(3.0, 0.0)].n, 2.0 * 0.5 - 1.6)
        self.assertEqual(low[(3.0, 0.0)].joint, "い")

    def test_quasi_walls_over_1_5_participate(self):
        wq = {
            # wind 30 m2 x 50 = 1500 cm required in Y, so the 600 cm of quasi walls stays below 1/2
            "stories": [{"story": "1", "floor_area_m2": 3.64 * 3.64, "wind_area_y_m2": 30.0,
                         "plan_polygons": [_rect(0, 0, 3.64, 3.64)]}],
            "quasi_walls": [
                {"name": "Q15", "story": "1", "direction": "y", "length_m": 1.82, "type": "quasi",
                 "material": "panel", "base_multiplier": 2.5, "material_height_m": 2.6,
                 "clear_height_m": 2.6, "x": 3.64, "y": 0.91},   # 1.5 -> ignored
                {"name": "Q18", "story": "1", "direction": "y", "length_m": 1.82, "type": "quasi",
                 "material": "panel", "base_multiplier": 3.0, "material_height_m": 2.6,
                 "clear_height_m": 2.6, "x": 3.64, "y": 2.73},   # 1.8 -> counted
            ],
        }
        summary = _summary([(1, 2.5, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0)], wq, stories=ONE_STORY)
        refs = set()
        for c in summary.n_values.columns:
            for d in c.directions:
                refs.update(d.wall_refs)
        self.assertIn("Q18", refs)
        self.assertNotIn("Q15", refs)

    def test_corner_fallback_and_override_without_plan(self):
        wq = {
            "stories": [{"story": "1", "floor_area_m2": 3.64 * 3.64}],
            "columns": [{"story": "1", "x": 1.82, "y": 0.0, "corner": True, "name": "C2"}],
        }
        summary = _summary([
            (1, 2.5, 0, 0.0, 0.0, 1.82, 0.0, 0.0, 3.0),
            (2, 2.5, 1, 0.0, 0.0, 0.0, 1.82, 0.0, 3.0),
        ], wq, stories=ONE_STORY)
        cols = self._cols(summary, "1")
        self.assertTrue(cols[(0.0, 0.0)].corner)
        self.assertEqual(cols[(0.0, 0.0)].corner_source, "walls")
        self.assertTrue(cols[(1.82, 0.0)].corner)
        self.assertEqual(cols[(1.82, 0.0)].corner_source, "override")
        self.assertEqual(cols[(1.82, 0.0)].name, "C2")
        self.assertFalse(cols[(0.0, 1.82)].corner)


if __name__ == "__main__":
    unittest.main()
