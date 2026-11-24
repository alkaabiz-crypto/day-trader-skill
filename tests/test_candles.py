import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import candles as cd  # noqa: E402


class Anatomy(unittest.TestCase):
    def test_types(self):
        self.assertEqual(cd.ctype(100, 100.5, 95, 100.3), "dragonfly")   # body 0.3, lower wick 5 of 5.5
        self.assertEqual(cd.ctype(100, 105, 99.9, 100.2), "gravestone")
        self.assertEqual(cd.ctype(100, 103, 97, 100.2), "longleg_doji")
        self.assertEqual(cd.ctype(100, 110, 99.5, 110), "marubozu_bull")
        self.assertEqual(cd.ctype(110, 110.2, 100, 100.1), "marubozu_bear")
        self.assertEqual(cd.ctype(100, 101.2, 94, 101), "hammer")         # body 1, lower wick 6 of 7.2
        self.assertEqual(cd.ctype(101, 108, 99.9, 100), "shooting_star")
        self.assertEqual(cd.ctype(100, 103, 97, 101), "spinning_top")
        self.assertEqual(cd.ctype(100, 108.5, 99, 108), "long_bull")
        self.assertEqual(cd.ctype(100, 104, 99, 102), "bull")
        self.assertIsNone(cd.ctype(100, 100, 100, 100))

    def test_first_rules(self):
        self.assertEqual(cd.first_rule("color", 100, 102, 99, 101), 1)
        self.assertEqual(cd.first_rule("color", 101, 102, 99, 100), -1)
        self.assertEqual(cd.first_rule("lower_wick", 100, 101, 95, 100.5), 1)
        self.assertEqual(cd.first_rule("upper_wick", 100, 106, 99.5, 100), -1)
        self.assertEqual(cd.first_rule("hammer", 100, 101.2, 94, 101), 1)
        self.assertEqual(cd.first_rule("hammer", 100, 104, 99, 102), 0)


class Patterns(unittest.TestCase):
    def series(self):
        # a 7-day decline, then a bearish candle, then a bullish engulfing candle
        O = [110, 109, 108, 107, 106, 105, 104, 103, 102, 99.8]
        C = [109, 108, 107, 106, 105, 104, 103, 102, 100, 103]
        H = [max(o, c) + 0.2 for o, c in zip(O, C)]
        L = [min(o, c) - 0.2 for o, c in zip(O, C)]
        return O, H, L, C

    def test_bull_engulfing_needs_downtrend(self):
        O, H, L, C = self.series()
        self.assertEqual(cd.daily_signal("bull_engulfing", O, H, L, C, 9), 1)
        C2 = [100 + k for k in range(9)] + [103]                    # uptrend instead
        O2 = [c - 0.5 for c in C2[:8]] + [102, 100.5]
        C2[8] = 100
        H2 = [max(o, c) + 0.2 for o, c in zip(O2, C2)]
        L2 = [min(o, c) - 0.2 for o, c in zip(O2, C2)]
        self.assertEqual(cd.daily_signal("bull_engulfing", O2, H2, L2, C2, 9), 0)

    def test_three_soldiers(self):
        O = [100] * 7 + [100, 101, 102]
        C = [100] * 7 + [101, 102, 103]
        H = [c + 0.1 for c in C]
        L = [o - 0.1 for o in O]
        self.assertEqual(cd.daily_signal("three_soldiers", O, H, L, C, 9), 1)
        self.assertEqual(cd.daily_signal("three_crows", O, H, L, C, 9), 0)

    def test_every_rule_runs(self):
        O, H, L, C = self.series()
        for r in cd.DAILY_RULES:
            self.assertIn(cd.daily_signal(r, O, H, L, C, 9), (-1, 0, 1))


class Scoring(unittest.TestCase):
    def test_counts_and_bar(self):
        self.assertEqual(len(cd.FIRST_RULES) * 5 + len(cd.DAILY_RULES) + 6, cd.N_TESTS)
        self.assertEqual(cd.T_BAR, 3.5)

    def test_first_candle_trade_uses_next_open(self):
        bars = [(100, 101, 99.9, 101)] + [(101.0, 101, 101, 101)] * 76 + [(102.0, 102, 102, 102.01)]
        res = cd.part1_trades({"G": {"X": [("2025-01-02", bars)]}})["G"]["color"]
        k, raw = res["2025-01-02"][0]
        self.assertEqual(k, 1)
        self.assertAlmostEqual(raw, 102.01 / 101.0 - 1)

    def test_verdict(self):
        s = {"in_sample": {"t": 0.5, "days": 100, "mean_bps": 1}, "judged": {"t": 3.6, "days": 100, "mean_bps": 2}}
        self.assertEqual(cd.verdict(s), "PASS")
        s["judged"]["t"] = 3.4
        self.assertEqual(cd.verdict(s), "FAIL")


if __name__ == "__main__":
    unittest.main()
