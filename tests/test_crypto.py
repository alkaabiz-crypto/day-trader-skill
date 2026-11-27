import unittest

from _load import load

try:
    import numpy as np
    cs = load("trader-lab", "crypto_search")
    sp = load("trader-lab", "sp500_search")
except ImportError:          # numpy is optional (research script only)
    np = None


def coin(n=900, seed=0):
    import datetime
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.02, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.02, n))
    d0 = datetime.date(2018, 1, 1)
    d = [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(n)]
    return {"d": d, "o": o, "h": h, "l": l, "c": c, "v": rng.uniform(1, 3, n), "rf": np.zeros(n)}


@unittest.skipIf(np is None, "numpy not installed")
class Crypto(unittest.TestCase):
    def test_no_condition_looks_ahead(self):
        A = coin()
        full = cs.conditions(A, "BTC-USD")
        k = 700
        cut = cs.conditions({key: v[:k] for key, v in A.items()}, "BTC-USD")
        self.assertEqual(sorted(full), sorted(cut))
        bad = [nm for nm in full if not np.array_equal(full[nm][:k], cut[nm])]
        self.assertEqual(bad, [])

    def test_streaming_gate_matches_the_in_memory_version(self):
        rng = np.random.default_rng(5)
        E = rng.normal(0, 0.01, (300, 800))
        E[17] += 0.002
        whole = sp.reality_check_big(E.astype(np.float32), B=100, seed=3)
        g = cs.StreamingGate(800, B=100, seed=3)
        for a in range(0, 300, 70):
            g.add(E[a:a + 70].astype(np.float32))
        r = g.result()
        for key in ("rc_p", "spa_p", "rw_rejects", "passes"):
            self.assertEqual(r[key], whole[key], key)
        self.assertAlmostEqual(r["best_t"], whole["best_t"], places=4)

    def test_candidate_count_and_directions(self):
        A = coin()
        C = cs.conditions(A, "BTC-USD")
        C = {k: C[k] for k in sorted(C)[:6]}
        rows = list(cs.candidates(A, C))
        counted = sum(1 for _ in cs.candidates(A, C, count_only=True))
        self.assertEqual(len(rows), counted)
        one = [r for r in rows if r[0].startswith("one:")][:3]
        self.assertEqual([r[1]["dir"] for r in one], ["long_when", "long_unless", "short_when"])
        self.assertTrue(np.array_equal(one[2][3], -one[0][3]))
        self.assertTrue(np.array_equal(one[1][3], 1.0 - one[0][3]))


if __name__ == "__main__":
    unittest.main()
