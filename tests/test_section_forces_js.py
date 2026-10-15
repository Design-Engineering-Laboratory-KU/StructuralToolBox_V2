import json
import os
import shutil
import subprocess
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stb_engine import run_from_lines
from stb_gui.model_json import mdl_to_dict


NODE = shutil.which("node")
HEAD = [
    "MATE,1,STEEL,205000,79000,0,0,235",
    "SECT,1,H,1,2,300,150,6.5,9",
]
NODE_SCRIPT = r"""
import { sectionForceAt } from "./stb_gui/static/section_forces.js";
let text = "";
for await (const chunk of process.stdin) text += chunk;
const rows = JSON.parse(text).map(({ f, len, segs }) => ({
  mid: sectionForceAt(f, len, segs, 0.5),
  end: sectionForceAt(f, len, segs, 1),
}));
process.stdout.write(JSON.stringify(rows));
"""


@unittest.skipIf(NODE is None, "node is not installed")
class TestSectionForcesJs(unittest.TestCase):

    def test_node_unit_tests(self):
        proc = subprocess.run(
            [NODE, "--test"],
            cwd=os.path.join(ROOT, "tests", "js"),
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_python_models_close_at_mid_and_end(self):
        geometries = [
            ("horizontal", (0, 0, 0), (6, 0, 0), 0),
            ("sloped", (0, 0, 0), (4, 3, 2), 20),
            ("column_up", (0, 0, 0), (0, 0, 4), 25),
            ("column_down", (0, 0, 4), (0, 0, 0), -15),
        ]
        payload = []
        expected = []
        for name, p0, p1, beta in geometries:
            lines = HEAD + [
                "NODE,1,%g,%g,%g" % p0,
                "NODE,2,%g,%g,%g" % p1,
                "ELEM,1,1,2,1,%g" % beta,
                "CONS,1,1,1,1,1,1,1",
                "CONS,2,1,1,1,1,1,1",
                "ELOD,1,0,0,2,-6,3,1,-2,5,0.2,0.65",
                "ELOD,1,1,1,4,5,-2,1,0,7,0.35,0.9",
            ]
            mdl, _ = run_from_lines(lines)
            elem = mdl_to_dict(mdl, solved=True)["elements"][0]
            for lc in ("0", "1"):
                f = elem["forces"][lc]
                payload.append({
                    "f": f,
                    "len": elem["len"],
                    "segs": elem["wsegs"][lc],
                })
                expected.append((name, lc, f))

        proc = subprocess.run(
            [NODE, "--input-type=module", "-e", NODE_SCRIPT],
            cwd=ROOT,
            input=json.dumps(payload),
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        actual = json.loads(proc.stdout)
        for row, (name, lc, f) in zip(actual, expected):
            with self.subTest(member=name, lc=lc, station="mid"):
                self._assert_close(row["mid"]["My"], f[12])
                self._assert_close(row["mid"]["Mz"], f[13])
            with self.subTest(member=name, lc=lc, station="end"):
                for key, index in (("N", 6), ("Qy", 7), ("Qz", 8), ("My", 10), ("Mz", 11)):
                    self._assert_close(row["end"][key], f[index])

    def _assert_close(self, actual, expected):
        self.assertLessEqual(
            abs(actual - expected),
            1e-6 * max(1.0, abs(expected)),
            "%r != %r" % (actual, expected),
        )


if __name__ == "__main__":
    unittest.main()
