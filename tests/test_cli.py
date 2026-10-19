import os
import sys
import json
import shutil
import subprocess
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_stb(args):
    cmd = [sys.executable, "-m", "stb_cli"] + args
    return subprocess.run(
        cmd,
        cwd=_STB_ROOT,
        capture_output=True,
        text=True,
    )


def _data_path(name):
    return os.path.join(_STB_ROOT, "data", name)


class TestStbCli(unittest.TestCase):

    def test_version(self):
        r = _run_stb(["version"])
        self.assertEqual(r.returncode, 0)
        from stb_engine.version import __version__

        self.assertTrue("stb " + __version__ in r.stdout)

    def test_validate_input01(self):
        r = _run_stb(["validate", _data_path("input01.dat"), "-v"])
        self.assertEqual(r.returncode, 0)
        self.assertTrue("nodes:" in r.stdout)

    def test_validate_missing_file(self):
        r = _run_stb(["validate", "data/no_such_file.dat"])
        self.assertEqual(r.returncode, 1)
        self.assertTrue("not found" in r.stderr)

    def test_solve_input01_to_file(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        out_path = os.path.join(out_dir, "cli.out")

        r = _run_stb([
            "solve",
            _data_path("input01.dat"),
            "-o",
            out_path,
            "-q",
            "-v",
        ])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(os.path.isfile(out_path))
        f = open(out_path, "r")
        txt = f.read()
        f.close()
        self.assertTrue("NDSP" in txt)

    def test_solve_project_json_applies_load_combinations(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        project_path = os.path.join(out_dir, "cli_combo.project.json")
        out_path = os.path.join(out_dir, "cli_combo.out")
        project = {
            "schema": 1,
            "model": {"dat": "cli_combo.dat"},
            "building": {"name": "CLI combo", "designer": {}},
            "grids": [],
            "stories": [],
            "member_classes": [],
            "load_conditions": {
                "load_combinations": [
                    {
                        "load_case": 10,
                        "name": "PX2",
                        "duration": "LONG_TERM",
                        "factors": [2.0],
                        "load_cases": [0],
                    }
                ]
            },
            "report": {},
        }
        shutil.copyfile(_data_path("input01.dat"), os.path.join(out_dir, "cli_combo.dat"))
        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(project, f)

        r = _run_stb(["solve", project_path, "-o", out_path, "-q", "-v"])

        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("LCMB->dat:  1", r.stdout)
        with open(os.path.join(out_dir, "cli_combo.dat"), "r", encoding="utf-8") as f:
            dat_text = f.read()
        self.assertIn("LCMB,", dat_text)
        self.assertIn("PX2", dat_text)
        with open(out_path, "r", encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("NDSP", txt)
        self.assertIn("    10,", txt)

        r = _run_stb(["solve", os.path.join(out_dir, "cli_combo.dat"), "-o", out_path, "-q"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

    def test_loads_combinations_write_dat(self):
        out_dir = os.path.join(_STB_ROOT, "tests", "_tmp_out")
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        dat_path = os.path.join(out_dir, "cli_lcmb.dat")
        project_path = os.path.join(out_dir, "cli_lcmb.project.json")
        shutil.copyfile(_data_path("input01.dat"), dat_path)
        project = {
            "schema": 1,
            "model": {"dat": "cli_lcmb.dat"},
            "building": {"name": "CLI LCMB", "designer": {}},
            "grids": [],
            "stories": [],
            "member_classes": [],
            "load_conditions": {
                "load_combinations": [
                    {
                        "load_case": 11,
                        "name": "PX3",
                        "duration": "SHORT_TERM",
                        "factors": [3.0],
                        "load_cases": [0],
                    }
                ]
            },
            "report": {},
        }
        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(project, f)

        r = _run_stb(["loads", "combinations", "--project", project_path, "--write-dat", "-v"])

        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("LCMB records: 1", r.stdout)
        with open(dat_path, "r", encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("LCMB,", txt)
        self.assertIn("PX3", txt)
        self.assertIn("LCMB_DURATION, 11, SHORT_TERM", txt)

    def test_solve_invalid_input(self):
        r = _run_stb(["solve", _data_path("input01.dat") + ".missing", "-q"])
        self.assertEqual(r.returncode, 1)

    def test_solve_parse_error(self):
        bad = os.path.join(_STB_ROOT, "tests", "_tmp_out", "bad_elem.dat")
        out_dir = os.path.dirname(bad)
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        f = open(bad, "w")
        f.write("ELEM,0,1,2,0\n")
        f.close()

        r = _run_stb(["solve", bad, "-q"])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
