import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "kit", ".claude", "skills", "tl-analytics", "scripts"))
import an_stats  # noqa: E402


class WilsonAndVerdictTests(unittest.TestCase):
    # the reference table of statistics.md / ANALYST_DESIGN.md
    TABLE = [((0, 100), 0.0263, "INSUFFICIENT"), ((0, 133), 0.0199, "PASS"),
             ((5, 500), 0.0204, "INSUFFICIENT"), ((10, 1000), 0.0167, "PASS"),
             ((15, 1000), 0.0228, "INSUFFICIENT"), ((60, 5000), 0.0148, "PASS"),
             ((40, 1000), 0.0515, "FAIL")]

    def test_reference_table(self):
        for (k, n), upper, verdict in self.TABLE:
            with self.subTest(k=k, n=n):
                res = an_stats.verdict(k, n, 0.02)
                self.assertAlmostEqual(res["upper"], upper, places=4)
                self.assertEqual(res["verdict"], verdict)

    def test_edges(self):
        self.assertEqual(an_stats.verdict(0, 0, 0.02)["verdict"], "INSUFFICIENT")
        self.assertEqual(an_stats.wilson(5, 5)["upper"], 1.0)
        self.assertEqual(an_stats.wilson(0, 5)["lower"], 0.0)
        with self.assertRaises(ValueError):
            an_stats.wilson(6, 5)
        with self.assertRaises(ValueError):
            an_stats.wilson(-1, 5)

    def test_two_sided_is_wider(self):
        self.assertGreater(an_stats.wilson(10, 1000, two_sided=True)["upper"],
                           an_stats.wilson(10, 1000)["upper"])


class MinNTests(unittest.TestCase):
    def test_zero_errors(self):
        self.assertEqual(an_stats.min_n(0.02), 133)

    def test_monotone_in_expected_rate(self):
        self.assertLess(an_stats.min_n(0.02, 0.005), an_stats.min_n(0.02, 0.01))
        self.assertLess(an_stats.min_n(0.02, 0.01), an_stats.min_n(0.02, 0.015))

    def test_result_really_passes(self):
        n = an_stats.min_n(0.02, 0.01)
        self.assertLessEqual(an_stats.wilson(0.01 * n, n)["upper"], 0.02)
        self.assertGreater(an_stats.wilson(0.01 * (n - 1), n - 1)["upper"], 0.02)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            an_stats.min_n(0.02, 0.03)


class StabilityTests(unittest.TestCase):
    def test_bad_month_is_unstable(self):
        res = an_stats.stability([("a", 500, 2), ("b", 500, 25)], 0.02)
        self.assertEqual(res["unstable_periods"], ["b"])
        self.assertFalse(res["stable"])

    def test_small_noisy_month_is_only_watch(self):
        res = an_stats.stability([("a", 500, 2), ("b", 110, 3)], 0.02)
        self.assertEqual(res["watch_periods"], ["b"])
        self.assertTrue(res["stable"])

    def test_too_few_cases(self):
        res = an_stats.stability([("a", 10, 5)], 0.02)
        self.assertEqual(res["periods"][0]["flag"], "too few cases")

    def test_csv_input(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Period,N,K\n2026-04,500,2\n2026-05,500,25\n")
        try:
            self.assertEqual(an_stats.read_csv_rows(f.name), [("2026-04", 500, 2), ("2026-05", 500, 25)])
        finally:
            os.unlink(f.name)


class CompareTests(unittest.TestCase):
    def test_significant_and_not(self):
        self.assertTrue(an_stats.compare(60, 1000, 20, 1000)["significant"])
        self.assertFalse(an_stats.compare(20, 1000, 22, 1000)["significant"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = an_stats.main(list(args))
        return code, out.getvalue()

    def test_verdict_json(self):
        code, out = self.run_cli("verdict", "--k", "10", "--n", "1000", "--threshold", "0.02", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["verdict"], "PASS")

    def test_stability_rows(self):
        code, out = self.run_cli("stability", "--threshold", "0.02", "--rows", "a:500:2,b:500:25")
        self.assertEqual(code, 0)
        self.assertIn("UNSTABLE: b", out)

    def test_bad_input_returns_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self.run_cli("verdict", "--k", "5", "--n", "3", "--threshold", "0.02")
        self.assertEqual(code, 2)

    def test_selftest_passes(self):
        code, out = self.run_cli("--selftest")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
