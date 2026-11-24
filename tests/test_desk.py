import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import desk  # noqa: E402


class Desk(unittest.TestCase):
    def test_scoreboard_never_calls_r3_a_pass(self):
        files = {"daily-latest.json": {"chosen": [{"rule": "s_r3", "pass": True}]},
                 "latest.json": {"chosen": [{"strategy": "noise", "keep": False}]}}
        with mock.patch.object(desk, "_load", side_effect=lambda n: files.get(n)):
            sb = desk.scoreboard()
        verdicts = {r["study"]: r["verdict"] for r in sb["rows"]}
        self.assertEqual(verdicts["daily rule R3 (Connors, dip-buying)"], "UNPROVEN")
        self.assertFalse(sb["any_pass"])
        self.assertIn("paper", sb["bottom_line"])

    def test_scoreboard_reports_a_real_pass(self):
        files = {"latest.json": {"chosen": [{"strategy": "x", "keep": True}]}}
        with mock.patch.object(desk, "_load", side_effect=lambda n: files.get(n)):
            sb = desk.scoreboard()
        self.assertTrue(sb["any_pass"])

    def test_candidates_carry_lab_evidence_and_news(self):
        scan = {"as_of": "x", "hits": [{"symbol": "NVDA", "setups": ["oversold_bounce"], "price": 1.0, "rsi": 30},
                                       {"symbol": "AAPL", "setups": ["something_new"], "price": 2.0, "rsi": 50}]}
        news = {"moving": [{"ticker": "NVDA", "pct": 5.0, "moving": True}],
                "by_ticker": {"NVDA": {"tags": ["earnings"], "headlines": 2, "filings": []}}}
        with mock.patch.object(desk, "run", return_value=(scan, None)):
            c = desk.candidates(["NVDA", "AAPL"], news)
        first = c["hits"][0]
        self.assertEqual(first["symbol"], "NVDA")               # the moving name sorts first
        self.assertEqual(first["setups"][0]["label"], "FAIL")
        self.assertEqual(c["hits"][1]["setups"][0]["label"], "UNTESTED")
        self.assertEqual(first["news"]["tags"], ["earnings"])

    def test_failing_parts_degrade_not_crash(self):
        with mock.patch.object(desk, "run", return_value=(None, "host blocked")):
            self.assertIn("error", desk.congress())
            self.assertIn("error", desk.candidates(["X"], None))
            self.assertIn("error", desk.news(["X"], 24))
            self.assertIn("error", desk.trade_sheet("X", 2.0, False))

    def test_text_report_renders_with_errors(self):
        rep = {"created": "t", "investing": desk.investing(), "market": {"error": "offline"},
               "scoreboard": {"rows": [], "bottom_line": "b", "any_pass": False}, "news": {"error": "x"},
               "congress": {"error": "x"}, "candidates": {"error": "x"},
               "trade_sheet": {"error": "x"}}
        out = desk.text(rep)
        self.assertIn("INVESTING", out)
        self.assertIn("unavailable", out)


if __name__ == "__main__":
    unittest.main()
