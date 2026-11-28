import math
import unittest

from _load import load

exness = load("trader-lab", "exness")
judge = load("trader-lab", "judge")


class Exness(unittest.TestCase):
    def test_min_lot_exposure(self):
        # USTEC: 0.05 lot x $1 per point -> $1,250 at 25,000
        self.assertAlmostEqual(exness.exposure_usd("USTEC", 25000), 1250.0)
        # gold: 0.01 lot x 100 oz = 1 oz
        self.assertAlmostEqual(exness.exposure_usd("XAUUSD", 3600), 3600.0)
        self.assertAlmostEqual(exness.exposure_usd("btcusd", 90000), 900.0)

    def test_round_trip_cost(self):
        # USTEC: (1.12 spread + 1 slippage) x 0.05 = $0.106
        self.assertAlmostEqual(exness.round_trip_usd("USTEC"), 0.106)
        self.assertGreater(exness.round_trip_usd("USTEC", at_open=True), exness.round_trip_usd("USTEC"))
        self.assertAlmostEqual(exness.round_trip_bps("US500", 6800), 0.9 / 6800 * 1e4)

    def test_check_flags_lot_below_minimum(self):
        r = exness.check("US500", 6800, 6700, lots=0.10)
        self.assertFalse(r["ok"])
        self.assertIn("below the US500 minimum", r["problems"][0])

    def test_check_flags_min_lot_that_cannot_shrink(self):
        # 200-point stop at 0.05 = $10 + cost: fine at $60, too big at $5
        self.assertTrue(exness.check("USTEC", 25000, 24800, max_loss=60)["ok"])
        r = exness.check("USTEC", 25000, 24800, max_loss=5)
        self.assertFalse(r["ok"])
        self.assertIn("cannot be smaller", r["problems"][0])

    def test_check_flags_leverage(self):
        # 1 oz of gold at $3,600 on a $1,000 account is 3.6x
        r = exness.check("XAUUSD", 3600, 3500, account=1000, max_leverage=2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["leverage"], 3.6)

    def test_unknown_symbol(self):
        with self.assertRaises(KeyError):
            exness.spec("DOGEUSD")


class Judge(unittest.TestCase):
    def dates(self):
        import datetime
        d, out = datetime.date(2016, 1, 4), []
        while d.year < 2027:
            if d.weekday() < 5:
                out.append(d.isoformat())
            d += datetime.timedelta(days=1)
        return out

    def test_tstat_and_drop(self):
        self.assertAlmostEqual(judge.tstat([1, 2, 3]), 2 / (1 / math.sqrt(3)))
        self.assertTrue(math.isnan(judge.tstat([1, 1, 1])))
        self.assertEqual(judge.worst_drop([10, -5, -20, 30, -1]), -25)

    def test_a_steady_edge_is_worthy(self):
        ds = self.dates()
        pnl = [1.0 if i % 3 else -0.5 for i in range(len(ds))]
        r = judge.verdict(ds, pnl, [x - 0.1 for x in pnl], [0.0] * 100)
        self.assertTrue(r["worthy"], r["failed"])

    def test_dead_since_2024_fails(self):
        ds = self.dates()
        pnl = [(1.0 if i % 3 else -0.5) if d < "2024-01-01" else (0.5 if i % 2 else -0.6) for i, d in enumerate(ds)]
        r = judge.verdict(ds, pnl, pnl, [0.0] * 100)
        self.assertIn("since_2024", r["failed"])

    def test_big_drop_and_luck_fail(self):
        ds = self.dates()
        pnl = [1.0 if i % 3 else -0.5 for i in range(len(ds))]
        pnl[100] = -400.0
        r = judge.verdict(ds, pnl, pnl, [1e9] * 100)
        self.assertIn("worst_drop", r["failed"])
        self.assertIn("random_timing", r["failed"])

    def test_corr(self):
        a = {"d1": 1, "d2": -1, "d3": 2}
        self.assertAlmostEqual(judge.corr(a, a), 1.0)
        self.assertAlmostEqual(judge.corr(a, {k: -v for k, v in a.items()}), -1.0)


if __name__ == "__main__":
    unittest.main()
