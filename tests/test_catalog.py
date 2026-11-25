import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import catalog as cg  # noqa: E402


def market(n=600, drift=0.0005, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(drift + 0.01 * rng.standard_normal(n)))
    o = c * (1 + 0.002 * rng.standard_normal(n))
    h = np.maximum(o, c) * 1.005
    l = np.minimum(o, c) * 0.995
    d = ["2010-%02d-%02d" % (1 + (i // 28) % 12, 1 + i % 28) for i in range(n)]
    return {"o": o, "h": h, "l": l, "c": c, "v": np.full(n, 1e6), "d": d, "month": np.array([int(x[5:7]) for x in d])}


class Indicators(unittest.TestCase):
    def test_sma_ema_rsi(self):
        x = np.arange(1.0, 11.0)
        self.assertAlmostEqual(cg.sma(x, 3)[-1], 9.0)
        self.assertTrue(np.isnan(cg.sma(x, 3)[1]))
        self.assertAlmostEqual(cg.ema(np.ones(5), 3)[-1], 1.0)
        self.assertGreater(cg.rsi(x, 3)[-1], 99)                 # only up moves

    def test_latch(self):
        e = np.array([0, 1, 0, 0, 0], bool)
        x = np.array([0, 0, 0, 1, 0], bool)
        self.assertEqual(cg.latch(e, x).tolist(), [False, True, True, False, False])

    def test_no_look_ahead(self):
        D = market()
        S = cg.build(D)
        D2 = {k: (v[:400] if hasattr(v, "__len__") else v) for k, v in D.items()}
        S2 = cg.build(D2)
        for name in S:
            self.assertEqual(S[name][1][:400].tolist(), S2[name][1].tolist(), name)   # past positions never change

    def test_catalog_size_and_fills(self):
        S = cg.build(market())
        self.assertGreaterEqual(len(S), 55)
        D = market()
        net, mkt = cg.strategy_returns(D, np.ones(len(D["c"]), bool), 0.0)
        self.assertAlmostEqual(mkt[0], D["o"][2] / D["o"][1] - 1)  # the day-0 decision earns open 1 -> open 2


if __name__ == "__main__":
    unittest.main()
