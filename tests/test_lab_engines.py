import math
import unittest

from _load import load

daily = load("trader-lab", "daily")
hourly = load("trader-lab", "hourly")


def series(rows, start="2020-01-06"):
    """rows: [(o, h, l, c)] -> a daily dict with consecutive weekday dates."""
    import datetime
    d0 = datetime.date(*map(int, start.split("-")))
    D = {k: [] for k in "dohlcv"}
    d = d0
    for o, h, l, c in rows:
        while d.weekday() > 4:
            d += datetime.timedelta(days=1)
        D["d"].append(d.isoformat())
        for k, x in zip("ohlc", (o, h, l, c)):
            D[k].append(float(x))
        D["v"].append(1.0)
        d += datetime.timedelta(days=1)
    return D


class Fills(unittest.TestCase):
    def setUp(self):
        self.D = series([(100, 101, 99, 100), (100, 104, 97, 103)])

    def test_open_to_close(self):
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "oc"}), (100, 103))

    def test_stop_entry_gap_and_miss(self):
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "stop", "entry": 102}), (102, 103))
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "stop", "entry": 99}), (100, 103))
        self.assertIsNone(daily.fill(self.D, 1, {"side": 1, "hold": "stop", "entry": 105}))

    def test_a_day_that_touches_the_stop_is_stopped(self):
        sig = {"side": 1, "hold": "stop", "entry": 102, "sl": 98}
        self.assertEqual(daily.fill(self.D, 1, sig), (102, 98))

    def test_target_and_overnight(self):
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "target", "target": 102}), (100, 102))
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "co"}), (100, 100))
        self.assertEqual(daily.fill(self.D, 1, {"side": 1, "hold": "cc"}), (100, 103))


class Indicators(unittest.TestCase):
    def test_rsi_extremes(self):
        c = [10, 9, 8, 7]
        self.assertEqual(daily.rsi(c, 4, 2), 0.0)
        self.assertEqual(daily.rsi([1, 2, 3], 3, 2), 100.0)
        self.assertIsNone(daily.rsi(c, 2, 2))

    def test_ibs_and_sma(self):
        D = series([(10, 12, 10, 10.4)])
        self.assertAlmostEqual(daily.ibs(D, 0), 0.2)
        self.assertEqual(daily.sma([1, 2, 3, 4], 4, 2), 3.5)
        self.assertIsNone(daily.sma([1, 2], 1, 2))

    def test_rules_use_only_the_past(self):
        # IBS for day i is decided from day i-1's bar only
        D = series([(10, 12, 10, 10.2), (99, 99, 1, 98)])
        self.assertEqual(daily.r_ibs(D, 1, {"x": 0.2, "side": 1, "hold": "oc"})["side"], 1)

    def test_turn_of_month_and_preholiday(self):
        D = series([(1, 1, 1, 1)] * 30, start="2021-01-25")   # spans the January/February turn
        fired = [D["d"][i] for i in range(1, 29) if daily.r_tom(D, i, {"n": 1, "hold": "oc"})]
        self.assertIn("2021-01-29", fired)   # last trading day of January
        self.assertIn("2021-02-01", fired)   # first of February
        self.assertNotIn("2021-02-10", fired)
        H = series([(1, 1, 1, 1)] * 3, start="2021-07-01")
        H["d"] = ["2021-07-01", "2021-07-02", "2021-07-06"]   # July 5 holiday, Friday -> Tuesday
        self.assertTrue(daily.r_preholiday(H, 1, {"hold": "oc"}))
        self.assertFalse(daily.r_preholiday(H, 0, {"hold": "oc"}))


class Swing(unittest.TestCase):
    def test_marks_to_market_and_exits(self):
        rows = [(100, 101, 99, 100)] * 25 + [(100, 100, 90, 90), (91, 96, 91, 95), (95, 99, 95, 99)]
        D = series(rows)
        entry = lambda D, j, p: 1 if j == 25 else 0
        out, n = daily.run_swing(D, entry, {"exit": "up"}, 0.0)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 1)                       # exited on the first up close
        self.assertAlmostEqual(list(out.values())[0], (95 / 90.0 - 1) * 1e4)
        out, _ = daily.run_swing(D, entry, {"exit": "up", "fill": "open"}, 0.0)
        self.assertAlmostEqual(list(out.values())[0], (95 / 91.0 - 1) * 1e4)


class SwingState(unittest.TestCase):
    def test_enter_hold_and_flat(self):
        rows = [(100, 101, 99, 100)] * 25 + [(100, 100, 90, 90)]
        D = series(rows)
        sig = lambda D, j, p: 1 if j == len(D["c"]) - 1 or j == 25 else 0
        self.assertEqual(daily.swing_state(D, sig, {"exit": "up"})[0], "enter")
        D2 = series(rows + [(90, 90, 85, 86)])
        st = daily.swing_state(D2, lambda D, j, p: 1 if j == 25 else 0, {"exit": "up"})
        self.assertEqual(st[:2], ("hold", 1))
        D3 = series(rows + [(90, 96, 90, 95)])
        self.assertIsNone(daily.swing_state(D3, lambda D, j, p: 1 if j == 25 else 0, {"exit": "up"}))

    def test_vix_gate(self):
        daily.VIX.clear()
        daily.VIX["2020-01-06"] = (30.0, 20.0)
        self.assertTrue(daily.vix_ok("2020-01-06", {"vix": "high"}))
        self.assertFalse(daily.vix_ok("2020-01-06", {"vix": "low"}))
        self.assertFalse(daily.vix_ok("2020-01-07", {"vix": "high"}))
        self.assertTrue(daily.vix_ok("2020-01-07", {}))
        daily.VIX.clear()


class Statistics(unittest.TestCase):
    def test_norm_ppf_round_trip(self):
        for p in (0.01, 0.2, 0.5, 0.9, 0.999):
            self.assertAlmostEqual(daily.norm_cdf(daily.norm_ppf(p)), p, places=6)

    def test_deflated_sharpe_falls_with_more_trials(self):
        import random
        rnd = random.Random(7)
        x = [rnd.gauss(0.1, 1) for _ in range(1000)]
        one = daily.deflated_sharpe(x, 1, 0.0)
        many = daily.deflated_sharpe(x, 500, 0.05 ** 2)
        self.assertGreater(one, 0.95)
        self.assertLess(many, one)

    def test_robust_var_ignores_outliers(self):
        x = [0.01, -0.01, 0.02, -0.02, 0.0, -5.0]
        self.assertLess(daily.robust_var(x), 0.001)


class Hourly(unittest.TestCase):
    def bar(self, o, h, l, c):
        return {"o": o, "h": h, "l": l, "c": c, "v": 1}

    def test_orb60_stop_entry_and_stopout(self):
        B = [self.bar(100, 101, 99, 100.5)] + [self.bar(100.5, 102, 100.2, 101.5)] + \
            [self.bar(101.5, 101.6, 98.5, 99)] + [self.bar(99, 99, 99, 99)] * 4
        S = [("d0", [self.bar(100, 100, 100, 100)] * 7), ("d1", B)]
        t = hourly.h_orb60(S, 1, {"pc": 100}, {"dir": "both", "stop": "range"})
        self.assertEqual(t, [(1, 101, 99)])
        t = hourly.h_orb60(S, 1, {"pc": 100}, {"dir": "both", "stop": "mid"})
        self.assertEqual(t, [(1, 101, 100)])

    def test_imom_and_rod_direction(self):
        B = [self.bar(100, 101, 100, 101)] + [self.bar(101, 101, 101, 101)] * 5 + [self.bar(101, 102, 101, 102)]
        S = [("d0", B), ("d1", B)]
        self.assertEqual(hourly.h_imom(S, 1, {"pc": 100}, {"min": 0, "mode": "mom"}), [(1, 101, 102)])
        self.assertEqual(hourly.h_rod(S, 1, {"pc": 100}, {"min": 0, "mode": "rev"}), [(-1, 101, 102)])


if __name__ == "__main__":
    unittest.main()
