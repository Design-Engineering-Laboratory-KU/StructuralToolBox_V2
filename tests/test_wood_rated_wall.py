import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLASSES_DIR = os.path.join(_STB_ROOT, "classes")
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if _CLASSES_DIR not in sys.path:
    sys.path.insert(0, _CLASSES_DIR)

from classes.nd import Nd
from classes.wood_wall import order_wwll_corner_node_ids, wwll_length_height_from_nodes
from stb_checks import build_wood_check_summary
from stb_engine import parse_input, run_from_lines
from stb_engine.errors import StbParseError
from stb_project import validate_project_dict


class TestWoodRatedWall(unittest.TestCase):

    def _base_lines(self):
        return [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "SECT, 1, C120, 1, 0, 120, 120",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1.82, 0, 0",
            "NODE, 3, 1.82, 0, 2.73",
            "NODE, 4, 0, 0, 2.73",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 1, 1, 1, 1, 1, 1",
        ]

    def test_equivalent_brace_generation_from_multiplier(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)

        self.assertEqual(len(mdl.wwalls), 1)
        w = mdl.wwalls[0]
        self.assertAlmostEqual(w.qa_kN, 1.96 * 2.0 * 1.82, places=6)
        self.assertAlmostEqual(w.delta, 0.0083333333 * 2.73, places=8)
        self.assertTrue(w.k_n_per_m > 0.0)
        self.assertEqual(len(w.generated_elem_ids), 2)  # X brace pair
        generated = [e for e in mdl.elms if getattr(e, "generated_from", "") == "WOOD_RATED_WALL"]
        self.assertEqual(len(generated), 2)

    def test_shear_panel_generates_panel_stiffness(self):
        lines = self._base_lines() + [
            "WWLL, 2, W2, 1, 1.5, 1.82, 2.73, 1, 0.01, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        w = mdl.wwalls[0]
        self.assertEqual(w.model_requested, "SHEAR_PANEL")
        self.assertEqual(w.model_active, "SHEAR_PANEL")
        self.assertEqual(len(w.generated_elem_ids), 0)
        self.assertEqual(len(w.generated_shear_panel_ids), 1)
        self.assertEqual(len(mdl.wshears), 1)
        self.assertTrue(mdl.wshears[0].k > 0.0)

    def test_order_wwll_corner_node_ids_ccw_rectangle(self):
        by_id = {n.id: n for n in [
            Nd(1, 0.0, 0.0, 0.0),
            Nd(2, 1.82, 0.0, 0.0),
            Nd(3, 1.82, 0.0, 2.73),
            Nd(4, 0.0, 0.0, 2.73),
        ]}
        n1, n2, n3, n4, direction = order_wwll_corner_node_ids([4, 3, 2, 1], by_id)
        self.assertEqual((n1, n2, n3, n4), (1, 2, 3, 4))
        self.assertEqual(direction, 0)

    def test_swapped_top_corners_normalized_on_parse_for_brace(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 1, 2, 4, 3, , 1",
        ]
        mdl = parse_input(lines)
        w = mdl.wwalls[0]
        self.assertEqual((w.n1, w.n2, w.n3, w.n4), (1, 2, 3, 4))
        generated = [e for e in mdl.elms if getattr(e, "generated_from", "") == "WOOD_RATED_WALL"]
        self.assertEqual(len(generated), 2)
        pairs = {(e.n0.id, e.n1.id) for e in generated}
        self.assertIn((1, 3), pairs)
        self.assertIn((2, 4), pairs)

    def test_length_height_from_nodes_supports_diagonal_corner_order(self):
        # UK-style ordering: N1/N2 left edge, N3/N4 right edge.
        n0 = Nd(0, 0.0, 7.795, 0.3)
        n1 = Nd(1, 0.0, 7.795, 3.035)
        n2 = Nd(2, 0.0, 6.885, 0.3)
        n3 = Nd(3, 0.0, 6.885, 3.035)
        length, height = wwll_length_height_from_nodes(n0, n1, n3, n2)
        self.assertAlmostEqual(length, 0.91, places=6)
        self.assertAlmostEqual(height, 2.735, places=6)

    def test_omitted_length_height_derived_from_nodes(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, , , 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        w = mdl.wwalls[0]
        self.assertAlmostEqual(w.length, 1.82, places=6)
        self.assertAlmostEqual(w.height, 2.73, places=6)
        self.assertAlmostEqual(w.length_from_nodes, 1.82, places=6)
        self.assertAlmostEqual(w.height_from_nodes, 2.73, places=6)
        self.assertEqual(mdl.input_warnings, [])

    def test_explicit_length_height_matching_nodes_has_no_warning(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        self.assertEqual(mdl.input_warnings, [])

    def test_explicit_length_height_mismatch_emits_warning(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, 2.00, 2.73, 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        w = mdl.wwalls[0]
        self.assertAlmostEqual(w.length, 2.00, places=6)
        self.assertAlmostEqual(w.height, 2.73, places=6)
        self.assertEqual(len(mdl.input_warnings), 1)
        self.assertIn("input L=", mdl.input_warnings[0])
        self.assertIn("using input value", mdl.input_warnings[0])

    def test_partial_omit_height_derived_from_nodes(self):
        lines = self._base_lines() + [
            "WWLL, 1, W1, 0, 2.0, 1.82, , 0, 0.0083333333, 1, 2, 3, 4, , 1",
        ]
        mdl = parse_input(lines)
        w = mdl.wwalls[0]
        self.assertAlmostEqual(w.length, 1.82, places=6)
        self.assertAlmostEqual(w.height, 2.73, places=6)
        self.assertEqual(mdl.input_warnings, [])

    def test_omitted_length_height_without_nodes_raises(self):
        lines = [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "WWLL, 1, W1, 0, 2.0, , , 0, 0.0083333333, , , , , , 1",
        ]
        with self.assertRaises(StbParseError):
            parse_input(lines)

    def test_membrane_wall_is_reserved(self):
        lines = self._base_lines() + [
            "WWLL, 3, W3, 2, 1.5, 1.82, 2.73, 0, 0.01, 1, 2, 3, 4, , 1",
        ]
        with self.assertRaises(StbParseError):
            parse_input(lines)

    def _project_for_checks(self):
        return validate_project_dict({
            "schema": 1,
            "model": {"dat": "dummy.dat"},
            "building": {
                "name": "WallCheck",
                "location": "",
                "use": "",
                "structure": "wood",
                "calculation_route": "",
                "designer": {"name": "", "qualification": "", "license_number": "", "contact": ""},
            },
            "grids": [
                {"name": "X1", "direction": "x", "coordinate": 0.0},
                {"name": "Y1", "direction": "y", "coordinate": 0.0},
            ],
            "stories": [{"name": "1", "elevation": 0.0, "height": 2.73}],
            "member_classes": [
                {"name": "dummy", "kind": "column", "element_ids": [], "story": "1", "use": "", "notes": ""},
            ],
            "design_checks": {
                "wood": {
                    "enabled": True,
                    "load_cases": [1],
                    "deflection_limit_ratio": 250.0,
                    "allowable_stresses": {"bending": 8.0, "shear": 0.8, "compression": 6.0, "tension": 4.0},
                },
            },
            "report": {"title": "t", "mode": "practice", "language": "ja", "format": "markdown", "include_manual_items": True, "include_warnings": True},
        })

    def test_wall_capacity_check_outputs_wall_level_metrics_equivalent_brace(self):
        lines = [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "SECT, 1, C120, 1, 0, 120, 120",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 1.82, 0, 0",
            "NODE, 3, 1.82, 0, 2.73",
            "NODE, 4, 0, 0, 2.73",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 1, 1, 1, 1, 1, 1",
            "CONS, 3, 0, 1, 1, 1, 1, 1",
            "CONS, 4, 0, 1, 1, 1, 1, 1",
            "WWLL, 1, W1, 0, 2.0, 1.82, 2.73, 0, 0.0083333333, 1, 2, 3, 4, , 1",
            "PLOD, 3, 1, 1.0, 0, 0, 0, 0, 0",
            "PLOD, 4, 1, 1.0, 0, 0, 0, 0, 0",
        ]
        mdl, _txt = run_from_lines(lines)
        summary = build_wood_check_summary(mdl, self._project_for_checks())
        self.assertEqual(len(summary.wall_checks), 1)
        wc = summary.wall_checks[0]
        self.assertEqual(wc.wall_id, 1)
        self.assertEqual(wc.wall_name, "W1")
        self.assertEqual(wc.direction, "X")
        self.assertTrue(wc.allowable_shear_capacity_Qa > 0.0)
        self.assertTrue(wc.analysis_shear_force_Q > 0.0)
        self.assertTrue(wc.utilization_ratio > 0.0)

    def test_wall_capacity_check_outputs_wall_level_metrics_shear_panel(self):
        lines = [
            "MATE, 1, SUGI, 9500, 633, 5.0, 3.0e-06, 20",
            "NODE, 1, 0, 0, 0",
            "NODE, 2, 0, 1.82, 0",
            "NODE, 3, 0, 1.82, 2.73",
            "NODE, 4, 0, 0, 2.73",
            "CONS, 1, 1, 1, 1, 1, 1, 1",
            "CONS, 2, 1, 1, 1, 1, 1, 1",
            "CONS, 3, 1, 0, 1, 1, 1, 1",
            "CONS, 4, 1, 1, 1, 1, 1, 1",
            "WWLL, 2, W2, 1, 1.5, 1.82, 2.73, 1, 0.01, 1, 2, 3, 4, , 1",
            "PLOD, 3, 1, 0, 1.0, 0, 0, 0, 0",
        ]
        mdl, _txt = run_from_lines(lines)
        summary = build_wood_check_summary(mdl, self._project_for_checks())
        self.assertEqual(len(summary.wall_checks), 1)
        wc = summary.wall_checks[0]
        self.assertEqual(wc.wall_id, 2)
        self.assertEqual(wc.direction, "Y")
        self.assertTrue(wc.analysis_shear_force_Q > 0.0)


if __name__ == "__main__":
    unittest.main()
