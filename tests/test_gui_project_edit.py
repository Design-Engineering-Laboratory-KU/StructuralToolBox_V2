import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)

from stb_project import load_project_file, validate_project_dict
from stb_gui.project_edit import build_project_edit_form
from stb_gui.project_view import (
    build_new_project_template_view,
    default_project_dict_for_dat,
)


class TestProjectEditForm(unittest.TestCase):

    def test_build_edit_form_includes_seismic_fields(self):
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "practice_wood_single_story.project.json")
        )
        form = build_project_edit_form(project)
        load_section = next(s for s in form["sections"] if s["id"] == "load_conditions")
        paths = [f["path"] for f in load_section["fields"]]
        self.assertIn("load_conditions.seismic.ci", paths)
        self.assertIn("load_conditions.seismic.rt", paths)
        self.assertIn("table", load_section)
        self.assertEqual(load_section["table"]["path"], "load_conditions.diaphragms")
        directions_section = next(s for s in form["sections"] if s["id"] == "seismic_directions")
        self.assertEqual(directions_section["table"]["path"], "load_conditions.seismic.directions")
        direction_columns = [c["path"] for c in directions_section["table"]["columns"]]
        self.assertEqual(direction_columns, ["name", "axis", "load_case", "sign"])
        weight_lc_section = next(s for s in form["sections"] if s["id"] == "seismic_weight_load_cases")
        self.assertEqual(weight_lc_section["table"]["path"], "load_conditions.seismic.weight_load_cases")
        weight_lc_columns = [c["path"] for c in weight_lc_section["table"]["columns"]]
        self.assertEqual(weight_lc_columns, ["load_case", "name", "factor", "role"])
        floor_section = next(s for s in form["sections"] if s["id"] == "floor_loads")
        self.assertEqual(floor_section["table"]["path"], "load_conditions.floor_loads")
        floor_columns = [c["path"] for c in floor_section["table"]["columns"]]
        self.assertEqual(
            floor_columns,
            ["diaphragm_id", "story", "role", "load_case", "name", "pressure_kN_m2"],
        )
        masses_section = next(s for s in form["sections"] if s["id"] == "seismic_masses")
        self.assertEqual(masses_section["table"]["path"], "load_conditions.seismic_masses")
        mass_columns = [c["path"] for c in masses_section["table"]["columns"]]
        self.assertIn("mass_role", mass_columns)
        self.assertIn("application_diaphragm", mass_columns)

    def test_default_project_template_for_missing_sidecar(self):
        raw = default_project_dict_for_dat("data/UK_240416panel.dat")
        project = validate_project_dict(raw)
        self.assertEqual(project.dat_path, "UK_240416panel.dat")
        self.assertEqual(project.building.name, "UK_240416panel")

        view = build_new_project_template_view("data/UK_240416panel.dat")
        self.assertFalse(view["found"])
        self.assertTrue(view["draft"])
        self.assertIn("edit", view)
        self.assertGreater(len(view["edit"]["sections"]), 0)

    def test_wall_quantity_settings_are_in_edit_form(self):
        project = load_project_file(
            os.path.join(_STB_ROOT, "data", "sample_wall_quantity_2f.project.json")
        )
        form = build_project_edit_form(project)
        by_id = {section["id"]: section for section in form["sections"]}

        settings = by_id["wall_quantity"]
        field_paths = [field["path"] for field in settings["fields"]]
        self.assertIn("wall_quantity.seismic.method", field_paths)
        self.assertIn("wall_quantity.wind.coefficient_cm_m2", field_paths)
        self.assertIn("wall_quantity.column_size.enabled", field_paths)

        stories = by_id["wall_quantity_stories"]["table"]
        self.assertEqual(stories["path"], "wall_quantity.stories")
        self.assertEqual(len(stories["rows"]), 2)
        self.assertIn("plan_polygons", [column["path"] for column in stories["columns"]])

        walls = by_id["wall_quantity_walls"]["table"]
        self.assertEqual(walls["path"], "wall_quantity.walls")
        self.assertGreater(len(walls["rows"]), 0)
        self.assertIn("brace_section", [column["path"] for column in walls["columns"]])

        self.assertIn("wall_quantity_quasi_walls", by_id)
        self.assertIn("wall_quantity_column_stories", by_id)
        self.assertIn("wall_quantity_tributary_checks", by_id)


if __name__ == "__main__":
    unittest.main()
