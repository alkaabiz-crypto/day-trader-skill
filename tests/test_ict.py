import unittest

from _load import load

ict = load("trader-lab", "ict")


def bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


class FVG(unittest.TestCase):
    def test_bullish_and_bearish_gaps(self):
        up = [bar(100, 101, 99, 100.5), bar(100.5, 104, 100.5, 103.8), bar(103.8, 105, 102, 104.5)]
        self.assertEqual(ict.fvg(up, 2), (1, 102, 99))
        dn = [bar(100, 101, 99, 99.5), bar(99.5, 99.5, 96, 96.2), bar(96.2, 97.5, 95, 95.5)]
        self.assertEqual(ict.fvg(dn, 2), (-1, 97.5, 101))
        flat = [bar(100, 101, 99, 100)] * 3
        self.assertIsNone(ict.fvg(flat, 2))


class Manage(unittest.TestCase):
    def test_limit_fill_then_target_and_stop_first(self):
        bars = [bar(103, 103.5, 101.9, 102.5), bar(102.5, 108, 102.4, 107.5), bar(107, 107, 106, 106.5)]
        self.assertEqual(ict.manage(bars, 0, 1, 102, 99, 2.0, 0), (102, 108, "target"))
        bars = [bar(103, 103.5, 98, 99)]                   # fills and stops in the same candle
        self.assertEqual(ict.manage(bars + [bar(99, 99, 99, 99)], 0, 1, 102, 99, 2.0, 0), (102, 99, "stop"))
        bars = [bar(103, 104, 102.5, 103)] * 3             # never trades back to the limit
        self.assertIsNone(ict.manage(bars, 0, 1, 102, 99, 2.0, 1))


class Full(unittest.TestCase):
    def test_pooled_averages_markets_per_day(self):
        by = {"A": [{"date": "2024-05-01", "ret": 0.02}, {"date": "2025-02-01", "ret": -0.01}],
              "B": [{"date": "2024-05-01", "ret": 0.0}]}
        ins, jud = ict.pooled(by)
        self.assertEqual(ins, [0.01])
        self.assertEqual(jud, [-0.01])
        self.assertEqual(set(ict.FULL_SETUPS), {"silver_bullet", "silver_bullet_pm", "judas_swing"})


if __name__ == "__main__":
    unittest.main()
