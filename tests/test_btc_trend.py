import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import btc_trend as bt  # noqa: E402

CFG = dict(bt.CFG, sma=3, cost_bps=0.0)


def days(closes):
    return [("2026-01-%02d" % (i + 1), c) for i, c in enumerate(closes)]


def fresh():
    return {"cash": 10000.0, "positions": [], "start": None, "last_day": None, "hold_qty": None}


class BtcTrend(unittest.TestCase):
    def test_frozen(self):
        self.assertEqual((bt.CFG["sma"], bt.CFG["cost_bps"], bt.CFG["min_days"]), (200, 20.0, 365))

    def test_buys_above_and_sells_below_the_average(self):
        st = fresh()
        closed, eq, log = bt.step(st, days([10, 10, 10, 12, 13, 9]), CFG)
        self.assertEqual(len(closed), 1)                     # bought at 12, sold at 9
        self.assertAlmostEqual(closed[0]["entry"], 12)
        self.assertAlmostEqual(st["cash"], 10000 * 9 / 12)
        self.assertEqual(st["positions"], [])

    def test_catch_up_runs_each_day_once(self):
        st = fresh()
        bt.step(st, days([10, 10, 10, 12]), CFG)
        n = st["last_day"]
        closed, eq, log = bt.step(st, days([10, 10, 10, 12]), CFG)
        self.assertEqual((eq, st["last_day"]), ([], n))       # nothing new, nothing done twice

    def test_only_completed_days(self):
        bars = {"d": ["2026-11-23", "2026-11-24", "2026-11-25"], "c": [1, 2, 3]}
        self.assertEqual(bt.completed(bars, "2026-11-25"), [("2026-11-23", 1), ("2026-11-24", 2)])


if __name__ == "__main__":
    unittest.main()
