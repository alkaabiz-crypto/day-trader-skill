import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab", "daybrain"))
try:
    import numpy as np
    import brain
    import alpaca_days
except ImportError:
    np = None


@unittest.skipIf(np is None, "numpy not installed")
class DayBrain(unittest.TestCase):
    def test_ranks_centered(self):
        r = brain.ranks(np.array([3.0, 1.0, 2.0, 2.0]))
        self.assertAlmostEqual(r.sum(), 0.0)
        self.assertEqual(r[1], -0.5)
        self.assertEqual(r[0], 0.5)

    def test_summary_and_features(self):
        bars = []
        import datetime
        for day in range(20):
            d0 = datetime.datetime(2026, 1, 5) + datetime.timedelta(days=day)   # EST, 9:30 = 14:30 UTC
            for k in range(78):
                t = d0 + datetime.timedelta(hours=14, minutes=30 + 5 * k)
                p = 100.0 + day + k * 0.01
                bars.append({"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "o": p, "h": p + 0.05, "l": p - 0.05, "c": p + 0.01,
                             "v": 1000.0})
        sm = alpaca_days.summarise(bars)
        self.assertEqual(len(sm), 20)
        first = sm[sorted(sm)[0]]
        self.assertEqual(first[0], 100.0)
        rows = brain.rows_from_days(sm, min_dollar_vol=0)
        self.assertEqual(len(rows), 5)
        f, y = rows[sorted(rows)[0]]
        self.assertEqual(len(f), 12)
        self.assertAlmostEqual(f[7], 0.0)          # same first-candle volume as usual: log rvol 0


if __name__ == "__main__":
    unittest.main()
