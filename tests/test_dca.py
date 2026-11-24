import unittest

from _load import load

try:
    import numpy as np
    dca = load("trader-lab", "dca")
except ImportError:          # numpy is optional (research script only)
    np = None


def asset(prices):
    import datetime
    d0 = datetime.date(2020, 1, 1)
    d = [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(len(prices))]
    p = np.array(prices, float)
    return {"d": d, "o": p, "c": p}


@unittest.skipIf(np is None, "numpy not installed")
class Dca(unittest.TestCase):
    def test_irr_of_a_known_flow(self):
        self.assertAlmostEqual(dca.irr([-100.0, 110.0], [0.0, 1.0]), 0.10, places=6)

    def test_flat_price_returns_the_money_put_in(self):
        p = dca.plan(asset([10.0] * 100), 50.0)
        self.assertEqual(p["months"], 4)                 # Jan, Feb, Mar, Apr 2020 starts
        self.assertAlmostEqual(p["invested"], 200.0)
        self.assertAlmostEqual(p["value"], 200.0)
        self.assertAlmostEqual(p["irr"], 0.0, places=6)
        self.assertEqual(p["max_drop"], 0.0)

    def test_a_drop_shows_up(self):
        p = dca.plan(asset([10.0] * 50 + [5.0] * 50), 50.0)
        self.assertAlmostEqual(p["max_drop"], 0.5)
        self.assertLess(p["value"], p["invested"])



@unittest.skipIf(np is None, "numpy not installed")
class Mixes(unittest.TestCase):
    def test_rebalance_each_january(self):
        mx = load("trader-lab", "mixes")
        months = ["2020-%02d" % m for m in range(1, 13)] + ["2021-01"]
        rets = {"A": {m: 0.10 for m in months}, "B": {m: 0.0 for m in months}}
        r = mx.simulate({"A": 0.5, "B": 0.5}, rets, months)
        self.assertAlmostEqual(r[0], 0.05)                      # starts at 50/50
        self.assertGreater(r[11], r[0])                         # A drifted up during the year
        self.assertLess(r[12], 0.05)                            # reset to 50/50 in January, minus cost
        self.assertAlmostEqual(r[12], 0.05 - sum(abs(0.5 - w) for w in (
            1.1 ** 12 / (1.1 ** 12 + 1), 1 / (1.1 ** 12 + 1))) * 5e-4, places=9)


if __name__ == "__main__":
    unittest.main()
