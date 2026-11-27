import math
import unittest

from _load import load

try:
    import numpy as np
    us = load("trader-lab", "universe_search")
except ImportError:          # numpy is optional (research script only)
    np = None


@unittest.skipIf(np is None, "numpy not installed")
class Execution(unittest.TestCase):
    def asset(self, o, c):
        o, c = np.array(o, float), np.array(c, float)
        return {"o": o, "c": c, "h": np.maximum(o, c), "l": np.minimum(o, c), "v": np.ones(len(c)),
                "d": ["2020-01-%02d" % (i + 1) for i in range(len(c))]}

    def test_next_open_execution_and_costs(self):
        A = self.asset([10, 10, 11, 12, 12], [10, 10, 12, 12, 12])
        pos = np.array([1, 1, 1, 1, 1], float)            # long from the close of day 0
        r = us.returns_for(A, pos, 0.0, 0.0)
        # day 1: entered at day 1's open (10), session 10 -> 10: 0
        # day 2: overnight 10 -> 11 (+10%), session 11 -> 12 (+9.09%)
        self.assertAlmostEqual(r[1], 0.0)
        self.assertAlmostEqual(r[2], 1.1 * (12 / 11.0) - 1)       # overnight and session compound
        rc = us.returns_for(A, pos, 10.0, 0.0)
        self.assertAlmostEqual(r[1] - rc[1], 0.001)         # 10 bps on the entry day only
        self.assertAlmostEqual(r[2] - rc[2], 0.0)

    def test_always_long_equals_buy_and_hold(self):
        A = self.asset([10, 11, 12, 11, 13], [11, 12, 11, 13, 14])
        bh = us.returns_for(A, np.ones(5), 2.0, 0.0)
        self.assertTrue(np.allclose(bh - us.returns_for(A, np.maximum(np.ones(5), 0), 2.0, 0.0), 0))

    def test_helpers(self):
        st = us.ffill_state(np.array([0, 1, 0, 0, 0], bool), np.array([0, 0, 0, 1, 0], bool))
        self.assertEqual(st.tolist(), [0, 1, 1, 0, 0])
        pos = us.ffill_pos(np.array([0, 1, 0, 0], bool), np.array([0, 0, 0, 1], bool))
        self.assertEqual(pos.tolist(), [0, 1, 1, -1])
        self.assertEqual(us.hold_for(np.array([0, 1, 0, 0, 0], bool), 2).tolist(), [0, 1, 1, 0, 0])
        self.assertEqual(us.delay(np.array([1, -1, -1, -1, 1], float), 3).tolist(), [0, 0, 0, -1, -1])
        self.assertAlmostEqual(us.z_bonferroni(1), 1.95996, places=3)


@unittest.skipIf(np is None, "numpy not installed")
class EntryExit(unittest.TestCase):
    def asset(self, o, h, l, c):
        return {"o": np.array(o, float), "h": np.array(h, float), "l": np.array(l, float),
                "c": np.array(c, float), "v": np.ones(len(c)), "d": ["2020-01-%02d" % (i + 1) for i in range(len(c))]}

    def test_take_profit_stop_and_time_exit(self):
        A = self.asset([100, 100, 101, 102, 103], [100, 101, 104, 103, 104], [100, 99, 100, 101, 102],
                       [100, 100, 103, 102, 103])
        ev = np.array([1, 0, 0, 0, 0], bool)                       # signal at day 0's close -> enter day 1's open (100)
        pos, ex = us.trade_path(A, ev, 0.03, 0.05, 10)
        self.assertEqual(pos.tolist(), [0, 1, 1, 0, 0])            # +3% target 103 hit on day 2 (high 104)
        self.assertEqual(ex, {2: 103.0})
        pos, ex = us.trade_path(A, ev, None, 0.005, 10)            # 0.5% stop at 99.5: day 1's low 99 hits it
        self.assertEqual(ex, {1: 99.5})
        pos, ex = us.trade_path(A, ev, None, None, 2)              # time stop: out at day 2's close
        self.assertEqual(pos.tolist(), [0, 1, 1, 0, 0])
        self.assertEqual(ex, {})

    def test_both_touched_counts_the_stop(self):
        A = self.asset([100, 100, 100], [100, 110, 100], [100, 90, 100], [100, 100, 100])
        pos, ex = us.trade_path(A, np.array([1, 0, 0], bool), 0.05, 0.05, 5)
        self.assertEqual(ex, {1: 95.0})

    def test_returns_with_an_intraday_exit(self):
        A = self.asset([100, 100, 101, 102], [100, 101, 104, 103], [100, 99, 100, 101], [100, 100, 103, 102])
        pos, ex = us.trade_path(A, np.array([1, 0, 0, 0], bool), 0.03, None, 10)
        r = us.returns_exit(A, pos, ex, 0.0, 0.0)
        self.assertAlmostEqual(r[1], 0.0)                          # 100 -> 100 on day 1
        self.assertAlmostEqual(r[2], 1.01 * (103 / 101.0) - 1)    # overnight then open-to-target, compounded
        self.assertAlmostEqual(r[3], 0.0)
        self.assertAlmostEqual(float(np.prod(1 + r)) , 1.01 * 103 / 101.0)


@unittest.skipIf(np is None, "numpy not installed")
class RealityCheck(unittest.TestCase):
    def test_noise_is_not_significant_and_a_real_edge_is(self):
        rng = np.random.default_rng(1)
        noise = rng.normal(0, 0.01, (200, 1500))
        r = us.reality_check(noise, B=200)
        self.assertGreater(r["rc_p"], 0.2)
        self.assertGreater(r["spa_p"], 0.05)
        edge = noise.copy()
        edge[7] += 0.002                                   # one rule with a 20 bp/day edge (t ~ 7.7)
        r = us.reality_check(edge, B=200)
        self.assertLess(r["rc_p"], 0.01)
        self.assertLess(r["spa_p"], 0.01)


@unittest.skipIf(np is None, "numpy not installed")
class GateCalibration(unittest.TestCase):
    """Rules that are on/off copies of one fat-tailed, volatility-clustered market at very different
    leverage, with signals unrelated to the returns: the gate must rarely pass, and must pass a real edge."""

    def rules(self, seed, M=150, n=1200):
        rng = np.random.default_rng(seed)
        vol = np.exp(np.convolve(rng.normal(0, 0.25, n + 50), np.ones(50) / 7.0, "valid")[:n])
        f = 0.01 * vol * rng.standard_t(3, n) / math.sqrt(3)
        f -= f.mean()
        lev = np.exp(rng.uniform(np.log(0.3), np.log(5), M))
        on = np.cumsum(rng.random((M, n)) < 0.05, axis=1) % 2              # persistent on/off signals
        return lev[:, None] * on * f[None, :]

    def test_null_rarely_passes_and_an_edge_does(self):
        passes = 0
        for seed in range(10):
            r = us.reality_check(self.rules(seed), B=200, seed=seed)
            passes += r["passes"]
        self.assertLessEqual(passes, 1)
        E = self.rules(99)
        E[5] += 0.004                                                       # a real 40 bp/day edge
        r = us.reality_check(E, B=200)
        self.assertTrue(r["passes"])
        self.assertGreaterEqual(r["rw_rejects"], 1)


@unittest.skipIf(np is None, "numpy not installed")
class BigRealityCheck(unittest.TestCase):
    def test_prefix_sum_version_agrees_on_noise_and_edge(self):
        sp = load("trader-lab", "sp500_search")
        rng = np.random.default_rng(3)
        noise = rng.normal(0, 0.01, (300, 1500)).astype(np.float32)
        r = sp.reality_check_big(noise, B=200)
        self.assertGreater(r["rc_p"], 0.2)
        edge = noise.copy()
        edge[11] += 0.002
        r = sp.reality_check_big(edge, B=200)
        self.assertLess(r["rc_p"], 0.01)
        self.assertLess(r["spa_p"], 0.01)
        self.assertTrue(r["passes"])


if __name__ == "__main__":
    unittest.main()
