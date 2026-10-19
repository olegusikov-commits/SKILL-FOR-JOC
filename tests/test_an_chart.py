import io
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kit", ".claude", "skills", "tl-analytics", "scripts"))
import an_chart  # noqa: E402

CSV = "month,auto,after,lo,hi\n2026-04,7.9,14.1,13.2,15.0\n2026-05,8.1,15.2,14.1,16.0\n2026-06,\"7,8\",14.9,14.0,15.8\n"


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.csv = os.path.join(self.tmp, "share.csv")
        with open(self.csv, "w", encoding="utf-8") as f:
            f.write(CSV)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_tool(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = an_chart.main(list(argv))
        return code, out.getvalue() + err.getvalue()

    def parse(self, path):
        return ET.parse(path).getroot()

    def test_bar(self):
        code, out = self.run_tool("bar", self.csv, "--x", "month", "--y", "auto", "--unit", "%",
                                  "--title", "Доля авто", "--target", "10")
        self.assertEqual(code, 0, out)
        svg = self.parse(os.path.join(self.tmp, "share.svg"))
        ns = "{http://www.w3.org/2000/svg}"
        bars = [r for r in svg.iter(ns + "rect") if r.find(ns + "title") is not None]
        self.assertEqual(len(bars), 3)
        text = ET.tostring(svg, encoding="unicode")
        self.assertIn("7.8%", text)            # "7,8" read as a decimal comma
        self.assertIn("prefers-color-scheme: dark", text)
        self.assertIn('class="tgt"', text)

    def test_line_with_band(self):
        out_svg = os.path.join(self.tmp, "x.svg")
        code, _ = self.run_tool("line", self.csv, "--x", "month", "--y", "auto,after", "--lo", "lo", "--hi", "hi",
                                "--out", out_svg)
        self.assertEqual(code, 0)
        text = open(out_svg, encoding="utf-8").read()
        self.assertEqual(text.count("<polyline"), 2)
        self.assertIn('class="band"', text)
        self.parse(out_svg)

    def test_missing_column(self):
        code, out = self.run_tool("bar", self.csv, "--x", "month", "--y", "nope")
        self.assertEqual(code, 2)
        self.assertIn("columns not in the CSV: nope", out)


if __name__ == "__main__":
    unittest.main()
