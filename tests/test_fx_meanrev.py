import unittest

import numpy as np

from _load import load

mr = load("trader-lab", "fx_meanrev")


class Signals(unittest.TestCase):
    def bars(self, closes):
        return np.array([[3600 * i, c, c * 1.001, c * 0.999, c] for i, c in enumerate(closes)], float)

    def test_rsi_buy_after_a_fall_and_sell_after_a_rise(self):
        flat = [100 + (0.5 if i % 2 else -0.5) for i in range(20)]
        up = [100 + i for i in range(1, 16)]
        down = [up[-1] - 3 * i for i in range(1, 15)]
        b, s, _ = mr.signals(self.bars(flat + up + down), "rsi_bot")
        self.assertTrue(b[35:].any())               # the fall makes a new buy (buy low)
        self.assertTrue(s[20:35].any())             # the steady rise makes a new sell (sell high)
        self.assertEqual(int(b.sum()), 1)          # only the crossing bar, not every oversold bar

    def test_band_signal_and_mean(self):
        c = [100.0 + (0.1 if i % 2 else -0.1) for i in range(40)] + [95.0]
        b, s, sma = mr.signals(self.bars(c), "band_mean")
        self.assertTrue(b[-1])
        self.assertAlmostEqual(sma[-2], 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
