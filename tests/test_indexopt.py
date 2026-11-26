import unittest

from _load import load

opt = load("trader-lab", "indexopt")


class Grid(unittest.TestCase):
    def test_grid_has_48_settings_including_the_current_rule(self):
        g = opt.grid()
        self.assertEqual(len(g), 48)
        self.assertIn(opt.CURRENT, g)

    def test_walk_forward_uses_only_earlier_years(self):
        a, b = opt.CURRENT, (5, 100, 50, 5, (4, 0.25))
        days = ["%d-%02d-15" % (y, m) for y in range(2010, 2016) for m in range(1, 13)]
        # a is good to 2014 and bad in 2015; b the opposite. The 2015 pick must still be a.
        ca = [(d, 0.0, (0.01 if d < "2015" else -0.01) + (0.002 if d[5:7] in ("01", "07") else 0), 0.0) for d in days]
        cb = [(d, 0.0, (-0.01 if d < "2015" else 0.01) + (0.002 if d[5:7] in ("01", "07") else 0), 0.0) for d in days]
        picks, stitched = opt.walk_forward({a: ca, b: cb}, years=[2015], start="2010-01-01")
        self.assertEqual(picks[2015], a)
        self.assertTrue(all(x[0].startswith("2015") for x in stitched))

    def test_run_restores_module_defaults(self):
        before = (opt.survivors.features, opt.indexbot.SLOTS)
        n = 260
        c = [100 + 0.1 * i for i in range(n)]
        c[250], c[251] = 120.0, 119.0
        dates = ["2015-%03d" % i for i in range(n)]
        data = {s: {"d": dates, "o": list(c), "c": list(c)} for s in opt.indexbot.US_ONLY}
        old = opt.indexbot.START
        opt.indexbot.START = "2015-000"
        try:
            curve, trades = opt.run(data, (15, 200, 50, 5, (4, 0.25)))
        finally:
            opt.indexbot.START = old
        self.assertTrue(trades)
        self.assertEqual((opt.survivors.features, opt.indexbot.SLOTS), before)


if __name__ == "__main__":
    unittest.main()
