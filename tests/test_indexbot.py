import unittest

from _load import load

ib = load("trader-lab", "indexbot")


class IndexBot(unittest.TestCase):
    def test_universe_maps_to_cfds(self):
        self.assertEqual(ib.CFD["SPY"], "US500")
        self.assertEqual(ib.CFD["EWG"], "DE30")
        self.assertEqual(len(ib.UNIVERSE), 10)
        self.assertEqual([ib.CFD[s] for s in ib.US_ONLY], ["US500", "USTEC", "US30", "US2000"])

    def test_simulate_uses_only_the_given_markets(self):
        n = 260
        c = [100 + 0.1 * i for i in range(n)]
        c[250], c[251] = 120.0, 119.0
        dates = ["2015-%03d" % i for i in range(n)]
        data = {s: {"d": dates, "o": list(c), "c": list(c)} for s in ib.US_ONLY}
        old = ib.START
        ib.START = "2015-000"
        try:
            curve, trades = ib.simulate(data)
        finally:
            ib.START = old
        self.assertTrue(trades)
        self.assertTrue(all(t["sym"] in ib.US_ONLY for t in trades))

    def test_simulate_buys_a_dip_and_charges_swap(self):
        n = 260
        c = [100 + 0.1 * i for i in range(n)]
        c[250], c[251] = 120.0, 119.0              # a sharp two-day dip in an uptrend
        dates = ["2015-%03d" % i for i in range(n)]
        data = {s: {"d": dates, "o": list(c), "c": list(c)} for s in ib.UNIVERSE}
        old = ib.START
        ib.START = "2015-000"
        try:
            curve, trades = ib.simulate(data)
        finally:
            ib.START = old
        self.assertTrue(trades)
        self.assertTrue(all(t["in"] >= "2015-251" for t in trades))


if __name__ == "__main__":
    unittest.main()
