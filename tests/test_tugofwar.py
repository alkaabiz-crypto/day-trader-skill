import unittest

from _load import load

tw = load("trader-lab", "tugofwar")


class Legs(unittest.TestCase):
    def test_overnight_is_dividend_adjusted(self):
        # a 1.00 dividend paid overnight: raw close 100 -> open 99, adjusted factor makes it flat
        D = {"d": ["2020-01-02", "2020-01-03"], "o": [100.0, 99.0], "c": [100.0, 99.0], "a": [99.0, 99.0]}
        on, intra = tw.legs(D)["2020-01-03"]
        self.assertAlmostEqual(on, 0.0)
        self.assertAlmostEqual(intra, 0.0)

    def test_month_ends(self):
        self.assertEqual(tw.month_ends(["2020-01-30", "2020-01-31", "2020-02-03"]), ["2020-01-31", "2020-02-03"])


class Simulate(unittest.TestCase):
    def test_overnight_winners_earn_their_overnight_spread(self):
        tw.LOOKBACK, old = 3, tw.LOOKBACK
        try:
            dates = ["2020-01-%02d" % d for d in range(1, 29)] + ["2020-02-%02d" % d for d in range(1, 6)]
            R = {}
            for n, s in enumerate("ABCDEF"):
                R[s] = {d: (0.001 * n, 0.0) for d in dates}
            r = tw.simulate(R, dates, "overnight", cost_bps=0.0)
            feb = [v for d, v in r.items() if d.startswith("2020-02")]
            self.assertTrue(feb)
            self.assertAlmostEqual(feb[0], 0.001 * 4.5 - 0.001 * 0.5)
        finally:
            tw.LOOKBACK = old


if __name__ == "__main__":
    unittest.main()
