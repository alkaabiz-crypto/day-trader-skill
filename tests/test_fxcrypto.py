import unittest

from _load import load

fx = load("trader-scanner", "fxcrypto")


def series(closes, t0=1_700_000_000):
    return {"t": [t0 + 3600 * i for i in range(len(closes))], "c": list(closes)}


class FxCrypto(unittest.TestCase):
    def test_forming_bar_and_nulls_are_dropped(self):
        s = series([1.0, None, 2.0, 3.0])
        now = s["t"][3] + 1800                      # the last hour is still forming
        self.assertEqual([c for _, c in fx.complete_hours(s, now)], [1.0, 2.0])

    def test_breakdown_and_24h_move(self):
        closes = [100.0 + 0.1 * i for i in range(40)] + [90.0]
        s = series(closes)
        r = fx.analyse("BTC-USD", s, s["t"][-1] + 3600)
        self.assertIn("breakdown_20h", r["setups"])
        self.assertEqual(r["kind"], "crypto")
        self.assertAlmostEqual(r["chg_24h_pct"], (90.0 / closes[-25] - 1) * 100)

    def test_too_short_is_skipped(self):
        s = series([1.0] * 10)
        self.assertIsNone(fx.analyse("EURUSD=X", s, s["t"][-1] + 3600))


if __name__ == "__main__":
    unittest.main()
