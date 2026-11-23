import datetime
import unittest

from _load import load

oil = load("trader-lab", "oil")


def series(closes, opens=None, start="2020-01-06"):
    d0 = datetime.date(*map(int, start.split("-")))
    D = {k: [] for k in "dohlcva"}
    d = d0
    for i, c in enumerate(closes):
        while d.weekday() > 4:
            d += datetime.timedelta(days=1)
        o = opens[i] if opens else c
        D["d"].append(d.isoformat())
        D["o"].append(float(o))
        D["h"].append(float(max(o, c)))
        D["l"].append(float(min(o, c)))
        D["c"].append(float(c))
        D["v"].append(1.0)
        D["a"].append(float(c))
        d += datetime.timedelta(days=1)
    return D


class DCA(unittest.TestCase):
    P = {"drop": 10, "step": 5, "layers": 3, "tp": 5, "max_days": 120}

    def test_ladder_adds_layers_and_takes_profit_on_average_cost(self):
        closes = [100.0] * 25 + [89.0, 84.0, 79.0, 80.0, 90.0, 90.0]
        D = series(closes)
        out, camps = oil.dca(D, self.P, cost_bps=0.0, night_bps=0.0)
        self.assertEqual(len(camps), 1)
        start, end, ret, used = camps[0]
        # first buy at the open after the trigger close: o[26]=84. The next layer needs a close 5% below
        # that FILL (<= 79.8): c[27]=79 -> second layer at o[28]=80. Average 82, profit target 86.1,
        # reached on day 29 (90). The third layer never triggers.
        self.assertEqual((start, end, used), (26, 29, 2))
        self.assertAlmostEqual(ret, (90 / 82.0 - 1) * 1e4)

    def test_marks_use_each_layers_own_fill(self):
        closes = [100.0] * 25 + [89.0, 89.0, 89.0]
        opens = [100.0] * 25 + [89.0, 88.0, 89.0]
        D = series(closes, opens)
        out, _ = oil.dca(D, dict(self.P, max_days=1), cost_bps=0.0, night_bps=0.0)
        # bought at o[26]=88, first day marked 88 -> 89 on one layer of three
        self.assertAlmostEqual(out[D["d"][26]], (89 / 88.0 - 1) * 1e4 / 3)

    def test_costs_and_financing_reduce_the_result(self):
        closes = [100.0] * 25 + [89.0, 84.0, 79.0, 80.0, 90.0, 90.0]
        D = series(closes)
        free = sum(oil.dca(D, self.P, 0.0, 0.0)[0].values())
        paid = sum(oil.dca(D, self.P, 5.0, 1.0)[0].values())
        self.assertLess(paid, free)


class TrackState(unittest.TestCase):
    P = {"drop": 10, "step": 5, "layers": 3, "tp": 5, "max_days": 120}

    def test_open_ladder_and_next_levels(self):
        D = series([100.0] * 25 + [89.0, 84.0, 82.0])
        st = oil.dca_state(D, self.P)
        self.assertTrue(st["open"])
        self.assertEqual(st["layers"], [84.0])
        self.assertAlmostEqual(st["take_profit_close"], 88.2)
        self.assertAlmostEqual(st["next_add_close"], 79.8)
        self.assertEqual(st["action"], "HOLD")

    def test_trigger_today_and_wait(self):
        self.assertIn("BUY", oil.dca_state(series([100.0] * 25 + [89.0]), self.P)["action"])
        self.assertIn("WAIT", oil.dca_state(series([100.0] * 26), self.P)["action"])


class Carry(unittest.TestCase):
    def test_roll_jump_reads_as_contango(self):
        # the front series jumps +2% at a roll (contango); the fund that rolls does not
        fut = series([100.0] * 30 + [102.0] * 10)                  # the jump falls inside the last 21 days
        fund = series([50.0] * 40)
        c = oil.carry_series(fut, fund, Ls=(21,))
        last = fut["d"][-1]
        self.assertAlmostEqual(c[last][21], __import__("math").log(1.02))
        oil.CARRY.clear()
        oil.CARRY[id(fund)] = c
        self.assertEqual(oil.sw_carry(fund, 39, {"L": 21}), 0)     # contango: no long
        oil.CARRY.clear()

    def test_backwardation_goes_long(self):
        fut = series([100.0] * 30 + [98.0] * 10)                    # roll jump down: backwardation
        fund = series([50.0] * 40)
        oil.CARRY.clear()
        oil.CARRY[id(fund)] = oil.carry_series(fut, fund, Ls=(21,))
        self.assertEqual(oil.sw_carry(fund, 39, {"L": 21}), 1)
        self.assertEqual(oil.sw_carry(fund, 39, {"L": 21, "trend": True}), 0)   # fund flat: no trend
        oil.CARRY.clear()


class Rules(unittest.TestCase):
    def test_eia_wednesday_follows_or_fades_tuesday(self):
        D = series([100, 101, 103, 103], opens=[100, 100, 101, 103], start="2020-01-06")  # Mon..Thu
        self.assertEqual(oil.r_wed_eia(D, 2, {"min": 1.0, "mode": "mom"})["side"], 1)     # Tue +1%
        self.assertEqual(oil.r_wed_eia(D, 2, {"min": 1.0, "mode": "rev"})["side"], -1)
        self.assertIsNone(oil.r_wed_eia(D, 3, {"min": 0.0, "mode": "mom"}))               # Thursday

    def test_month_and_tsmom(self):
        D = series([1.0] * 3, start="2020-07-01")
        self.assertTrue(oil.r_month(D, 0, {"months": [7]}))
        self.assertIsNone(oil.r_month(D, 0, {"months": [8]}))
        U = series([float(i) for i in range(1, 30)])
        self.assertEqual(oil.sw_tsmom(U, 25, {"L": 21}), 1)
        self.assertFalse(oil.ex_tsmom(U, 25, {"L": 21}, 0))

    def test_spread_trades_against_a_stretched_spread(self):
        n = 40
        cl = series([100.0] * n, start="2020-01-06")
        wiggle = [105.0 + (0.3 if i % 2 else -0.3) for i in range(n - 2)]   # a normal, noisy spread
        bz = series(wiggle + [110.0, 110.0], opens=wiggle + [110.0, 110.0], start="2020-01-06")
        bz["c"][-1] = 108.9                              # Brent falls back on the last day
        out = oil.spread_rule(cl, bz, {"lb": 20, "z": 1.0}, 0.0)
        last = bz["d"][-1]
        self.assertIn(last, out)
        self.assertGreater(out[last], 0)                 # short Brent / long WTI earned the reversion


if __name__ == "__main__":
    unittest.main()
