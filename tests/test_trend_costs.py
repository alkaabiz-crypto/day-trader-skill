import math
import unittest

from _load import load

trend = load("trader-lab", "trend")
costs = load("trader-lab", "costs")


def days(n, start=(2010, 1, 4)):
    import datetime
    d = datetime.date(*start)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def asset(prices, dates):
    D = {"d": dates, "o": list(prices), "h": list(prices), "l": list(prices), "c": list(prices),
         "v": [1.0] * len(prices), "a": list(prices)}
    return D, {d: i for i, d in enumerate(dates)}


class Costs(unittest.TestCase):
    def test_pure_bid_ask_bounce_recovers_the_spread(self):
        # no volatility: every day trades between bid 99.9 and ask 100.1, closes at 100
        n = 10
        s = costs.cs_spread([100.1] * n, [99.9] * n, [100.0] * n)
        x = math.log(100.1 / 99.9)
        self.assertIsNone(s[0])
        self.assertAlmostEqual(s[5], 2 * (math.exp(x) - 1) / (1 + math.exp(x)), places=9)

    def test_negative_estimates_are_floored(self):
        # a steady trend with a tiny range gives a negative raw estimate -> 0
        H = [100 + i + 0.01 for i in range(6)]
        L = [100 + i - 0.01 for i in range(6)]
        s = costs.cs_spread(H, L, [100 + i for i in range(6)])
        self.assertTrue(all(v >= 0 for v in s[1:]))

    def test_check_warns_when_costs_eat_the_reward(self):
        orig = costs.spread_bps
        costs.spread_bps = lambda sym, live=True: (20.0, "2026-11-20", "test")
        try:
            r = costs.check("XYZ", 100.0, 99.0, 100.5)
            self.assertAlmostEqual(r["round_trip_bps"], 20 + 2 * costs.SLIP_BPS + costs.SEC_FEE_BPS)
            self.assertEqual(len(r["warnings"]), 2)
            r = costs.check("XYZ", 100.0, 95.0, 110.0)
            self.assertEqual(r["warnings"], [])
        finally:
            costs.spread_bps = orig


class Trend(unittest.TestCase):
    def setUp(self):
        self.dates = days(400)
        up = [100 * (1.001 ** i) for i in range(400)]
        down = [100 * (0.999 ** i) for i in range(400)]
        self.uni = {"UP": asset(up, self.dates), "DN": asset(down, self.dates)}
        self.cash = {d: 0.0001 for d in self.dates}

    def test_tsmom_and_sma_hold_only_the_riser(self):
        d = self.dates[300]
        w = trend.w_tsmom(self.uni, self.cash, d, {"L": 12, "w": "eq"})
        self.assertEqual(set(w), {"UP"})
        self.assertAlmostEqual(w["UP"], 0.5)          # half the book; the falling asset's half is in cash
        self.assertEqual(set(trend.w_sma(self.uni, self.cash, d, {})), {"UP"})

    def test_simulate_trades_at_the_next_open_and_cash_earns(self):
        me = set(self.dates[i] for i in range(len(self.dates) - 1) if self.dates[i][:7] != self.dates[i + 1][:7])
        ser = trend.simulate(self.uni, self.cash, self.dates, me, lambda u, c, d, p: {}, {})
        self.assertAlmostEqual(ser[10][1], 0.0001)    # all cash: the T-bill rate
        hold = trend.simulate(self.uni, self.cash, self.dates, me, lambda u, c, d, p: {"UP": 1.0}, {}, cost_bps=0)
        first = [k for k, (d, _) in enumerate(hold) if self.dates[k] in me][0] + 1
        self.assertAlmostEqual(hold[first + 3][1], 0.001, places=9)   # a held day earns the asset's return

    def test_metrics_and_drawdown_overlay(self):
        ser = [(d, 0.01 if i < 50 else -0.02) for i, d in enumerate(self.dates[:120])]
        m = trend.metrics(ser, self.cash)
        self.assertLess(m["mdd"], -0.5)
        dd = trend.overlay(ser, self.cash, "dd", cost_bps=0)
        self.assertGreater(trend.metrics(dd, self.cash)["mdd"], m["mdd"])   # the overlay cuts the loss


if __name__ == "__main__":
    unittest.main()
