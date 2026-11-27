import unittest

from _load import load

ab = load("trader-lab", "alpaca_bars")


def session(path):
    return [{"o": p, "h": p * 1.001, "l": p * 0.999, "c": p, "v": 1000} for p in path]


class Records(unittest.TestCase):
    def test_breakout_recorded_and_flat_day_not(self):
        flat = session([100.0] * 78)
        self.assertEqual(ab.records(flat)["d"], {})
        up = session([100.0] * 3 + [103.0 + 0.2 * i for i in range(75)])     # a clear break, worth its costs
        rec = ab.records(up)
        self.assertIn("09:50", rec["d"])
        self.assertIn("10:17", rec["d"])
        cv, over, pnl, risk, how = rec["d"]["10:17"]
        self.assertGreater(over, 0)
        self.assertIn(how, ("stop", "target", "close"))

    def test_bot_caps_and_ranking(self):
        R = {s: {"2026-01-05": {"c": 50, "v": 2e6, "d": {"10:17": [cv, 0.01, 1.0, 9.0, "close"]}}}
             for s, cv in (("A", 3e9), ("B", 2e9), ("C", 1e9))}
        ok = {"2026-01-05": {"A", "B", "C"}}
        old = ab.run_bot(R, ok, "old")
        self.assertEqual([t["sym"] for t in old], ["A", "B"])          # 2 a run, biggest $ volume first
        self.assertEqual(len(ab.run_bot(R, ok, "now")), 3)


if __name__ == "__main__":
    unittest.main()
