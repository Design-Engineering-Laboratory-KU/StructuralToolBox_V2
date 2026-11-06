import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_checks import allowable_load_area_m2, build_wall_quantity_summary, required_column_size_mm
from stb_engine import parse_input
from stb_project import ProjectSchemaError, validate_project_dict
from stb_project.column_fc_table import lookup_column_fc

from tests.test_wall_quantity import _project


# 表計算ツール ver1.2 「表計算ツール入力例」 sheet: 2F/1F 2.81 m, 50.25 / 50.25 m2,
# スレート屋根, サイディング, 太陽光なし, 断熱材 初期値, 柱材 JAS目視等級 すぎ 二級.
EXAMPLE_STORIES = [
    {"name": "1", "elevation": 0.0, "height": 2.81},
    {"name": "2", "elevation": 2.81, "height": 2.81},
]
SUGI_2 = {"jas": "JAS目視等級区分構造用製材", "species": "すぎ", "grade": "二級"}


def _example(column_size=None, lines=None):
    wq = {
        "seismic": {"roof": "slate", "exterior_wall": "siding"},
        "stories": [{"story": "1", "floor_area_m2": 50.25}, {"story": "2", "floor_area_m2": 50.25}],
    }
    if column_size is not None:
        wq["column_size"] = column_size
    project = validate_project_dict(_project(wq, stories=EXAMPLE_STORIES))
    return build_wall_quantity_summary(parse_input(lines or []), project)


class TestColumnSizeAgainstToolExample(unittest.TestCase):

    def test_required_wall_and_column_loads(self):
        summary = _example()
        self.assertEqual([s.lw_cm_m2 for s in summary.seismic.stories], [40.0, 22.0])
        req = {r.story: r for r in summary.column_size.stories}
        self.assertAlmostEqual(req["2"].outer_load_kN_m2, 1.6203571, places=6)   # T39
        self.assertAlmostEqual(req["2"].inner_load_kN_m2, 1.2003571, places=6)   # U39
        self.assertAlmostEqual(req["1"].outer_load_kN_m2, 4.5710714, places=6)   # T40
        self.assertAlmostEqual(req["1"].inner_load_kN_m2, 3.3110714, places=6)   # U40
        self.assertEqual(req["2"].length_mm, 2705.0)
        self.assertEqual(req["1"].length_mm, 2690.0)

    def test_method_2_1_default_sugi(self):
        req = {r.story: r for r in _example().column_size.stories}
        self.assertEqual(req["2"].required_mm, 78.0)
        self.assertEqual(req["2"].required_ratio_text, "1/34.6")
        self.assertEqual(req["1"].required_mm, 100.0)
        self.assertEqual(req["1"].required_ratio_text, "1/26.9")
        self.assertEqual(req["1"].material_label, "無等級材 すぎ")

    def test_method_2_2_selected_species(self):
        summary = _example({"stories": [dict(SUGI_2, story="1"), dict(SUGI_2, story="2")]})
        req = {r.story: r for r in summary.column_size.stories}
        self.assertAlmostEqual(req["1"].fc_n_mm2, 20.4)
        self.assertEqual(req["2"].required_mm, 76.0)
        self.assertEqual(req["1"].required_mm, 97.0)
        self.assertEqual(req["1"].default_required_mm, 100.0)

    def test_method_2_3_allowable_areas(self):
        summary = _example({"stories": [dict(SUGI_2, story="1"), dict(SUGI_2, story="2")]})
        req = {r.story: r for r in summary.column_size.stories}
        areas = {(r.story, a["size_mm"], a["location"]): a["allowable_m2"]
                 for r in req.values() for a in r.allowable_areas}
        expected = {
            ("2", 105.0, "outer"): 20.7, ("2", 120.0, "outer"): 34.5,
            ("2", 105.0, "inner"): 28.0, ("2", 120.0, "inner"): 46.6,
            ("1", 105.0, "outer"): 7.4, ("1", 120.0, "outer"): 12.3,
            ("1", 105.0, "inner"): 10.3, ("1", 120.0, "inner"): 17.0,
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertAlmostEqual(areas[key], value)


class TestColumnSizeChecks(unittest.TestCase):

    def test_model_columns_are_checked_per_story(self):
        lines = [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "SECT, 1, C105, 1, 0, 105, 105",
            "SECT, 2, C90, 1, 0, 90, 90",
            "SECT, 3, B120, 1, 0, 120, 240",
            "NODE, 1, 0, 0, 0", "NODE, 2, 0, 0, 2.81", "NODE, 3, 0, 0, 5.62",
            "NODE, 4, 3.64, 0, 2.81",
            "ELEM, 1, 1, 2, 1, 0",   # 1F column 105: required 100 -> OK
            "ELEM, 2, 2, 3, 2, 0",   # 2F column 90: required 78 -> OK
            "ELEM, 3, 2, 4, 3, 0",   # beam: ignored
        ]
        summary = _example(lines=lines)
        checks = {(c.story, c.section): c for c in summary.column_size.model_columns}
        self.assertEqual(set(checks), {("1", "C105"), ("2", "C90")})
        self.assertEqual(checks[("1", "C105")].status, "OK")
        self.assertEqual(checks[("1", "C105")].element_ids, (1,))
        self.assertEqual(summary.column_size.status, "OK")

        # 1F column 90 < 100 -> NG
        lines_ng = ["ELEM, 1, 1, 2, 2, 0" if l.startswith("ELEM, 1,") else l for l in lines]
        summary_ng = _example(lines=lines_ng)
        check = [c for c in summary_ng.column_size.model_columns if c.story == "1"][0]
        self.assertEqual(check.status, "NG")
        self.assertEqual(summary_ng.column_size.status, "NG")
        self.assertEqual(summary_ng.overall_status, "NG")

    def test_tributary_area_checks(self):
        summary = _example({
            "stories": [dict(SUGI_2, story="1"), dict(SUGI_2, story="2")],
            "tributary_checks": [
                {"name": "C1", "story": "1", "location": "outer", "b_mm": 105, "d_mm": 105, "area_m2": 7.0},
                {"name": "C2", "story": "1", "location": "inner", "b_mm": 105, "d_mm": 105, "area_m2": 10.5},
            ],
        })
        checks = {c.name: c for c in summary.column_size.tributary_checks}
        self.assertEqual(checks["C1"].status, "OK")
        self.assertAlmostEqual(checks["C2"].allowable_m2, 10.3)
        self.assertEqual(checks["C2"].status, "NG")

    def test_formulas_and_slenderness_limit(self):
        self.assertEqual(required_column_size_mm(1.6203571, 2705.0, 17.7), 78.0)
        self.assertIsNone(allowable_load_area_m2(60.0, 60.0, 1.0, 2705.0, 17.7))   # 2705/60 > 43.3
        self.assertAlmostEqual(allowable_load_area_m2(105.0, 105.0, 1.6203571, 2705.0, 20.4), 20.7)

    def test_direct_method_requires_column_loads(self):
        wq = {
            "seismic": {"method": "direct"},
            "stories": [{"story": "1", "floor_area_m2": 50.0, "weight_kN": 200.0}],
        }
        stories = [{"name": "1", "elevation": 0.0, "height": 2.9}]
        summary = build_wall_quantity_summary(parse_input([]), validate_project_dict(_project(wq, stories=stories)))
        self.assertIsNone(summary.column_size)
        self.assertTrue(any("Wd" in w for w in summary.warnings))

        wq["column_size"] = {"stories": [{"story": "1", "outer_load_kN_m2": 1.6, "inner_load_kN_m2": 1.2}]}
        summary = build_wall_quantity_summary(parse_input([]), validate_project_dict(_project(wq, stories=stories)))
        self.assertEqual(summary.column_size.stories[0].length_mm, 2900.0 - 105.0)

    def test_fc_table_and_schema(self):
        self.assertAlmostEqual(lookup_column_fc("無等級材", "すぎ", ""), 17.7)
        self.assertAlmostEqual(lookup_column_fc("JAS同一等級構成集成材", "", "E105-F300(3層)"), 25.5)
        self.assertAlmostEqual(lookup_column_fc("JAS機械等級区分構造用製材", "ひのき", "E90"), 24.6)
        with self.assertRaises(ProjectSchemaError):
            _example({"stories": [{"story": "1", "jas": "無等級材", "species": "まつ"}]})
        project = validate_project_dict(_project({
            "seismic": {"roof": "slate", "exterior_wall": "siding"},
            "stories": [{"story": "1", "floor_area_m2": 50.25}, {"story": "2", "floor_area_m2": 50.25}],
            "column_size": {"stories": [dict(SUGI_2, story="1", length_mm=2700.0)],
                            "tributary_checks": [{"story": "1", "location": "inner", "b_mm": 105,
                                                  "d_mm": 105, "area_m2": 5.0}]},
        }, stories=EXAMPLE_STORIES))
        again = validate_project_dict(project.to_dict())
        self.assertEqual(again.wall_quantity.column_size, project.wall_quantity.column_size)


if __name__ == "__main__":
    unittest.main()
