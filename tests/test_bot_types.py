import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import bot_types as bt  # noqa: E402

DAY = 86400


def bars(prices, start=1700000000):
    """One candle a day; each tuple is (o, h, l, c)."""
    return [(start + i * DAY, o, h, l, c) for i, (o, h, l, c) in enumerate(prices)]


class Dca(unittest.TestCase):
    def test_take_profit_after_a_dip_buy(self):
        b = bars([(100, 100, 100, 100), (100, 100, 97.5, 98), (98, 101.5, 98, 101), (101, 101, 101, 101)])
        path, n = bt.run_dca(b, fee=0.0)
        self.assertEqual(n, 1)                      # bought at 100 and 98, sold at 2% over the 99 average
        self.assertGreater(path[2][1], 500)

    def test_stop_loss(self):
        b = bars([(100, 100, 100, 100), (100, 100, 80, 82)])
        path, n = bt.run_dca(b, fee=0.0)
        self.assertEqual(n, 1)
        self.assertLess(path[-1][1], 500 - 50)      # all 5 buys filled, then out at the 85 stop


class Grid(unittest.TestCase):
    def test_round_trip_earns_one_level(self):
        b = bars([(100, 100, 100, 100), (100, 100, 96, 97), (97, 99.9, 97, 99), (99, 99, 99, 99)])
        path, n = bt.run_grid(b, fee=0.0)
        self.assertGreaterEqual(n, 2)
        self.assertGreater(path[-1][1], 500)        # bought low, sold one level up, nothing else moved


class Judge(unittest.TestCase):
    def test_frozen(self):
        self.assertEqual((bt.SPLIT, bt.T_BAR, bt.FEE), ("2024-01-01", 3.0, 0.001))
        self.assertEqual(bt.DCA["steps"], [0.02, 0.04, 0.06, 0.08])


if __name__ == "__main__":
    unittest.main()
