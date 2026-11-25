import unittest

import numpy as np

from _load import load

dtc = load("trader-lab", "dtc_btc")


class Ribbon(unittest.TestCase):
    def test_up_and_down(self):
        up_c = np.linspace(100, 300, 200)
        up, dn = dtc.ribbon(up_c)
        self.assertTrue(up[-1])
        self.assertFalse(dn[-1])
        self.assertFalse(up[10])                    # still warming up
        up, dn = dtc.ribbon(up_c[::-1].copy())
        self.assertTrue(dn[-1])
        p = dtc.positions(up_c[::-1].copy())
        self.assertEqual(p["dtc_long_flat"][-1], 0.0)
        self.assertEqual(p["dtc_long_short"][-1], -1.0)


class Costs(unittest.TestCase):
    def test_spread_swap_and_next_open(self):
        o = np.array([100.0, 100.0, 110.0, 110.0, 110.0])
        ts = np.array([0.0, 86400, 2 * 86400, 3 * 86400, 4 * 86400])
        net, mkt = dtc.returns(o, ts, [1.0, 1.0, 0.0, 0.0, 0.0])
        self.assertAlmostEqual(mkt[0], 0.10)
        self.assertAlmostEqual(net[0], 0.10 - 0.0003 - 0.0003)     # half spread on entry, one night
        self.assertAlmostEqual(net[2], 0.0 - 0.0003)               # half spread on exit


if __name__ == "__main__":
    unittest.main()
