import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import seasonal_xs as sx  # noqa: E402


def months(y0, y1):
    return ["%04d-%02d" % (y, m) for y in range(y0, y1 + 1) for m in range(1, 13)]


class SeasonalXS(unittest.TestCase):
    def test_frozen_design(self):
        self.assertEqual((sx.YEARS, sx.MIN_SET, sx.COST_BPS, sx.SPLIT, sx.T_BAR), (5, 6, 10.0, "2012-01", 3.0))

    def test_signal_uses_only_past_same_months(self):
        r = {m: (0.05 if m.endswith("-03") else 0.0) for m in months(2000, 2006)}
        r["2006-03"] = -9.0                                   # the month being forecast is never used
        self.assertAlmostEqual(sx.signal(r, "2006-03"), 0.05)
        self.assertAlmostEqual(sx.signal(r, "2006-04"), 0.0)

    def test_needs_all_five_years(self):
        r = {m: 0.01 for m in months(2002, 2006)}
        self.assertIsNone(sx.signal(r, "2006-03"))           # only 2002..2005 before it
        self.assertIsNotNone(sx.signal(r, "2007-03"))

    def test_planted_seasonality_pays(self):
        data = {}
        for i, s in enumerate(sx.SECTORS):
            data[s] = {m: (0.03 if int(m[5:]) % 9 == i else 0.0) for m in months(1999, 2015)}
        ms, h1, h2 = sx.series(data, 0.0)
        self.assertTrue(ms)
        self.assertGreater(sum(h1), 0)
        self.assertGreater(sum(h2), 0)

    def test_shift(self):
        self.assertEqual(sx.shift("2006-03", -12), "2005-03")
        self.assertEqual(sx.shift("2006-01", -1), "2005-12")


if __name__ == "__main__":
    unittest.main()
