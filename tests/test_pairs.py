import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import pairs as pr  # noqa: E402


class Pairs(unittest.TestCase):
    def setUp(self):
        self.days = ["d%03d" % i for i in range(pr.TRADE)]

    def run_pair(self, a, b, sd=0.01):
        px = {"A": dict(zip(self.days, a)), "B": dict(zip(self.days, b))}
        p = {"a": "A", "b": "B", "base_a": 1.0, "base_b": 1.0, "sd": sd}
        return pr.trade_pair(self.days, px, 0, p, 0.0)

    def test_divergence_then_convergence_makes_money(self):
        n = pr.TRADE
        a = [1.0] * n
        b = [1.0] * n
        b[1:4] = [1.05, 1.05, 1.05]       # B rich: spread -0.05 < -2 sd -> long A, short B, entered at day 2's close
        pnl = self.run_pair(a, b)
        self.assertAlmostEqual(sum(pnl.values()), 0.05 / 1.05, places=6)   # $1 short B from 1.05 to 1.0

    def test_one_day_wait(self):
        n = pr.TRADE
        a = [1.0] * n
        b = [1.0] * n
        b[1] = 1.05                        # diverges for one day only: by the next close it's back, so no P&L
        b[2:] = [1.0] * (n - 2)
        pnl = self.run_pair(a, b)
        self.assertAlmostEqual(sum(pnl.values()), 0.0, places=9)

    def test_costs_charged_per_leg(self):
        n = pr.TRADE
        a, b = [1.0] * n, [1.0] * n
        b[1:4] = [1.05, 1.05, 1.05]
        px = {"A": dict(zip(self.days, a)), "B": dict(zip(self.days, b))}
        p = {"a": "A", "b": "B", "base_a": 1.0, "base_b": 1.0, "sd": 0.01}
        gross = sum(pr.trade_pair(self.days, px, 0, p, 0.0).values())
        net = sum(pr.trade_pair(self.days, px, 0, p, 5.0).values())
        self.assertAlmostEqual(gross - net, 4 * 5 / 1e4, places=9)

    def test_frozen(self):
        self.assertEqual((pr.FORM, pr.TRADE, pr.NPAIRS, pr.ENTRY_SD, pr.COST_BPS, pr.SPLIT, pr.T_BAR, len(pr.UNIVERSE)),
                         (252, 126, 20, 2.0, 5.0, "2015-01-01", 3.0, 60))


if __name__ == "__main__":
    unittest.main()
