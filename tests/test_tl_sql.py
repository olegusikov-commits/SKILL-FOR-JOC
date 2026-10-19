import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kit", ".claude", "tech-lead-kit", "scripts"))
import tl_sql  # noqa: E402

SCHEMA = {"tables": {
    "dbo.Orders": {"rows": 5_000_000, "stats_date": "2026-10-01",
                   "columns": [{"name": "order_id", "type": "int", "nullable": False},
                               {"name": "created_at", "type": "datetime2", "nullable": False},
                               {"name": "branch_id", "type": "int", "nullable": False},
                               {"name": "status", "type": "varchar(10)", "nullable": True}],
                   "indexes": [{"name": "IX_Orders_created", "columns": ["created_at", "branch_id"]}]},
    "dbo.OrderLines": {"rows": 20_000_000, "columns": [{"name": "order_id", "type": "int"}],
                       "indexes": [{"name": "IX_Lines_order", "columns": ["order_id"]}]},
    "dbo.Branches": {"rows": 40, "columns": [{"name": "branch_id", "type": "int"}], "indexes": []}},
    "fks": [{"from": "dbo.OrderLines.order_id", "to": "dbo.Orders.order_id"},
            {"from": "dbo.Orders.branch_id", "to": "dbo.Branches.branch_id"}]}


def levels(findings, level):
    return " | ".join(msg for lvl, msg in findings if lvl == level)


class CheckTests(unittest.TestCase):
    def test_writes_refused_on_prod_allowed_on_writable_test(self):
        for sql in ("DELETE FROM dbo.Orders WHERE order_id = 1", "EXEC dbo.Recalc",
                    "SELECT order_id INTO #t FROM dbo.Orders", "UPDATE dbo.Orders SET status = 'X'",
                    "TRUNCATE TABLE dbo.Orders"):
            with self.subTest(sql=sql):
                self.assertTrue(levels(tl_sql.check(sql, "sqlserver", "PROD"), "ERROR"))
        self.assertFalse(levels(tl_sql.check("UPDATE dbo.Orders SET status = 'X' WHERE order_id = 1",
                                             "sqlserver", "TEST", read_only=False), "ERROR"))

    def test_words_in_strings_and_comments_and_columns_are_not_writes(self):
        sql = ("-- delete later\nSELECT TOP (10) created_at, status FROM dbo.Orders "
               "WHERE status = 'DELETE' /* update */")
        self.assertEqual(levels(tl_sql.check(sql, "sqlserver", "PROD"), "ERROR"), "")

    def test_guard_set_options_are_allowed(self):
        sql = tl_sql.guard("SELECT COUNT(*) FROM dbo.Orders", "sqlserver")
        self.assertEqual(levels(tl_sql.check(sql, "sqlserver", "PROD"), "ERROR"), "")
        self.assertIn("SET LOCK_TIMEOUT 5000;", sql)
        self.assertIn("QUERY_GOVERNOR_COST_LIMIT", sql)

    def test_quality_warnings(self):
        warns = levels(tl_sql.check("SELECT * FROM dbo.Orders o WHERE YEAR(o.created_at) = 2026 "
                                    "AND status LIKE '%X'", "sqlserver", "PROD"), "WARN")
        self.assertIn("unbounded", warns)
        self.assertIn("SELECT *", warns)
        self.assertIn("YEAR(column)", warns)
        self.assertIn("leading wildcard", warns)
        self.assertIn("cartesian", levels(tl_sql.check("SELECT COUNT(*) FROM dbo.Orders, dbo.Branches",
                                                       "sqlserver", "PROD"), "WARN"))

    def test_bounded_and_catalog_queries_pass(self):
        ok = "SELECT branch_id, COUNT(*) FROM dbo.Orders WHERE created_at >= @f AND created_at < @t GROUP BY branch_id"
        self.assertEqual(levels(tl_sql.check(ok, "sqlserver", "PROD"), "WARN"), "")
        self.assertEqual(levels(tl_sql.check("SELECT name FROM sys.indexes", "sqlserver", "PROD"), "WARN"), "")

    def test_schema_cache_warnings(self):
        scan = "SELECT COUNT(*) FROM dbo.Orders WHERE status = 'X'"
        self.assertIn("full scan", levels(tl_sql.check(scan, "sqlserver", "PROD", schema=SCHEMA), "WARN"))
        seek = "SELECT COUNT(*) FROM dbo.Orders WHERE created_at >= @f"
        self.assertNotIn("full scan", levels(tl_sql.check(seek, "sqlserver", "PROD", schema=SCHEMA), "WARN"))
        self.assertIn("not in the schema cache",
                      levels(tl_sql.check("SELECT COUNT(*) FROM dbo.Ordrs", "sqlserver", "PROD", schema=SCHEMA), "WARN"))

    def test_db2_guard(self):
        sql = tl_sql.guard("SELECT ACCT, AMT FROM APP.CHQ", "db2-zos", max_rows=50)
        self.assertTrue(sql.rstrip().endswith("FETCH FIRST 50 ROWS ONLY\nWITH UR;"))
        self.assertIn("WITH UR", levels(tl_sql.check("SELECT COUNT(*) FROM APP.CHQ", "db2-zos", "PROD"), "INFO"))


class RunAndSchemaTests(unittest.TestCase):
    """`run` with a fake command-line client (a Python script) in place of sqlcmd / DB2 CLP."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.mem = os.path.join(self.root, ".claude", "tl-memory")
        os.makedirs(os.path.join(self.mem, "db"))
        fake = os.path.join(self.root, "fake_client.py")
        with open(fake, "w", encoding="utf-8") as f:
            f.write("import sys, time\nmode = sys.argv[1]\n"
                    "if mode == 'sleep': time.sleep(30)\n"
                    "if mode == 'fail': print('Msg 1222, Lock request time out period exceeded.'); sys.exit(1)\n"
                    "print('branch,cnt'); print('------,---'); print('1,10'); print('2,7'); print('(2 rows affected)')\n")
        sources = []
        for alias, mode in (("ok", "ok"), ("slow", "sleep"), ("locked", "fail")):
            sources.append({"alias": alias, "access": "cli", "engine": "sqlserver", "env": "PROD", "read_only": True,
                            "timeout_s": 1, "command": [sys.executable, fake, mode, "{file}"]})
        sources.append({"alias": "viamcp", "access": "mcp", "server": "db", "engine": "sqlserver", "env": "TEST"})
        with open(os.path.join(self.mem, "data-sources.json"), "w", encoding="utf-8") as f:
            json.dump({"sources": sources}, f)
        with open(os.path.join(self.mem, "db", "ok.json"), "w", encoding="utf-8") as f:
            json.dump(SCHEMA, f)
        self.query = os.path.join(self.root, "q.sql")
        with open(self.query, "w", encoding="utf-8") as f:
            f.write("SELECT branch_id, COUNT(*) FROM dbo.Orders WHERE created_at >= '2026-09-01' GROUP BY branch_id")

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_tool(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = tl_sql.main([*argv, "--root", self.root])
        return code, out.getvalue()

    def journal(self):
        with open(os.path.join(self.mem, "sql-journal.csv"), encoding="utf-8") as f:
            return f.read()

    def test_run_ok_saves_csv_and_journal(self):
        code, out = self.run_tool("run", self.query, "--source", "ok")
        self.assertEqual(code, 0, out)
        self.assertIn("OK · 2 row(s)", out)
        self.assertIn(",ok", self.journal())
        results = os.listdir(os.path.join(self.mem, "results"))
        self.assertTrue(any(n.endswith(".csv") for n in results))
        guarded = [n for n in results if n.endswith(".sql")][0]
        with open(os.path.join(self.mem, "results", guarded), encoding="utf-8") as f:
            self.assertIn("SET LOCK_TIMEOUT", f.read())

    def test_run_stops_a_hanging_client(self):
        code, out = self.run_tool("run", self.query, "--source", "slow", "--timeout", "1")
        self.assertEqual(code, 3)
        self.assertIn("TIMEOUT", out)
        self.assertIn("Do not repeat the same query", out)
        self.assertIn(",timeout", self.journal())

    def test_run_explains_lock_timeout(self):
        code, out = self.run_tool("run", self.query, "--source", "locked")
        self.assertEqual(code, 1)
        self.assertIn("too heavy as written", out)

    def test_run_refuses_writes_and_mcp_sources(self):
        with open(self.query, "w", encoding="utf-8") as f:
            f.write("DELETE FROM dbo.Orders")
        code, out = self.run_tool("run", self.query, "--source", "ok")
        self.assertEqual(code, 1)
        self.assertIn("Refused", out)
        old, sys.stderr = sys.stderr, io.StringIO()
        try:
            self.assertEqual(self.run_tool("run", self.query, "--source", "viamcp")[0], 2)
        finally:
            sys.stderr = old

    def test_check_cli_with_schema(self):
        code, out = self.run_tool("check", self.query, "--source", "ok")
        self.assertEqual(code, 0)
        self.assertNotIn("no schema cache", out)

    def test_schema_commands(self):
        self.assertIn("dbo.Orders", self.run_tool("schema", "find", "ok", "created")[1])
        table = self.run_tool("schema", "table", "ok", "Orders")[1]
        self.assertIn("index IX_Orders_created: (created_at, branch_id)", table)
        joins = self.run_tool("schema", "joins", "ok", "dbo.OrderLines", "dbo.Branches")[1]
        self.assertEqual(joins.strip().splitlines(), ["JOIN ON dbo.OrderLines.order_id = dbo.Orders.order_id",
                                                      "JOIN ON dbo.Orders.branch_id = dbo.Branches.branch_id"])
        self.assertEqual(self.run_tool("schema", "find", "nocache", "x")[0], 2)


if __name__ == "__main__":
    unittest.main()
