import unittest

from _load import load

try:
    import numpy as np
    ms = load("trader-lab", "market_search")
    from test_crypto import coin
except ImportError:          # numpy is optional (research script only)
    np = None


@unittest.skipIf(np is None, "numpy not installed")
class Markets(unittest.TestCase):
    def test_no_condition_looks_ahead(self):
        A = coin(1000, seed=2)
        A["d"] = [d for d in A["d"]]
        for lag in ({"us": 0, "fx": 1}, {"us": 1, "fx": 1}, {"us": 0, "fx": 0}):
            full = ms.conditions(A, "SPY", lag)
            k = 800
            cut = ms.conditions({key: v[:k] for key, v in A.items()}, "SPY", lag)
            self.assertEqual(sorted(full), sorted(cut))
            # the calendar's "next session" on the last cut day is a guess; everything else must match
            bad = [nm for nm in full if not np.array_equal(full[nm][:k - 1], cut[nm][:k - 1])]
            self.assertEqual(bad, [])

    def test_outside_series_are_lagged_to_this_markets_close(self):
        self.assertEqual(ms.lags("^N225"), {"us": 1, "fx": 1})       # Tokyo closes before New York
        self.assertEqual(ms.lags("AAPL"), {"us": 0, "fx": 1})        # FX bars close after 16:00 New York
        self.assertEqual(ms.lags("EURUSD=X"), {"us": 0, "fx": 0})
        self.assertGreaterEqual(len(ms.markets()), 60)

    def test_a_dead_runners_lock_is_ignored(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            lock = os.path.join(t, "x.lock")
            open(lock, "w").write("999999999")
            self.assertFalse(ms.locked(lock))
            open(lock, "w").write(str(os.getppid()))
            self.assertTrue(ms.locked(lock))


if __name__ == "__main__":
    unittest.main()
